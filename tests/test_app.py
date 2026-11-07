# SPDX-License-Identifier: AGPL-3.0-or-later
"""画面の組み立ての確認。Flet の page は偽物で、view() が返す物の文を見る。

話す（やり取りを記録から組む、送った時の分かれ道、「こういう事ができます」の例、返事の中の写真）、
写真（大きく開いた所の三つの操作）、Form 形式を残さない事、スマートフォンの包みで import できる事。
"""

from __future__ import annotations

import asyncio
import dataclasses
import shutil

import flet as ft
import pytest

from seed import album, cli, local
from seed import highlights as H
from seed.app import cards, gallery, photo, talk
from seed.app.main import App
from seed.records import Line, Observation, Plan, Public


class FakePage:
    route = "/"
    web = False
    platform = None
    width = None
    height = None

    def __init__(self) -> None:
        self.views: list = []
        self.updated = 0
        self.dialogs: list = []
        self.tasks: list = []

    def update(self) -> None:
        self.updated += 1

    async def push_route(self, route: str) -> None:
        self.route = route

    def show_dialog(self, d) -> None:
        self.dialogs.append(d)

    def pop_dialog(self) -> None:
        pass

    def run_task(self, fn, *args) -> None:  # 索引の読み込みなど。テストでは走らせない
        self.tasks.append(fn)


def walk(control):
    """部品の木を全部たどる（dataclass の欄にある部品と部品の並び）。"""
    seen = set()
    stack = [control]
    while stack:
        c = stack.pop()
        if id(c) in seen:
            continue
        seen.add(id(c))
        yield c
        for f in dataclasses.fields(c):
            if f.name.startswith("_") or f.name == "parent":
                continue
            v = getattr(c, f.name, None)
            for x in v if isinstance(v, list) else [v]:
                if isinstance(x, ft.BaseControl):
                    stack.append(x)


def texts(control) -> list[str]:
    """部品の木から、見える文を全部集める。"""
    out: list[str] = []
    for c in walk(control):
        if isinstance(c, (ft.Text, ft.Markdown)) and c.value:
            out.append(str(c.value))
        if isinstance(c, ft.Text):
            out += [str(sp.text) for sp in c.spans or [] if getattr(sp, "text", None)]
        for name in ("content", "tooltip", "hint_text", "label"):
            v = getattr(c, name, None)
            if isinstance(v, str):
                out.append(v)
    return out


@pytest.fixture(autouse=True)
def no_lookup(monkeypatch):
    """土地の照会は網に出るので、テストでは呼ばない（使うテストは上書きする）。"""
    from seed import lookup as L

    monkeypatch.setattr(L, "available", lambda: False)


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


def observe(seedfolder, tmp_path, reading=(), record=()):
    """写真二枚（約 33 m 離れて撮った物）の観察を作る。名は 142107 と 142200。"""
    from test_photos import make_jpeg

    a = make_jpeg(tmp_path / "in" / "a.jpg", taken="2026:11:05 14:21:07")
    b = make_jpeg(tmp_path / "in" / "b.jpg", lat=34.0515, taken="2026:11:05 14:22:00")
    assert cli.main(["observe", "--folder", str(seedfolder), "--claude-code", str(a), str(b)]) == 0
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    obs = Observation.read(path)
    obs.reading = list(reading)
    obs.model = "claude-code" if reading else None
    obs.record += list(record)
    obs.write(path)
    return path


A = "photos/2026-11-05/142107.jpg"
B = "photos/2026-11-05/142200.jpg"
NEW_READING = [
    Line("overall", "今日の一枚: 142200。穂が出ていて、草の名が分かりやすい", 0.8),
    Line("overall", "草が大半で、作物は見えない", 0.8),
    Line("plants", "142107 の手前はススキが優占", 0.6),
    Line("crops", "作物は見えない", 0.6),
    Line("water", "水は見えない", 0.5),
    Line("uncertain", "問い: 北側は雨の後に水が溜まりますか", 0.3),
    Line("next_to_observe", "次の一枚: 株元を地面に近く", 0.5),
]


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- 画面は二つ（と管理）。どの版でも組める


@pytest.mark.parametrize(
    "web,platform",
    [(False, None), (True, None), (False, ft.PagePlatform.IOS), (False, ft.PagePlatform.ANDROID)],
)
def test_screens_build_on_every_version(app, seedfolder, tmp_path, web, platform):
    observe(seedfolder, tmp_path, NEW_READING)
    app.page.web, app.page.platform = web, platform
    assert [sc.route for sc in app.screens()] == ["/", "/photos", "/p/land", "/p/weather"]
    for path in ("/", "/photos", "/p/land"):
        app.route_change(path=path)
        v = app.page.views[-1]
        assert v.route == path and any(w.startswith("seed — ") for w in texts(v))
    # 古い道は「話す」へ
    for old in ("/observe", "/records", "/plan", "/publish", "/find", "/settings", "/admin"):
        app.route_change(path=old)
        assert app.page.views[-1].route == "/"
    words = " ".join(texts(app.page.views[-1]))
    assert "入口" not in words
    # 別のフォルダーを開く札は PC のアプリだけ
    talk.add(app, card="settings")
    app.route_change(path="/")
    has = "別のフォルダーを開く" in texts(app.page.views[-1])
    assert has == (not web and platform is None)


FORMS = (ft.Dropdown, ft.Checkbox, ft.RadioGroup, ft.SegmentedButton, ft.Switch)


