# SPDX-License-Identifier: AGPL-3.0-or-later
"""Claude Code と同じやり方をアプリの中に（seed/direct.py）。Claude は呼ばない（運び方と網を差し替える）。

道具の繰り返し、上限、記録のフォルダーの外を断る事、公開を送る道具が無い事、自分の鍵の扱い、運び方の分かれ道、
読みの指示がサーバーと端末で同じ事、スマートフォンの包みの依存。
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import httpx
import pytest
from test_app import NEW_READING, FakePage, observe, texts

from seed import direct, local
from seed import prompts as P
from seed import records as R
from seed.app import talk
from seed.app.main import App
from seed.client import ClientError
from seed.records import Line, Observation, Plan

KEY = "sk-ant-test-not-a-real-key-000000000000"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_lookup(monkeypatch):
    from seed import lookup as L

    monkeypatch.setattr(L, "available", lambda: False)


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


def run(coro):
    return asyncio.run(coro)


def use(name: str, inp: dict, id_: str = "toolu_1") -> dict:
    return {"type": "tool_use", "id": id_, "name": name, "input": inp}


def text(t: str) -> dict:
    return {"type": "text", "text": t}


class FakeTransport:
    """返事を順に返す運び方。送られたやり取りの写しを残す。"""

    via = "fake"
    model = "claude-opus-5-5"

    def __init__(self, replies):
        self.replies = list(replies)
        self.sent: list[list[dict]] = []

    def send(self, messages):
        self.sent.append(json.loads(json.dumps(messages)))
        content, stop = self.replies.pop(0)
        return direct.Reply(content, stop, {"input_tokens": 10, "output_tokens": 5}, self.model)


# ---------------------------------------------------------------- 道具の形


def test_tools_have_no_publish_or_command():
    names = {t["name"] for t in P.TOOLS}
    assert names == set(direct.TOOL_RUN)
    for bad in ("publish", "send_public", "bash", "run", "command", "shell", "delete"):
        assert not any(bad in n for n in names if n != "draft_public") and "publish" not in names
    assert all(t["input_schema"]["additionalProperties"] is False for t in P.TOOLS)
    assert "公開を送る事" in P.TALK_RULES and "![一言](photos/…)" in P.TALK_RULES
    assert "呼び名" in P.TALK_RULES and "name が無い" in P.TALK_RULES


# ---------------------------------------------------------------- 繰り返し


def test_loop_tool_result_then_answer(app, seedfolder, tmp_path):
    """読みの間違い: 印を付け、本人の言葉を残し、読みを書き直し、直した行を先に返す。"""
    path = observe(seedfolder, tmp_path, NEW_READING)
    name = path.stem
    fixed = [
        {
            "key": "overall",
            "text": "今日の一枚: 142200。穂が出ていて、草の名が分かりやすい",
            "confidence": 0.8,
        },
        {"key": "plants", "text": "142107 の手前はオギ（本人の言葉に拠る）", "confidence": 0.7},
    ]
    t = FakeTransport(
        [
            (
                [
                    text("見ます"),
                    use(
                        "mark_line",
                        {"observation": name, "key": "plants", "verdict": "wrong", "reason": "オギ"},
                        "a",
                    ),
                    use("add_words", {"observation": name, "key": "said", "text": "ススキではなくオギ"}, "b"),
                ],
                "tool_use",
            ),
            ([use("write_reading", {"observation": name, "lines": fixed}, "c")], "tool_use"),
            ([text("直しました。\n![手前](photos/2026-11-05/142107.jpg)")], "end_turn"),
        ]
    )
    messages: list[dict] = []
    desk = direct.Desk(app.folder, app.settings)
    out = direct.run(t, desk, messages, "ススキではなくオギ")
    assert out.stopped is None and out.text.startswith("直しました。")
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant", "user", "assistant"]
    results = messages[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"] and not any(r.get("is_error") for r in results)
    obs = Observation.read(path)
    assert Line("said", "ススキではなくオギ") in obs.record
    assert any(l.text == "142107 の手前はオギ（本人の言葉に拠る）" for l in obs.reading)
    assert any(l.verdict == "wrong" for l in obs.earlier)  # 違うと言われた行は前の読みへ
    assert obs.model == "claude-opus-5-5"
    # 二度目は同じやり取りに足す
    t.replies = [([text("どういたしまして")], "end_turn")]
    direct.run(t, desk, messages, "ありがとう")
    assert t.sent[-1][0]["content"][0]["text"] == "ススキではなくオギ" and len(t.sent[-1]) == 7


def test_loop_stops_at_the_limit_and_on_stop(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING)
    t = FakeTransport([([use("list_observations", {}, f"x{i}")], "tool_use") for i in range(5)])
    messages: list[dict] = []
    out = direct.run(t, direct.Desk(app.folder, app.settings), messages, "一覧", max_rounds=3)
    assert out.stopped == "max_rounds" and len(t.sent) == 3
    assert messages[-1]["role"] == "user" and messages[-1]["content"][0]["type"] == "tool_result"
    import threading

    stop = threading.Event()
    stop.set()
    t2 = FakeTransport([([text("x")], "end_turn")])
    out = direct.run(t2, direct.Desk(app.folder, app.settings), [], "止める", stop)
    assert out.stopped == "stopped" and t2.sent == []


def test_loop_clears_on_failure_and_refusal(app, seedfolder):
    class Broken(FakeTransport):
        def send(self, messages):
            raise ClientError("server_limit", "limit")

    messages: list[dict] = [
        {"role": "user", "content": [text("前")]},
        {"role": "assistant", "content": [text("はい")]},
    ]
    with pytest.raises(ClientError):
        direct.run(Broken([]), direct.Desk(app.folder, app.settings), messages, "次")
    assert messages == []
    messages = [{"role": "user", "content": [text("前")]}]
    out = direct.run(FakeTransport([([], "refusal")]), direct.Desk(app.folder, app.settings), messages, "x")
    assert out.stopped == "refusal" and messages == []


def test_tools_stay_inside_the_folder(app, seedfolder, tmp_path):
    path = observe(seedfolder, tmp_path, NEW_READING)
    (seedfolder.parent / "secret.jpg").write_bytes(b"\xff\xd8\xff\xe0")
    desk = direct.Desk(app.folder, app.settings)
    for bad in (
        "../secret.jpg",
        str(seedfolder.parent / "secret.jpg"),
        "/etc/hosts",
        "photos/../../secret.jpg",
        "file:///etc/hosts",
        "seed.toml",
        "photos/2026-11-05/000000.jpg",
    ):
        out, err = direct.run_tool(desk, "view_photo", {"path": bad})
        assert err, bad
    for bad in ("../../etc/passwd", "2026-11-05-142107/../../x", "/etc/hosts", "plan"):
        out, err = direct.run_tool(desk, "read_observation", {"name": bad})
        assert err, bad
    out, err = direct.run_tool(
        desk, "draft_public", {"observations": [path.stem], "id": "../x", "place": "a", "word": "b"}
    )
    assert err
    out, err = direct.run_tool(desk, "publish", {"file": "public/x.md"})
    assert err and "無い" in out
    # 写真は縮めた JPEG で、細かい座標を渡さない
    out, err = direct.run_tool(desk, "view_photo", {"path": "photos/2026-11-05/142107.jpg"})
    assert not err and out[1]["source"]["media_type"] == "image/jpeg"
    out, err = direct.run_tool(desk, "read_observation", {"name": path.stem})
    assert not err and "location" not in out and "34.05" not in out


def test_draft_is_made_but_not_sent(app, seedfolder, tmp_path, monkeypatch):
    """公開は下書きまで。送るのは、アプリが全文を見せ、本人が「出す」を押した時。"""
    path = observe(seedfolder, tmp_path, [Line("overall", "草が大半", 0.8, "right")])
    app.settings.anthropic_key = KEY
    sent: list = []

    async def call(method, *args):
        sent.append((method, args))
        return {"id": "2026-11-05-north", "url": "https://seed.aiseed.dev/public/2026-11-05-north.md"}

    monkeypatch.setattr(app, "call", call)
    replies = [
        (
            [
                use(
                    "draft_public",
                    {
                        "observations": [path.stem],
                        "id": "2026-11-05-north",
                        "place": "徳島県",
                        "word": "草の畑",
                        "name": "にじ",
                    },
                )
            ],
            "tool_use",
        ),
        ([text("下書きを作りました。全文を読んで『出す』を押してください。")], "end_turn"),
    ]
    monkeypatch.setattr(talk, "transport", lambda app, via: FakeTransport(replies))
    run(talk.send(app, "この観察を公開したい"))
    assert sent == []  # まだ送らない
    item = next(i for i in app.state["talk"] if i.get("draft"))
    assert item["draft"] == "public/2026-11-05-north.md" and "草の畑" in item["draft_text"]
    words = texts(talk.view(app))
    assert "出す" in words and any("草の畑" in w for w in words)
    run(talk.send_draft(app, item))
    # 文と、その日の一枚（選んだ物が無ければ最初の写真）が一緒に出る
    assert [s[0] for s in sent] == ["publish"] and sent[0][1][0] == item["draft_text"] and item["sent"]
    assert list(sent[0][1][1]) == ["2026-11-05_142107.jpg"]
    assert any("公開しました" in (i.get("text") or "") for i in app.state["talk"])


def test_draft_changed_after_showing_is_not_sent(app, seedfolder, tmp_path, monkeypatch):
    observe(seedfolder, tmp_path)
    (seedfolder / "public").mkdir(exist_ok=True)
    (seedfolder / "public" / "x.md").write_text("A", encoding="utf-8")
    talk.add_draft(app, "public/x.md")
    item = app.state["talk"][-1]
    (seedfolder / "public" / "x.md").write_text("B", encoding="utf-8")
    monkeypatch.setattr(app, "call", lambda *a: pytest.fail("見せた文と違うので送らない"))
    run(talk.send_draft(app, item))
    assert item["draft_text"] == "B" and not item.get("sent")


def test_plan_tools(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING)
    desk = direct.Desk(app.folder, app.settings, model="claude-opus-5-5")
    out, err = direct.run_tool(desk, "read_plan", {})
    assert not err and "まだ無い" in out
    lines = [{"key": "ground", "text": "北側は湿る", "confidence": 0.6}]
    out, err = direct.run_tool(desk, "write_plan", {"lines": lines, "season": "2027 春"})
    assert not err
    plan = Plan.read(seedfolder / "plan.md")
    assert plan.reading[0].text == "北側は湿る" and plan.season == "2027 春"
    out, err = direct.run_tool(
        desk, "add_words", {"observation": "plan", "key": "decided", "text": "南は刈らない"}
    )
    assert not err and Plan.read(seedfolder / "plan.md").record == [Line("decided", "南は刈らない")]
    out, err = direct.run_tool(
        desk, "write_plan", {"lines": [{"key": "bogus", "text": "x", "confidence": 1}]}
    )
    assert err


# ---------------------------------------------------------------- 自分の鍵（Anthropic の API に直に）


def mock_api(monkeypatch, replies):
    """Anthropic の API を差し替える。届いた要求（見出しと中身）を残す。"""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        status, body = replies.pop(0)
        return httpx.Response(status, json=body)

    monkeypatch.setattr(direct, "TRANSPORT", httpx.MockTransport(handler))
    return seen


def test_key_transport_request_shape_and_key_stays_in_the_header(monkeypatch, tmp_path):
    seen = mock_api(
        monkeypatch,
        [
            (
                200,
                {
                    "content": [text("はい")],
                    "stop_reason": "end_turn",
                    "model": "claude-opus-5-5",
                    "usage": {},
                },
            )
        ],
    )
    t = direct.KeyTransport(KEY, "claude-opus-5-5", None, "ja")
    assert KEY not in repr(t)
    r = t.send([{"role": "user", "content": [text("こんにちは")]}])
    assert r.content == [text("はい")] and r.stop_reason == "end_turn"
    (req,) = seen
    assert str(req.url) == direct.API_URL
    assert req.headers["x-api-key"] == KEY and req.headers["anthropic-version"] == direct.API_VERSION
    assert req.headers["anthropic-beta"] == P.FALLBACK_BETA
    body = json.loads(req.content)
    assert KEY not in req.content.decode()  # 鍵は見出しだけ。Claude に渡す文には入らない
    assert body["tools"] == P.TOOLS and body["system"] == P.talk_system(P.BUILTIN_RULES, "ja")
    assert body["fallbacks"] == "default" and body["output_config"] == {"effort": "medium"}
    assert "thinking" not in body and "tool_choice" not in body
    # Haiku には fallbacks が無い
    mock_api(monkeypatch, [(200, {"content": [], "stop_reason": "end_turn"})])
    t = direct.KeyTransport(KEY, "claude-haiku-5-5", None, "ja")
    t.send([{"role": "user", "content": "x"}])


@pytest.mark.parametrize(
    "status,word",
    [
        (401, "key_bad"),
        (403, "key_bad"),
        (404, "key_model"),
        (429, "key_limit"),
        (529, "key_busy"),
        (400, "key_rejected"),
    ],
)
def test_key_errors_never_carry_the_key(monkeypatch, status, word):
    mock_api(monkeypatch, [(status, {"type": "error", "error": {"type": "x", "message": "nope"}})])
    with pytest.raises(direct.DirectError) as e:
        direct.KeyTransport(KEY, "claude-opus-5-5", None, "ja").send([{"role": "user", "content": "x"}])
    assert e.value.word == word and KEY not in str(e.value) and KEY not in repr(e.value)

    def down(request):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(direct, "TRANSPORT", httpx.MockTransport(down))
    with pytest.raises(direct.DirectError) as e:
        direct.KeyTransport(KEY, "claude-opus-5-5", None, "ja").send([{"role": "user", "content": "x"}])
    assert e.value.word == "key_unreachable" and KEY not in str(e.value)


def test_read_instructions_are_the_same_on_server_and_device(app, seedfolder, tmp_path, monkeypatch):
    """自分の鍵で読む時と、サーバーの /api/read で、Claude に渡す指示が同じ。"""
    from seed import photos
    from seed.server import read as RD

    path = observe(seedfolder, tmp_path, record=[Line("said", "北の角")])
    obs = Observation.read(path)
    app.settings.anthropic_key = KEY
    lines = {"lines": [{"key": "overall", "text": "草が大半", "confidence": 0.8}]}
    seen = mock_api(
        monkeypatch,
        [
            (
                200,
                {"content": [text(json.dumps(lines))], "stop_reason": "end_turn", "model": "claude-opus-5-5"},
            )
        ],
    )
    reading = direct.read_with_key(app.settings, app.folder, obs, None)
    assert [l.text for l in reading.lines] == ["草が大半"]
    device = json.loads(seen[0].content)
    assert KEY not in seen[0].content.decode()

    got: dict = {}

    async def call(client, **kw):
        got.update(kw)
        raise RD.ReadError(502, "stop")

    monkeypatch.setattr(RD, "call", call)
    with pytest.raises(RD.ReadError):
        asyncio.run(
            RD.read(
                None,
                model="claude-opus-5-5",
                skill_dir=None,
                photos=photos.shrunk(app.folder, obs),
                data=list(obs.data),
                place_data=app.folder.place_data(),
                previous=None,
                record="- said: 北の角",
                language="ja",
                ask=list(obs.ask),
                names=[Path(r).stem for r in obs.photos],
                date=obs.date,
                time=obs.time,
                kind=obs.kind,
            )
        )
    asked = device["messages"][0]["content"][-1]["text"]
    assert f"- date: {obs.date}\n- time: {obs.time}\n- kind: {obs.kind}" in asked
    for k in ("model", "max_tokens", "system", "messages", "output_config", "fallbacks"):
        assert device[k] == got[k], k


# ---------------------------------------------------------------- 画面: 鍵の一行、運び方の分かれ道


def test_key_line_is_not_kept_anywhere(app, seedfolder, tmp_path, caplog, credentials_in_tmp):
    observe(seedfolder, tmp_path, NEW_READING)
    talk.ask_key(app)
    assert app.state["await_key"]
    box = next(c for c in __import__("test_app").walk(talk.view(app)) if type(c).__name__ == "TextField")
    assert box.password and app.t("talk_hint_key") in box.hint_text
    run(talk.send(app, KEY))
    assert app.settings.anthropic_key == KEY and not app.state["await_key"]
    assert app.state["talk"][-1]["text"] == "入りました。"
    assert not any(KEY in str(i) for i in app.state["talk"])
    assert not any(KEY in w for w in texts(talk.view(app)))
    for p in seedfolder.rglob("*"):
        if p.is_file():
            assert KEY not in p.read_text(encoding="utf-8", errors="ignore"), p
    assert KEY not in caplog.text
    assert KEY in credentials_in_tmp.read_text(encoding="utf-8")  # 置き場は端末の秘密のファイルだけ
    assert oct(credentials_in_tmp.stat().st_mode & 0o777) == "0o600"
    # 設定の札: 鍵は「入っています」とだけ。外すのは二度押し
    from seed.app import cards

    words = texts(cards.frame(app, "settings", cards.settings_card(app)))
    assert "自分の Claude の鍵" in words and KEY not in " ".join(words)
    assert "自分の Claude の鍵で（claude-opus-5-5）" in words


def test_routes_order(app, monkeypatch):
    assert talk.routes(app) == [] and talk.route(app) is None
    app.settings.invite = "inv-x"
    assert talk.route(app) == "server"
    app.settings.anthropic_key = KEY
    assert (
        talk.routes(app) == ["key", "server"] and talk.route(app) == "key"
    )  # スマートフォン: 自分の鍵 → サーバー
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    assert talk.routes(app) == ["local", "key", "server"] and talk.route(app) == "local"  # PC: 手元が先
    app.settings.read = "server"
    assert talk.route(app) == "server"  # 設定で変えた物
    app.settings.read = "local"
    monkeypatch.setattr(local, "available", lambda: None)
    assert talk.route(app) == "key"  # 選んだ物が無ければ次


def test_words_go_by_route(app, seedfolder, tmp_path, monkeypatch):
    """言葉だけ: 手元の Claude Code／自分の鍵／サーバー／どれも無い。"""
    path = observe(seedfolder, tmp_path, NEW_READING)
    used: list[str] = []

    def fake_transport(app, via):
        used.append(via)
        return FakeTransport([([text(f"{via} で答えた")], "end_turn")])

    monkeypatch.setattr(talk, "transport", fake_transport)
    monkeypatch.setattr(local, "talk", lambda *a, **k: (used.append("local") or "手元で答えた", "s"))
    # どれも無い → 書き留めて、理由を返す
    run(talk.send(app, "北は湿る"))
    assert used == [] and Observation.read(path).record[-1].text.startswith("北は湿る")
    assert app.state["talk"][-1]["text"].endswith(app.t("talk_noted_how"))
    # サーバー（招待コードあり）
    app.settings.invite = "inv-x"
    run(talk.send(app, "どう？"))
    assert used == ["server"] and app.state["talk"][-1]["text"] == "server で答えた"
    # 自分の鍵（スマートフォンでも）
    app.settings.anthropic_key = KEY
    run(talk.send(app, "どう？"))
    assert used[-1] == "key"
    # 手元の Claude Code（PC）
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    run(talk.send(app, "どう？"))
    assert used[-1] == "local"


def test_server_limit_notes_words_and_says_why(app, seedfolder, tmp_path, monkeypatch):
    path = observe(seedfolder, tmp_path, NEW_READING)
    app.settings.invite = "inv-x"

    def handler(request):
        assert request.url.path == "/api/talk"
        body = json.loads(request.content)
        assert set(body) == {"messages", "language", "invite"}  # system と道具は送らない
        return httpx.Response(429, json={"error": "limit", "kind": "daily", "detail": "今日はここまで"})

    monkeypatch.setattr(
        talk, "transport", lambda app, via: direct.ServerTransport(app.settings, httpx.MockTransport(handler))
    )
    run(talk.send(app, "雨の後だけ溜まる"))
    assert Observation.read(path).record[-1].text.startswith("雨の後だけ溜まる")
    last = app.state["talk"][-1]["text"]
    assert last.startswith("今日はここまで") and app.t("talk_noted") in last
    assert app.state.get("direct_messages") == []


def test_examples_go_to_claude_with_key(app, seedfolder, tmp_path, monkeypatch):
    observe(seedfolder, tmp_path, NEW_READING)
    app.settings.anthropic_key = KEY
    monkeypatch.setattr(
        talk, "transport", lambda app, via: FakeTransport([([text("計画を立てました")], "end_turn")])
    )
    run(talk.run_example(app, "plan_make"))
    assert app.state["talk"][-1]["text"] == "計画を立てました"
    # 鍵が在れば、今までの並びで Claude の要る物を後ろへ回さない（場面の例はその前に詰まる。§5.19）
    assert talk.EXAMPLES["plan_make"].needs_claude and talk.base_keys(app)[0] == "landform"


def test_fresh_start_before_limits():
    msgs = [{"role": "user", "content": [text("x")]} for _ in range(P.TALK_MESSAGES_MAX - 5)]
    assert direct.fresh_if_needed(msgs) and msgs == []
    msgs = [{"role": "user", "content": [text("x")]}]
    assert not direct.fresh_if_needed(msgs) and len(msgs) == 1


# ---------------------------------------------------------------- スマートフォンの包み


def test_phone_package_has_what_the_new_path_needs():
    conf = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    app_conf = conf["tool"]["flet"]["app"]
    assert "seed/server" in app_conf["exclude"]
    for plat in ("ios", "android"):
        deps = " ".join(conf["tool"]["flet"][plat]["dependencies"])
        for need in ("flet==", "httpx", "pillow", "pyyaml"):
            assert need in deps, (plat, need)
        assert "anthropic" not in deps


def test_new_path_imports_without_server_and_sdk():
    """seed/server と anthropic の SDK が無い所（スマートフォンの包み）でも、話すの道が import できる。"""
    code = (
        "import sys, importlib.abc\n"
        "class Block(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'anthropic' or name.startswith(('anthropic.', 'seed.server', 'fastapi', 'kagi')):\n"
        "            raise ImportError('blocked: ' + name)\n"
        "sys.meta_path.insert(0, Block())\n"
        "import seed.prompts, seed.direct, seed.app.talk, seed.app.cards\n"
        "print('ok')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=False)
    assert r.returncode == 0 and r.stdout.strip() == "ok", r.stderr


# ---------------------------------------------------------------- 公開の写真


def _draft(app, path, **extra):
    desk = direct.Desk(app.folder, app.settings)
    inp = {"observations": [path.stem], "id": "north-1", "place": "徳島県", "word": "草の畑", "name": "にじ"}
    return direct.run_tool(desk, "draft_public", {**inp, **extra})


def test_draft_has_photo_of_the_day(app, seedfolder, tmp_path):
    path = observe(seedfolder, tmp_path, [Line("overall", "今日の一枚: 142200。穂が出ている", 0.8, "right")])
    out, err = _draft(app, path)
    assert not err, out
    pub = R.Public.read(seedfolder / "public" / "north-1.md")
    assert pub.days["2026-11-05"][0] == Line("photo", "2026-11-05_142200.jpg")
    # 本人が選び直した物が先
    obs = Observation.read(path)
    obs.record.append(Line("note", "今日の一枚: 142107"))
    obs.write(path)
    _draft(app, path)
    assert R.Public.read(seedfolder / "public" / "north-1.md").photo_names() == ["2026-11-05_142107.jpg"]


def test_draft_without_a_chosen_photo_takes_the_first(app, seedfolder, tmp_path):
    """選んだ一枚が無くても、写真の無い公開にしない。アプリが今日の一枚として見せている物（最初の写真）が入る。"""
    path = observe(seedfolder, tmp_path, [Line("overall", "草が大半", 0.8, "right")])
    assert not _draft(app, path)[1]
    assert R.Public.read(seedfolder / "public" / "north-1.md").photo_names() == ["2026-11-05_142107.jpg"]


def test_draft_photos_can_be_chosen_and_are_limited(app, seedfolder, tmp_path):
    path = observe(seedfolder, tmp_path, [Line("overall", "今日の一枚: 142200。穂", 0.8, "right")])
    out, err = _draft(app, path, photos=["142107", "photos/2026-11-05/142200.jpg"])
    assert not err, out
    pub = R.Public.read(seedfolder / "public" / "north-1.md")
    assert pub.photo_names() == ["2026-11-05_142107.jpg", "2026-11-05_142200.jpg"]
    assert not _draft(app, path, photos=[])[1]
    assert R.Public.read(seedfolder / "public" / "north-1.md").photo_names() == []
    out, err = _draft(app, path, photos=["999999"])
    assert err and "999999" in out
    out, err = _draft(app, path, photos="142107")
    assert err


def test_photo_limit_per_day_in_draft(app, seedfolder, tmp_path):
    from test_photos import make_jpeg

    from seed import photos as photos_mod

    path = observe(seedfolder, tmp_path, [Line("overall", "草", 0.8, "right")])
    extra = [
        make_jpeg(tmp_path / "in" / f"c{i}.jpg", taken=f"2026:11:05 14:23:0{i}", lat=None, lon=None)
        for i in range(2)
    ]
    rels = photos_mod.import_photos(app.folder, extra)
    obs = Observation.read(path)
    obs.photos += rels
    obs.write(path)
    out, err = _draft(app, path, photos=[Path(r).stem for r in obs.photos])
    assert err and "一日 3 枚" in out


def test_send_draft_sends_shrunk_photos_or_says_missing(app, seedfolder, tmp_path, monkeypatch):
    import base64 as b64mod
    import io

    from PIL import Image

    from seed.client import Client

    path = observe(seedfolder, tmp_path, [Line("overall", "今日の一枚: 142200。穂", 0.8, "right")])
    assert not _draft(app, path)[1]
    rel = "public/north-1.md"
    text_ = (seedfolder / rel).read_text(encoding="utf-8")
    sent: list = []

    async def call(method, *args):
        sent.append((method, args))
        return {"id": "north-1", "url": "https://seed.test/public/north-1.md"}

    monkeypatch.setattr(app, "call", call)
    assert talk.draft_photos(text_) == ["photos/2026-11-05/142200.jpg"]
    item = {"who": "claude", "draft": rel, "draft_text": text_}
    run(talk.send_draft(app, item))
    (method, (md, shots)) = sent[0]
    assert method == "publish" and md == text_ and list(shots) == ["2026-11-05_142200.jpg"]
    with Image.open(io.BytesIO(shots["2026-11-05_142200.jpg"])) as img:
        assert img.format == "JPEG" and not img.getexif()
    # client は base64 にして photos で送る
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.read())
        return httpx.Response(200, json={"id": "north-1"})

    Client("http://seed.test", "t" * 32, transport=httpx.MockTransport(handler)).publish(md, shots)
    assert b64mod.b64decode(seen["body"]["photos"]["2026-11-05_142200.jpg"]) == shots["2026-11-05_142200.jpg"]
    # 写真が手元に無ければ送らない
    (seedfolder / "photos" / "2026-11-05" / "142200.jpg").unlink()
    item = {"who": "claude", "draft": rel, "draft_text": text_}
    run(talk.send_draft(app, item))
    assert len(sent) == 1 and not item.get("sent")
    assert any("2026-11-05_142200.jpg" in (i.get("text") or "") for i in app.state["talk"])
