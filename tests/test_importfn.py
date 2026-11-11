"""fieldnotes の記録を seed の形に移す（記録の形 §23、importfn.py）。網には出ない。"""

import json

from test_photos import make_jpeg

from seed import cli, walk
from seed.records import Hypotheses, Line, Observation, Plan

SITE = """---
site: test-farm
place: Ishii, Tokushima, Japan
country: JP
lat: 34.0801
lon: 134.4454
checked: 2026-10-28
---

# Site profile

- `data` — explanation, not a line.

## Location

- `data` 徳島県名西郡石井町 高川原 (municipality code 36341). — GSI reverse geocoder

## Terrain

- `hypothesis` A slightly raised ground (微高地). — farmer. Check: GSI 地形分類.
- `refuted` "Low floodplain" — AI guess from elevation alone; corrected by the farmer.
- `hypothesis` Ordinary floods do not inundate it. — farmer.
- `record` 昔はホウレンソウの産地。 — the farmer, 2026-11-02.

## How a hypothesis is checked

- `hypothesis` this is the explanation, not a hypothesis.
"""

DAY = """---
field: uncut
date: '2026-10-28'
photos:
- photos/uncut/2026-10-28/121701-uncut.jpg
- photos/uncut/2026-10-28/121730-b.jpg
weather:
  tmax: 18.4
coverage:
  vegetation: 91.8
cover_range:
  vegetation: [80.1, 97.3]
---

## AI observation (muse-spark-1.3)
- overall: 密生している。 [0.85]  → farmer: right
- dominant: オギ (Miscanthus sacchariflorus) ~55% [0.80]
- weed_height: 頭上を越える [0.70]  → farmer: wrong (胸の高さ)

## Earlier AI lines
- acidity: 5.0-5.5; evidence: スギナ [0.40]  → farmer: wrong (スギナは少ない)

## From the farmer's voice (muse-voice-transcribe-1.0)
- work: 東側を刈った
- seen: ダイコンに本葉

## Checks (muse-spark-1.3)
- h2: agrees: 泥の跡が無い [0.85]  → farmer: right

## Farmer note (muse-voice-transcribe-1.0, ja)
12:20 東側を刈った (121755-voice.m4a)
北の端は低い。
"""

EXPECT = """---
field: uncut
model: muse-spark-1.3
---

## Expectations (muse-spark-1.3)
- h1: holds: 水が溜まらない; fails: 溜まる; visible: yes [0.60]
"""

CUT = """---
field: uncut
date: '2026-10-29'
kind: cut
model: muse-spark-1.3
---

## Cut proposal (muse-spark-1.3)
- summary: 南の縁を先に刈る [0.60]  → farmer: right
- leave: 北のオギは残す [0.50]
- watch: 一週間で株元に緑 [0.40]
"""

LOOKUP = """---
place: x
fetched: 2026-10-30
---

## Terrain

- `data` Elevation 7 m (DEM: 1m（レーザ）). — 出典：国土地理院 標高API, https://example
"""


def farm(tmp_path):
    src = tmp_path / "fn"
    rec = src / "records"
    (rec / "uncut").mkdir(parents=True)
    (rec / "site.md").write_text(SITE, encoding="utf-8")
    (rec / "lookup.md").write_text(LOOKUP, encoding="utf-8")
    (rec / "uncut" / "2026-10-28.md").write_text(DAY, encoding="utf-8")
    make_jpeg(rec / "uncut" / "2026-10-28-overlay-1.jpg")
    (rec / "_checks" / "uncut").mkdir(parents=True)
    (rec / "_checks" / "uncut" / "expect.md").write_text(EXPECT, encoding="utf-8")
    (rec / "_proposals" / "uncut").mkdir(parents=True)
    (rec / "_proposals" / "uncut" / "2026-10-29-cut.md").write_text(CUT, encoding="utf-8")
    (rec / "_concepts").mkdir()
    (rec / "_concepts" / "uncut.md").write_text(
        "## Concepts\n- concept: vegetation | by: default\n", encoding="utf-8"
    )
    (rec / "lookup").mkdir()
    ring = [[134.445, 34.08], [134.446, 34.08], [134.446, 34.081], [134.445, 34.08]]
    parcel = {"parcel": {"geometry": {"type": "Polygon", "coordinates": [ring]}}}
    (rec / "lookup" / "parcel_jp.json").write_text(json.dumps(parcel), encoding="utf-8")
    (rec / "_compare").mkdir()
    (rec / "_compare" / "2026-10-30.md").write_text("比べた", encoding="utf-8")
    day = src / "photos" / "uncut" / "2026-10-28"
    make_jpeg(day / "121701-uncut.jpg")
    make_jpeg(day / "121730-b.jpg")
    (day / "121755-voice.m4a").write_bytes(b"voice")
    (day / "index.json").write_text(
        json.dumps(
            [
                {"file": "121701-uncut.jpg", "lat": 34.0801, "lon": 134.4454},
                {"file": "121730-b.jpg", "lat": 34.0802, "lon": 134.4455},
            ]
        ),
        encoding="utf-8",
    )
    return src


