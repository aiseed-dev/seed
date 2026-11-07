# SPDX-License-Identifier: AGPL-3.0-or-later
"""門のテスト: 相手ごとの token の台帳（ハッシュ、範囲、期限、取り消し）と、誰が何をしたかの記録。"""

import datetime as dt
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kagi import audit
from seed import cli
from seed import lookup as L
from seed.records import Line, Public
from seed.server import gate
from seed.server import publish as P
from seed.server.main import create_app
from seed.server.settings import Settings

TOKEN = "t" * 32  # 持ち主の token（公開の書き直し用。門の token とは別）
INVITE = "inv-test-code-1234"
TODAY = dt.date(2026, 11, 6)
RID = "2026-11-06-yoshino-ai-1"


def _public() -> str:
    p = Public(
        id=RID, place="徳島県 吉野川市", since="2026-11-06", name="にじ", word="草が伸びた。", language="ja"
    )
    p.days["2026-11-06"] = [Line("overall", "草が大半", 0.8, "right"), Line("did", "見ただけ")]
    return p.render()


PUBLIC = _public()


@pytest.fixture(autouse=True)
def no_fieldnotes(monkeypatch):
    monkeypatch.setattr(L, "_load", lambda: None)
    L.clear_cache()
    yield
    L.clear_cache()


@pytest.fixture
def ledger(tmp_path) -> Path:
    return tmp_path / "etc" / "tokens.json"


@pytest.fixture
def keyfile(tmp_path, monkeypatch) -> Path:
    k = tmp_path / "log-key"
    k.write_bytes(b"gate-test-key-not-a-secret-000")
    os.chmod(k, 0o600)
    monkeypatch.setenv("KAGI_LOG_KEY_FILE", str(k))
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    return k


def make(tmp_path, ledger, audit_path=None, **kw) -> Settings:
    return Settings(
        api_key="test-key",  # 読みの口が門まで進むように（Claude は呼ばれない。門で断るので）
        public_dir=tmp_path / "public",
        daily_usd=20.0,
        daily_reads=200,
        per_token_reads=10,
        per_ip_reads=20,
        model="claude-opus-5-5",
        skill_dir=tmp_path / "no-skill",
        invites={INVITE: "てすと"},
        open=False,
        tokens_path=ledger,
        audit_path=audit_path,
        **kw,
    )


# ---- 台帳


def test_ledger_keeps_only_the_hash(ledger):
    code = gate.add(ledger, "買い手 A", ["buyer"], 30, "直売の客", TODAY)
    text = ledger.read_text()
    assert code not in text and gate.code_hash(code) in text
    assert oct(ledger.stat().st_mode & 0o777) == "0o600"
    (row,) = gate.rows(ledger, TODAY)
    assert row == {
        "name": "買い手 A",
        "scope": ["buyer"],
        "created": "2026-11-06",
        "expires": "2026-12-06",
        "state": "live",
        "revoked": "",
        "note": "直売の客",
    }
    assert "sha256" not in row
    book = gate.TokenBook(ledger)
    assert book.find(code, TODAY)[0]["name"] == "買い手 A"
    assert book.find(code, dt.date(2026, 12, 7)) == (None, "expired")
    assert book.find("x" * 24, TODAY) == (None, "unknown")


