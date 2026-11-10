# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

import pytest

from seed import lang
from seed.records import (
    EMPTY,
    Connection,
    Folder,
    Line,
    Observation,
    Public,
    coarse_coord,
    demote_directives,
    parse_lines,
    sort_reading,
)

# docs/記録の形.md §3 の例、そのまま
EXAMPLE = """---
date: '2026-11-05'
time: '14:21:07'
photos:
- photos/2026-11-05/142107.jpg
location:
  center: [34.0512, 134.2534]
  points: 1
  extent_m: 0
model: claude-opus-5-5
language: ja
---
## Reading (claude-opus-5-5)
- overall: 草丈 1 m を超えるセイタカアワダチソウとススキが大半。作物は見えない [0.80]  → farmer: right
- soil_surface: 地表は見えない。裸地は無い [0.85]
- basis: ススキの優占は刈らない年が続いたことと合う（06 畑を読む）[0.60]
- next_to_observe: 根元の土の色と湿り。一枚、地面に近く撮る [0.70]

## Data
- geology: 和泉層群の砂岩・泥岩（出典: 産総研 シームレス地質図 V2、確認日 2026-11-05）

## Record
- did: 今日は見ただけ。刈っていない
- saw: 北側の端だけ草が低い
"""


# ---- 行


def test_line_ai_with_verdict():
    l = Line.parse("- overall: 草が高い [0.80]  → farmer: wrong (ススキではなくオギ)")
    assert l.key == "overall" and l.text == "草が高い"
    assert l.confidence == 0.8 and l.by_ai and l.judged
    assert l.verdict == "wrong" and l.reason == "ススキではなくオギ"
    assert l.render() == "- overall: 草が高い [0.80]  → farmer: wrong (ススキではなくオギ)"


def test_line_own_has_no_confidence():
    l = Line.parse("- did: 今日は見ただけ")
    assert l.confidence is None and not l.by_ai and not l.judged
    assert l.render() == "- did: 今日は見ただけ"


def test_line_not_a_line():
    assert Line.parse("(none)") is None
    assert Line.parse("- Overall: 大文字は駄目") is None
    assert Line.parse("ただの文") is None


def test_line_roundtrip_examples_from_fieldnotes():
    # fieldnotes（11-11 に一本化）の docs/records.md の形で書かれた行が読めること
    for s in [
        "- overall: silvergrass and goldenrod, no crop [0.85]  → farmer: right",
        "- dominant: Solidago altissima [0.9]  → farmer: wrong (it is Miscanthus)",
        "- weather: 18.4 °C max (source: Open-Meteo, 2026-10-28)",
    ]:
        l = Line.parse(s)
        assert l is not None
        if "[0.9]" not in s:
            assert l.render() == s
        else:
            assert l.render() == s.replace("[0.9]", "[0.90]")


def test_line_validation():
    with pytest.raises(ValueError):
        Line("Bad-Key", "x")
    with pytest.raises(ValueError):
        Line("k", "x", confidence=1.5)
    with pytest.raises(ValueError):
        Line("k", "x", verdict="maybe")


def test_directive_demoted_japanese_and_english():
    lines = [
        Line("plants", "ススキを刈るべき", 0.7),
        Line("water", "You should drain the north side", 0.6),
        Line("did", "刈るべきだと思った"),  # 本人の行は触らない
        Line("overall", "草が高い", 0.8),
    ]
    out = demote_directives(lines)
    assert [l.key for l in out] == ["uncertain", "uncertain", "did", "overall"]
    assert "plants" in out[0].text and out[0].confidence == 0.7


def test_candidate_material_keys_between_water_and_change():
    from seed.records import PLAN_KEYS, READING_KEYS

    i = READING_KEYS.index
    assert i("water") < i("access") < i("sun_slope") < i("surroundings") < i("change") < i("basis")
    assert (
        PLAN_KEYS[:3] == ("cut", "ground", "sow")
        and "mix" in PLAN_KEYS
        and PLAN_KEYS[-1] == "next_to_observe"
    )


def test_change_key_sorts_after_water_before_basis():
    lines = [Line("basis", "b", 0.5), Line("change", "c", 0.5), Line("water", "w", 0.5)]
    assert [l.key for l in sort_reading(lines)] == ["water", "change", "basis"]


def test_sort_reading_order_and_unknown_last():
    lines = [Line("basis", "b", 0.5), Line("zzz", "z", 0.5), Line("overall", "o", 0.5)]
    assert [l.key for l in sort_reading(lines)] == ["overall", "basis", "zzz"]


def test_parse_lines_skips_none_and_prose():
    assert parse_lines(f"{EMPTY}\nprose\n- did: x") == [Line("did", "x")]


# ---- 観察


