# SPDX-License-Identifier: AGPL-3.0-or-later
"""画面の組み立ての確認。Flet の page は偽物で、view() が返す物の文を見る。

話す（やり取りを記録から組む、送った時の分かれ道、「こういう事ができます」の例、返事の中の写真）、
写真（大きく開いた所の三つの操作）、Form 形式を残さない事、管理。
"""

from __future__ import annotations

import asyncio
import dataclasses

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
    from seed.server import lookup as L

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
    assert [sc.route for sc in app.screens()] == ["/", "/photos"]
    for path in ("/", "/photos"):
        app.route_change(path=path)
        v = app.page.views[-1]
        assert v.route == path and any(w.startswith("seed — ") for w in texts(v))
    # 古い道は「話す」へ
    for old in ("/observe", "/records", "/plan", "/publish", "/find", "/settings", "/admin"):
        app.route_change(path=old)
        assert app.page.views[-1].route == "/"
    words = " ".join(texts(app.page.views[-1]))
    assert "入口" not in words


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


def test_conversation_without_observations(app):
    assert talk.turns(app.folder) == []
    words = texts(talk.view(app))
    assert app.t("talk_hello") in words and app.t("talk_first_photo") in words
    assert talk.examples(app) == ["first"]  # 観察が無い時は「まず一枚、撮ってみます」だけ
    assert "まず一枚、撮ってみます" in words


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
    assert parts == [("text", "直しました。"), ("photos", [A])]


def test_send_words_without_local_claude_only_notes(app, seedfolder, tmp_path, monkeypatch):
    """言葉だけ、手元の Claude なし（電話）→ 一番新しい観察に本人の言葉として足すだけ。AI は呼ばない。"""
    monkeypatch.setattr(talk, "read_on_server", lambda *a: pytest.fail("言葉だけでサーバーを呼ばない"))
    run(talk.send(app, "あれはススキ"))
    assert app.state["talk"][-1]["text"] == app.t("talk_first_photo")  # 観察がまだ無い
    path = observe(seedfolder, tmp_path, NEW_READING)
    run(talk.send(app, "雨の後だけ溜まる"))
    obs = Observation.read(path)
    assert obs.record[-1] == Line("said", "雨の後だけ溜まる（問い: 北側は雨の後に水が溜まりますか）")
    assert H.answered(obs, "北側は雨の後に水が溜まりますか") == "雨の後だけ溜まる"
    run(talk.send(app, "3 行目は違う。あれはオギ"))
    assert Observation.read(path).record[-1] == Line("said", "3 行目は違う。あれはオギ")
    assert app.state["talk"][-1]["text"] == app.t("talk_noted")
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
        ("photos", [A]),
        ("text", "外 絶対 無い\n142200 は穂が出ている"),  # 出せない絵は一言だけ。道は Markdown に渡さない
        ("photos", [B]),
    ]


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
    # やり取りの一番上に、まとめた形で（各組の頭の一行。「続きを読む」で全部）
    words = texts(talk.view(app))
    assert (
        "この土地の成り立ち" in words
        and "水田化褐色低地土" in words
        and "後期更新世の段丘堆積物" not in words
    )
    assert not any("34.05123" in w for w in words)
    app.state["talk_open"] = {"land"}
    assert "後期更新世の段丘堆積物" in texts(talk.view(app))


def test_land_is_on_top_before_the_first_observation(app, seedfolder, tmp_path):
    observe(seedfolder, tmp_path, NEW_READING)
    app.folder.add_place_data(PLACE)
    conv = talk.conversation(app)
    first, second = texts(conv[0]), texts(conv[1])
    assert "この土地の成り立ち" in first and "2026-11-05 14:21" in second


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
    words = texts(talk.view(app))
    assert "題 photo-1936" in words and "題 own" not in words