def test_no_form_controls_on_talk_and_photos(app, seedfolder, tmp_path):
    """話すと写真の画面には、選ぶ欄や印を付ける欄が無い。文字を打つ欄は一画面に一つまで。"""
    observe(seedfolder, tmp_path, NEW_READING)
    Plan.new("ja", "2026-27 冬", "2026-11-03").write(seedfolder / "plan.md")
    app.index = {"records": [{"id": "x-1", "name": "見本", "word": "一言"}]}
    for key in ("plan", "published", "plants", "others", "settings", "record:x-1"):
        talk.add(app, card=key)
    talk.add(app, who="claude", places=True)
    talk.add(app, who="claude", text="並べました", examples=talk.examples(app, everything=True))
    app.state["talk_to"] = "x-1"
    for build in (talk.view, gallery.view):
        v = build(app)
        everything = list(walk(v))
        assert not [c for c in everything if isinstance(c, FORMS)]
        assert sum(isinstance(c, ft.TextField) for c in everything) <= 1


# ---------------------------------------------------------------- やり取りを記録から組む


@pytest.mark.parametrize("platform,suffix", [(ft.PagePlatform.LINUX, "_pc"), (ft.PagePlatform.ANDROID, "")])
def test_first_photo_text_by_platform(app, platform, suffix):
    """PC にはカメラが無い: 案内も例の札も「選ぶ」言い方。スマートフォンは「撮る」。"""
    app.page.web, app.page.platform = False, platform
    words = texts(talk.view(app))
    assert app.t("talk_first_photo" + suffix) in words
    assert (app.t("talk_first_photo") in words) == (suffix == "")
    assert talk.example_label(app, "first") == app.t("ex_first" + suffix)


def test_conversation_without_observations(app):
    assert talk.turns(app.folder) == []
    words = texts(talk.view(app))
    assert app.t("talk_hello") in words and talk.first_photo_text(app) in words
    assert talk.examples(app) == ["first"]  # 観察が無い時は「まず一枚」だけ
    assert talk.example_label(app, "first") in words


def test_turn_from_old_reading(app, seedfolder, tmp_path):
    """決まった書き出しの無い古い読みでも崩れない。今日の一枚は最初の写真、一言は最初の行。"""
    observe(seedfolder, tmp_path, [Line("overall", "草が大半", 0.8), Line("water", "水は見えない", 0.5)])
    (turn,) = talk.turns(app.folder)
    assert turn.today == A and turn.today_words == "草が大半"
    assert [f.line.text for f in turn.found] == ["水は見えない"]
    assert turn.question is None and turn.next_shot is None
    words = texts(talk.view(app))
    assert "草が大半" in words and "水は見えない" in words
    assert "2026-11-05 14:21" in words
    # 候補地（kind: candidate）の観察は、日付に印を添える（記録の形 §19）
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    obs = Observation.read(path)
    obs.kind = "candidate"
    obs.write(path)
    assert "2026-11-05 14:21 · 自分の畑でない（候補地）" in texts(talk.view(app))


def test_turn_from_new_reading(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING, [Line("said", "北側は湿っている")])
    (turn,) = talk.turns(app.folder)
    assert turn.today == B and turn.today_words.startswith("穂が出ていて")
    assert turn.words == ["北側は湿っている"]
    found = {f.line.text: f.photos for f in turn.found}
    assert found["142107 の手前はススキが優占"] == [A]  # 行が名で指す写真を左に
    assert turn.question == "北側は雨の後に水が溜まりますか" and turn.next_shot == "株元を地面に近く"
    assert not any(H.marked(f.line) for f in turn.found)
    words = texts(talk.view(app))
    for w in ("問い", "北側は雨の後に水が溜まりますか", "次の一枚", "株元を地面に近く", "北側は湿っている"):
        assert w in words, w
    # 長い読みは頭の数行だけ。「続きを読む」で開く
    assert "水は見えない" not in words and any(w.startswith("続きを読む") for w in words)
    app.state["talk_open"] = {turn.name}
    assert "水は見えない" in texts(talk.view(app))
    # 本人が選び直した今日の一枚が先
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    obs = Observation.read(path)
    obs.record.append(H.chosen_line("142107", "ja"))
    obs.write(path)
    (turn,) = talk.turns(app.folder)
    assert turn.today == A and turn.words == ["北側は湿っている"]


# ---------------------------------------------------------------- 送った時の分かれ道


def fake_read(seen):
    def read(st, folder, obs):
        seen.append(list(obs.record))
        obs.reading = list(NEW_READING)
        obs.model = "fake"

    return read


def test_send_photos_makes_observation_and_reads(app, seedfolder, tmp_path, monkeypatch):
    from test_photos import make_jpeg

    seen: list = []
    monkeypatch.setattr(talk, "read_on_server", fake_read(seen))
    monkeypatch.setattr(talk, "read_local", lambda *a: pytest.fail("手元の Claude は無い"))
    app.settings.invite = "inv-test"
    a = make_jpeg(tmp_path / "in" / "a.jpg", taken="2026:11:05 14:21:07")
    b = make_jpeg(tmp_path / "in" / "b.jpg", taken="2026:11:05 14:22:00")
    run(talk.send(app, "北の角", [a, b]))
    obs = Observation.read(seedfolder / "observations" / "2026-11-05-142107.md")
    assert obs.photos == [A, B] and obs.record == [Line("said", "北の角")] and obs.model == "fake"
    assert obs.ask == ["soil", "history"]  # 土と歴史はいつも聞く
    assert seen == [[Line("said", "北の角")]] and "pending" not in app.state
    words = texts(talk.view(app))
    assert "北の角" in words and "株元を地面に近く" in words