def test_observation_parse_example():
    obs = Observation.parse(EXAMPLE)
    assert obs.date == "2026-11-05" and obs.time == "14:21:07"
    assert obs.filename == "2026-11-05-142107.md"
    assert obs.model == "claude-opus-5-5" and obs.language == "ja"
    assert obs.location["center"] == [34.0512, 134.2534]
    assert [l.key for l in obs.reading] == ["overall", "soil_surface", "basis", "next_to_observe"]
    assert obs.reading[0].verdict == "right"
    assert len(obs.data) == 1 and len(obs.record) == 2
    assert obs.unjudged() == obs.reading[1:]


def test_observation_roundtrip_is_stable():
    obs = Observation.parse(EXAMPLE)
    assert Observation.parse(obs.render()).render() == obs.render()


def test_observation_unquoted_yaml_date_is_read_as_text():
    text = EXAMPLE.replace("date: '2026-11-05'", "date: 2026-11-05")
    obs = Observation.parse(text)
    assert obs.date == "2026-11-05"
    assert "date: '2026-11-05'" in obs.render()


def test_reread_keeps_verdicts_and_moves_changed_marked_lines():
    obs = Observation.parse(EXAMPLE)
    obs.mark("soil_surface", "wrong", "北側は見える")
    new = [
        Line(
            "overall", "草丈 1 m を超えるセイタカアワダチソウとススキが大半。作物は見えない", 0.85
        ),  # 同じ文 → 判定を引き継ぐ
        Line("soil_surface", "北側に裸地がある", 0.7),  # 文が変わった → 前の判定の行は前の読みへ
        Line("plants", "ススキを刈るべき", 0.6),  # 判定の形 → uncertain
    ]
    obs.reread(new, "claude-code")
    assert obs.model == "claude-code"
    assert [l.key for l in obs.reading] == ["overall", "soil_surface", "uncertain"]
    assert obs.reading[0].verdict == "right" and obs.reading[0].confidence == 0.85
    assert obs.reading[1].verdict is None
    assert (
        len(obs.earlier) == 1 and obs.earlier[0].key == "soil_surface" and obs.earlier[0].verdict == "wrong"
    )
    assert len(obs.record) == 2  # 本人の行は残る
    assert "## Earlier reading" in obs.render()
    again = Observation.parse(obs.render())
    assert again.earlier == obs.earlier


def test_mark_and_say():
    obs = Observation.parse(EXAMPLE)
    l = obs.mark("basis", "right")
    assert l.judged and obs.reading[2].verdict == "right"
    with pytest.raises(KeyError):
        obs.mark("crops", "right")
    obs.say("saw", "水が溜まっていた")
    assert obs.record[-1] == Line("saw", "水が溜まっていた")
    with pytest.raises(ValueError):
        obs.say("overall", "本人は読みを書かない")


def test_observation_kind_candidate():
    obs = Observation.parse(EXAMPLE)
    assert obs.kind == "own" and "kind:" not in obs.render()  # 既定は書かない
    cand = Observation.parse(EXAMPLE.replace("language: ja", "language: ja\nkind: candidate"))
    assert cand.kind == "candidate" and "kind: candidate" in cand.render()
    with pytest.raises(ValueError):
        Observation("2026-11-05", "14:21:07", kind="rented")


def test_observation_ask_front_and_words():
    from seed.records import ASKS, ask_word, parse_asks

    obs = Observation.parse(EXAMPLE)
    assert obs.ask == [] and "ask:" not in obs.render()  # 無ければ書かない
    asked = Observation.parse(EXAMPLE.replace("language: ja", "language: ja\nask: [grow, soil]"))
    assert asked.ask == ["grow", "soil"]
    again = Observation.parse(asked.render())
    assert again.ask == ["grow", "soil"]  # 往復で変わらない
    with pytest.raises(ValueError):
        Observation("2026-11-05", "14:21:07", ask=["weather"])
    assert parse_asks("grow, soil,grow;names") == ["grow", "soil", "names"]
    assert parse_asks("") == []
    with pytest.raises(ValueError):
        parse_asks("grow,weather")
    assert ask_word("grow", "ja") == "この土地で何が育つか"
    assert ask_word("grow", "sw") == ask_word("grow", "en")
    assert ask_word("odd", "ja") == "odd"
    assert all(a in ask_word.__globals__["ASK_WORDS"]["ja"] for a in ASKS)


def test_observation_rejects_bad_date():
    with pytest.raises(ValueError):
        Observation("2026/11/05", "14:21:07")


def test_observation_empty_sections_render_none():
    obs = Observation("2026-11-05", "14:21:07", language="ja")
    text = obs.render()
    assert text.count(f"\n{EMPTY}\n") == 3 and "## Reading (none)" in text and "language: ja" in text


