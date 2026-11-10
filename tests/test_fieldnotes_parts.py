# SPDX-License-Identifier: AGPL-3.0-or-later
"""fieldnotes から seed に移した物（11-11 の一本化）: 歩いた写真の位置、SAM の覆い％と名詞、声、草の読み、仮説の確かめ、
刈り方、読みに添える畑の物、MCP、命令。Claude と Meta は呼ばない（local.ask と SAM と書き取りを差し替える）。"""

from __future__ import annotations

import io
import json
import wave

import httpx
import numpy as np
import pytest
from PIL import Image
from test_photos import make_jpeg

from seed import checks, cli, concepts, fieldctx, local, plants, voice, walk
from seed.records import Folder, Hypotheses, Line, Observation, Plan

# a 40 m x 30 m parcel; the photo points below fall in its corners and middle
W, S, E, N = 134.4450, 34.0800, 134.4454, 34.0803
RING = [[W, S], [E, S], [E, N], [W, N], [W, S]]
PARCEL = {"type": "Polygon", "coordinates": [RING]}


def entries():
    """Three photos in walk order: NW corner, middle, S edge."""
    return [
        {"file": "100000", "time": "10:00:00", "lat": N - 0.00002, "lon": W + 0.00002, "facing": 271.5},
        {"file": "101000", "time": "10:10:00", "lat": (S + N) / 2, "lon": (W + E) / 2, "facing": None},
        {"file": "102000", "time": "10:20:00", "lat": S + 0.00002, "lon": (W + E) / 2, "facing": 180.0},
    ]


# ---------------------------------------------------------------- walk.py


def test_positions_in_the_parcel_else_the_walk_else_none(tmp_path):
    walk.save_parcel(tmp_path, PARCEL)
    rings = walk.parcels(tmp_path)
    assert walk.labels(entries(), rings) == {
        "100000": "1 of 3, 10:00, NW corner, facing W",
        "101000": "2 of 3, 10:10, middle",
        "102000": "3 of 3, 10:20, S edge, facing S",
    }
    assert "farm parcel" in walk.frame_note(entries(), rings)
    # no parcel: the walk's own extent (it reached only the parcel's west half, so the middle is its east end)
    assert walk.labels(entries(), [])["101000"] == "2 of 3, 10:10, E edge"
    assert "the area the walk covered" in walk.frame_note(entries(), [])
    bare = [{**e, "lat": None, "lon": None, "facing": None} for e in entries()]
    assert walk.labels(bare, [])["100000"] == "1 of 3, 10:00" and "no location" in walk.frame_note(bare, [])


def test_photos_outside_the_parcel_say_so_with_their_distance():
    """Niihama 2026-10-29: 2 of 24 photos in the parcel; the reading's "S edge" was a terrace 30-40 m S of it."""
    south = S - 35 / walk.EARTH_M_PER_DEG
    found = [
        {"file": "a", "time": "10:00:00", "lat": (S + N) / 2, "lon": (W + E) / 2},
        {"file": "b", "time": "10:10:00", "lat": south, "lon": (W + E) / 2, "facing": 180.0},
        {"file": "c", "time": "10:20:00", "lat": south, "lon": E + 0.00004},
    ]
    labels = walk.labels(found, [RING])
    assert labels["a"] == "1 of 3, 10:00, NW corner, in the parcel"
    assert labels["b"] == "2 of 3, 10:10, SW corner, outside the parcel, 35 m S, facing S"
    note = walk.frame_note(found, [RING])
    assert "only 1 of 3 lie in the farm's parcel" in note and "never a corner or edge of the field" in note
    assert walk.outside(E + 10 / walk.EARTH_M_PER_DEG, (S + N) / 2, RING)[1] == "E"
    assert walk.sample(list(range(10)), 3) == [0, 4, 9] and walk.sample([1, 2], 5) == [1, 2]


# ---------------------------------------------------------------- SAM と名詞