def test_send_words_with_local_claude(app, seedfolder, tmp_path, monkeypatch):
    """言葉だけ、手元の Claude あり → Claude Code に渡す。直した行を先に、返事の中の写真も出す。"""
    path = observe(seedfolder, tmp_path, NEW_READING)
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    calls = []

    def fake_talk(folder, text, language, session=None):
        calls.append((text, session))
        obs = Observation.read(path)
        obs.mark("plants", "wrong", "あれはオギ")
        obs.reread(
            [*obs.reading[:2], Line("plants", "142107 の手前はオギ（本人の言葉に拠る）", 0.7)], "claude-code"
        )
        obs.write(path)
        return "直しました。\n![手前](photos/2026-11-05/142107.jpg)", "sess-1"

    monkeypatch.setattr(local, "talk", fake_talk)
    run(talk.send(app, "ススキではなくオギ"))
    run(talk.send(app, "ありがとう"))
    assert calls == [("ススキではなくオギ", None), ("ありがとう", "sess-1")]  # 会話を続ける
    item = next(i for i in app.state["talk"] if i.get("reply"))
    assert [l.text for l in item["fixed"]] == ["142107 の手前はオギ（本人の言葉に拠る）"]
    v = talk.view(app)
    words = texts(v)
    assert "直した所" in words and "ススキではなくオギ" in words
    assert words.index("142107 の手前はオギ（本人の言葉に拠る）") >= 0
    # 返事の中の写真（![…](photos/…)）は、写真として出る
    parts = talk.reply_parts(item["text"], app.folder, talk.photo_index(app.folder))
    assert parts == [("text", "直しました。"), ("photos", [(A, "手前")])]


def test_send_words_without_local_claude_only_notes(app, seedfolder, tmp_path, monkeypatch):
    """言葉だけ、Claude を呼ぶ所がどれも無い（鍵も招待コードも無い）→ 本人の言葉として足すだけ。AI は呼ばない。"""
    monkeypatch.setattr(talk, "read_on_server", lambda *a: pytest.fail("言葉だけでサーバーを呼ばない"))
    run(talk.send(app, "あれはススキ"))
    assert app.state["talk"][-1]["text"] == talk.first_photo_text(app)  # 観察がまだ無い
    path = observe(seedfolder, tmp_path, NEW_READING)
    run(talk.send(app, "雨の後だけ溜まる"))
    obs = Observation.read(path)
    assert obs.record[-1] == Line("said", "雨の後だけ溜まる（問い: 北側は雨の後に水が溜まりますか）")
    assert H.answered(obs, "北側は雨の後に水が溜まりますか") == "雨の後だけ溜まる"
    run(talk.send(app, "3 行目は違う。あれはオギ"))
    assert Observation.read(path).record[-1] == Line("said", "3 行目は違う。あれはオギ")
    assert app.state["talk"][-1]["text"] == app.t("talk_noted") + app.t("talk_noted_how")  # 理由も返す
    assert "雨の後だけ溜まる" in texts(talk.view(app))


def test_invite_line_is_not_kept(app, seedfolder, tmp_path, monkeypatch, caplog):
    from test_photos import make_jpeg

    seen: list = []
    monkeypatch.setattr(talk, "read_on_server", fake_read(seen))
    code = "inv-secret-0042"
    run(talk.send(app, "", [make_jpeg(tmp_path / "in" / "a.jpg")]))
    assert app.state["await_invite"] and app.state["talk"][-1]["text"] == app.t("talk_invite_ask")
    assert seen == []  # 招待コードが無いので、まだ読まない
    v = talk.view(app)
    assert app.t("talk_hint_invite") in texts(v)
    run(talk.send(app, code))
    assert app.settings.invite == code and not app.state["await_invite"]
    assert len(seen) == 1  # 入ったら、待っていた観察を読む
    assert app.state["talk"][-1]["text"] == "入りました。" or any(
        i.get("text") == "入りました。" for i in app.state["talk"]
    )
    assert not any(code in str(i) for i in app.state["talk"])
    assert not any(code in w for w in texts(talk.view(app)))
    for p in (seedfolder / "observations").glob("*.md"):
        assert code not in p.read_text(encoding="utf-8")
    assert code not in (seedfolder / "seed.toml").read_text(encoding="utf-8")
    assert code not in caplog.text


# ---------------------------------------------------------------- 「こういう事ができます」の例


def test_examples_answer_without_ai_or_point_to_pc(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING)
    keys = talk.examples(app)
    assert len(keys) == talk.EXAMPLES_SHOWN + 1 and keys[-1] == "more"
    assert not any(
        talk.EXAMPLES[k].needs_claude for k in keys[:-1]
    )  # 手元の Claude が無い端末は AI 無しの物を先に
    run(talk.run_example(app, "by_place"))
    assert app.state["talk"][-2] == {
        "who": "me",
        "text": "写真を場所ごとに、時の順に並べて",
        "after": "2026-11-05-142107",
    }
    words = texts(talk.view(app))
    assert any(w.startswith("場所 1: 1 枚、中心から") for w in words) and "2026-11-05" in words
    run(talk.run_example(app, "plan_make"))
    reply = app.state["talk"][-1]["text"]
    assert reply.startswith("これは PC の Claude Code でできます") and "できません" not in reply
    # 打った言葉が例と同じなら、例として答える
    run(talk.send(app, "設定を見せて"))
    assert app.state["talk"][-1]["card"] == "settings"
    assert "招待コード" in texts(talk.view(app))
    run(talk.run_example(app, "more"))
    assert "ほかの人の畑を見たい" in texts(talk.view(app))