def test_unknown_heading_is_ignored():
    text = EXAMPLE + "\n## Something else\n- weird: line\n"
    obs = Observation.parse(text)
    assert len(obs.record) == 2 and not any(l.key == "weird" for l in obs.reading + obs.data + obs.record)


# ---- 公開ファイル


def make_public():
    obs = Observation.parse(EXAMPLE)
    pub = Public(
        id="2026-11-05-yoshino-ai-1",
        place="徳島県 吉野川市",
        since="2026-11-05",
        name="にじ",
        word="四年、何も入れていない畑。藍の跡地。",
        coord=coarse_coord(obs.location["center"]),
        what=["自給農", "放棄地", "藍"],
        next=["売る", "加工"],
        contact="discord:xxxx",
        language="ja",
    )
    pub.add(obs, [obs.reading[0], obs.data[0], obs.record[0]])
    return pub


def test_public_roundtrip_and_check():
    pub = make_public()
    assert pub.check() == []
    assert pub.coord == [34.05, 134.25] and pub.observations == 1
    text = pub.render()
    assert "## 2026-11-05" in text and "contact: discord:xxxx" in text and "language: ja" in text
    again = Public.parse(text)
    assert again.days == pub.days and again.front() == pub.front()
    assert "contact" not in again.front(for_index=True)


def test_public_check_finds_problems():
    pub = make_public()
    pub.id = "Yoshino Ai"
    pub.coord = [34.0512, 134.25]
    pub.word = "x" * 201
    pub.days["2026-11-05"].append(Line("said", "連絡は 090-1234-5678 か me@example.com へ <b>急ぎ</b>"))
    bad = pub.check()
    assert any("id" in b for b in bad) and any("coord" in b for b in bad)
    assert any("word" in b for b in bad) and any("HTML" in b for b in bad)
    assert any("電話" in b for b in bad)


def test_public_rejects_unknown_or_missing_keys():
    text = make_public().render()
    with pytest.raises(ValueError):
        Public.parse(text.replace("name: にじ", "name: にじ\nreal_name: 本名"))
    with pytest.raises(ValueError):
        Public.parse(text.replace("word: 四年、何も入れていない畑。藍の跡地。\n", ""))


# ---- 繋がりとフォルダー


def test_connection_roundtrip():
    c = Connection("2026-11-06", "abcd1234", "2026-11-05-yoshino-ai-1", "藍、うちも跡地です")
    assert Connection.parse(c.render()) == c
    assert Connection.parse("- not a connection") is None


def test_folder_init_and_place_data(tmp_path: Path):
    f = Folder(tmp_path / "seed")
    f.init()
    assert f.photos.is_dir() and f.observations.is_dir() and f.public.is_dir()
    assert f.place.read_text(encoding="utf-8").startswith("## Data\n(none)")
    assert "## Sell" in f.next.read_text(encoding="utf-8")
    assert f.place_data() == []
    f.place.write_text(
        "## Data\n- soil: 褐色低地土（出典: 農研機構、確認日 2026-11-05）\n\n## Record\n- note: 四年、何も入れていない\n",
        encoding="utf-8",
    )
    assert f.place_data() == [Line("soil", "褐色低地土（出典: 農研機構、確認日 2026-11-05）")]
    obs = Observation.parse(EXAMPLE)
    obs.write(f.observation_path(obs))
    assert f.list_observations() == [f.observations / "2026-11-05-142107.md"]
    assert Observation.read(f.list_observations()[0]).render() == obs.render()
    f.add_connection(Connection("2026-11-06", "a", "b", "w"))
    assert f.list_connections() == [Connection("2026-11-06", "a", "b", "w")]
    f.init()  # 二度目は何も壊さない
    assert f.list_connections() == [Connection("2026-11-06", "a", "b", "w")]


def test_previous_observation_same_place(tmp_path: Path):
    f = Folder(tmp_path / "seed")
    f.init()
    first = Observation.parse(EXAMPLE)  # 11-05 14:21、34.0512,134.2534
    far = Observation.parse(
        EXAMPLE.replace("time: '14:21:07'", "time: '15:00:00'").replace("134.2534", "134.40")
    )
    later = Observation.parse(EXAMPLE.replace("date: '2026-11-05'", "date: '2026-11-06'"))
    for o in (first, far, later):
        o.write(f.observation_path(o))
    prev = f.previous_observation(later)
    assert prev is not None and prev.time == "14:21:07"  # 8 km 東の物は飛ばす
    assert f.previous_observation(first) is None
    assert f.skill == f.root / "skill" and f.plan == f.root / "plan.md"