def test_import_fieldnotes_farm_into_a_field(tmp_path, seedfolder):
    src = farm(tmp_path)
    before = sorted(p.relative_to(src) for p in src.rglob("*"))
    assert cli.main(["import", "fieldnotes", str(src), "--folder", str(seedfolder)]) == 0
    assert sorted(p.relative_to(src) for p in src.rglob("*")) == before  # 元は変えない
    f = seedfolder / "fields" / "uncut"
    obs = Observation.read(f / "observations" / "2026-10-28-121701.md")
    assert obs.photos == ["photos/2026-10-28/121701.jpg", "photos/2026-10-28/121730.jpg"]
    assert obs.model == "muse-spark-1.3" and obs.language == "ja"
    assert obs.coverage == {"vegetation": 91.8} and obs.cover_model == "sam-3.1"
    assert obs.location["points"] == 2 and "weather" not in obs.kept_front
    keys = [(l.key, l.verdict) for l in obs.reading]
    assert keys == [("overall", "right"), ("dominant", None), ("change", "wrong")]
    assert obs.reading[2].text == "weed_height: 頭上を越える" and obs.reading[2].reason == "胸の高さ"
    assert obs.earlier[0].reason == "スギナは少ない"
    assert obs.checks[0].key == "h2" and obs.checks[0].verdict == "right"
    rec = [(l.key, l.text) for l in obs.record]
    assert ("did", "東側を刈った（声から: muse-voice-transcribe-1.0）") in rec
    assert ("saw", "ダイコンに本葉（声から: muse-voice-transcribe-1.0）") in rec
    assert ("said", "12:20 東側を刈った（書き取り、121755-voice.m4a）") in rec and (
        "note",
        "北の端は低い。",
    ) in rec
    assert (f / "photos" / "2026-10-28" / "121755-voice.m4a").read_bytes() == b"voice"
    assert (f / "observations" / "2026-10-28-121701.sam" / "1.jpg").exists()
    # 仮説: site.md の hypothesis の行の順の番号のまま。違った物は wrong、説明の節の物は入れない
    h = Hypotheses.read(f / "hypotheses.md")
    assert [(l.key, l.verdict) for l in h.lines] == [("h1", None), ("h2", None), ("h3", "wrong")]
    assert h.lines[1].text.startswith("Ordinary floods") and h.expect[0].key == "h1"
    place = (f / "place.md").read_text(encoding="utf-8")
    assert "- center: 34.0801, 134.4454" in place and "標高 7 m" in place
    assert "昔はホウレンソウの産地" in place and "explanation" not in place
    plan = Plan.read(f / "plan.md")
    assert [(l.key, l.verdict) for l in plan.reading] == [
        ("cut", "right"),
        ("cut", None),
        ("next_to_observe", None),
    ]
    assert walk.parcels(f) == [[[134.445, 34.08], [134.446, 34.08], [134.446, 34.081], [134.445, 34.08]]]
    assert (f / "concepts.md").exists() and (
        seedfolder / "notes" / "fieldnotes" / "_compare" / "2026-10-30.md"
    ).exists()
    # 二度目は観察を上書きしない（本人が seed で付けた判定を消さない）
    obs.mark("dominant", "right")
    obs.write(f / "observations" / "2026-10-28-121701.md")
    assert cli.main(["import", "fieldnotes", str(src), "--folder", str(seedfolder)]) == 0
    assert Observation.read(f / "observations" / "2026-10-28-121701.md").reading[1].verdict == "right"
    assert len(Hypotheses.read(f / "hypotheses.md").lines) == 3


def test_import_refuses_a_folder_without_records(tmp_path, seedfolder, capsys):
    assert cli.main(["import", "fieldnotes", str(tmp_path / "nothing"), "--folder", str(seedfolder)]) == 1
    assert "records/" in capsys.readouterr().err


# ---------------------------------------------------------------- 移す先に同じ物が既にある時（記録の形 §23）


def _snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _import(src, seedfolder):
    assert cli.main(["import", "fieldnotes", str(src), "--folder", str(seedfolder)]) == 0


