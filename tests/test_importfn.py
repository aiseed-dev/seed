"""fieldnotes の記録を seed の形に移す（記録の形 §23、importfn.py）。網には出ない。"""

import json

from test_photos import make_jpeg

from seed import cli, walk
from seed.records import Hypotheses, Observation, Plan

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