def test_land_examples_do_not_call_ai(app, seedfolder, tmp_path, monkeypatch):
    from seed import land
    from seed.server import lookup as L

    observe(seedfolder, tmp_path, NEW_READING)
    no_ai(monkeypatch)
    asked = []
    monkeypatch.setattr(L, "available", lambda: True)
    monkeypatch.setattr(L, "data_lines", lambda lat, lon, lg: asked.append((round(lat), round(lon))) or PLACE)
    run(talk.run_example(app, "landform"))
    assert asked == [(34, 134)] and app.folder.place_data()  # 照会の結果が無ければ、照会する（AI 無し）
    assert (
        app.state["talk"][-2]["text"] == "この土地の成り立ちを教えて"
        and app.state["talk"][-1]["land"] == "all"
    )
    run(talk.send(app, "土はどんな土？"))
    assert app.state["talk"][-1]["land"] == "soil" and len(asked) == 1
    made = []

    def make(folder, language, fetch=None):
        made.append(language)
        fake_frames(seedfolder)
        return land.frames(folder)

    monkeypatch.setattr(land, "make_frames", make)
    run(talk.run_example(app, "past"))
    assert made == ["ja"] and app.state["talk"][-1]["land"] == "past"
    run(talk.run_example(app, "past"))
    assert made == ["ja"]  # もう在れば作らない
    words = texts(talk.view(app))
    assert "題 photo-1961" in words and "昔の地図と空中写真（地図を先に、空中写真は古い順）" in words


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
    assert "知人の田 に変える" in words and "自分の畑" in words and "サーバーで" in words


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
    system = cmd[cmd.index("--system-prompt") + 1]
    assert "![一言](photos/…)" in system and "seed mark --folder" in system and "直した行を先に" in system
    assert seen["env"]["SEED_FOLDER"] == str(seedfolder) and seen["cwd"] == folder.root


# ---- 管理の画面（動かす人）


def _admin_app(tmp_path, monkeypatch, scopes=("admin",)):
    monkeypatch.setenv("SEED_CREDENTIALS", str(tmp_path / "cred.toml"))
    app = App(FakePage(), str(tmp_path / "seed"))
    app.scopes = set(scopes)
    return app


OVERVIEW = {
    "version": "0.0.1",
    "records": 2,
    "connections": 3,
    "boxes": 1,
    "tokens": {"live": 2, "expired": 1, "revoked": 0},
    "invites": 4,
    "read": False,
    "audit": "off",
    "remaining": {"reads": 0, "usd": 20.0},
}


def test_admin_tab_only_for_the_operator(tmp_path, monkeypatch):
    app = _admin_app(tmp_path, monkeypatch, scopes=("member",))
    assert "/admin" not in [sc.route for sc in app.screens()]
    app.route_change(path="/admin")  # 入れない人が道を打っても、入口に戻る
    assert "管理" not in texts(app.page.views[-1])
    app.scopes = {"admin"}
    assert [sc.route for sc in app.screens()][-1] == "/admin"