class FakeSam:
    """segment_concepts without the API: vegetation covers the left half, bare soil the top quarter."""

    def __init__(self):
        self.calls = []

    def __call__(self, photo, nouns, max_side=2048):
        from seed.sam import ConceptResult, Instance, SegmentResult

        self.calls.append((photo.name, list(nouns)))
        with Image.open(photo) as im:
            w, h = im.size
        found = {}
        for noun in nouns:
            union = np.zeros((h, w), dtype=np.uint8)
            if noun == "vegetation":
                union[:, : w // 2] = 1
            elif noun == "bare soil":
                union[: h // 4, :] = 1
            inst = [Instance(1, (0, 0, w, h), int(union.sum()), 0.9)] if union.any() else []
            found[noun] = ConceptResult(noun, w, h, inst, union)
        return SegmentResult(photo, w, h, found)


def field(tmp_path, n_photos=2) -> tuple[Folder, Observation]:
    folder = Folder(tmp_path / "f")
    folder.init()
    rels = []
    for i in range(n_photos):
        rel = f"photos/2026-10-28/12170{i}.jpg"
        make_jpeg(folder.root / rel, size=(64, 48))
        rels.append(rel)
    obs = Observation(date="2026-10-28", time="12:17:00", photos=rels, language="ja")
    obs.reading = [
        Line(
            "dominant",
            "オギ (Miscanthus sacchariflorus) ~55%; セイタカアワダチソウ (Solidago altissima) ~35%",
            0.8,
        )
    ]
    obs.write(folder.observation_path(obs))
    return folder, obs


def fake_ask(answers, calls=None):
    def ask(folder, system, user, schema, model=None, *a, **k):
        if calls is not None:
            calls.append((system, user))
        return answers.pop(0), "claude-test"

    return ask


def test_nouns_from_claude_then_sam_cover_and_overlays(tmp_path):
    folder, obs = field(tmp_path)
    assert concepts.species_in(obs) == [
        ("オギ", "Miscanthus sacchariflorus"),
        ("セイタカアワダチソウ", "Solidago altissima"),
    ]
    calls = []
    ask = fake_ask(
        [
            {
                "lines": [
                    {"scientific": "Solidago altissima", "noun": "Yellow Flower Clusters", "confidence": 0.6}
                ]
            }
        ],
        calls,
    )
    fc = concepts.ensure(folder, concepts.species_in(obs), ask=ask)
    assert "yellow flower clusters" in fc.nouns() and "vegetation" in fc.nouns()
    assert "Solidago altissima" in calls[0][1]
    sam = FakeSam()
    concepts.segment_field(folder, obs, run=sam)
    assert obs.coverage["vegetation"] == 50.0 and obs.coverage["bare soil"] == 25.0
    assert obs.cover_range["vegetation"] == [50.0, 50.0] and obs.cover_model == "sam-3.1"
    assert (folder.sam_dir(obs) / "1.jpg").exists() and (folder.sam_dir(obs) / "2.jpg").exists()
    text = folder.concepts.read_text(encoding="utf-8")
    assert (
        "- concept: vegetation | for: (all plants) | by: default | last: 2026-10-28 50.0%, 2 objects" in text
    )
    # 本人が違うと付けた句は次から聞かない。共有の帳面に数が残る
    concepts.mark(folder, "yellow flower clusters", "wrong", "花だけ", "goldenrod plumes")
    nouns = concepts.FieldConcepts.load(folder).nouns()
    assert "yellow flower clusters" not in nouns and "goldenrod plumes" in nouns
    shared = (folder.root / concepts.SHARED_FILE).read_text(encoding="utf-8")
    assert (
        "yellow flower clusters | for: Solidago altissima | right: 0 | wrong: 1 | last reason: 花だけ"
        in shared
    )


def test_sam_with_nothing_found_is_zero_not_absent():
    from seed.sam import records_to_concept

    got = records_to_concept("leaf", 10, 8, [])
    assert got.coverage == 0.0 and got.union.shape == (8, 10) and got.instances == []


# ---------------------------------------------------------------- 声


def wav_bytes(rate=24_000, channels=1, seconds=0.2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(np.zeros(int(rate * seconds) * channels, dtype=np.int16).tobytes())
    return buf.getvalue()


def test_transcribe_request_and_conversion(monkeypatch):
    sent = {}

    class Reply:
        status_code = 200

        def json(self):
            return {"transcript": " 刈った "}

    def post(url, headers, files, timeout):
        sent.update(
            url=url,
            auth=headers["Authorization"],
            request=json.loads(files["request"][1]),
            audio=files["audio"][1],
        )
        return Reply()

    monkeypatch.setattr(httpx, "post", post)
    data = wav_bytes()
    assert voice.transcribe(data, ["オギ"], "ja", key="test-key") == "刈った"
    assert sent["url"] == voice.URL and sent["auth"] == "Bearer test-key" and sent["audio"] == data
    assert sent["request"] == {
        "model": "muse-voice-transcribe-1.0",
        "audioEncoding": "WAV",
        "mode": "PUSH_TO_TALK",
        "keywords": ["オギ"],
        "languageBias": ["Japanese"],
    }
    assert voice.bias("zh") == ["Mandarin Chinese"] and voice.bias("xx") == []
    with wave.open(io.BytesIO(voice.to_wav(wav_bytes(rate=44_100, channels=2)))) as f:
        assert (f.getnchannels(), f.getsampwidth(), f.getframerate()) == (1, 2, 24_000)


def test_voice_is_kept_written_down_and_sorted(tmp_path):
    folder, obs = field(tmp_path)
    obs.reading.append(Line("acidity", "5.0-5.5; evidence: スギナ", 0.4))
    rec = tmp_path / "rec.m4a"
    rec.write_bytes(b"audio")
    heard = []

    def transcriber(data, keywords, lang, key):
        heard.append((data, keywords, lang))
        return "東側を刈った。酸度は違う、スギナが少ない。"

    ask = fake_ask(
        [
            {
                "lines": [
                    {"kind": "did", "text": "東側を刈った", "ref": "", "verdict": "", "reason": ""},
                    {
                        "kind": "verdict",
                        "text": "",
                        "ref": "acidity",
                        "verdict": "wrong",
                        "reason": "スギナが少ない",
                    },
                    {"kind": "verdict", "text": "", "ref": "crops", "verdict": "right", "reason": ""},
                ]
            }
        ]
    )
    _text, _changed = voice.file_voice(folder, obs, rec, transcriber=transcriber, ask=ask)
    kept = list((folder.photos / "2026-10-28").glob("*-voice.m4a"))
    assert len(kept) == 1 and kept[0].read_bytes() == b"audio" and heard[0][2] == "ja"
    assert "Miscanthus sacchariflorus" in heard[0][1]
    said = [l for l in obs.record if l.key == "said"]
    assert said and said[0].text.endswith(f"（書き取り: muse-voice-transcribe-1.0、{kept[0].name}）")
    assert ("did", "東側を刈った（声から: claude-test）") in [(l.key, l.text) for l in obs.record]
    assert obs.reading[1].verdict == "wrong" and obs.reading[1].reason == "スギナが少ない"
    assert any(
        l.key == "saw" and l.text.startswith("crops: right") for l in obs.record
    )  # 無い行への判定は見たこと


# ---------------------------------------------------------------- 草の読み


def test_plant_note_is_asked_once_and_fed_back(tmp_path):
    folder, _obs = field(tmp_path)
    calls = []
    ask = fake_ask(
        [{"name": "オギ", "lines": [{"aspect": "moisture", "text": "湿りを好む", "confidence": 0.7}]}], calls
    )
    note = plants.ecology(folder, "オギ", "Miscanthus sacchariflorus", "ja", ask=ask)
    assert note.lines[0].render() == "- moisture: 湿りを好む [0.70]"
    assert (
        plants.ecology(folder, "オギ", "Miscanthus sacchariflorus", "ja", ask=ask).name == "オギ"
    )  # 二度目は聞かない
    assert len(calls) == 1
    path = plants.PlantNote.path_for(folder, "Miscanthus sacchariflorus")
    p = plants.PlantNote.parse(path.read_text(encoding="utf-8"))
    p.lines[0] = p.lines[0].marked("wrong", "乾いた所にも出る")
    p.save(folder)
    lines = plants.notes_for_prompt(folder, plants.species_of(folder))
    assert lines[0] == "オギ (Miscanthus sacchariflorus):" and "本人は違うと言った" in lines[1]


# ---------------------------------------------------------------- 仮説の確かめ


def test_expect_then_check_only_what_photos_can_show(tmp_path, monkeypatch):
    folder, obs = field(tmp_path)
    h = Hypotheses(language="ja")
    h.add("微高地にある（出典: 本人）")
    h.add("2000 年前の大水が土を置いた（出典: 本人）")
    h.add("低い氾濫原")
    h.mark("h3", "wrong", "標高では分からない")
    h.write(folder.hypotheses)
    calls = []
    answers = [
        {
            "lines": [
                {
                    "key": "h1",
                    "holds": "水が溜まらない; 草が直立",
                    "fails": "溜まる",
                    "visible": True,
                    "confidence": 0.6,
                },
                {"key": "h2", "holds": "見えない", "fails": "見えない", "visible": False, "confidence": 0.1},
            ]
        },
        {
            "lines": [
                {"key": "h1", "result": "agrees", "seen": "水たまりが無い", "confidence": 0.7},
                {"key": "h2", "result": "agrees", "seen": "聞いていない", "confidence": 0.9},
            ]
        },
    ]
    monkeypatch.setattr(local, "ask", fake_ask(answers, calls))
    h = checks.expect(folder)
    assert [l.key for l in h.expect] == ["h1", "h2"] and h.model == "claude-test"
    assert h.expect[0].text == "holds: 水が溜まらない, 草が直立; fails: 溜まる; visible: yes"
    assert "h3" not in calls[0][1]  # 本人が違うと付けた仮説は見込みを書かない
    lines = checks.check(folder, obs)
    assert [l.render() for l in lines] == [
        "- h1: agrees: 水たまりが無い [0.70]"
    ]  # 見えない h2 は聞かず、答えても入れない
    assert str(folder.root / obs.photos[0]) in calls[1][1]
    assert obs.checks_model == "claude-test"


# ---------------------------------------------------------------- 刈り方


def test_cut_plan_replaces_only_the_cut_lines(tmp_path, monkeypatch, seedfolder):
    from seed import settings as settings_mod
    from seed.client import Reading

    st = settings_mod.load(seedfolder)
    folder = st.records
    folder.init()
    plan = Plan.new("ja", today="2026-10-29")
    plan.reading = [Line("sow", "クリムソンクローバー", 0.6, "right"), Line("cut", "古い刈り方", 0.5)]
    asked = {}

    def fake_plan(folder, plan, model=None, effort="medium", timeout=0, cut=False):
        asked["cut"] = cut
        return Reading(
            [Line("cut", "南の縁を 40 cm で", 0.6), Line("sow", "聞いていない", 0.5)], [], "claude-test", {}
        )

    monkeypatch.setattr(local, "plan", fake_plan)
    cli.plan_local(st, folder, plan, cut=True)
    assert asked["cut"] is True
    assert [(l.key, l.text, l.verdict) for l in plan.reading] == [
        ("cut", "南の縁を 40 cm で", None),
        ("sow", "クリムソンクローバー", "right"),
    ]
    assert "最初の一刈り" in local.plan_prompt(folder, plan, [], cut=True)
    assert "最初の一刈り" not in local.plan_prompt(folder, plan, [])


# ---------------------------------------------------------------- 読みに添える畑の物


def test_field_context_has_positions_cover_and_plant_notes(tmp_path):
    folder, obs = field(tmp_path, n_photos=3)
    walk.save_parcel(folder.root, PARCEL)
    obs.coverage, obs.cover_range, obs.cover_model = (
        {"vegetation": 50.0},
        {"vegetation": [40.0, 60.0]},
        "sam-3.1",
    )
    plants.PlantNote(
        "オギ", "Miscanthus sacchariflorus", "m", "2026-10-28", [Line("moisture", "湿り", 0.7)]
    ).save(folder)
    text = "\n".join(fieldctx.lines(folder, obs))
    assert "## 写真の位置" in text and "121700: 1 of 3" in text
    assert "- vegetation: 50.0%（40.0〜60.0）" in text and "0 はその句が何にも当たらなかった" in text
    assert "オギ (Miscanthus sacchariflorus):" in text
    assert "34.05" not in text  # 座標そのものは書かない
    prompt = local.prompt(folder, obs, None)
    assert "## 写真の位置" in prompt and prompt.index("## 写真の位置") < prompt.index("## Data")


# ---------------------------------------------------------------- 命令と MCP


def run(folder, *argv):
    return cli.main([*argv, "--folder", str(folder)])


def test_hypothesis_commands_and_marks(seedfolder, capsys):
    assert run(seedfolder, "hypothesis", "add", "南に水田が並ぶ（出典: 本人）") == 0
    assert run(seedfolder, "hypothesis", "add", "伏流水が 4 m 下（出典: 本人）") == 0
    assert run(seedfolder, "mark", "hypotheses", "h2", "wrong", "--reason", "井戸は 6 m") == 0
    capsys.readouterr()
    assert run(seedfolder, "hypothesis", "list") == 0
    out = capsys.readouterr().out
    assert "- h1: 南に水田が並ぶ（出典: 本人）" in out and "→ farmer: wrong (井戸は 6 m)" in out


def test_sam_and_voice_need_the_meta_key(seedfolder, capsys, monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(seedfolder / "no-config"))
    st = __import__("seed.settings", fromlist=["load"]).load(seedfolder)
    obs = Observation(date="2026-10-28", time="12:00:00", photos=[])
    st.records.init()
    obs.write(st.records.observation_path(obs))
    assert run(seedfolder, "sam") == 1
    assert "meta_key" in capsys.readouterr().err
    assert run(seedfolder, "voice", "x.m4a") == 1


def test_voice_text_goes_into_the_newest_observation(seedfolder, monkeypatch):
    st = __import__("seed.settings", fromlist=["load"]).load(seedfolder)
    st.records.init()
    for t in ("10:00:00", "11:00:00"):
        obs = Observation(date="2026-10-28", time=t, photos=[])
        obs.write(st.records.observation_path(obs))
    monkeypatch.setattr(
        local,
        "ask",
        fake_ask([{"lines": [{"kind": "saw", "text": "芽", "ref": "", "verdict": "", "reason": ""}]}]),
    )
    assert run(seedfolder, "voice", "--text", "芽が出た") == 0
    newest = Observation.read(st.records.observations / "2026-10-28-110000.md")
    assert [l.key for l in newest.record] == ["said", "saw"] and "芽が出た" in newest.record[0].text


def test_mcp_tools_read_mark_note_and_timeline(tmp_path, seedfolder):
    import asyncio

    from seed import mcp_server
    from seed import settings as settings_mod

    st = settings_mod.load(seedfolder)
    st.records.init()
    obs = Observation(date="2026-10-28", time="12:00:00", photos=[], language="ja")
    obs.reading = [Line("overall", "密生", 0.8)]
    obs.checks = [Line("h1", "agrees: 水たまりが無い", 0.7)]
    obs.write(st.records.observation_path(obs))
    server = mcp_server.build(seedfolder)

    def call(name, **kw):
        result = asyncio.run(server.call_tool(name, kw))
        blocks = result[0] if isinstance(result, tuple) else result
        blocks = getattr(blocks, "content", blocks)
        return "\n".join(getattr(b, "text", "") for b in blocks)

    assert "observations: 2026-10-28-120000" in call("fields")
    assert call("mark", target="2026-10-28-120000", key="h1", verdict="right").endswith("→ farmer: right")
    assert "| 2026-10-28 12:00:00 | 密生 | - | 1 | 0 | h1 agrees |" in call("timeline")
    assert call("note", text="昔はホウレンソウの産地").startswith("- note: 昔はホウレンソウの産地（本人、")
    assert "ホウレンソウ" in call("land")


@pytest.mark.parametrize("name", ["land_checks"])
def test_checks_screen_builds_and_marks(name, seedfolder):
    from test_app import FakePage, texts

    from seed.app.main import App

    app = App(FakePage(), str(seedfolder))
    app.lang = "ja"
    h = Hypotheses(language="ja")
    h.add("微高地にある")
    h.write(app.folder.hypotheses)
    app.route_change(path=f"/p/{name}")
    v = app.page.views[-1]
    assert (
        "土地の仮説" in texts(v)
        and "h1: 微高地にある" in texts(v)
        and "vegetation — (all plants)" in texts(v)
    )