def test_previous_observation_same_kind(tmp_path: Path):
    """候補地の観察の前の観察に、自分の畑の観察を渡さない（その逆も）。"""
    f = Folder(tmp_path / "seed")
    f.init()
    own = Observation.parse(EXAMPLE)  # 11-05 14:21、自分の畑
    cand = Observation.parse(EXAMPLE.replace("time: '14:21:07'", "time: '15:00:00'"))
    cand.kind = "candidate"  # 同じ場所（100 m 以内）の候補地
    own2 = Observation.parse(EXAMPLE.replace("date: '2026-11-05'", "date: '2026-11-06'"))
    cand2 = Observation.parse(EXAMPLE.replace("date: '2026-11-05'", "date: '2026-11-07'"))
    cand2.kind = "candidate"
    for o in (own, cand, own2, cand2):
        o.write(f.observation_path(o))
    assert f.previous_observation(cand) is None  # 前にあるのは自分の畑の物だけ
    prev = f.previous_observation(own2)
    assert prev is not None and prev.date == "2026-11-05" and prev.kind == "own"  # 間の候補地は飛ばす
    prev = f.previous_observation(cand2)
    assert prev is not None and prev.time == "15:00:00" and prev.kind == "candidate"


# ---- 言語


def test_language_normalize_and_default(monkeypatch):
    assert lang.normalize("ja_JP.UTF-8") == "ja"
    assert lang.normalize("en-US") == "en"
    assert lang.normalize("C") is None and lang.normalize("C.UTF-8") is None and lang.normalize("") is None
    assert lang.default_language("sw") == "sw"
    for v in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    assert lang.default_language(None) == "ja"
    monkeypatch.setenv("LANGUAGE", "en:ja")
    assert lang.default_language(None) == "en"


def test_language_strings():
    assert lang.t("Reading", "ja") == "読み" and lang.t("right", "ja") == "合う"
    assert lang.t("Reading", "sw") == "Reading"  # 無い言語は en
    assert lang.t("unknown word", "ja") == "unknown word"


def test_mark_by_unique_part_of_text():
    obs = Observation(date="2026-11-05", time="14:21:07", language="ja")
    obs.reading = [
        Line("plants", "白い穂のススキらしいイネ科が上の層", 0.7),
        Line("plants", "蔓草が中の層", 0.6),
    ]
    got = obs.mark("plants", "wrong", "ススキではなくてオギ", text="ススキらしい")
    assert got.verdict == "wrong" and got.text.startswith("白い穂")
    with pytest.raises(KeyError):
        obs.mark("plants", "right", text="層")  # 二つに含まれる


def test_folder_add_place_data_merges(tmp_path):
    f = Folder(tmp_path / "seed")
    f.init()
    geo = Line("geology", "砂岩（出典: 産総研、確認日 2026-11-05）")
    assert f.add_place_data([geo]) == 1
    assert f.place_data() == [geo] and f.place_record() == []
    assert f.add_place_data([geo]) == 0  # 同じ行は増えない
    f.place.write_text(
        f.place.read_text(encoding="utf-8").replace("## Record\n(none)", "## Record\n- saw: 湿る"),
        encoding="utf-8",
    )
    assert f.add_place_data([geo, Line("soil", "褐色低地土（出典: 農研機構、確認日 2026-11-05）")]) == 1
    assert [l.key for l in f.place_data()] == ["geology", "soil"]
    assert [l.text for l in f.place_record()] == ["湿る"]  # Record は残る


PLAN_EXAMPLE = """---
since: '2026-11-20'
season: 2026-27 冬
language: ja
model: claude-code
---
## Plan (claude-code)
- ground: 元田んぼの硬盤層。耕さずに深根の緑肥で様子を見る案と、一度だけ起こす案 [0.50]  → farmer: right
- sow: 北側に小麦。12 月の初め [0.70]
- uncertain: 混植の案は、資料が無いので書いていない

## Data
- soil: 細粒質水田化褐色低地土（出典: 農研機構 日本土壌インベントリー、確認日 2026-11-02）

## Record
- decided: 南側は今年は草のまま
- did: 11-20 に北側の草を刈って敷いた
"""


def test_plan_parse_render_roundtrip():
    from seed.records import Plan

    plan = Plan.parse(PLAN_EXAMPLE)
    assert plan.since == "2026-11-20" and plan.season == "2026-27 冬" and plan.model == "claude-code"
    assert [l.key for l in plan.reading] == ["ground", "sow", "uncertain"]
    assert plan.reading[0].verdict == "right" and plan.data[0].key == "soil"
    assert [l.key for l in plan.record] == ["decided", "did"]
    assert Plan.parse(plan.render()).render() == plan.render()
    assert "since: '2026-11-20'" in plan.render()  # 前書きは段の形
    with pytest.raises(ValueError):
        Plan(since="20 Nov")