def test_admin_says_what_to_do(tmp_path, monkeypatch):
    from seed.app import admin

    app = _admin_app(tmp_path, monkeypatch)
    warns = admin.attention(app, OVERVIEW, {"verified": False})
    assert len(warns) == 5
    said = dict(warns)
    # 何が起きているか → サーバーで打つコマンド（文とコマンドは分かれている。コマンドは一行に一つ）
    assert said["写真を読み取れません。Claude の鍵が入っていません。サーバーで次を打ちます。"] == [
        "sudoedit /etc/seed/env   # ANTHROPIC_API_KEY= の後に鍵を入れる",
        "sudo systemctl restart seed",
    ]
    (audit_off,) = [w for w in warns if w[0].startswith("操作の記録を書いていません。")]
    assert "鍵がもう在る時は作り直しません" in audit_off[0]
    assert audit_off[1] == [
        "sudo test -e /etc/seed/log-key || sudo sh -c 'umask 077; head -c 32 /dev/urandom > /etc/seed/log-key'",
        "sudo systemctl restart seed",
    ]
    (tampered,) = [w for w in warns if w[0].startswith("操作の記録が書き換えられています。")]
    assert "『受け付けを止める』" in tampered[0]
    assert tampered[1] == ["last -n 20", "sudo journalctl -u ssh --since -2d"]
    assert any("出し直します" in w and not cmds for w, cmds in warns)
    err = admin.attention(app, {**OVERVIEW, "audit": "error"})
    assert ["df -h /var/lib/seed", "ls -ld /var/lib/seed/audit"] in [c for _, c in err]
    good = {**OVERVIEW, "read": True, "audit": "on", "tokens": {"live": 2, "expired": 0, "revoked": 0}}
    good["remaining"] = {"reads": 180}
    good["denied_today"] = admin.DENIED_MANY - 1
    good["keys"] = {"claude": True, "plantnet": False}
    assert admin.attention(app, good, {"verified": True}) == []
    rows = dict(admin.state_rows(app, good))
    assert (
        rows["写真の読み取り（Claude）"] == "できます"
        and rows["操作の記録"] == "書いています"
        and rows["今日の残り"] == "読み取り 180 回"
        and rows["受け付け"] == "受け付けています"
        and rows["外の鍵"] == "Claude 在る、Pl@ntNet 無い"
        and rows["公開"] == "記録 2 件、寄せられた一言 3 件"
        and rows["入れる人"] == "token 2 人、招待コード 4 人、Web 版で記録を置いている人 1 人"
    )
    # 止めている、断った要求が多い、もうすぐ切れる token
    busy = {**good, "paused": True, "denied_today": admin.DENIED_MANY}
    busy["tokens"] = {**good["tokens"], "expiring": 3}
    warns = admin.attention(app, busy, {"verified": True})
    assert [w for w, _ in warns] == [
        "受け付けを止めています。戻すには下の『受け付けを再開する』を押します。",
        (
            f"今日、断った要求が {admin.DENIED_MANY} 回あります。誰かが試しているかもしれません。"
            "下の『誰が何をしたか』で相手を見ます。続くなら『受け付けを止める』を押します。"
        ),
        "あと 14 日以内に切れる token が 3 件あります。要る人には、切れる前に出し直します。",
    ]
    assert all(cmds == [] for _, cmds in warns)
    assert dict(admin.state_rows(app, busy))["受け付け"] == "止めています"
    # en も同じ形
    app.lang = "en"
    assert dict(admin.state_rows(app, busy))["Requests"] == "Paused"
    assert len(admin.attention(app, OVERVIEW, {"verified": False})) == 5
    app.lang = "ja"
    tokens = [
        {
            "name": "b",
            "scope": ["buyer"],
            "state": "revoked",
            "created": "2026-11-01",
            "expires": "2026-12-01",
        },
        {
            "name": "a",
            "scope": ["admin"],
            "state": "live",
            "created": "2026-11-06",
            "expires": "2027-02-04",
            "note": "n",
        },
    ]
    tr = admin.token_rows(app, tokens)
    assert [(r["name"], r["live"]) for r in tr] == [("a", True), ("b", False)]
    assert tr[0]["scope"] == "動かす人（この画面）" and tr[1]["state"] == "取り消し済み"
    lines = [
        {"ts": "2026-11-06T16:55:01+09:00", "actor": "?", "action": "publish", "detail": "断った: scope"},
        {
            "ts": "2026-11-06T16:54:00+09:00",
            "actor": "にじ",
            "action": "admin.token.add",
            "detail": "買い手 buyer",
        },
    ]
    assert admin.audit_rows(app, lines) == [
        ["2026-11-06 16:55", "知らない人", "公開した", "断った: scope"],
        ["2026-11-06 16:54", "にじ", "管理: token を出した", "買い手 buyer"],
    ]
    more = [
        {"ts": "2026-11-06T17:00:00+09:00", "actor": "にじ", "action": a, "detail": d}
        for a, d in (
            ("admin.pause", "通した"),
            ("admin.resume", "通した"),
            ("admin.token_revoke_all", "3 件"),
        )
    ]
    assert [r[2] for r in admin.audit_rows(app, more)] == [
        "管理: 受け付けを止めた",
        "管理: 受け付けを再開した",
        "管理: token を全部取り消した",
    ]