def _field_with(seedfolder, obs=None, photo_bytes=None):
    """seed で先に付けた畑 uncut。同じ時刻の名の写真（中身は違う）と、同じ名の観察を置ける。"""
    assert cli.main(["field", "new", "uncut", "--folder", str(seedfolder)]) == 0
    f = seedfolder / "fields" / "uncut"
    if photo_bytes is not None:
        (f / "photos" / "2026-10-28").mkdir(parents=True, exist_ok=True)
        (f / "photos" / "2026-10-28" / "121701.jpg").write_bytes(photo_bytes)
    if obs is not None:
        (f / "observations").mkdir(parents=True, exist_ok=True)
        obs.write(f / "observations" / obs.filename)
    return f


def _own_obs():
    obs = Observation(
        date="2026-10-28",
        time="12:17:01",
        photos=["photos/2026-10-28/121701.jpg"],
        location={"center": [34.08, 134.44], "points": 1, "extent_m": 0},
        model="claude-x",
        language="ja",
    )
    obs.reading = [Line("overall", "seed で読んだ", 0.7)]
    return obs


def test_import_twice_adds_nothing(tmp_path, seedfolder, capsys):
    src = farm(tmp_path)
    _import(src, seedfolder)
    first = _snapshot(seedfolder)
    capsys.readouterr()
    _import(src, seedfolder)
    assert _snapshot(seedfolder) == first  # 写真も行も一文も notes/ の物も増えない
    out = capsys.readouterr().out
    assert "観察 0（在った観察に足した 0）、写真 0（在って写さなかった 2）" in out


def test_same_time_photo_already_there_is_used_not_copied(tmp_path, seedfolder):
    src = farm(tmp_path)
    f = _field_with(seedfolder, photo_bytes=b"seed's own photo")
    _import(src, seedfolder)
    day = f / "photos" / "2026-10-28"
    assert sorted(p.name for p in day.iterdir()) == ["121701.jpg", "121730.jpg", "121755-voice.m4a"]
    assert (day / "121701.jpg").read_bytes() == b"seed's own photo"  # 中身では比べない
    obs = Observation.read(f / "observations" / "2026-10-28-121701.md")
    assert obs.photos == ["photos/2026-10-28/121701.jpg", "photos/2026-10-28/121730.jpg"]


def test_existing_observation_gets_what_is_missing(tmp_path, seedfolder, capsys):
    src = farm(tmp_path)
    own = _own_obs()
    f = _field_with(seedfolder, obs=own, photo_bytes=b"seed's own photo")
    capsys.readouterr()
    _import(src, seedfolder)
    path = f / "observations" / "2026-10-28-121701.md"
    obs = Observation.read(path)
    # 在る物は変えない
    assert obs.photos == own.photos and obs.location == own.location and obs.model == "claude-x"
    assert [(l.key, l.text) for l in obs.reading] == [("overall", "seed で読んだ")]
    # 古い読みは Earlier reading へ、一文を添えて
    assert [l.key for l in obs.earlier] == ["overall", "dominant", "change", "acidity"]
    assert obs.kept_text["Earlier reading"] == "fieldnotes の読み（muse-spark-1.3、2026-10-28 の一日分）"
    assert obs.checks[0].key == "h2" and obs.checks_model == "muse-spark-1.3"
    assert obs.coverage == {"vegetation": 91.8} and obs.cover_range == {"vegetation": [80.1, 97.3]}
    assert obs.cover_model == "sam-3.1"
    rec = [(l.key, l.text) for l in obs.record]
    assert ("did", "東側を刈った（声から: muse-voice-transcribe-1.0）") in rec
    assert ("note", "北の端は低い。") in rec
    assert (f / "observations" / "2026-10-28-121701.sam" / "1.jpg").exists()
    assert not (seedfolder / "notes" / "fieldnotes" / "records").exists()  # 全部入った
    out = capsys.readouterr().out
    assert "観察 0（在った観察に足した 1）、写真 1（在って写さなかった 1）" in out
    # 二度目は何も増えない（行も一文も重ならない）
    text = path.read_text(encoding="utf-8")
    _import(src, seedfolder)
    assert path.read_text(encoding="utf-8") == text
    assert text.count("fieldnotes の読み") == 1