def test_plan_reread_keeps_marks_and_record_and_sorts_by_plan_keys():
    from seed.records import Plan

    plan = Plan.parse(PLAN_EXAMPLE)
    plan.reread(
        [
            Line("next_to_observe", "12 月に地面の湿り", 0.6),
            Line("sow", "北側に小麦。12 月の初め", 0.8),
            Line("ground", "元田んぼの硬盤層。耕さずに深根の緑肥で様子を見る案と、一度だけ起こす案", 0.6),
            Line("cover", "刈った草をそのまま敷くべき", 0.7),
        ],
        "claude-opus-5-5",
    )
    assert [l.key for l in plan.reading] == [
        "ground",
        "sow",
        "uncertain",
        "next_to_observe",
    ]  # 09 の順。判定は uncertain に
    assert plan.reading[0].verdict == "right"  # 同じ文には判定が残る
    assert [l.key for l in plan.record] == ["decided", "did"] and plan.model == "claude-opus-5-5"
    plan.say("decided", "小麦は 12 月 5 日")
    with pytest.raises(ValueError):
        plan.say("saw", "x")  # 計画の本人の行は decided と did だけ
    plan.mark("sow", "wrong", "種が無い")
    assert plan.reading[1].reason == "種が無い"


def test_plan_new_and_folder_path(tmp_path):
    from seed.records import Plan

    f = Folder(tmp_path / "seed")
    f.init()
    plan = Plan.new("ja", "冬", "2026-11-03")
    plan.write(f.plan)
    assert f.plan.name == "plan.md" and Plan.read(f.plan).season == "冬" and Plan.read(f.plan).reading == []


# ---- 合う／違うの付いた行（seed marks）

MARKED_OBSERVATIONS = {
    "2026-11-05-142107.md": """---
date: '2026-11-05'
time: '14:21:07'
photos: []
language: ja
---
## Reading (claude-opus-5-5)
- overall: 草が大半 [0.80]  → farmer: right
- plants: ススキらしいイネ科が優占 [0.70]  → farmer: wrong (ススキではなくてオギ)
- soil_surface: 地表は見えない [0.85]

## Data
(none)

## Record
- did: 見ただけ
""",
    "2026-11-02-153402.md": """---
date: '2026-11-02'
time: '15:34:02'
photos: []
language: ja
---
## Reading (claude-opus-5-5)
- soil_surface: 北側は湿って黒い [0.60]  → farmer: wrong
- next_to_observe: 根元を地面に近く撮る [0.70]

## Earlier reading
- plants: 草丈 1 m のススキ [0.50]  → farmer: wrong (3 m はある)

## Data
(none)

## Record
(none)
""",
}
MARKED_PLAN = PLAN_EXAMPLE.replace(
    "- sow: 北側に小麦。12 月の初め [0.70]",
    "- sow: 北側に小麦。12 月の初め [0.70]  → farmer: wrong (種が無い)",
).replace("## Data", "## Earlier plan\n- cover: 刈った草を敷く [0.70]  → farmer: right\n\n## Data")


def make_marked_folder(root: Path) -> Folder:
    """観察二つと plan.md に合う／違うを付けたフォルダー。test_cli でも使う。"""
    f = Folder(root)
    f.init()
    for name, text in MARKED_OBSERVATIONS.items():
        (f.observations / name).write_text(text, encoding="utf-8")
    f.plan.write_text(MARKED_PLAN, encoding="utf-8")
    return f


def test_folder_marks_order_and_fields(tmp_path):
    from seed.records import Mark

    f = make_marked_folder(tmp_path / "seed")
    before = {p: p.read_text(encoding="utf-8") for p in f.root.rglob("*.md")}
    marks = f.marks()
    # 観察は古い順、中は Reading → Earlier reading、plan.md は最後に Plan → Earlier plan
    assert [(m.when, m.key, m.verdict, m.earlier) for m in marks] == [
        ("2026-11-02 15:34:02", "soil_surface", "wrong", False),
        ("2026-11-02 15:34:02", "plants", "wrong", True),
        ("2026-11-05 14:21:07", "overall", "right", False),
        ("2026-11-05 14:21:07", "plants", "wrong", False),
        ("plan", "ground", "right", False),
        ("plan", "sow", "wrong", False),
        ("plan", "cover", "right", True),
    ]
    assert [m.source for m in marks] == ["observation"] * 4 + ["plan"] * 3
    assert marks[0].reason is None and marks[1].reason == "3 m はある"
    assert marks[3] == Mark(
        "2026-11-05 14:21:07",
        "plants",
        "ススキらしいイネ科が優占",
        "wrong",
        "ススキではなくてオギ",
        "observation",
        False,
        0.7,
    )
    assert marks[3].name == "2026-11-05-142107" and marks[5].name == "plan"
    assert {p: p.read_text(encoding="utf-8") for p in f.root.rglob("*.md")} == before  # 読むだけ