def test_examples_with_local_claude_go_to_claude_code(app, seedfolder, tmp_path, monkeypatch):
    observe(seedfolder, tmp_path, NEW_READING)
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    monkeypatch.setattr(local, "talk", lambda folder, text, language, session=None: (f"受けた: {text}", "s"))
    run(talk.run_example(app, "track"))
    assert app.state["talk"][-1]["text"] == "受けた: 同じ物を日ごとに追って"


def test_reply_parts_keep_photos_inside_the_folder(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING)
    known = talk.photo_index(app.folder)
    text = "## 場所 1\n![手前](photos/2026-11-05/142107.jpg)\n![外](../../etc/passwd) ![絶対](/etc/hosts) ![無い](photos/2026-11-05/000000.jpg)\n142200 は穂が出ている"
    assert talk.reply_parts(text, app.folder, known) == [
        ("text", "## 場所 1"),
        ("photos", [(A, "手前")]),
        ("text", "外 絶対 無い\n142200 は穂が出ている"),  # 出せない絵は一言だけ。道は Markdown に渡さない
        ("photos", [(B, "")]),
    ]


def test_reply_photos_carry_captions(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, tag_reading())
    text = "見つけた草です。\n![セイタカアワダチソウ](photos/2026-11-05/142107.jpg) ![オギ](photos/2026-11-05/142200.jpg)"
    ctl = talk.reply_controls(app, text)
    caps = [c.value for x in ctl for c in walk(x) if isinstance(c, ft.Text) and c.size == 12]
    assert sorted(caps) == ["オギ", "セイタカアワダチソウ"]
    assert len([c for x in ctl for c in walk(x) if isinstance(c, ft.Image)]) == 2
    # 名で指しただけの写真は、付いたタグを下に出す
    ctl = talk.reply_controls(app, "142200 を見てください")
    caps = [c.value for x in ctl for c in walk(x) if isinstance(c, ft.Text) and c.size == 12]
    assert caps == ["オギ、刈った"]


# ---------------------------------------------------------------- この土地の成り立ち（AI 無し）

PLACE = [
    Line("place_name", "徳島県 見本市 見本町（出典: 見本の住所の資料、確認日 2026-11-05）"),
    Line("elevation", "標高 6.9 m（出典: 見本の標高、確認日 2026-11-05）"),
    Line("landform", "氾濫平野 34.05123, 134.25345 の辺り（出典: 見本の地形分類、確認日 2026-11-05）"),
    Line("soil", "水田化褐色低地土（出典: 見本の土壌図、確認日 2026-11-05）"),
    Line("geology", "後期更新世の段丘堆積物（出典: 見本の地質図、確認日 2026-11-05）"),
    Line("hazard", "洪水の浸水想定区域の中（出典: 見本のハザード、確認日 2026-11-05）"),
    Line("history", "見本の祠（出典: 見本の史跡、確認日 2026-11-05）"),
]


def fake_frames(folder, day="2026-11-05"):
    from PIL import Image

    d = folder / "origin" / day / "frames"
    d.mkdir(parents=True)
    names = ["std-z14", "photo-1961", "photo-1936", "soil", "photo-latest", "own"]
    rows = []
    for i, n in enumerate(names, 1):
        f = f"{i:02d}-{n}.png"
        Image.new("RGB", (64, 36), (40 * i, 90, 60)).save(d / f)
        rows.append(f"| {i} | 題 {n} | [{f}](frames/{f}) | 字幕 | 出典 | |")
    (d.parent / "captions.md").write_text(
        "\n".join(["# 見本", "", "| 順 | 場面 |", "|---|---|", *rows]), encoding="utf-8"
    )


def no_ai(monkeypatch):
    monkeypatch.setattr(talk, "read_on_server", lambda *a: pytest.fail("AI を呼ばない"))
    monkeypatch.setattr(talk, "read_local", lambda *a: pytest.fail("AI を呼ばない"))
    monkeypatch.setattr(local, "talk", lambda *a, **k: pytest.fail("AI を呼ばない"))


def test_land_summary_in_four_groups_without_fine_coords(app, seedfolder):
    from seed import land

    cli.prepare(app.folder)
    app.folder.add_place_data(PLACE)
    groups = land.summary(app.folder, "ja")
    assert [g.key for g in groups] == ["where", "soil", "water", "history"]
    assert [f.key for f in groups[0].facts] == ["place_name", "elevation", "landform"]
    assert [f.key for f in groups[1].facts] == ["soil", "geology"]
    assert (
        groups[0].facts[2].body == "氾濫平野 … の辺り"
        and groups[0].facts[2].source == "見本の地形分類（2026-11-05）"
    )
    # 「この土地」の画面に、四つの組の全部（出典つき）。座標は細かく出さない
    words = texts(land_view(app))
    assert "この土地の成り立ち" in words and "水田化褐色低地土" in words
    assert "後期更新世の段丘堆積物" in words and "見本の土壌図（2026-11-05）" in words
    assert not any("34.05123" in w for w in words)
    # 話すの上にはもう出ない
    assert "水田化褐色低地土" not in texts(talk.view(app))