def test_ledger_rules(ledger):
    gate.add(ledger, "a", ["member"], 90, today=TODAY)
    for args, msg in (
        (("a", ["member"], 90), "もうある"),
        (("", ["member"], 90), "呼び名"),
        (("b", ["root"], 90), "範囲"),
        (("b", [], 90), "範囲"),
        (("b", ["member"], 0), "期限"),
    ):
        with pytest.raises(gate.GateError, match=msg):
            gate.add(ledger, *args, today=TODAY)
    assert gate.revoke(ledger, "a", TODAY) == 1
    with pytest.raises(gate.GateError, match="無い"):
        gate.revoke(ledger, "a", TODAY)
    # 取り消しても行は残る。取り消した後は同じ呼び名で出し直せる
    gate.add(ledger, "a", ["member"], 90, today=TODAY)
    assert [r["state"] for r in gate.rows(ledger, TODAY)] == ["revoked", "live"]
    # token そのものの欄がある台帳は読まない
    ledger.write_text(json.dumps({"tokens": [{"name": "x", "sha256": "0", "scope": [], "token": "plain"}]}))
    with pytest.raises(gate.GateError, match="ハッシュだけ"):
        gate.load(ledger)
    # 期限の無い物は生きていない側に
    assert gate.state({"name": "x"}, TODAY) == "expired"


def test_other_apps_tokens_do_not_open_seed(ledger):
    code = gate.add(ledger, "fieldnotes の客", ["member"], 30, today=TODAY, app="fieldnotes")
    assert gate.TokenBook(ledger).find(code, TODAY) == (None, "unknown")
    assert gate.rows(ledger, TODAY) == []


# ---- 門


def connect(c, code):
    return c.post(
        "/api/connect",
        json={"to": "2026-11-06-yoshino-ai-1", "from": "x", "word": "買いたい", "invite": code},
    )


def publish(c, code):
    return c.post("/api/publish", json={"token": TOKEN, "markdown": PUBLIC, "invite": code})


def test_scopes_at_the_gate(tmp_path, ledger):
    member = gate.add(ledger, "仲間", ["member"], 90)
    buyer = gate.add(ledger, "買い手", ["buyer"], 30)
    c = TestClient(create_app(make(tmp_path, ledger)))

    # 招待コードの一覧の人は今まで通り
    assert publish(c, INVITE).status_code == 200
    # member の token は招待コードと同じに通る
    assert publish(c, member).status_code == 200
    assert c.get("/api/lookup", params={"lat": 34.0, "lon": 134.0, "invite": member}).status_code == 200
    # buyer は一言だけ。読み、公開、取り下げ、照会は断る
    assert connect(c, buyer).status_code == 200
    for r in (
        publish(c, buyer),
        c.get("/api/lookup", params={"lat": 34.0, "lon": 134.0, "invite": buyer}),
        c.post(
            "/api/read",
            data={"token": TOKEN, "invite": buyer},
            files=[("photos", ("a.jpg", b"\xff\xd8\xff", "image/jpeg"))],
        ),
        c.request("DELETE", "/api/publish/2026-11-06-yoshino-ai-1", json={"token": TOKEN, "invite": buyer}),
    ):
        assert r.status_code == 403 and r.json()["reason"] == "scope", r.text
    # 知らない物、無い物
    assert connect(c, "nope").json()["reason"] == "unknown"
    assert connect(c, None).json()["reason"] == "missing"
    for r in (connect(c, "nope"), connect(c, None)):
        assert r.status_code == 403 and r.json()["error"] == "invite_required"


def test_revoke_and_expiry_take_effect_on_the_next_request(tmp_path, ledger):
    buyer = gate.add(ledger, "買い手", ["buyer"], 30)
    old = gate.add(ledger, "去年の人", ["member"], 1, today=dt.date(2025, 1, 1))
    c = TestClient(create_app(make(tmp_path, ledger)))
    publish(c, INVITE)
    assert connect(c, buyer).status_code == 200
    gate.revoke(ledger, "買い手")
    r = connect(c, buyer)
    assert r.status_code == 403 and r.json()["reason"] == "revoked"
    r = publish(c, old)
    assert r.status_code == 403 and r.json()["reason"] == "expired"
    # 台帳が無くなれば閉じる側に
    ledger.unlink()
    assert connect(c, buyer).json()["reason"] == "unknown"
    assert publish(c, INVITE).status_code == 200  # 招待コードの一覧は別


# ---- 記録