def test_folder_marks_empty(tmp_path):
    f = Folder(tmp_path / "seed")
    assert f.marks() == []  # フォルダーがまだ無い
    f.init()
    Observation.parse(EXAMPLE.replace("  → farmer: right", "")).write(f.observations / "2026-11-05-142107.md")
    assert f.marks() == []  # 判定の無い行だけ


# ---------------------------------------------------------------- 公開の写真


def test_public_photo_names_round_trip():
    from seed import records as R

    for rel in ("photos/2026-11-05/142107.jpg", "photos/2026-11-05/142107-12.jpg"):
        name = R.public_photo_name(rel)
        assert name and R.safe_photo_name(name) and R.photo_rel(name) == rel
    assert R.public_photo_name("photos/2026-11-05/142107.jpg") == "2026-11-05_142107.jpg"
    for bad in ("../x.jpg", "a/b.jpg", "x.png", "a..b.jpg", ".x.jpg", "", None):
        assert not R.safe_photo_name(bad)
    assert R.public_photo_name("elsewhere/2026-11-05/1.jpg") is None
    assert R.photo_rel("plain.jpg") is None


def test_public_photo_lines_parse_split_and_check():
    p = Public(id="a-1", place="徳島県", since="2026-11-05", name="にじ", word="畑", language="ja")
    p.days["2026-11-04"] = [Line("photo", "2026-11-04_101500.jpg"), Line("did", "見た")]
    p.days["2026-11-05"] = [Line("photo", "2026-11-05_142107.jpg"), Line("overall", "草", 0.8, "right")]
    q = Public.parse(p.render())
    assert q.check() == [] and q.photo_names() == ["2026-11-04_101500.jpg", "2026-11-05_142107.jpg"]
    shots, lines = q.day_parts("2026-11-05")
    assert shots == ["2026-11-05_142107.jpg"] and [l.key for l in lines] == ["overall"]
    assert q.cover() == "2026-11-05_142107.jpg"
    q.days["2026-11-05"].append(Line("photo", "../etc.jpg"))
    assert any("photo の行" in b for b in q.check())
    q.days["2026-11-05"] = [Line("photo", f"2026-11-05_14210{i}.jpg") for i in range(4)]
    assert any("一日 3 枚" in b for b in q.check())
    q.days = {f"2026-10-{d:02d}": [Line("photo", f"2026-10-{d:02d}_1.jpg")] for d in range(1, 14)}
    assert any("12 枚" in b for b in q.check())


def test_tags_key_after_crops_and_ten_states():
    from seed.records import READING_KEYS, TAG_STATES

    i = READING_KEYS.index
    assert (
        i("crops") < i("emerging") < i("tags") < i("zone") < i("water")
    )  # 芽生えと違う所は fieldnotes から（11-11）
    assert len(TAG_STATES["ja"]) == 10 and len(TAG_STATES["en"]) == 10


# ---- 本人が手で書き足した物は、書き戻しで消えない


# 今の記録の形のまま（seed が書く形）。読んで書き戻すと一文字も変わらない
CURRENT_OBSERVATION = """---
date: '2026-11-05'
time: '14:21:07'
photos: [photos/2026-11-05/142107.jpg]
location:
  center: [34.0512, 134.2534]
  points: 1
  extent_m: 0
model: claude-opus-5-5
language: ja
---

## Reading (claude-opus-5-5)
- overall: 草丈 1 m を超えるセイタカアワダチソウとススキが大半。作物は見えない [0.80]  → farmer: right
- soil_surface: 地表は見えない。裸地は無い [0.85]

## Earlier reading
- plants: 草丈 1 m のススキ [0.50]  → farmer: wrong (3 m はある)

## Data
- geology: 和泉層群の砂岩・泥岩（出典: 産総研 シームレス地質図 V2、確認日 2026-11-05）

## Record
- did: 今日は見ただけ。刈っていない
"""

HAND_WRITTEN = """---
date: '2026-11-05'
time: '14:21:07'
photos: []
weather_memo: 朝は霧
language: ja
---
## Reading (claude-opus-5-5)
- overall: 草が大半 [0.80]
読みの下に本人が書いた一言

## メモ
祖父の代は桑畑だったと聞いた。
- weird: 行の形でも読まない

## Data
(none)
資料の下の文

## Record
- did: 見ただけ
北の端で、
キジを見た。

- saw: 草が低い
## 後で
"""