def land_view(app):
    """プラグイン「この土地」の画面を、画面の並び（screens）から組む。"""
    (sc,) = [sc for sc in app.screens() if sc.route == "/p/land"]
    return sc.build(app)


def test_land_is_not_in_the_talk_screen(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING)
    app.folder.add_place_data(PLACE)
    conv = talk.conversation(app)
    assert all("この土地の成り立ち" not in texts(c) for c in conv)
    assert "2026-11-05 14:21" in texts(conv[0])
    v = land_view(app)
    assert v.route == "/p/land" and "seed — この土地" in texts(v)


def test_land_screen_buttons(app, seedfolder, tmp_path, monkeypatch):
    from seed import land
    from seed import lookup as L

    # 位置の入った写真が無い
    assert "位置の入った写真を一枚送ると、この土地を調べられます。" in texts(land_view(app))
    observe(seedfolder, tmp_path, NEW_READING)
    no_ai(monkeypatch)
    words = texts(land_view(app))
    assert "この場所の資料を調べる" in words and "昔の地図と空中写真を取って来る" in words
    buttons = {b.content: b for b in walk(land_view(app)) if isinstance(b, ft.TextButton)}
    asked = []
    monkeypatch.setattr(L, "available", lambda: True)
    monkeypatch.setattr(L, "data_lines", lambda lat, lon, lg: asked.append(round(lat)) or PLACE)
    run(buttons["この場所の資料を調べる"].on_click(None))
    assert asked == [34] and app.folder.place_data()
    made = []

    def make(folder, language, fetch=None):
        made.append(language)
        fake_frames(seedfolder)
        return land.frames(folder)

    monkeypatch.setattr(land, "make_frames", make)
    run(buttons["昔の地図と空中写真を取って来る"].on_click(None))
    assert made == ["ja"]
    words = texts(land_view(app))
    assert "題 photo-1961" in words and "昔の地図と空中写真（地図を先に、空中写真は古い順）" in words
    assert "昔の地図と空中写真を取って来る" not in words


def test_origin_frames_old_to_new(app, seedfolder):
    from seed import land

    cli.prepare(app.folder)
    fake_frames(seedfolder)
    got = land.frames(app.folder)
    assert [f.name for f in got] == [
        "std-z14",
        "soil",
        "photo-1936",
        "photo-1961",
        "photo-latest",
    ]  # 本人の写真は入れない
    assert got[0].title == "題 std-z14"
    words = texts(land_view(app))
    assert "題 photo-1936" in words and "題 own" not in words


def test_land_examples(app, seedfolder, tmp_path, monkeypatch):
    """「この土地の成り立ち」「土は？」は、打った言葉と同じに話す道へ。「昔は」は土地の画面へ。"""
    observe(seedfolder, tmp_path, NEW_READING)
    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    calls = []

    def fake_talk(folder, text, language, session=None):
        calls.append(text)
        return "答えです", None

    monkeypatch.setattr(local, "talk", fake_talk)
    run(talk.run_example(app, "landform"))
    run(talk.run_example(app, "soil_q"))
    assert calls == ["この土地の成り立ちを教えて", "土はどんな土？"]
    assert all("land" not in it for it in app.state["talk"])
    run(talk.run_example(app, "past"))
    assert app.page.route == "/p/land" and app.page.views[-1].route == "/p/land"
    assert len(calls) == 2


def test_land_lines_are_shown_apart_from_photo_lines(app, seedfolder, tmp_path):
    reading = [*NEW_READING, Line("basis", "土壌図では水田化褐色低地土", 0.6)]
    observe(seedfolder, tmp_path, reading)
    (turn,) = talk.turns(app.folder)
    assert [f.line.text for f in turn.found if talk.is_land_line(f)] == ["土壌図では水田化褐色低地土"]
    words = texts(talk.view(app))
    assert "土地の資料から分かる事" in words and "土壌図では水田化褐色低地土" in words


# ---------------------------------------------------------------- 写真を場所ごとに、時の順に


def test_by_place_groups_near_photos_without_fine_coords(app, seedfolder, tmp_path, capsys):
    from test_photos import make_jpeg

    observe(seedfolder, tmp_path, NEW_READING)
    c = make_jpeg(tmp_path / "in2" / "c.jpg", lat=None, lon=None, taken="2026:11:06 09:00:00")
    d = make_jpeg(tmp_path / "in2" / "d.jpg", lat=34.05121, taken="2026:11:06 09:05:00")
    assert cli.main(["observe", "--folder", str(seedfolder), "--claude-code", str(c), str(d)]) == 0
    spots = album.by_place(app.folder)
    assert [(sp.number, [s.rel for s in sp.shots]) for sp in spots] == [
        (1, [A, "photos/2026-11-06/090500.jpg"]),
        (2, [B]),
        (0, ["photos/2026-11-06/090000.jpg"]),
    ]
    text = album.render_places(spots, "ja")
    assert (
        "場所 1: 2 枚、中心から" in text and "場所 2: 1 枚、中心から北へ" in text and "位置なし: 1 枚" in text
    )
    assert "  2026-11-05: photos/2026-11-05/142107.jpg" in text
    assert "34.05" not in text and "134.25" not in text  # 細かい座標は出さない
    assert cli.main(["photos", "--folder", str(seedfolder), "--by-place"]) == 0
    assert "場所 1: 2 枚" in capsys.readouterr().out
    assert cli.main(["photos", "--folder", str(seedfolder)]) == 1