def test_admin_view_builds_from_loaded_state(tmp_path, monkeypatch):
    app = _admin_app(tmp_path, monkeypatch)
    app.state["admin"] = {
        "loaded": True,
        "overview": OVERVIEW,
        "tokens": [
            {
                "name": "買い手 A",
                "scope": ["buyer"],
                "state": "live",
                "created": "2026-11-06",
                "expires": "2026-12-06",
            }
        ],
        "audit": {"state": "off", "verified": None, "lines": []},
        "records": [{"id": "2026-11-06-x-1", "name": "にじ", "place": "徳島県", "since": "2026-11-06"}],
        "new_token": {"name": "買い手 A", "code": "not-a-real-token-000"},
    }
    app.route_change(path="/admin")
    seen = " ".join(texts(app.page.views[-1]))
    for word in (
        "今の状態",
        "気を付ける事",
        "人に渡す、入る鍵（token）",
        "渡す相手の名前",
        "受け付けを止める",
        "token を全部取り消す",
        "sudo systemctl restart seed",
        "公開された記録",
        "誰が何をしたか",
        "買い手 A",
        "取り消す",
        "取り下げる",
        "出るのはこの一度だけ",
        "not-a-real-token-000",
    ):
        assert word in seen, word
    # 止めている間は、同じ所のボタンが「再開する」になる。全部取り消すは二度押し
    app.state["admin"].update(overview={**OVERVIEW, "paused": True}, confirm=("revoke_all", ""))
    app.route_change(path="/admin")
    seen = " ".join(texts(app.page.views[-1]))
    assert "受け付けを再開する" in seen and "受け付けを止める" not in seen
    assert "本当に全部取り消す（自分の分は残す）" in seen
    # まだ読んでいなければ、尋ねている事だけを出す
    app.state["admin"] = {}
    app.route_change(path="/admin")
    assert "サーバーに尋ねています…" in texts(app.page.views[-1])


def test_admin_record_rows(tmp_path, monkeypatch):
    from seed.app import admin

    app = _admin_app(tmp_path, monkeypatch)
    recs = [
        {
            "id": "2026-11-06-x-1",
            "name": "にじ",
            "place": "徳島県",
            "since": "2026-11-06",
            "owner": "仲間",
            "published": "2026-11-06",
            "connections": 2,
            "url": "https://seed.example/p/2026-11-06-x-1",
        },
        {
            "id": "2026-11-05-y-1",
            "name": "y",
            "owner": "",
            "published": "2026-11-05",
            "connections": 0,
            "url": "",
        },
    ]
    rows = admin.record_rows(app, recs)
    assert rows[0] == {
        "id": "2026-11-06-x-1",
        "head": "にじ · 徳島県 · 2026-11-06",
        "meta": "公開した人 仲間　公開した日 2026-11-06　寄せられた一言 2 件",
        "url": "https://seed.example/p/2026-11-06-x-1",
    }
    assert rows[1]["meta"].startswith("公開した人 分からない人")
    conns = [
        {"name": "2026-11-06-n-0123abcd", "date": "2026-11-06", "from": "買い手", "word": "分けてほしい"}
    ]
    assert admin.connection_rows(conns) == [
        {"name": "2026-11-06-n-0123abcd", "head": "2026-11-06　買い手", "word": "分けてほしい"}
    ]
    # 画面: 開いた記録の下に一言と「消す」。二度押しで「本当に消す」
    app.state["admin"] = {
        "loaded": True,
        "overview": OVERVIEW,
        "tokens": [],
        "audit": {"lines": []},
        "records": recs,
        "conns": {"2026-11-06-x-1": conns},
        "confirm": ("connection", "2026-11-06-x-1/2026-11-06-n-0123abcd"),
    }
    app.route_change(path="/admin")
    seen = " ".join(texts(app.page.views[-1]))
    for word in (
        "公開の頁を開く",
        "寄せられた一言を閉じる",
        "寄せられた一言を見る",
        "分けてほしい",
        "本当に消す",
        "公開した人 仲間",
    ):
        assert word in seen, word