# HAND_WRITTEN を書き戻した形。知っている見出しの下の文はその行の後、知らない見出しは Record の後、知らない鍵は前書きの最後
HAND_WRITTEN_RENDERED = """---
date: '2026-11-05'
time: '14:21:07'
photos: []
model: claude-opus-5-5
language: ja
weather_memo: 朝は霧
---

## Reading (claude-opus-5-5)
- overall: 草が大半 [0.80]

読みの下に本人が書いた一言

## Data
資料の下の文

## Record
- did: 見ただけ
- saw: 草が低い

北の端で、
キジを見た。

## メモ
祖父の代は桑畑だったと聞いた。
- weird: 行の形でも読まない

## 後で
"""


def test_current_format_is_written_back_unchanged():
    from seed.records import Plan

    texts = [CURRENT_OBSERVATION, Observation("2026-11-05", "14:21:07", language="ja").render()]
    texts += [Observation.parse(t).render() for t in MARKED_OBSERVATIONS.values()]
    for text in texts:
        assert Observation.parse(text).render() == text
    plans = [Plan.parse(PLAN_EXAMPLE).render(), Plan.parse(MARKED_PLAN).render(), Plan.new("ja").render()]
    for text in plans:
        assert Plan.parse(text).render() == text


def test_empty_reading_heading_is_not_read_as_a_model():
    obs = Observation.parse(Observation("2026-11-05", "14:21:07").render())
    assert obs.model is None and "model:" not in obs.render()


def test_hand_written_text_is_kept_but_not_read():
    obs = Observation.parse(HAND_WRITTEN)
    # 読む側は今のまま。知らない物は行として読まない
    assert [l.key for l in obs.reading] == ["overall"] and obs.data == []
    assert [l.key for l in obs.record] == ["did", "saw"]
    assert not any(l.key == "weird" for l in obs.reading + obs.data + obs.record)
    assert obs.kept_front == {"weather_memo": "朝は霧"}
    assert obs.render() == HAND_WRITTEN_RENDERED
    again = Observation.parse(obs.render())
    assert again.render() == obs.render()
    assert again.record == obs.record and again.reading == obs.reading


def test_reread_moves_reading_text_to_earlier_and_keeps_record_text():
    obs = Observation.parse(HAND_WRITTEN)
    obs.reread([Line("overall", "草とススキ", 0.7)], "claude-opus-5-5")
    text = obs.render()
    assert "## Earlier reading\n読みの下に本人が書いた一言\n" in text
    reading_part = text.split("## Reading")[1].split("## Earlier reading")[0]
    assert "一言" not in reading_part
    assert (
        "北の端で、\nキジを見た。" in text
        and "祖父の代は桑畑だった" in text
        and "weather_memo: 朝は霧" in text
    )
    assert Observation.parse(text).render() == text


def test_plan_keeps_hand_written_text():
    from seed.records import Plan

    text = (
        PLAN_EXAMPLE.replace("language: ja\n", "language: ja\nfield_name: 北の田\n")
        .replace(
            "- sow: 北側に小麦。12 月の初め [0.70]\n",
            "- sow: 北側に小麦。12 月の初め [0.70]\n計画への本人の言葉\n",
        )
        .replace("- decided: 南側は今年は草のまま\n", "- decided: 南側は今年は草のまま\n隣の人と話してから\n")
        + "\n## 種の在庫\n小麦 2 kg\n"
    )
    plan = Plan.parse(text)
    assert [l.key for l in plan.reading] == ["ground", "sow", "uncertain"]
    assert [l.key for l in plan.record] == ["decided", "did"]
    out = plan.render()
    for kept in (
        "field_name: 北の田\n---",
        "計画への本人の言葉",
        "隣の人と話してから",
        "## 種の在庫\n小麦 2 kg\n",
    ):
        assert kept in out
    assert out.index("隣の人と話してから") > out.index("- did:") and out.endswith("## 種の在庫\n小麦 2 kg\n")
    assert Plan.parse(out).render() == out
    plan.reread([Line("ground", "耕さない", 0.6)], "claude-code")
    out = plan.render()
    assert (
        "## Earlier plan" in out
        and "計画への本人の言葉" in out.split("## Earlier plan")[1].split("## Data")[0]
    )
    assert "隣の人と話してから" in out and Plan.parse(out).render() == out