# ---------------------------------------------------------------- 写真の画面と、大きく開いた所の三つの操作


def buttons(dialog) -> dict[str, ft.Control]:
    return {c.content: c for c in walk(dialog) if isinstance(c, ft.TextButton) and isinstance(c.content, str)}


def test_photos_screen_and_viewer_actions(app, seedfolder, tmp_path):
    path = observe(seedfolder, tmp_path, NEW_READING)
    v = gallery.view(app)
    assert "2026-11-05" in texts(v)
    shots = gallery.all_shots(app)
    assert [s.rel for s in shots] == [A, B]
    photo.open_viewer(app, shots, 0)
    dialog = app.page.dialogs[-1]
    got = buttons(dialog)
    assert set(got) == {"この草の名前は？", "今日の一枚にする", "この写真を外す", "閉じる"}
    # 今日の一枚を選び直す: 本人の行に残り、Claude が選んだ物より先
    got["今日の一枚にする"].on_click(None)
    obs = Observation.read(path)
    assert obs.record[-1] == H.chosen_line("142107", "ja") and H.today(obs)[0] == A
    # 外す: 二度押し。消さずに photos/removed/ へ移す。「戻す」で戻る
    got["この写真を外す"].on_click(None)
    assert (seedfolder / A).exists()
    buttons(dialog)["本当に外す"].on_click(None)
    assert not (seedfolder / A).exists() and (seedfolder / "photos/removed/2026-11-05/142107.jpg").exists()
    assert Observation.read(path).photos == [B]
    snack = app.page.dialogs[-1]
    assert isinstance(snack, ft.SnackBar) and snack.action.label == "戻す"
    snack.action.on_click(None)
    assert (seedfolder / A).exists() and Observation.read(path).photos == [A, B]


def test_published_card_withdraws_on_second_press(app, seedfolder):
    pub = Public(
        id="my-field", place="徳島県", since="2026-11-05", name="見本", word="見本の一言", language="ja"
    )
    pub.days["2026-11-05"] = [Line("overall", "草が大半", 0.8)]
    (seedfolder / "public").mkdir(parents=True, exist_ok=True)
    pub.write(seedfolder / "public" / "my-field.md")
    calls = []

    async def call(method, *args):
        calls.append((method, *args))

    app.call = call
    talk.add(app, card="published")
    v = talk.view(app)
    words = texts(v)
    assert "my-field · 2026-11-05" in words and app.t("talk_publish_pc") in words
    run(next(c for c in walk(v) if isinstance(c, ft.TextButton) and c.content == "取り下げる").on_click(None))
    assert calls == []
    v = talk.view(app)
    run(
        next(
            c for c in walk(v) if isinstance(c, ft.FilledButton) and c.content == "本当に取り下げる"
        ).on_click(None)
    )
    assert calls == [("unpublish", "my-field")] and not (seedfolder / "public" / "my-field.md").exists()


def test_settings_card_switches_field(app, seedfolder, tmp_path):
    from seed import fields as fields_mod

    fl = fields_mod.Fields()
    fl.add("自分の畑", str(seedfolder))
    fl.add("知人の田", str(tmp_path / "other"))
    fields_mod.save_fields(fl)
    words = " ".join(texts(cards.frame(app, "settings", cards.settings_card(app))))
    assert "知人の田 に変える" in words and "自分の畑" in words
    assert "使える物がありません。自分の Claude の鍵か招待コードを入れます" in words  # 鍵も招待コードも無い


def test_local_talk_command(seedfolder, monkeypatch):
    from seed.records import Folder

    folder = Folder(seedfolder)
    cli.prepare(folder)
    seen = {}

    def fake_run(cmd, cwd, timeout, env=None):
        seen.update(cmd=cmd, cwd=cwd, env=env)
        return {"result": "はい", "session_id": "s-2"}

    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    monkeypatch.setattr(local, "_run", fake_run)
    assert local.talk(folder, "計画を立てたい", "ja", session="s-1") == ("はい", "s-2")
    cmd = seen["cmd"]
    assert cmd[:3] == ["/usr/bin/claude", "-p", "計画を立てたい"]
    assert cmd[cmd.index("--resume") + 1] == "s-1" and "--restricted" in cmd
    allowed = cmd[cmd.index("--allowedTools") + 1 :]
    assert "Bash(seed mark *)" in allowed and "Bash(seed photos *)" in allowed
    assert not any("token" in a or "prune" in a or "invite" in a for a in allowed)
    assert "Bash(mkdir *)" in allowed and "Bash(mv *)" in allowed
    assert not any(a.startswith("Bash(rm") for a in allowed)
    system = cmd[cmd.index("--system-prompt") + 1]
    assert "![一言](photos/…)" in system and "seed mark --folder" in system and "直した行を先に" in system
    assert seen["env"]["SEED_FOLDER"] == str(seedfolder) and seen["cwd"] == folder.root


# ---- スマートフォンの包み（seed/server と kagi は入らない。anthropic と fastapi も入れない）

