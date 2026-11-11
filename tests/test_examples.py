# SPDX-License-Identifier: AGPL-3.0-or-later
"""話すの入力欄の上の例（設計書 §5.19「入力欄の上の例を、場面で選ぶ」）。

場面から選ぶ物（AI を呼ばない）、Claude が返事の終わりに付けた `>> ` の一言、三つまでと「ほかに何ができますか」、
命令でしかできなかった AI の要らない物（帳簿、ロット、気象、違うを集める、残す量、残さない物を消す）。
本物の Claude も命令の子も呼ばない（差し替える）。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import subprocess

import flet as ft
import pytest
from test_app import NEW_READING, FakePage, observe, texts

from seed import claude_md, local
from seed import prompts as P
from seed.app import settings_form, setup, talk
from seed.app.main import App
from seed.records import Line, Observation

NAME = "2026-11-05-142107"
NO_QUESTION = [l for l in NEW_READING if not l.text.startswith("問い")]


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    """網に出ない、Claude を呼ばない、命令を子として走らせない。今日は観察の 5 日後。"""
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


def top(app) -> list[str]:
    return talk.examples(app)


# ---------------------------------------------------------------- 場面ごとの並び


def test_no_observation_first_photo(app):
    assert top(app) == ["first", "settings", "more"]


def test_setup_needed_on_pc_and_phone(app, seedfolder, tmp_path):
    app.ready["needs"] = ["login"]
    assert top(app)[:2] == ["setup", "first"]
    app.page.platform = ft.PagePlatform.ANDROID
    app.ready["needs"] = ["phone_read"]
    assert top(app)[:2] == ["find_pc", "first"]
    assert talk.example_label(app, "find_pc") == "PC を探す"


def test_setup_not_doubled_under_a_fix_button(app):
    """直前の頼みが届かず、文の下に直し方のボタンが在る時は、例の側に準備を出さない。"""
    app.ready["needs"] = ["login"]
    talk.say(app, "ログインが切れています", fix="login")
    assert "setup" not in top(app)


def test_setup_example_opens_setup_without_running_commands(app, monkeypatch):
    app.ready["needs"] = ["login"]
    opened = []

    async def fake_open(a):
        opened.append(a)

    monkeypatch.setattr(setup, "open_setup", fake_open)
    run(talk.run_example(app, "setup"))
    assert opened == [app]
    shown = []
    monkeypatch.setattr(settings_form, "open_form", lambda a: shown.append(a))
    run(talk.run_example(app, "find_pc"))
    assert shown == [app]


def test_question_gives_answer_and_keeps_it_in_the_record_form(app, seedfolder, tmp_path, monkeypatch):
    path = observe(seedfolder, tmp_path, NEW_READING)
    keys = top(app)
    assert keys[0] == "answer" and len(keys) == talk.EXAMPLES_SHOWN + 1 and keys[-1] == "more"

    async def no_claude(*a, **k):
        raise AssertionError("Claude を呼んだ")

    monkeypatch.setattr(talk, "send_words", no_claude)
    run(talk.run_example(app, "answer"))  # 送らずに、入力欄の言い出しが変わる
    assert app.state["answer_to"] == NAME and not [
        i for i in app.state.get("talk", []) if i.get("who") == "me"
    ]
    assert app.t("talk_hint_answer") in texts(talk.view(app))
    run(talk.send(app, "雨の後だけ溜まります"))
    obs = Observation.read(path)
    assert obs.record[-1] == Line("said", "雨の後だけ溜まります（問い: 北側は雨の後に水が溜まりますか）")
    assert "answer" not in top(app) and "answer_to" not in app.state


def test_just_read_offers_wrong_and_name(app, seedfolder, tmp_path, monkeypatch):
    from test_photos import make_jpeg

    observe(seedfolder, tmp_path, NO_QUESTION)
    assert "wrong" not in top(app)[:3]
    shot = make_jpeg(tmp_path / "in2" / "c.jpg", taken="2026:11:06 09:00:00")

    async def read_ok(app, obs, sources=None):
        obs.reading = list(NO_QUESTION)
        obs.write(app.folder.observation_path(obs))
        return True

    monkeypatch.setattr(talk, "read_obs", read_ok)
    run(talk.send(app, "", [shot]))
    assert top(app)[:2] == ["wrong", "name_it"]
    assert talk.example_label(app, "wrong").startswith("それは違う。あれは")
    run(talk.run_example(app, "wrong"))  # 押したら、読みの直後の例は消える
    assert "name_it" not in top(app)[:2]


def test_gap_of_a_week_offers_todays_photo_and_compare(app, seedfolder, tmp_path, monkeypatch):
    observe(seedfolder, tmp_path, NO_QUESTION)
    assert "today_shot" not in top(app)  # 5 日
    monkeypatch.setattr(talk, "today", lambda: dt.date(2026, 11, 5) + dt.timedelta(days=talk.GAP_DAYS))
    assert top(app)[:2] == ["today_shot", "compare"]
    assert talk.example_label(app, "today_shot") == "今日の一枚を選ぶ"  # PC にはカメラが無い
    run(talk.run_example(app, "compare"))  # Claude が無い: 場所ごとに時の順に並べる
    assert app.state["talk"][-1].get("places")


def test_unsent_draft_offers_show_draft(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NO_QUESTION)
    (seedfolder / "public").mkdir(exist_ok=True)
    (seedfolder / "public" / "x.md").write_text("下書きの全文", encoding="utf-8")
    talk.add_draft(app, "public/x.md")
    talk.say(app, "ほかの話")
    assert top(app)[0] == "show_draft"
    run(talk.run_example(app, "show_draft"))
    items = app.state["talk"]
    assert items[-1]["draft"] == "public/x.md" and sum(1 for i in items if i.get("draft")) == 1
    items[-1]["sent"] = True  # 送れた時は、送った全文も覚える（send_draft と同じ）
    app.folder.mark_sent("x", "下書きの全文")
    assert "show_draft" not in top(app)


def test_three_at_most_and_more_is_last(app, seedfolder, tmp_path, monkeypatch):
    observe(seedfolder, tmp_path, NEW_READING)
    app.ready["needs"] = ["install"]
    app.state["just_read"] = NAME
    app.state["next_words"] = ["土の色を見たい"]
    monkeypatch.setattr(talk, "today", lambda: dt.date(2026, 12, 31))
    keys = top(app)
    assert keys == ["setup", "answer", "wrong", "more"]
    assert len(talk.examples(app, everything=True)) > talk.EXAMPLES_SHOWN


# ---------------------------------------------------------------- Claude の返事の終わりの一言


REPLY = (
    "直しました。\n\n"
    ">> この草の名前は？\n"
    ">> https://example.com を見て\n"
    ">> skill/SKILL.md を読んで\n"
    ">> plan.md\n"
    ">> `seed prune --yes`\n"
    ">> seed keep text\n"
    ">> ls | head\n"
    ">> 123456\n"
    ">> 公開して出す\n"
    ">> " + "長" * 41 + "\n"
    ">> 来年の春の計画を立てたい\n"
    ">> この草の名前は？\n"
    ">> 土の色を見たい\n"
    ">> 四つ目の言葉\n"
)


def test_split_next_words_drops_unsafe_and_keeps_three():
    body, words = P.split_next_words(REPLY)
    assert body == "直しました。"
    assert words == ["この草の名前は？", "来年の春の計画を立てたい", "土の色を見たい"]
    for bad in (
        "www.example.com",
        "C:\\seed",
        "~/seed",
        "rm -rf x",
        "sudo ls",
        "a && b",
        "a; b",
        "$HOME",
        "1234567",
    ):
        assert not P.next_word_ok(bad), bad
    assert P.next_word_ok("同じ場所を前と比べて")


def test_reply_lines_leave_the_screen_and_come_back_as_examples(app, seedfolder, tmp_path, monkeypatch):
    observe(seedfolder, tmp_path, NO_QUESTION)
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    replies = iter([(REPLY, "s1"), ("二つ目です。\n>> 写真を場所ごとに並べたい", "s1")])
    monkeypatch.setattr(local, "talk", lambda *a, **k: next(replies))
    run(talk.send(app, "直して"))
    item = app.state["talk"][-1]
    assert item["text"] == "直しました。" and ">>" not in str(app.state["talk"])
    assert not any(">>" in w for w in texts(talk.view(app)))
    keys = top(app)
    assert keys[0] == "say:この草の名前は？"  # 場面の例が無い時は Claude の物が先
    assert talk.example_label(app, keys[0]) == "この草の名前は？"
    run(talk.send(app, "次"))  # 次の返事で入れ替わる
    assert [k for k in top(app) if k.startswith(talk.SAY)] == ["say:写真を場所ごとに並べたい"]
    app.open_folder(str(seedfolder))  # 畑を替える（開き直す）と消える
    assert not [k for k in top(app) if k.startswith(talk.SAY)]
    for p in (seedfolder / "observations").glob("*.md"):
        assert ">>" not in p.read_text(encoding="utf-8")


def test_reply_lines_leave_the_kept_messages_with_a_key(app, seedfolder, tmp_path, monkeypatch):
    """自分の鍵か家の PC（/api/talk）を通った返事も、端末の側で外れる。次の頼みで送るやり取りにも残らない。"""
    from test_direct import KEY, FakeTransport, text

    observe(seedfolder, tmp_path, NO_QUESTION)
    app.settings.anthropic_key = KEY
    fake = FakeTransport([([text(REPLY)], "end_turn"), ([text("はい")], "end_turn")])
    monkeypatch.setattr(talk, "transport", lambda app, via: fake)
    run(talk.send(app, "直して"))
    assert app.state["talk"][-1]["text"] == "直しました。"
    assert ">>" not in str(app.state["direct_messages"])
    assert top(app)[0] == "say:この草の名前は？"
    run(talk.send(app, "続き"))
    assert ">>" not in str(fake.sent[-1])
    assert not [k for k in top(app) if k.startswith(talk.SAY)]


def test_claude_word_is_sent_as_the_persons_words_not_as_a_key(app, seedfolder, tmp_path, monkeypatch):
    observe(seedfolder, tmp_path, NO_QUESTION)
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    got = []
    monkeypatch.setattr(local, "talk", lambda folder, text, *a, **k: (got.append(text) or "受けた", "s"))
    app.state["await_key"] = True
    run(talk.run_example(app, "say:来年の春の計画を立てたいです"))
    assert got == ["来年の春の計画を立てたいです"] and not app.settings.anthropic_key
    assert app.state["talk"][-2] == {"who": "me", "text": "来年の春の計画を立てたいです", "after": NAME}


def test_next_words_rule_is_the_same_for_three_routes_and_not_in_claude_md(app, seedfolder):
    rule = P.NEXT_WORDS_RULE.rstrip("\n")
    assert rule in P.talk_system(P.BUILTIN_RULES, "ja")[0]["text"]  # 自分の鍵とサーバー
    assert rule in local.talk_rules(app.folder, None, "ja")  # 手元の Claude Code（家の PC も）
    assert rule in local.talk_rules(app.folder, None, "ja", home=True)
    for lg in ("ja", "en"):
        assert ">>" not in claude_md.text(lg)


def test_preview_words_from_the_environment(app, monkeypatch):
    monkeypatch.setenv(talk.ENV_NEXT_PREVIEW, "土の色を見たい|https://x.example|草の名前は？")
    assert talk.next_words(app) == ["土の色を見たい", "草の名前は？"]
    app.state["next_words"] = []  # 返事が来たら、見本は使わない
    assert talk.next_words(app) == []


# ---------------------------------------------------------------- 「ほかに何ができますか」に足した物


def test_tools_work_without_claude(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NO_QUESTION)
    assert not talk.can_talk(app)
    everything = talk.examples(app, everything=True)
    for key in talk.TOOLS:
        assert key in everything and not talk.EXAMPLES[key].needs_claude
    want = {
        "ledger": "2026-11 の合計",
        "lots": "ロットはまだ無い",
        "weather": "2026-11 の気象の記録はまだありません。",
        "marks": "合う／違うの付いた行はまだ無い",
        "keep": "残す量は photos",
    }
    for key, head in want.items():
        run(talk.run_example(app, key))
        me, reply = app.state["talk"][-2:]
        assert me["who"] == "me" and me["text"] == app.t(f"ex_{key}")
        assert reply["who"] == "claude" and head in reply["text"], (key, reply["text"])
    assert app.settings.keep == "photos"  # 見るだけ
    # 打った言葉が同じでも、AI 無しで
    run(talk.send(app, "今月の帳簿を見せて"))
    assert "2026-11 の合計" in app.state["talk"][-1]["text"]


def test_prune_needs_two_presses(app, seedfolder):
    run(talk.run_example(app, "prune"))
    assert app.state["talk"][-1]["text"] == app.t("prune_nothing", keep="photos")
    orig = app.settings.records.originals
    orig.mkdir(parents=True)
    (orig / "a.heic").write_bytes(b"x" * 2_000_000)
    run(talk.run_example(app, "prune"))
    item = app.state["talk"][-1]
    assert "2 MB" in item["text"] and str(orig) in item["text"] and item["prune"] == [str(orig)]
    button = next(c for c in talk.prune_controls(app, item) if isinstance(c, ft.TextButton))
    assert button.content == app.t("prune_run")
    run(button.on_click(None))  # 一度目: 消さない
    assert orig.exists() and item.get("sure")
    button = next(c for c in talk.prune_controls(app, item) if isinstance(c, ft.FilledButton))
    assert button.content == app.t("prune_run_sure")
    run(button.on_click(None))  # 二度目: 消す
    assert not orig.exists()
    assert app.state["talk"][-1]["text"] == app.t("prune_done", n=1, mb=2)
    assert next(c for c in talk.prune_controls(app, item) if isinstance(c, ft.FilledButton)).disabled


def test_prune_does_not_widen_what_was_shown(app, seedfolder):
    orig = app.settings.records.originals
    orig.mkdir(parents=True)
    (orig / "a.heic").write_bytes(b"x" * 1000)
    run(talk.run_example(app, "prune"))
    item = app.state["talk"][-1]
    item["prune"] = ["/nowhere"]  # 見せた物に今の物が無い
    item["sure"] = True
    run(talk.prune_now(app, item))
    assert orig.exists()
