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
from seed.app import main as app_main
from seed.records import Line, Public
from seed.server import gate
from seed.server import lookup as L
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


# ---- Web 版の入口と命令


def test_web_login_takes_member_tokens_only(ledger, monkeypatch):
    member = gate.add(ledger, "仲間", ["member"], 90)
    buyer = gate.add(ledger, "買い手", ["buyer"], 30)
    monkeypatch.delenv("SEED_INVITES", raising=False)
    monkeypatch.setenv("SEED_TOKENS", str(ledger))
    assert app_main.web_user_for(member).name == "仲間"
    assert app_main.web_user_for(buyer) is None and app_main.web_user_for("nope") is None
    gate.revoke(ledger, "仲間")
    assert app_main.web_user_for(member) is None


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
    assert o["records"] == 1 and o["tokens"] == {"live": 1, "expired": 0, "revoked": 1} and o["invites"] == 1


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