PHONE_PROBE = """
import importlib, sys

BLOCKED = ("seed.server", "kagi", "anthropic", "fastapi")


class Block:
    def find_spec(self, name, path=None, target=None):
        if any(name == b or name.startswith(b + ".") for b in BLOCKED):
            raise ImportError(f"not in the phone build: {name}")
        return None


sys.meta_path.insert(0, Block())
from seed.app.main import make_main  # src/main.py と同じ道（ft.run は呼ばない）

assert callable(make_main())
for m in ("seed.app.talk", "seed.app.cards", "seed.app.gallery", "seed.app.photo",
          "seed.direct", "seed.prompts", "seed.land"):
    importlib.import_module(m)
print("ok")
"""


def test_phone_build_imports_without_server_parts():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "-c", PHONE_PROBE], check=False, capture_output=True, text=True, timeout=120
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"


# ---------------------------------------------------------------- 公開の写真（ページと同じ分け方: Public.day_parts）


def _images(control) -> list[str]:
    return [str(c.src) for c in walk(control) if isinstance(c, ft.Image) and isinstance(c.src, str)]


def test_others_and_record_cards_show_published_photos(app):
    app.settings.override_url = "https://seed.test/"
    app.index = {
        "records": [
            {"id": "x-1", "name": "見本", "word": "一言", "photo": "/photos/x-1/2026-11-05_142107.jpg"},
            {"id": "x-2", "name": "見本2", "word": "一言", "photo": "https://elsewhere.test/a.jpg"},
        ]
    }
    pub = Public(id="x-1", place="徳島県", since="2026-11-05", name="見本", word="一言", language="ja")
    pub.days["2026-11-05"] = [Line("photo", "2026-11-05_142107.jpg"), Line("did", "見ただけ")]
    app.state["public_cache"] = {"x-1": ("ok", pub.render())}
    others = cards.card(app, "others")
    assert _images(others) == ["https://seed.test/photos/x-1/2026-11-05_142107.jpg"]  # よその道は出さない
    rec = cards.card(app, "record:x-1")
    assert _images(rec) == ["https://seed.test/photos/x-1/2026-11-05_142107.jpg"]
    words = " ".join(texts(rec))
    assert "見ただけ" in words and "2026-11-05_142107.jpg" not in words  # 写真の行は文で出さない


def test_draft_card_shows_outgoing_photos_above_text(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING)
    pub = Public(id="d-1", place="徳島県", since="2026-11-05", name="見本", word="一言", language="ja")
    pub.days["2026-11-05"] = [Line("photo", "2026-11-05_142200.jpg"), Line("did", "見ただけ")]
    text_ = pub.render()
    assert talk.draft_photos(text_) == [B] and talk.draft_photos("壊れた下書き") == []
    got = talk.draft_controls(app, {"draft": "public/d-1.md", "draft_text": text_})
    kinds = [type(c).__name__ for c in got]
    assert len(got) == 4 and kinds[1] != "FilledButton"  # 説明、写真、全文、出す
    assert not [c for c in walk(ft.Column(got)) if isinstance(c, FORMS)]


def test_project_name_listed_and_unlisted(app, seedfolder, tmp_path):
    from seed import fields as fields_mod

    assert app.project_name == "seed"  # 一覧に無ければフォルダーの名
    fl = fields_mod.Fields()
    fl.add("自分の畑", str(seedfolder))
    fields_mod.save_fields(fl)
    assert app.project_name == "自分の畑"


def test_app_bar_shows_project_and_folder_icon(app, seedfolder):
    from seed import fields as fields_mod

    fl = fields_mod.Fields()
    fl.add("自分の畑", str(seedfolder))
    fields_mod.save_fields(fl)
    v = app.view("/photos", [])
    assert v.appbar.title.value.startswith("自分の畑 — ")
    first = v.appbar.actions[0]
    assert first.icon == ft.Icons.FOLDER_OPEN_OUTLINED and first.tooltip == "プロジェクトフォルダーを変える"


def test_project_sheet_lists_fields_and_switches(app, seedfolder, tmp_path):
    from seed import fields as fields_mod

    other = tmp_path / "other"
    other.mkdir()
    fl = fields_mod.Fields()
    fl.add("自分の畑", str(seedfolder))
    fl.add("知人の田", str(other))
    fields_mod.save_fields(fl)
    app.show_projects()
    sheet = app.page.dialogs[-1]
    assert isinstance(sheet, ft.BottomSheet)
    words = texts(sheet)
    assert "今のプロジェクトフォルダー" in words and app.folder_label in words
    buttons = {c.content: c for c in walk(sheet) if isinstance(c, ft.TextButton)}
    assert buttons["自分の畑"].disabled and buttons["自分の畑"].icon == ft.Icons.CHECK
    assert not buttons["知人の田"].disabled
    assert "別のフォルダーを開く" in buttons  # FakePage は PC
    run(buttons["知人の田"].on_click(None))
    assert app.folder.root == other and app.project_name == "知人の田"
    app.page.platform = ft.PagePlatform.ANDROID
    app.show_projects()
    assert "別のフォルダーを開く" not in [
        c.content for c in walk(app.page.dialogs[-1]) if isinstance(c, ft.TextButton)
    ]


def test_open_other_folder_switches_and_remembers(app, tmp_path):
    from seed import fields as fields_mod

    other = tmp_path / "farm" / "別の畑"
    other.mkdir(parents=True)
    app.state["x"] = 1
    run(app.open_other_folder(str(other)))
    assert app.folder.root == other
    assert "x" not in app.state  # 前の畑の物は残らない
    fl = fields_mod.load_fields()
    assert fl.current == "別の畑" and fl.get("別の畑").path == other


