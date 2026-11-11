# SPDX-License-Identifier: AGPL-3.0-or-later
"""設計書 §5.19 の 11-11 に足した物: 残す量をアプリで変える、手元の Claude Code の下書きも「下書きを見せて」に、
アプリの答えに命令の言い方を出さない。本物の Claude も命令の子も呼ばない。"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import subprocess

import flet as ft
import httpx
import pytest
from test_app import FakePage
from test_cli import mock_server

from seed import cli, local
from seed.app import talk
from seed.app.main import App
from seed.app.strings import VOICE, s
from seed.records import Folder, Line, Public, text_sha256


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    from seed import lookup as L

    monkeypatch.setattr(L, "available", lambda: False)
    monkeypatch.setattr(local, "available", lambda: None)
    monkeypatch.setattr(talk, "today", lambda: dt.date(2026, 11, 10))

    def no_child(*a, **k):
        raise AssertionError("命令を子として走らせた")

    monkeypatch.setattr(subprocess, "run", no_child)
    monkeypatch.setattr(subprocess, "Popen", no_child)


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


def run(coro):
    return asyncio.run(coro)


def buttons(app) -> dict[str, ft.OutlinedButton]:
    return {b.data: b for b in talk.keep_controls(app).controls}


def draft(folder, pid: str = "d-1", word: str = "一言") -> str:
    pub = Public(id=pid, place="徳島県", since="2026-11-05", name="見本", word=word, language="ja")
    pub.days["2026-11-05"] = [Line("overall", "草が大半", 0.8)]
    folder.mkdir(parents=True, exist_ok=True)
    pub.write(folder / f"{pid}.md")
    return (folder / f"{pid}.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- 残す量のボタン


def test_keep_answer_has_three_buttons_and_current_is_disabled(app):
    run(talk.run_example(app, "keep"))
    item = app.state["talk"][-1]
    assert item.get("keep_levels")
    assert app.t("keep_change_app") in item["text"] and "seed keep" not in item["text"]
    got = buttons(app)
    assert list(got) == ["text", "photos", "research"]
    assert got["photos"].disabled and not got["text"].disabled and not got["research"].disabled
    assert got["text"].content == app.t("keep_btn_text")
    assert app.settings.keep == "photos"  # 見るだけでは変えない
    assert any(
        isinstance(c, ft.Row) and c.controls and c.controls[0].data == "text"
        for c in _walk(talk.item_controls(app, item))
    )


def test_keep_button_saves_in_one_press(app, seedfolder):
    run(talk.run_example(app, "keep"))
    buttons(app)["research"].on_click(None)
    assert app.settings.keep == "research"
    assert 'keep = "research"' in (seedfolder / "seed.toml").read_text(encoding="utf-8")
    last = app.state["talk"][-1]
    assert last["text"] == app.t("keep_changed", desc=app.t("keep_btn_research")) and not last.get("examples")
    got = buttons(app)
    assert got["research"].disabled and not got["photos"].disabled
    # 下げても、残さない物が無ければ消す例は出さない
    buttons(app)["photos"].on_click(None)
    assert app.settings.keep == "photos" and not app.state["talk"][-1].get("examples")


def test_lowering_with_something_to_delete_offers_prune_and_deletes_nothing(app):
    app.settings.keep = "research"
    orig = app.settings.records.originals
    orig.mkdir(parents=True)
    (orig / "a.heic").write_bytes(b"x" * 1000)
    buttons(app)["photos"].on_click(None)
    last = app.state["talk"][-1]
    assert app.settings.keep == "photos" and orig.exists()
    assert last["examples"] == ["prune"] and app.t("keep_lowered") in last["text"]
    assert talk.example_label(app, "prune") == "残さない物を消したい"


def test_keep_is_not_a_talk_command():
    assert "keep" not in local.TALK_COMMANDS


# ---------------------------------------------------------------- 送った下書きの覚え


def test_unsent_drafts(tmp_path):
    folder = Folder(tmp_path / "seed")
    assert folder.unsent_drafts() == []
    pub = folder.public
    a = draft(pub, "a-1")
    draft(pub, "b-1")
    os.utime(pub / "a-1.md", (1, 1))  # b-1 が新しい
    (pub / ".hidden.md").write_text("x", encoding="utf-8")
    assert [p.name for p in folder.unsent_drafts()] == ["b-1.md", "a-1.md"]  # 覚えが無い。点の物は入れない
    folder.mark_sent("a-1", a)
    assert [p.name for p in folder.unsent_drafts()] == ["b-1.md"]  # 同じ全文
    sent = json.loads(folder.sent_path.read_text(encoding="utf-8"))
    assert sent["a-1"]["sha256"] == text_sha256(a) and dt.datetime.fromisoformat(sent["a-1"]["at"])
    (pub / "a-1.md").write_text(a + "\n", encoding="utf-8")  # 送った後に直した
    assert {p.name for p in folder.unsent_drafts()} == {"a-1.md", "b-1.md"}
    assert not list(pub.glob("*.tmp"))
    folder.sent_path.write_text("壊れた", encoding="utf-8")
    assert folder.sent() == {}


def test_index_skips_the_sent_record(tmp_path):
    from seed import index

    folder = Folder(tmp_path / "seed")
    text = draft(folder.public, "a-1")
    folder.mark_sent("a-1", text)
    got = index.build_index(folder.public, tmp_path / "connections")
    assert [r["id"] for r in got["records"]] == ["a-1"]


def test_app_send_records_the_sent_text(app, seedfolder):
    text = draft(seedfolder / "public", "d-2")

    async def call(method, *args):
        assert method == "publish" and args[0] == text
        return {"id": "d-2", "url": "u", "state": "pending"}  # 預かった時も覚える

    app.call = call
    item = {"draft": "public/d-2.md", "draft_text": text}
    run(talk.send_draft(app, item))
    assert app.folder.sent()["d-2"]["sha256"] == text_sha256(text)
    assert app.folder.unsent_drafts() == []


def test_cli_publish_file_records_the_sent_text(seedfolder, monkeypatch, capsys):
    f = str(seedfolder)
    assert cli.main(["init", "--folder", f]) == 0
    text = draft(seedfolder / "public", "d-3")
    sent = []

    def handler(req):
        sent.append(json.loads(req.read().decode())["markdown"])
        return httpx.Response(200, json={"id": "d-3", "url": "u"})

    mock_server(monkeypatch, handler)
    folder = Folder(seedfolder)
    assert [p.name for p in folder.unsent_drafts()] == ["d-3.md"]
    assert cli.main(["publish", "--folder", f, "--file", str(seedfolder / "public" / "d-3.md")]) == 0
    assert sent == [text] and folder.sent()["d-3"]["sha256"] == text_sha256(text)
    assert folder.unsent_drafts() == []
    assert ".sent" not in sent[0]
    # 送れなかった時は覚えない
    (seedfolder / "public" / "d-3.md").write_text(text.replace("一言", "二言"), encoding="utf-8")
    mock_server(monkeypatch, lambda req: httpx.Response(500, json={}))
    assert cli.main(["publish", "--folder", f, "--file", str(seedfolder / "public" / "d-3.md")]) != 0
    assert [p.name for p in folder.unsent_drafts()] == ["d-3.md"]


def test_show_draft_from_a_file_claude_code_wrote(app, seedfolder, tmp_path):
    from test_app import observe
    from test_examples import NO_QUESTION

    observe(seedfolder, tmp_path, NO_QUESTION)
    assert "show_draft" not in talk.examples(app)
    pub = seedfolder / "public"
    old = draft(pub, "old-1")
    os.utime(pub / "old-1.md", (1, 1))
    draft(pub, "new-1")
    assert talk.examples(app)[0] == "show_draft"
    run(talk.run_example(app, "show_draft"))
    item = app.state["talk"][-1]
    assert item["draft"] == "public/new-1.md" and item["draft_text"] == (pub / "new-1.md").read_text()
    # 送る時の決まりは同じ（見せた全文と今のファイルが同じ時だけ）
    app.folder.mark_sent("new-1", item["draft_text"])
    item["sent"] = True
    assert talk.examples(app)[0] == "show_draft"  # old-1 がまだ
    app.folder.mark_sent("old-1", old)
    assert "show_draft" not in talk.examples(app)
    run(talk.run_example(app, "show_draft"))
    assert app.state["talk"][-1]["text"] == app.t("talk_draft_missing")


# ---------------------------------------------------------------- アプリの言い方


def test_app_voice_only_inside_the_app(app, seedfolder, monkeypatch, capsys):
    assert VOICE.get() == ()
    f = str(seedfolder)
    # 端末の文は変わらない
    assert cli.main(["weather", "show", "--folder", f, "--month", "2026-11"]) == 0
    assert "seed weather fetch" in capsys.readouterr().out
    assert cli.main(["keep", "--folder", f]) == 0
    assert "seed keep text" in capsys.readouterr().out
    assert cli.main(["marks", "--folder", f]) == 0
    # アプリ: 自分の鍵・サーバー（手元の Claude Code が無い）
    assert talk.tool_text(app, "weather") == s("weather_none_app", "ja", month="2026-11")
    assert "seed" not in talk.tool_text(app, "keep").replace("seed.toml", "")
    # 手元の Claude Code なら、言えば取れる
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    assert talk.tool_text(app, "weather") == s("weather_none_app_local", "ja", month="2026-11")
    assert "「今月の天気を取って」" in talk.tool_text(app, "weather")
    assert VOICE.get() == ()


def test_app_voice_marks_and_ledger(app, seedfolder, tmp_path, monkeypatch):
    import argparse

    from test_app import NEW_READING, observe

    from seed.app.strings import STRINGS

    path = observe(seedfolder, tmp_path, NEW_READING)
    f = str(seedfolder)
    assert cli.main(["mark", "--folder", f, path.stem, "crops", "right"]) == 0
    text = talk.tool_text(app, "marks")
    assert "--all" not in text and text == s("marks_no_wrong_app", "ja", about="", n=1)
    ns = argparse.Namespace(key=None, all=False, json=False)
    assert "--all" in cli.captured(cli.cmd_marks, app.settings, ns)[1]  # 端末の言い方は変わらない
    # 06 章が見つからない時
    assert cli.main(["mark", "--folder", f, path.stem, "water", "wrong"]) == 0
    monkeypatch.setattr(cli, "chapter_path", lambda folder: None)
    text = talk.tool_text(app, "marks")
    assert "seed init" not in text and s("marks_chapter_missing_app", "ja") in text
    ledger = talk.tool_text(app, "ledger")
    assert "(sale)" not in ledger and "売った" in ledger
    ns = argparse.Namespace(act="sum", month="2026-11")
    assert "(sale)" in cli.captured(cli.cmd_ledger, app.settings, ns)[1]
    for lg in ("ja", "en"):
        for key in (
            "keep_change",
            "weather_none",
            "weather_none_app_local",
            "marks_no_wrong",
            "marks_chapter_missing",
        ):
            assert (key if key.endswith("_local") else key + "_app") in STRINGS[lg]


def _walk(controls):
    for c in controls:
        yield c
        for attr in ("controls", "content"):
            sub = getattr(c, attr, None)
            if isinstance(sub, list):
                yield from _walk(sub)
            elif isinstance(sub, ft.Control):
                yield from _walk([sub])


def test_cli_send_succeeds_even_if_the_sent_record_cannot_be_written(seedfolder, monkeypatch, capsys):
    f = str(seedfolder)
    assert cli.main(["init", "--folder", f]) == 0
    draft(seedfolder / "public", "d-4")
    mock_server(monkeypatch, lambda req: httpx.Response(200, json={"id": "d-4", "url": "u"}))

    def broken(self, public_id, text):
        raise OSError("disk full")

    monkeypatch.setattr(Folder, "mark_sent", broken)
    capsys.readouterr()
    assert cli.main(["publish", "--folder", f, "--file", str(seedfolder / "public" / "d-4.md")]) == 0
    out = capsys.readouterr()
    assert "公開しました" in out.out
    assert out.err.strip() == s("sent_not_recorded", "ja", path=Folder(seedfolder).sent_path)
