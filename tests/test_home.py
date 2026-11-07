# SPDX-License-Identifier: AGPL-3.0-or-later
"""家のサーバー（seed home。設計書 §5.13）。スマートフォン → PC のプロジェクトフォルダー、一方通行。

Claude Code は呼ばない（local.read と local.talk を差し替える）。uvicorn は立てない。
"""

import asyncio
import os
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from test_photos import make_jpeg

from seed import cli, local, photos
from seed import client as seed_client
from seed import lookup as L
from seed import settings as settings_mod
from seed.client import Client, Reading
from seed.records import Folder, Line, Observation
from seed.server.main import create_app
from seed.server.settings import Settings, load_invites

REAL_IS_HOME = seed_client.is_home  # conftest が網に出ない物に替える前の本物
TOKEN = "t" * 32
READ = [Line("overall", "草が大半", 0.8), Line("soil_surface", "地表は見えない", 0.85)]


@pytest.fixture(autouse=True)
def no_fieldnotes(monkeypatch):
    monkeypatch.setattr(L, "_load", lambda: None)
    L.clear_cache()
    yield
    L.clear_cache()


@pytest.fixture
def claude(monkeypatch):
    """手元の Claude Code が在る事にし、読む・話すを差し替える。渡された物を残す。"""
    seen = {"read": [], "talk": []}
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")

    def fake_read(folder, obs, model=None, raw_dir=None, **kw):
        seen["read"].append((folder.root, list(obs.photos)))
        return Reading(list(READ), [], "claude-code", {"duration_ms": 1000})

    def fake_talk(folder, text, language, session=None, **kw):
        seen["talk"].append((folder.root, text, session))
        return f"答え: {text}", "sess-1"

    monkeypatch.setattr(local, "read", fake_read)
    monkeypatch.setattr(local, "talk", fake_talk)
    return seen