# ---------------------------------------------------------------- スマートフォンから使う（Remote Control）


def fake_claude(tmp_path, monkeypatch):
    from test_remote import ASKING

    p = tmp_path / "claude"
    p.write_text(ASKING)
    p.chmod(0o755)
    monkeypatch.setenv("SEED_CLAUDE", str(p))
    monkeypatch.setattr(local, "available", lambda: shutil.which(local.command()))  # conftest の None を戻す


def settings_texts(app):
    talk.add(app, card="settings")
    app.route_change(path="/")
    return texts(app.page.views[-1])


@pytest.mark.parametrize("web,platform", [(False, None), (True, None), (False, ft.PagePlatform.IOS)])
def test_remote_row_only_on_pc_with_claude(app, tmp_path, monkeypatch, web, platform):
    app.page.web, app.page.platform = web, platform
    assert "スマートフォンから使う" not in settings_texts(app)
    fake_claude(tmp_path, monkeypatch)
    assert ("スマートフォンから使う" in settings_texts(app)) == (not web and platform is None)


def test_remote_flow(app, tmp_path, monkeypatch):

    fake_claude(tmp_path, monkeypatch)

    async def until(word, seconds=10):
        for _ in range(int(seconds * 20)):
            app.refresh()
            if word in texts(app.page.views[-1]):
                return True
            await asyncio.sleep(0.05)
        return False

    async def flow():
        talk.add(app, card="settings")
        app.route_change(path="/")
        await app.remote_start()
        assert await until("はい")
        await app.remote_yes()
        assert await until("止める")
        for _ in range(100):
            if app.state["remote"].url:
                break
            await asyncio.sleep(0.1)
        app.refresh()
        words = texts(app.page.views[-1])
        assert "https://claude.ai/code/abc123" in words
        assert any(isinstance(c, ft.Image) for c in walk(app.page.views[-1]))
        await app.remote_stop()
        assert "remote" not in app.state
        assert "始める" in texts(app.page.views[-1])

    run(flow())


def test_open_folder_stops_remote(app, tmp_path, monkeypatch):
    fake_claude(tmp_path, monkeypatch)

    async def flow():
        await app.remote_start()
        return app.state["remote"]

    r = run(flow())
    app.open_folder(str(app.folder.root))
    assert r.returncode is not None
    assert "remote" not in app.state


# ---------------------------------------------------------------- 写真のタグ


def tag_reading(*extra):
    return [
        Line("tags", "142107: セイタカアワダチソウ, オギ, 開花", 0.7),
        Line("tags", "142200: オギ、刈った、オギ", 0.7),
        *extra,
    ]


def test_tags_of_and_all_tags(app, seedfolder, tmp_path):
    path = observe(
        seedfolder,
        tmp_path,
        tag_reading(
            Line("tags", "999999: 幽霊", 0.7),
            Line("tags", "形が違う", 0.7),
            Line("tags", "142107: 間違い", 0.7, "wrong"),
        ),
    )
    obs = Observation.read(path)
    assert H.tags_of(obs) == {
        "142107": ["セイタカアワダチソウ", "オギ", "開花"],
        "142200": ["オギ", "刈った"],
    }
    assert H.all_tags([("a", obs)]) == [
        ("オギ", 2),
        ("セイタカアワダチソウ", 1),
        ("刈った", 1),
        ("開花", 1),
    ]
    en = Observation.read(path)
    en.reading = [Line("tags", "142200: Miscanthus, cut", 0.7)]
    assert H.tags_of(en) == {"142200": ["Miscanthus", "cut"]}


def test_gallery_tag_chips_filter(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, tag_reading())
    v = gallery.view(app)
    chips = {c.label: c for c in walk(v) if isinstance(c, ft.Chip)}  # walk は逆順に出る
    assert set(chips) == {"オギ 2", "セイタカアワダチソウ 1", "刈った 1", "開花 1"}
    tiles = lambda v: [
        c
        for c in walk(v)
        if isinstance(c, ft.Container) and c.on_click and not isinstance(c.content, ft.Text)
    ]
    assert len(tiles(v)) == 2
    chips["開花 1"].on_click(None)
    assert app.state["photo_tag"] == "開花"
    v = gallery.view(app)
    assert {c.label for c in walk(v) if isinstance(c, ft.Chip) and c.selected} == {"開花 1"}
    assert len(tiles(v)) == 1
    next(c for c in walk(v) if isinstance(c, ft.Chip) and c.selected).on_click(None)
    assert app.state["photo_tag"] is None and len(tiles(gallery.view(app))) == 2
    # 付いた写真が無い語は外れる
    app.state["photo_tag"] = "存在しない"
    gallery.view(app)
    assert app.state["photo_tag"] is None
    shots = gallery.all_shots(app)
    assert shots[0].tags and shots[1].tags


def test_turn_drops_tags_lines(app, seedfolder, tmp_path):
    path = observe(seedfolder, tmp_path, [*NEW_READING, *tag_reading()])
    t = talk.turn_of("x", Observation.read(path))
    assert t.found and all(f.line.key != "tags" for f in t.found)


def test_prompt_rules_ask_for_tags():
    ja, en = H.prompt_rules("ja"), H.prompt_rules("en")
    assert "tags" in ja and "開花" in ja and "flowering" in en