def test_existing_checks_and_coverage_are_kept_and_the_day_is_copied(tmp_path, seedfolder):
    src = farm(tmp_path)
    own = _own_obs()
    own.checks, own.checks_model = [Line("h1", "seed で確かめた", 0.6)], "claude-x"
    own.coverage, own.cover_model = {"vegetation": 50.0}, "sam-3.1"
    f = _field_with(seedfolder, obs=own)
    sam = f / "observations" / "2026-10-28-121701.sam"
    sam.mkdir()
    (sam / "1.jpg").write_bytes(b"seed overlay")
    _import(src, seedfolder)
    obs = Observation.read(f / "observations" / "2026-10-28-121701.md")
    assert [(l.key, l.text) for l in obs.checks] == [("h1", "seed で確かめた")]
    assert obs.checks_model == "claude-x" and obs.coverage == {"vegetation": 50.0}
    assert (sam / "1.jpg").read_bytes() == b"seed overlay"
    assert [l.key for l in obs.earlier] == ["overall", "dominant", "change", "acidity"]  # 読みは入る
    kept = seedfolder / "notes" / "fieldnotes" / "records" / "uncut"
    assert (kept / "2026-10-28.md").read_text(encoding="utf-8") == DAY
    assert (kept / "2026-10-28-overlay-1.jpg").exists()
    first = _snapshot(seedfolder)
    _import(src, seedfolder)
    assert _snapshot(seedfolder) == first


def test_two_photos_in_the_same_second(tmp_path, seedfolder):
    src = farm(tmp_path)
    day = src / "photos" / "uncut" / "2026-10-28"
    make_jpeg(day / "121701-zz.jpg")
    _import(src, seedfolder)
    got = seedfolder / "fields" / "uncut" / "photos" / "2026-10-28"
    assert sorted(p.name for p in got.glob("*.jpg")) == ["121701-2.jpg", "121701.jpg", "121730.jpg"]
    assert (got / "121701.jpg").read_bytes() == (day / "121701-uncut.jpg").read_bytes()
    assert (got / "121701-2.jpg").read_bytes() == (day / "121701-zz.jpg").read_bytes()
    _import(src, seedfolder)
    assert len(list(got.glob("*.jpg"))) == 3


def test_report_counts(tmp_path, seedfolder):
    from seed import importfn
    from seed.records import Folder

    src = farm(tmp_path)
    f = _field_with(seedfolder, obs=_own_obs(), photo_bytes=b"seed's own photo")
    folder = Folder(f, project=seedfolder)
    rep = importfn.import_farm(src, {"uncut": folder}, "ja")
    assert (rep.observations, rep.merged, rep.photos, rep.photos_there, rep.voices) == (0, 1, 1, 1, 1)
    rep = importfn.import_farm(src, {"uncut": folder}, "ja")
    assert (rep.observations, rep.merged, rep.photos, rep.photos_there, rep.voices) == (0, 0, 0, 2, 0)


# ---------------------------------------------------------------- 二つ目の農場を同じプロジェクトへ（記録の形 §23）


def _second_farm(tmp_path):
    """同じ名の lookup/parcel_jp.json を、違う中身で持つ二つ目の農場 farm2。"""
    src = farm(tmp_path / "b").rename(tmp_path / "farm2")
    (src / "records" / "lookup" / "parcel_jp.json").write_text('{"parcel": null}', encoding="utf-8")
    return src


def test_second_farm_goes_under_its_own_name(tmp_path, seedfolder):
    from seed import importfn
    from seed.records import Folder

    one, two = farm(tmp_path), _second_farm(tmp_path)
    first = (one / "records" / "lookup" / "parcel_jp.json").read_bytes()
    _import(one, seedfolder)
    folder = Folder(seedfolder / "fields" / "uncut", project=seedfolder)
    rep = importfn.import_farm(two, {"uncut": folder}, "ja")
    kept = seedfolder / "notes" / "fieldnotes"
    assert (kept / "lookup" / "parcel_jp.json").read_bytes() == first
    assert (kept / "farm2" / "lookup" / "parcel_jp.json").read_text(encoding="utf-8") == '{"parcel": null}'
    assert "farm2/lookup" in rep.kept and "lookup" not in rep.kept
    assert "_compare" in rep.kept  # 中身の同じ物は今までの所へ
    assert not (kept / "farm2" / "_compare").exists()


def test_two_farms_imported_again_change_nothing(tmp_path, seedfolder):
    one, two = farm(tmp_path), _second_farm(tmp_path)
    _import(one, seedfolder)
    _import(two, seedfolder)
    before = _snapshot(seedfolder)
    _import(one, seedfolder)
    assert _snapshot(seedfolder) == before
    _import(two, seedfolder)
    assert _snapshot(seedfolder) == before


def test_one_farm_twice_stays_in_the_plain_place(tmp_path, seedfolder):
    src = farm(tmp_path)
    _import(src, seedfolder)
    _import(src, seedfolder)
    kept = seedfolder / "notes" / "fieldnotes"
    assert sorted(p.name for p in kept.iterdir()) == ["_compare", "lookup"]