def test_text_before_first_heading_is_kept():
    from seed.records import Plan

    text = CURRENT_OBSERVATION.replace(
        "---\n\n## Reading", "---\n去年の秋に借りた畑。\n\n二枚目の段落\n## Reading"
    )
    obs = Observation.parse(text)
    out = obs.render()
    assert "---\n\n去年の秋に借りた畑。\n\n二枚目の段落\n\n## Reading (claude-opus-5-5)\n" in out
    assert out == CURRENT_OBSERVATION.replace(
        "---\n\n## Reading", "---\n\n去年の秋に借りた畑。\n\n二枚目の段落\n\n## Reading"
    )
    assert (
        Observation.parse(out).render() == out
        and obs.reading == Observation.parse(CURRENT_OBSERVATION).reading
    )
    plan_text = (
        Plan.parse(PLAN_EXAMPLE).render().replace("---\n\n## Plan", "---\n\n田の名は北の田\n\n## Plan")
    )
    assert Plan.parse(plan_text).render() == plan_text


def test_duplicate_headings_are_merged_not_lost():
    from seed.records import Plan

    text = (
        CURRENT_OBSERVATION
        + "\n## Record\n- saw: 二つ目の Record の行\n二つ目の下の文\n\n## Data\n- soil: 後の資料\n"
    )
    obs = Observation.parse(text)
    assert [l.text for l in obs.record] == ["今日は見ただけ。刈っていない", "二つ目の Record の行"]
    assert [l.key for l in obs.data] == ["geology", "soil"]
    out = obs.render()
    assert out.count("## Record") == 1 and out.count("## Data") == 1
    assert out.endswith(
        "## Record\n- did: 今日は見ただけ。刈っていない\n- saw: 二つ目の Record の行\n\n二つ目の下の文\n"
    )
    assert Observation.parse(out).render() == out
    plan = Plan.parse(
        PLAN_EXAMPLE + "\n## Plan (claude-code)\n- cover: 後の計画の行 [0.40]  → farmer: right\n"
    )
    assert [l.key for l in plan.reading] == ["ground", "sow", "uncertain", "cover"]
    assert plan.render().count("## Plan") == 1 and Plan.parse(plan.render()).render() == plan.render()


# ---------------------------------------------------------------- fieldnotes から足した物（記録の形 §3、§21。11-11）


def test_observation_keeps_cover_and_checks_and_marks_a_check():
    from seed.records import Observation

    text = """---
date: '2026-10-28'
time: '12:17:01'
photos:
- photos/2026-10-28/121701.jpg
language: ja
coverage:
  vegetation: 91.8
  goldenrod: 0.0
cover_range:
  vegetation: [80.1, 97.3]
cover_model: sam-3.1
---
## Reading (claude-opus-5-5)
- dominant: オギ (Miscanthus sacchariflorus) ~55% [0.80]
- acidity: unclear; evidence: 判断できない [0.30]

## Checks (claude-opus-5-5)
- h3: agrees: 倒伏が無い [0.85]
- h8: cannot tell: 土が見えない [0.90]

## Data
(none)

## Record
(none)
"""
    obs = Observation.parse(text)
    assert obs.coverage == {"vegetation": 91.8, "goldenrod": 0.0} and obs.cover_range["vegetation"] == [
        80.1,
        97.3,
    ]
    assert [l.key for l in obs.checks] == ["h3", "h8"] and obs.checks_model == "claude-opus-5-5"
    obs.mark("h3", "right")
    obs.mark("acidity", "wrong", "スギナが少ない")
    again = Observation.parse(obs.render())
    assert again.checks[0].verdict == "right" and again.reading[1].reason == "スギナが少ない"
    assert again.cover_model == "sam-3.1" and "## Checks (claude-opus-5-5)" in obs.render()
    # 読み直しても確かめは残り、確かめ直すと同じ文の判定は引き継ぐ
    again.reread([Line("overall", "密生", 0.8)], "claude-opus-5-5")
    assert again.checks[0].verdict == "right"
    again.recheck([Line("h3", "agrees: 倒伏が無い", 0.85), Line("h8", "agrees: 湿っている", 0.5)], "m2")
    assert again.checks[0].verdict == "right" and again.checks_model == "m2"


def test_hypotheses_add_mark_expect_roundtrip(tmp_path):
    from seed.records import Hypotheses

    h = Hypotheses(language="ja")
    h.add("吉野川の平野の南側の微高地（出典: 本人、2026-10-28）")
    h.add("南に水田が並ぶ", 0.6)
    h.mark("h1", "right")
    h.set_expect(
        [Line("h1", "holds: 水が溜まらない; fails: 溜まる; visible: yes", 0.6), Line("x", "no")], "m"
    )
    path = tmp_path / "hypotheses.md"
    h.write(path)
    back = Hypotheses.read(path)
    assert [l.key for l in back.lines] == ["h1", "h2"] and back.lines[0].verdict == "right"
    assert [l.key for l in back.expect] == ["h1"] and back.model == "m"
    assert back.next_key() == "h3" and Hypotheses.read(tmp_path / "none.md").lines == []