def test_journal_records_who_did_what_without_codes(tmp_path, ledger, keyfile):
    log = tmp_path / "audit" / "audit.log"
    buyer = gate.add(ledger, "買い手", ["buyer"], 30)
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    assert c.get("/health").json()["audit"] == "on"
    publish(c, INVITE)
    connect(c, buyer)
    publish(c, buyer)
    connect(c, "wrong-code-zzzz")
    recs = [json.loads(ln) for ln in log.read_text().splitlines()]
    assert [(r["actor"], r["action"], r["detail"]) for r in recs] == [
        ("てすと", "publish", "通した"),
        ("買い手", "connect", "2026-11-06-yoshino-ai-1"),
        ("?", "publish", "断った: scope"),
        ("?", "connect", "断った: unknown 2026-11-06-yoshino-ai-1"),
    ]
    text = log.read_text()
    for secret in (INVITE, buyer, "wrong-code-zzzz", TOKEN):
        assert secret not in text
    n, fails = audit.verify(log, audit.find_key())  # kagi log verify と同じ確かめ
    assert n == 4 and not fails
    # 一行消すと落ちる
    log.write_text("\n".join(text.splitlines()[1:]) + "\n")
    assert audit.verify(log, audit.find_key())[1]


def test_journal_notes_a_lockout_without_codes(tmp_path, ledger, keyfile):
    log = tmp_path / "audit.log"
    c = TestClient(
        create_app(make(tmp_path, ledger, log, gate_tries=3))
    )  # 数は Settings（SEED_GATE_TRIES）で変わる
    for n in range(3):
        assert connect(c, f"wrong-code-{n}").status_code == 403
    assert connect(c, INVITE).status_code == 429
    recs = [json.loads(ln) for ln in log.read_text().splitlines()]
    stops = [r for r in recs if r["detail"].startswith("止めた")]
    assert len(stops) == 1 and "3 回" in stops[0]["detail"]
    text = log.read_text()
    for secret in (INVITE, "wrong-code-0", "wrong-code-2"):
        assert secret not in text
    assert not audit.verify(log, audit.find_key())[1]