def single(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    settings_mod.load(proj)  # seed.toml を作る
    return proj


def multi(tmp_path: Path) -> Path:
    proj = single(tmp_path)
    for n in ("a", "b"):
        (proj / "fields" / n).mkdir(parents=True)
    settings_mod.write_field(proj, "b")
    return proj


def server(tmp_path: Path, proj: Path, api_key: str | None = None) -> tuple[TestClient, str]:
    invites, code = cli.home_invite(proj)
    st = Settings(
        api_key=api_key,
        public_dir=proj / "public-home",
        daily_usd=20.0,
        daily_reads=200,
        per_token_reads=100,
        per_ip_reads=100,
        model="claude-opus-5-5",
        skill_dir=tmp_path / "no-skill",
        invites_path=invites,
        home=proj,
    )
    return TestClient(create_app(st)), code


def jpeg(tmp_path: Path, name="IMG_1.jpg", **kw) -> bytes:
    return make_jpeg(tmp_path / "in" / name, **kw).read_bytes()


def post_read(c: TestClient, code: str, data: bytes, **form):
    return c.post(
        "/api/read",
        files=[("photos", ("IMG_1.jpg", data, "image/jpeg"))],
        data={"token": TOKEN, "invite": code, "language": "ja", **form},
    )


# ---------------------------------------------------------------- サーバー


def test_health_says_home(tmp_path, claude):
    c, _ = server(tmp_path, single(tmp_path))
    h = c.get("/health").json()
    assert h["home"] is True and h["read"] is True and h["talk"] is True


def test_health_without_home_has_no_home(tmp_path):
    st = Settings(
        api_key=None,
        public_dir=tmp_path / "pub",
        daily_usd=1.0,
        daily_reads=1,
        per_token_reads=1,
        per_ip_reads=1,
        model="m",
        skill_dir=tmp_path,
    )
    assert "home" not in TestClient(create_app(st)).get("/health").json()


def test_read_single_field_stores_photo_and_observation(tmp_path, claude):
    proj = single(tmp_path)
    c, code = server(tmp_path, proj)
    data = jpeg(tmp_path, size=(3000, 2000))
    r = post_read(c, code, data, record="- said: 北の角", ask="soil")
    assert r.status_code == 200, r.text
    body = r.json()
    assert [x["key"] for x in body["lines"]] == ["overall", "soil_surface"]
    assert body["model"] == "claude-code" and "## " in body["markdown"] and body["data"] == []
    # 写真は seed observe と同じ所に、元のまま（EXIF の座標も）
    stored = proj / "photos" / "2026-11-05" / "142107.jpg"
    assert stored.read_bytes() == data
    assert photos.exif_info(stored).lat == pytest.approx(34.0512, abs=1e-4)
    obs = Observation.read(proj / "observations" / "2026-11-05-142107.md")
    assert obs.photos == ["photos/2026-11-05/142107.jpg"]
    assert obs.record == [Line("said", "北の角")] and obs.ask == ["soil"]
    assert [l.text for l in obs.reading] == ["草が大半", "地表は見えない"] and obs.model == "claude-code"
    assert obs.location and obs.location["points"] == 1
    assert claude["read"] == [(proj, ["photos/2026-11-05/142107.jpg"])]
    # 一時のファイルは残らない。プロジェクトの外には何も書かない
    assert not list(proj.glob(".home-*"))


def test_read_picks_the_field(tmp_path, claude):
    proj = multi(tmp_path)
    c, code = server(tmp_path, proj)
    assert post_read(c, code, jpeg(tmp_path), field="a").status_code == 200
    assert (proj / "fields" / "a" / "photos" / "2026-11-05" / "142107.jpg").exists()
    assert (proj / "fields" / "a" / "observations" / "2026-11-05-142107.md").exists()
    # 名の無い畑、空 → 今の畑（seed.toml の field = b）
    data2 = jpeg(tmp_path, "IMG_2.jpg", taken="2026:11:06 09:00:00")
    assert post_read(c, code, data2, field="../x").status_code == 200
    assert (proj / "fields" / "b" / "observations" / "2026-11-06-090000.md").exists()
    assert not (proj / "photos").exists()


def test_read_allows_big_photos_at_home(tmp_path, claude):
    proj = single(tmp_path)
    c, code = server(tmp_path, proj)
    big = jpeg(tmp_path) + b"\0" * (3 * 1024 * 1024)  # 2 MB を超える元のまま
    assert post_read(c, code, big).status_code == 200
    too_big = jpeg(tmp_path) + b"\0" * (13 * 1024 * 1024)
    assert post_read(c, code, too_big).status_code == 413


def test_read_needs_the_home_code(tmp_path, claude):
    proj = single(tmp_path)
    c, _ = server(tmp_path, proj)
    r = post_read(c, "wrong-code", jpeg(tmp_path))
    assert r.status_code == 403 and r.json()["error"] == "invite_required"
    assert not (proj / "photos").exists()
    r = c.post("/api/talk", json={"messages": [{"role": "user", "content": "やあ"}], "invite": "nope"})
    assert r.status_code == 403


def test_read_without_claude_code_or_key_is_unavailable(tmp_path):
    proj = single(tmp_path)
    c, code = server(tmp_path, proj)
    r = post_read(c, code, jpeg(tmp_path))
    assert r.status_code == 503 and r.json()["error"] == "read_unavailable"


def test_talk_passes_the_last_words_to_claude_code(tmp_path, claude):
    proj = multi(tmp_path)
    c, code = server(tmp_path, proj)
    messages = [
        {"role": "user", "content": "前の言葉"},
        {"role": "assistant", "content": [{"type": "text", "text": "はい"}]},
        {"role": "user", "content": [{"type": "text", "text": "今日の畑は？"}]},
    ]
    r = c.post("/api/talk", json={"messages": messages, "invite": code, "language": "ja", "field": "a"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["content"] == [{"type": "text", "text": "答え: 今日の畑は？"}]
    assert out["stop_reason"] == "end_turn" and out["model"] == "claude-code"
    assert out["usage"]["input_tokens"] == 0 and out["usage"]["output_tokens"] == 0
    # 二度目は同じ会話を続ける
    c.post("/api/talk", json={"messages": messages, "invite": code, "field": "a"})
    assert [(root, s) for root, _, s in claude["talk"]] == [
        (proj / "fields" / "a", None),
        (proj / "fields" / "a", "sess-1"),
    ]
    r = c.post("/api/talk", json={"messages": [{"role": "assistant", "content": "x"}], "invite": code})
    assert r.status_code == 400


def test_talk_shape_is_a_final_answer_for_the_app(tmp_path, claude):
    """端末の道具の繰り返し（direct.run）が、家のサーバーの答えをそのまま終わりの答えとして読む。"""
    from seed import direct

    proj = single(tmp_path)
    c, code = server(tmp_path, proj)
    st = settings_mod.load(tmp_path / "phone")
    st.invite, st.server_url = code, "http://testserver"

    class Through(httpx.BaseTransport):
        def handle_request(self, request):
            r = c.request(request.method, request.url.path, content=request.read(), headers=request.headers)
            return httpx.Response(r.status_code, content=r.content, headers=r.headers)

    t = direct.ServerTransport(st, http=Through(), field="")
    out = direct.run(t, direct.Desk(st.records, st), [], "こんにちは")
    assert out.text == "答え: こんにちは" and out.stopped is None


# ---------------------------------------------------------------- seed home


def test_home_invite_is_written_once_and_kept(tmp_path):
    proj = single(tmp_path)
    path, code = cli.home_invite(proj)
    assert path == proj / "home.toml" and len(code) == 6
    assert load_invites(path) == {code: "home"}
    assert os.stat(path).st_mode & 0o777 == 0o600
    again_path, again = cli.home_invite(proj)
    assert (again_path, again) == (path, code)


def test_home_env(tmp_path):
    proj = single(tmp_path)
    path, _ = cli.home_invite(proj)
    env = cli.home_env(proj, path)
    assert env["SEED_HOME"] == str(proj) and env["SEED_INVITES"] == str(path)
    assert env["SEED_PUBLIC_DIR"] == str(proj / "public-home") and "SEED_SKILL_DIR" not in env
    (proj / "skill").mkdir()
    (proj / "skill" / "SKILL.md").write_text("# x", encoding="utf-8")
    assert cli.home_env(proj, path)["SEED_SKILL_DIR"] == str(proj / "skill")


def test_lan_ip_is_a_string():
    assert isinstance(cli.lan_ip(), str) and cli.lan_ip()


# ---------------------------------------------------------------- スマートフォンの側


def test_client_read_sends_field():
    seen = {}

    def handler(req):
        seen["body"] = req.read()
        return httpx.Response(200, json={"lines": [], "data": [], "model": "m"})

    c = Client("http://pc.test", "tok", "ja", transport=httpx.MockTransport(handler))
    c.read([b"\xff\xd8\xffx"], field="a")
    assert b'name="field"' in seen["body"] and b"\r\n\r\na\r\n" in seen["body"]


def test_is_home_asks_health_once(monkeypatch):
    monkeypatch.setattr(seed_client, "is_home", REAL_IS_HOME)
    asked = []

    def handler(req):
        asked.append(req.url.path)
        return httpx.Response(200, json={"home": True})

    t = httpx.MockTransport(handler)
    assert seed_client.is_home("http://pc.test/", transport=t) is True
    assert seed_client.is_home("http://pc.test", transport=t) is True
    assert asked == ["/health"] and seed_client.known_home("http://pc.test")


def test_read_on_server_sends_originals_and_field_to_home(tmp_path, monkeypatch):
    monkeypatch.setattr(seed_client, "is_home", lambda *a, **k: True)
    proj = multi(tmp_path)
    st = settings_mod.load(proj)
    folder = st.field_folder("a")
    cli.prepare(folder)
    src = make_jpeg(tmp_path / "in" / "big.jpg", size=(3000, 2000))
    obs = cli.ingest(folder, [src], "text", "ja")  # 手元は小さな写し
    obs.say("said", "北の角")
    sent = {}

    def handler(req):
        sent["body"] = req.read()
        return httpx.Response(200, json={"lines": [], "data": [], "model": "claude-code"})

    real = Client

    def make(server, token, language, **kw):
        return real(server, token, language, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(seed_client, "Client", make)
    cli.read_on_server(st, folder, obs, [src])
    body = sent["body"]
    assert src.read_bytes() in body  # 縮めない元
    assert b'name="field"' in body and b"\r\n\r\na\r\n" in body
    assert "said: 北の角".encode() in body


def test_read_on_server_shrinks_for_other_servers(tmp_path, monkeypatch):
    proj = single(tmp_path)
    st = settings_mod.load(proj)
    folder = Folder(proj)
    cli.prepare(folder)
    src = make_jpeg(tmp_path / "in" / "big.jpg", size=(3000, 2000))
    obs = cli.ingest(folder, [src], "photos", "ja")
    sent = {}

    def handler(req):
        sent["body"] = req.read()
        return httpx.Response(200, json={"lines": [], "data": [], "model": "m"})

    real = Client
    monkeypatch.setattr(
        seed_client, "Client", lambda s, t, lg, **kw: real(s, t, lg, transport=httpx.MockTransport(handler))
    )
    cli.read_on_server(st, folder, obs)
    assert src.read_bytes() not in sent["body"] and b'name="field"' not in sent["body"]


def test_app_keeps_only_a_small_copy_when_sending_home(seedfolder, tmp_path, monkeypatch):
    """家のサーバーへ送る時、スマートフォンには読み用の小さな写しだけ（originals/ も作らない）。元は PC へ。"""
    from test_app import FakePage

    from seed.app import talk
    from seed.app.main import App
    from seed.keep import READ_SIDE

    monkeypatch.setattr(seed_client, "is_home", lambda *a, **k: True)
    app = App(FakePage(), str(seedfolder))
    app.lang = "ja"
    app.settings.invite = "inv-home"
    app.settings.keep = "research"  # seed.toml の残す量に依らない
    app.settings.save()
    got = []

    def fake_read(st, folder, obs, sources=None):
        got.append(sources)
        obs.reading, obs.model = list(READ), "claude-code"

    monkeypatch.setattr(talk, "read_on_server", fake_read)
    src = make_jpeg(tmp_path / "in" / "big.jpg", size=(3000, 2000))
    asyncio.run(talk.send(app, "", [src]))
    kept = seedfolder / "photos" / "2026-11-05" / "142107.jpg"
    with Image.open(kept) as img:
        assert max(img.size) == READ_SIDE
    assert photos.exif_info(kept).lat is not None  # 座標は残る
    assert not (seedfolder / "originals").exists()
    assert got == [[src]]  # 元は送る側へ
    assert settings_mod.load(seedfolder).keep == "research"  # seed.toml は変えない


def phone_app(seedfolder):
    from test_app import FakePage

    from seed.app.main import App

    app = App(FakePage(), str(seedfolder))
    app.lang = "ja"
    return app


def test_change_server_url_from_the_settings_card(seedfolder, monkeypatch):
    """設定の「サーバーを変える」→ 次の一行が URL なら seed.toml の server_url に。やり取りには残さない。"""
    from test_app import texts

    from seed.app import cards, talk

    monkeypatch.delenv("SEED_SERVER_URL", raising=False)
    app = phone_app(seedfolder)
    card = cards.settings_card(app)
    button = next(
        c
        for c in card
        if getattr(c, "content", None) == "サーバーを変える" or getattr(c, "text", None) == "サーバーを変える"
    )
    button.on_click(None)
    assert app.state["await_server"] and app.state["talk"][-1]["text"] == app.t("talk_server_ask")
    assert app.t("talk_hint_server") in texts(talk.view(app))
    # URL でない物は断り、待ったまま
    asyncio.run(talk.send(app, "pc の番地"))
    assert app.state["await_server"] and app.state["talk"][-1]["text"] == app.t("server_url_bad")
    seed_client._HOME["http://192.168.1.5:8800"] = False  # 前の覚えは消える
    url = "http://192.168.1.5:8800/"
    asyncio.run(talk.send(app, url))
    assert not app.state["await_server"]
    assert app.state["talk"][-1]["text"] == "サーバーを http://192.168.1.5:8800 にしました。"
    assert app.settings.server == "http://192.168.1.5:8800"
    assert settings_mod.load(seedfolder).server_url == "http://192.168.1.5:8800"
    assert "http://192.168.1.5:8800" not in seed_client._HOME
    assert not any(i.get("who") == "me" and url.rstrip("/") in str(i.get("text")) for i in app.state["talk"])
    for p in (seedfolder / "observations").glob("*.md"):
        assert "192.168.1.5" not in p.read_text(encoding="utf-8")
    # その後の言葉は、ふだんの言葉
    asyncio.run(talk.send(app, "http://example.test"))
    assert settings_mod.load(seedfolder).server_url == "http://192.168.1.5:8800"


# ---------------------------------------------------------------- 6 桁と、PC を探す


def test_home_invite_is_six_digits(tmp_path):
    proj = single(tmp_path)
    path, code = cli.home_invite(proj)
    assert len(code) == 6 and code.isdigit()
    assert load_invites(path) == {code: "home"}
    path.write_text('[codes]\n"old-long-code-0123456789" = "home"\n', encoding="utf-8")
    assert cli.home_invite(proj)[1] == "old-long-code-0123456789"  # 在る物はそのまま


def test_answer_discovery_replies_with_the_url():
    import socket
    import threading

    from seed.server.home import answer_discovery

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    stop = threading.Event()
    th = threading.Thread(target=answer_discovery, args=("http://192.168.1.5:8800", port, stop), daemon=True)
    th.start()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c:
            c.settimeout(3)
            import time

            for _ in range(20):  # 口が開くまで
                c.sendto(b"other", ("127.0.0.1", port))
                c.sendto(b"seed?", ("127.0.0.1", port))
                try:
                    data, _ = c.recvfrom(1024)
                    break
                except TimeoutError:
                    time.sleep(0.1)
            assert data == b"seed-home http://192.168.1.5:8800"
    finally:
        stop.set()
        th.join(2)


class FakeSock:
    """reply は、送った数が after を超えてから届く（放送が通らない網を真似る）。"""

    def __init__(self, reply=None, after=0):
        self.reply, self.after, self.sent = reply, after, []

    def setsockopt(self, *a):
        pass

    def settimeout(self, t):
        self.timeout = t

    def sendto(self, data, addr):
        self.sent.append((data, addr))

    def recvfrom(self, n):
        if self.reply is None or len(self.sent) <= self.after:
            raise TimeoutError
        r, self.reply = self.reply, None
        return r, ("192.168.1.5", 8801)

    def close(self):
        pass


def test_find_home_with_a_fake_socket():
    from seed import discover

    s = FakeSock(b"seed-home http://192.168.1.5:8800")
    assert discover.find_home(sock=s) == "http://192.168.1.5:8800"
    assert s.sent[0] == (b"seed?", ("255.255.255.255", 8801))
    assert (b"seed?", ("192.168.1.255", 8801)) in s.sent and len(s.sent) == 3  # 放送だけで足りた
    assert discover.find_home(sock=FakeSock(None)) is None
    assert discover.find_home(sock=FakeSock(b"junk")) is None


def test_find_home_sweeps_the_subnet_when_broadcast_is_dropped():
    from seed import discover

    s = FakeSock(b"seed-home http://192.168.1.5:8800", after=3 + 253 - 1)  # 掃き終わってから届く
    assert discover.find_home(sock=s) == "http://192.168.1.5:8800"
    uni = [a[0] for _, a in s.sent[3:]]
    assert len(uni) == 253 and "192.168.1.10" not in uni and "192.168.1.1" in uni and "192.168.1.254" in uni
    assert discover.find_home(sock=FakeSock(None), own_ip="10.0.0.7") is None


def test_find_pc_button_saves_url_and_waits_for_the_code(seedfolder, monkeypatch):
    from seed import discover
    from seed.app import cards, talk

    monkeypatch.delenv("SEED_SERVER_URL", raising=False)
    app = phone_app(seedfolder)
    button = next(
        c
        for c in cards.settings_card(app)
        if getattr(c, "content", None) == "PC を探す" or getattr(c, "text", None) == "PC を探す"
    )
    button.on_click(None)  # 探すのは別の仕事（run_task）。ここでは押せる事だけ
    monkeypatch.setattr(discover, "find_home", lambda *a, **k: "http://192.168.1.5:8800")
    asyncio.run(talk.find_home(app))
    assert app.settings.server == "http://192.168.1.5:8800"
    assert settings_mod.load(seedfolder).server_url == "http://192.168.1.5:8800"
    assert app.state["await_invite"] and app.settings.read == "server"
    assert app.state["talk"][-1]["text"] == app.t("home_found", url="http://192.168.1.5:8800")
    assert app.t("talk_hint_code") in __import__("test_app").texts(talk.view(app))
    asyncio.run(talk.send(app, " 483 271 "))
    assert app.settings.invite == "483271" and not app.state["await_invite"]


def test_find_pc_not_found_says_so(seedfolder, monkeypatch):
    from seed import discover
    from seed.app import talk

    app = phone_app(seedfolder)
    before = app.settings.server
    monkeypatch.setattr(discover, "find_home", lambda *a, **k: None)
    asyncio.run(talk.find_home(app))
    assert app.state["talk"][-1]["text"] == app.t("home_not_found")
    assert not app.state.get("await_invite") and app.settings.server == before