def test_journal_off_without_key_or_path(tmp_path, ledger, monkeypatch):
    monkeypatch.delenv("KAGI_LOG_KEY_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    log = tmp_path / "audit.log"
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    assert c.get("/health").json()["audit"] == "off"
    assert publish(c, INVITE).status_code == 200 and not log.exists()
    assert TestClient(create_app(make(tmp_path, ledger))).get("/health").json()["audit"] == "off"


def test_journal_error_is_visible_and_does_not_stop_requests(tmp_path, ledger, keyfile):
    log = tmp_path / "audit.log"
    log.write_text("これは記録の行ではない\n")
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    assert publish(c, INVITE).status_code == 200
    assert c.get("/health").json()["audit"] == "error"


# ---- 命令


def test_cli_token(ledger, capsys, tmp_path):
    base = ["--folder", str(tmp_path / "seed"), "token"]
    assert (
        cli.main([*base, "add", "買い手 B", "--scope", "buyer", "--days", "14", "--file", str(ledger)]) == 0
    )
    out = capsys.readouterr()
    code = out.out.strip()
    assert len(code) >= 24 and "\n" not in code  # 標準出力は token の一行だけ
    assert "一度だけ" in out.err and code not in out.err
    assert code not in ledger.read_text()
    assert cli.main([*base, "list", "--file", str(ledger)]) == 0
    listed = capsys.readouterr().out
    assert "買い手 B" in listed and "buyer" in listed and "生きている" in listed and code not in listed
    assert cli.main([*base, "add", "買い手 B", "--file", str(ledger)]) == 1
    assert cli.main([*base, "revoke", "買い手 B", "--file", str(ledger)]) == 0
    assert cli.main([*base, "list", "--file", str(ledger)]) == 0
    assert "取り消した" in capsys.readouterr().out
    assert gate.TokenBook(ledger).find(code) == (None, "revoked")


# ---- 管理の口（動かす人。範囲 admin）


def hdr(code):
    return {"X-Seed-Invite": code} if code else {}


def test_admin_scope_and_whoami(tmp_path, ledger):
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    member = gate.add(ledger, "仲間", ["member"], 90)
    c = TestClient(create_app(make(tmp_path, ledger)))
    assert c.get("/api/whoami", headers=hdr(admin)).json() == {"name": "動かす人", "scopes": ["admin"]}
    assert c.get("/api/whoami", headers=hdr(INVITE)).json() == {"name": "てすと", "scopes": ["member"]}
    assert c.get("/api/whoami").status_code == 403
    # admin は member の事も全部できる
    assert publish(c, admin).status_code == 200
    # 管理の口は admin だけ
    for path in ("/api/admin/overview", "/api/admin/tokens", "/api/admin/audit", "/api/admin/records"):
        assert c.get(path, headers=hdr(admin)).status_code == 200, path
        for code in (member, INVITE, None, "nope"):
            assert c.get(path, headers=hdr(code)).status_code == 403, (path, code)
    assert c.post("/api/admin/tokens", json={"name": "x"}, headers=hdr(member)).status_code == 403
    assert c.request("DELETE", f"/api/admin/records/{RID}", headers=hdr(member)).status_code == 403


def test_admin_issues_and_revokes_tokens(tmp_path, ledger):
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    c = TestClient(create_app(make(tmp_path, ledger)))
    publish(c, admin)
    body = {"name": "買い手 C", "scope": "buyer", "days": 14, "note": "直売"}
    r = c.post("/api/admin/tokens", json=body, headers=hdr(admin))
    assert r.status_code == 200, r.text
    code = r.json()["token"]
    assert code not in ledger.read_text()  # 台帳にはハッシュだけ
    assert connect(c, code).status_code == 200 and publish(c, code).status_code == 403
    rows = c.get("/api/admin/tokens", headers=hdr(admin)).json()["tokens"]
    assert [(t["name"], t["scope"], t["state"]) for t in rows] == [
        ("動かす人", ["admin"], "live"),
        ("買い手 C", ["buyer"], "live"),
    ]
    assert "sha256" not in rows[0]
    # 同じ呼び名は二重に出せない。範囲に無い語も通さない
    for bad in ({"name": "買い手 C"}, {"name": "y", "scope": "root"}, {"name": "", "scope": "buyer"}):
        assert c.post("/api/admin/tokens", json=bad, headers=hdr(admin)).status_code == 400
    r = c.post("/api/admin/tokens/revoke", json={"name": "買い手 C"}, headers=hdr(admin))
    assert r.json() == {"revoked": 1}
    assert connect(c, code).json()["reason"] == "revoked"
    assert (
        c.post("/api/admin/tokens/revoke", json={"name": "買い手 C"}, headers=hdr(admin)).status_code == 400
    )
    o = c.get("/api/admin/overview", headers=hdr(admin)).json()
    assert (
        o["records"] == 1
        and o["tokens"] == {"live": 1, "expired": 0, "revoked": 1, "expiring": 0}
        and o["invites"] == 1
    )


def test_admin_reads_the_journal_and_withdraws(tmp_path, ledger, keyfile):
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    log = tmp_path / "audit" / "audit.log"
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    publish(c, INVITE)
    connect(c, "wrong-code-zzzz")
    recs = c.get("/api/admin/records", headers=hdr(admin)).json()["records"]
    assert [r["id"] for r in recs] == [RID]
    r = c.request("DELETE", f"/api/admin/records/{RID}", headers=hdr(admin))
    assert r.json() == {"id": RID, "withdrawn": True}
    assert c.get("/api/admin/records", headers=hdr(admin)).json()["records"] == []
    assert c.get(f"/public/{RID}.md").status_code == 404
    assert c.request("DELETE", f"/api/admin/records/{RID}", headers=hdr(admin)).status_code == 404
    a = c.get("/api/admin/audit", headers=hdr(admin)).json()
    assert a["state"] == "on" and a["verified"] is True
    seen = [(x["actor"], x["action"], x["detail"]) for x in a["lines"]]
    assert ("動かす人", "admin.withdraw", RID) in seen and ("?", "connect", f"断った: unknown {RID}") in seen
    assert seen[0][1] == "admin.audit"  # 新しい物が先。見た事も残る
    assert set(a["lines"][0]) == {"seq", "ts", "actor", "action", "detail"}  # 署名とハッシュは返さない
    for secret in (admin, INVITE, "wrong-code-zzzz"):
        assert secret not in log.read_text()
    # 記録を書き換えると、管理の画面に出る
    log.write_text(log.read_text().replace("断った: unknown", "通した", 1))
    assert c.get("/api/admin/audit", headers=hdr(admin)).json()["verified"] is False


# ---- 受け付けを止める、全部取り消す、気を付ける事の数（設計書 §5.10）


def _read(c, code):
    return c.post(
        "/api/read",
        data={"token": TOKEN, "invite": code},
        files=[("photos", ("a.jpg", b"\xff\xd8\xff", "image/jpeg"))],
    )


def _identify(c, code):
    return c.post(
        "/api/identify",
        data={"token": TOKEN, "invite": code},
        files=[("photos", ("a.jpg", b"\xff\xd8\xff", "image/jpeg"))],
    )


def test_pause_closes_the_paid_and_public_doors_only(tmp_path, ledger, keyfile, monkeypatch):
    monkeypatch.setenv("PLANTNET_API_KEY", "plantnet-test-key-not-real")
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    log = tmp_path / "audit" / "audit.log"
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    assert publish(c, INVITE).status_code == 200
    assert c.get("/health").json()["paused"] is False
    r = c.post("/api/admin/pause", json={"paused": True}, headers=hdr(admin))
    assert r.status_code == 200 and r.json() == {"paused": True}
    assert (ledger.parent / "paused").exists()  # 印は台帳の隣
    assert c.get("/health").json()["paused"] is True
    assert c.get("/api/admin/overview", headers=hdr(admin)).json()["paused"] is True

    # 断る: 公開、一言、写真の読み取り、草の名
    for r in (publish(c, INVITE), connect(c, INVITE), _read(c, INVITE), _identify(c, INVITE)):
        assert r.status_code == 503, r.text
        assert r.json()["error"] == "paused" and r.json()["reason"] == "paused"
    # 通す: 管理、whoami、health、公開の頁、本人の取り下げ、土地の照会
    assert c.get("/api/whoami", headers=hdr(admin)).status_code == 200
    assert c.get("/health").status_code == 200
    assert c.get(f"/public/{RID}.md").status_code == 200
    assert c.get("/").status_code == 200
    assert c.get("/api/lookup", params={"lat": 34.0, "lon": 134.0, "invite": INVITE}).status_code == 200
    assert c.get("/api/admin/records", headers=hdr(admin)).status_code == 200
    r = c.request("DELETE", f"/api/publish/{RID}", json={"token": TOKEN, "invite": INVITE})
    assert r.status_code == 200 and r.json()["withdrawn"] is True

    # 再起動を模す（新しく作り直しても、印のファイルで止めたまま）
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    assert c.get("/health").json()["paused"] is True and publish(c, INVITE).status_code == 503
    assert c.post("/api/admin/pause", json={"paused": False}, headers=hdr(admin)).json() == {"paused": False}
    assert publish(c, INVITE).status_code == 200 and not (ledger.parent / "paused").exists()

    # 止める・再開するは admin だけ。記録に一行ずつ
    assert c.post("/api/admin/pause", json={"paused": True}, headers=hdr(INVITE)).status_code == 403
    assert c.get("/health").json()["paused"] is False
    acts = [
        (x["actor"], x["action"], x["detail"])
        for x in c.get("/api/admin/audit", headers=hdr(admin)).json()["lines"]
    ]
    assert ("動かす人", "admin.pause", "通した") in acts and ("動かす人", "admin.resume", "通した") in acts
    assert ("?", "admin.pause", "断った: scope") in acts
    assert sum(1 for a in acts if a[1] == "admin.pause") == 2  # 通した一行と断った一行。二重には書かない


def test_pause_without_ledger_place_says_cannot(tmp_path, ledger, monkeypatch):
    no_place = make(tmp_path, None)
    assert no_place.pause_path is None and no_place.paused() is False
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    s = make(tmp_path, ledger)
    c = TestClient(create_app(s))
    monkeypatch.setattr(Settings, "pause_path", property(lambda self: None))
    r = c.post("/api/admin/pause", json={"paused": True}, headers=hdr(admin))
    assert r.status_code == 503 and r.json()["error"] == "no_ledger"
    assert c.get("/health").json()["paused"] is False


def test_revoke_all_keeps_the_pressers_token(tmp_path, ledger, keyfile):
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    member = gate.add(ledger, "仲間", ["member"], 90)
    buyer = gate.add(ledger, "買い手", ["buyer"], 30)
    other = gate.add(ledger, "もう一人の動かす人", ["admin"], 90)
    gate.revoke(ledger, "買い手")
    log = tmp_path / "audit" / "audit.log"
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    assert c.post("/api/admin/tokens/revoke_all", headers=hdr(member)).status_code == 403
    r = c.post("/api/admin/tokens/revoke_all", headers=hdr(admin))
    assert r.status_code == 200 and r.json() == {"revoked": 2}  # 仲間ともう一人。取り消し済みは数えない
    states = {t["name"]: t["state"] for t in c.get("/api/admin/tokens", headers=hdr(admin)).json()["tokens"]}
    assert states == {
        "動かす人": "live",
        "仲間": "revoked",
        "買い手": "revoked",
        "もう一人の動かす人": "revoked",
    }
    assert connect(c, member).json()["reason"] == "revoked"
    assert c.get("/api/whoami", headers=hdr(other)).status_code == 403
    assert c.get("/api/whoami", headers=hdr(admin)).status_code == 200
    # 二度目は 0 件（誤りにしない）
    assert c.post("/api/admin/tokens/revoke_all", headers=hdr(admin)).json() == {"revoked": 0}
    acts = [
        (x["actor"], x["action"], x["detail"])
        for x in c.get("/api/admin/audit", headers=hdr(admin)).json()["lines"]
    ]
    assert [a for a in acts if a[1] == "admin.token_revoke_all"] == [
        ("動かす人", "admin.token_revoke_all", "0 件"),
        ("動かす人", "admin.token_revoke_all", "2 件"),
        ("?", "admin.token_revoke_all", "断った: scope"),
    ]
    for secret in (admin, member, buyer, other):
        assert secret not in log.read_text()


def test_overview_counts_denied_expiring_and_keys(tmp_path, ledger, keyfile, monkeypatch):
    monkeypatch.delenv("PLANTNET_API_KEY", raising=False)
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    gate.add(ledger, "すぐ切れる人", ["member"], gate.EXPIRING_DAYS)
    gate.add(ledger, "明日切れる人", ["buyer"], 1)
    gate.add(ledger, "まだ先の人", ["member"], gate.EXPIRING_DAYS + 1)
    log = tmp_path / "audit" / "audit.log"
    c = TestClient(create_app(make(tmp_path, ledger, log)))
    for _ in range(3):
        connect(c, "wrong-code-zzzz")
    publish(c, None)
    publish(c, INVITE)  # 通した物は数えない
    o = c.get("/api/admin/overview", headers=hdr(admin)).json()
    assert o["denied_today"] == 4
    assert o["tokens"]["expiring"] == 2 and o["tokens"]["live"] == 4
    assert o["keys"] == {"claude": True, "plantnet": False}  # 在るか無いかだけ
    assert "test-key" not in json.dumps(o)
    monkeypatch.setenv("PLANTNET_API_KEY", "plantnet-test-key-not-real")
    o = c.get("/api/admin/overview", headers=hdr(admin)).json()
    assert o["keys"]["plantnet"] is True and "plantnet-test-key-not-real" not in json.dumps(o)
    # 昨日の断った行は数えない
    assert settings_of(c).journal.denied_today(TODAY - dt.timedelta(days=3650)) == 0


def test_denied_today_is_zero_without_a_journal(tmp_path, ledger, monkeypatch):
    monkeypatch.delenv("KAGI_LOG_KEY_FILE", raising=False)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    c = TestClient(create_app(make(tmp_path, ledger, tmp_path / "audit.log")))
    connect(c, "wrong-code-zzzz")
    assert c.get("/api/admin/overview", headers=hdr(admin)).json()["denied_today"] == 0


def settings_of(c) -> Settings:
    return c.app.state.settings


def test_client_turns_paused_into_words(tmp_path, ledger):
    import httpx

    from seed.app.strings import error_text
    from seed.client import Client, ClientError

    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    gate.add(ledger, "仲間", ["member"], 90)
    tc = TestClient(create_app(make(tmp_path, ledger)))

    def handler(request: httpx.Request) -> httpx.Response:
        r = tc.request(
            request.method, request.url.raw_path.decode(), content=request.content, headers=request.headers
        )
        return httpx.Response(r.status_code, content=r.content, headers=r.headers)

    assert tc.post("/api/admin/pause", json={"paused": True}, headers=hdr(admin)).json() == {"paused": True}
    with Client("http://seed.test", TOKEN, "ja", transport=httpx.MockTransport(handler), invite=admin) as cl:
        with pytest.raises(ClientError) as e:
            cl.publish(PUBLIC)
        assert e.value.word == "server_paused"
        assert error_text(e.value, "ja") == "今、受け付けを止めています。"


# ---- 公開された記録の管理（公開した人、日、寄せられた一言を見る・消す）


def _public_as(rid: str, name: str) -> str:
    p = Public(id=rid, place="徳島県", since="2026-11-06", name=name, word="見本", language="ja")
    p.days["2026-11-06"] = [Line("overall", "草が大半", 0.8)]
    return p.render()


def test_admin_records_show_owner_date_and_words(tmp_path, ledger, keyfile):
    admin = gate.add(ledger, "動かす人", ["admin"], 90)
    member = gate.add(ledger, "仲間", ["member"], 90)
    buyer = gate.add(ledger, "買い手", ["buyer"], 30)
    log = tmp_path / "audit" / "audit.log"
    c = TestClient(create_app(make(tmp_path, ledger, log, public_url="https://seed.example")))
    other = "u" * 32  # 二人目の持ち主の token（見本）
    assert publish(c, INVITE).status_code == 200  # 招待コードの人
    r = c.post(
        "/api/publish", json={"token": other, "markdown": _public_as("2026-11-06-x-1", "x"), "invite": member}
    )
    assert r.status_code == 200
    # この仕組みより前の公開（名前が残っていない）を模す
    pub3 = _public_as("2026-11-06-y-1", "y")
    assert (
        c.post("/api/publish", json={"token": "v" * 32, "markdown": pub3, "invite": INVITE}).status_code
        == 200
    )
    names = json.loads((tmp_path / "public" / ".publishers.json").read_text())
    del names["2026-11-06-y-1"]
    (tmp_path / "public" / ".publishers.json").write_text(json.dumps(names))

    assert connect(c, buyer).status_code == 200
    r = c.post("/api/connect", json={"to": RID, "from": "見本の人", "word": "分けてほしい", "invite": INVITE})
    assert r.status_code == 200

    recs = {x["id"]: x for x in c.get("/api/admin/records", headers=hdr(admin)).json()["records"]}
    assert recs[RID]["owner"] == "てすと" and recs[RID]["connections"] == 2
    assert recs["2026-11-06-x-1"]["owner"] == "仲間" and recs["2026-11-06-x-1"]["connections"] == 0
    assert recs["2026-11-06-y-1"]["owner"] == ""  # 画面では「分からない人」
    assert recs[RID]["published"] == dt.date.today().isoformat()
    assert recs[RID]["url"] == f"https://seed.example/p/{RID}"
    text = json.dumps(recs)
    for secret in (TOKEN, other, member, INVITE):
        assert secret not in text
    assert "sha256" not in text and "owners" not in text

    # 寄せられた一言を見る（新しい物が先。日、送った人、言葉、name）
    words = c.get(f"/api/admin/records/{RID}/connections", headers=hdr(admin)).json()["connections"]
    assert sorted(w["word"] for w in words) == ["分けてほしい", "買いたい"]
    assert {w["from"] for w in words} == {"買い手", "てすと"}  # 招待コードか token の名前が送り主
    name = next(w["name"] for w in words if w["word"] == "買いたい")
    # 道の文字は断る。無い物は 404。admin でなければ 403
    # （「..」は送る側の httpx が道を縮めてしまうので、口の下の関数で確かめる）
    for bad in ("..", "../.owners", "a/b", ".owners", "a.b", "A", "x_y", ""):
        with pytest.raises(P.PublishError) as e:
            P.remove_connection(settings_of(c), RID, bad)
        assert e.value.status == 400, bad
    with pytest.raises(P.PublishError):
        P.remove_connection(settings_of(c), "..", name)
    for bad in ("a.b", "A", "x_y", "..%2F..%2Fowners"):
        r = c.request("DELETE", f"/api/admin/records/{RID}/connections/{bad}", headers=hdr(admin))
        assert r.status_code in (400, 404), (bad, r.status_code)
    assert (tmp_path / "public" / ".owners.json").exists() and (tmp_path / "public" / f"{RID}.md").exists()
    assert (
        c.request("DELETE", f"/api/admin/records/{RID}/connections/a.b", headers=hdr(admin)).status_code
        == 400
    )
    assert (
        c.request("DELETE", f"/api/admin/records/{RID}/connections/nope", headers=hdr(admin)).status_code
        == 404
    )
    for code in (member, buyer, None):
        assert c.get(f"/api/admin/records/{RID}/connections", headers=hdr(code)).status_code == 403
        assert (
            c.request("DELETE", f"/api/admin/records/{RID}/connections/{name}", headers=hdr(code)).status_code
            == 403
        )

    # 止めている間も、管理の操作なので通る。消すと数が減り、索引が作り直される
    c.post("/api/admin/pause", json={"paused": True}, headers=hdr(admin))
    r = c.request("DELETE", f"/api/admin/records/{RID}/connections/{name}", headers=hdr(admin))
    assert r.status_code == 200 and r.json()["removed"] is True
    assert [
        w["word"]
        for w in c.get(f"/api/admin/records/{RID}/connections", headers=hdr(admin)).json()["connections"]
    ] == ["分けてほしい"]
    idx = json.loads((tmp_path / "public" / "index.json").read_text())
    assert idx["total"]["connections"] == 1
    assert {x["id"]: x for x in c.get("/api/admin/records", headers=hdr(admin)).json()["records"]}[RID][
        "connections"
    ] == 1
    # 記録には公開の id と日だけ。言葉は書かない
    acts = [
        (x["actor"], x["action"], x["detail"])
        for x in c.get("/api/admin/audit", headers=hdr(admin)).json()["lines"]
    ]
    assert ("動かす人", "admin.connection_remove", f"{RID} {name[:10]}") in acts
    assert "買いたい" not in log.read_text()
