# SPDX-License-Identifier: AGPL-3.0-or-later
"""畑に入っていない写真（seed/loose.py と、話すで知らせて言葉で入れる所。設計書 §5.17）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_app import FakePage, run, texts
from test_photos import make_jpeg

from seed import cli, loose
from seed import settings as settings_mod
from seed.app import talk
from seed.app.main import App
from seed.records import Line, Observation

LAT, LON = 34.0512, 134.2534
COORD_TEXTS = ("34.05", "134.25", "34,05", "134,25")


def observation(field: Path, name: str, lat: float, lon: float) -> Path:
    p = field / "observations" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\n"
        "date: '2026-11-05'\n"
        "time: '14:21:07'\n"
        "photos: []\n"
        "location:\n"
        f"  center: [{lat}, {lon}]\n"
        "  points: 1\n"
        "  extent_m: 10\n"
        "---\n",
        encoding="utf-8",
    )
    return p


def touch(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def by_rel(groups) -> dict[str, loose.Item]:
    return {i.rel: i for g in groups for i in g.items}


@pytest.fixture
def proj(tmp_path):
    """畑が二つ（北、南）のプロジェクト。北の観察は (LAT, LON)、南の観察は北へ約 1 km。"""
    root = tmp_path / "seed"
    observation(root / "fields" / "北", "2026-11-05-142107.md", LAT, LON)
    observation(root / "fields" / "南", "2026-11-05-142107.md", LAT + 0.009, LON)
    return root


# ---------------------------------------------------------------- 探す


def test_scan_skips_seen_and_dot_dirs(proj):
    for rel in (
        "photos/2026-11-05/1.jpg",
        "fields/北/photos/2026-11-05/1.jpg",
        "fields/北/originals/2026-11-05/1.heic",
        "fields/北/public/p.png",
        "notes/x.jpg",
        "public-home/y.jpg",
        "skill/z.png",
        ".unzip-1/c.jpg",
        "uploads/.hidden.jpg",
        "uploads/.cache/d.jpg",
        "uploads/memo.txt",
        "uploads/clip.mov",
    ):
        touch(proj / rel)
    make_jpeg(proj / "uploads" / "北側の畑" / "IMG_1.JPG", lat=None, lon=None)
    make_jpeg(proj / "島根" / "b.jpeg", lat=None, lon=None, size=(41, 20))
    make_jpeg(proj / "fields" / "北" / "写真" / "a.jpg", lat=None, lon=None, size=(42, 20))
    groups = loose.scan(proj)
    assert [g.folder for g in groups] == ["fields/北/写真", "uploads/北側の畑", "島根"]
    assert [g.name for g in groups] == ["写真", "北側の畑", "島根"]
    assert all(not i.in_seed and i.metres is None for g in groups for i in g.items)


def test_scan_without_photos_is_empty_and_does_not_hash(proj, monkeypatch):
    touch(proj / "uploads" / "memo.txt")
    monkeypatch.setattr(loose, "sha256_file", lambda p: pytest.fail("写真が無いのに読んだ"))
    assert loose.scan(proj) == []


def test_in_seed_by_hash_and_by_capture_time(proj):
    north = proj / "fields" / "北"
    same = make_jpeg(north / "photos" / "2026-11-05" / "142107.jpg")
    make_jpeg(north / "photos" / "2026-11-06" / "080000-1.jpg", taken="2026:11:06 08:00:00")
    up = proj / "uploads"
    touch(up / "copy.jpg", same.read_bytes())  # 中身が同じ
    make_jpeg(up / "IMG_2.JPG", size=(30, 30))  # 中身は違うが、撮った時刻の JPEG が在る
    make_jpeg(up / "IMG_3.JPG", taken="2026:11:06 08:00:00", size=(31, 31))  # -1 の付いた JPEG
    make_jpeg(up / "IMG_4.JPG", taken="2026:10:01 09:00:00", size=(32, 32))  # どこにも無い
    before = snapshot(proj)
    groups = loose.scan(proj)
    items = by_rel(groups)
    assert {r for r, i in items.items() if i.in_seed} == {
        "uploads/copy.jpg",
        "uploads/IMG_2.JPG",
        "uploads/IMG_3.JPG",
    }
    assert not items["uploads/IMG_4.JPG"].in_seed
    assert groups[0].some_in and not groups[0].all_in
    assert snapshot(proj) == before  # 読むだけ


def test_bulk_originals_count_as_in_seed(proj, tmp_path):
    bulk = tmp_path / "hdd" / "seed"
    touch(bulk / "fields" / "南" / "originals" / "2026-11-05" / "142107.heic", b"heic-bytes")
    touch(proj / "uploads" / "IMG_1.HEIC", b"heic-bytes")
    touch(proj / "uploads" / "IMG_2.HEIC", b"other-bytes")
    items = by_rel(loose.scan(proj, bulk))
    assert items["uploads/IMG_1.HEIC"].in_seed and not items["uploads/IMG_2.HEIC"].in_seed
    # 渡さなければ seed.toml の bulk を読む
    (proj / "seed.toml").write_text(f'bulk = "{bulk}"\n', encoding="utf-8")
    assert by_rel(loose.scan(proj))["uploads/IMG_1.HEIC"].in_seed
    # bulk が無い時は、畑の中の originals/
    touch(proj / "fields" / "北" / "originals" / "2026-11-05" / "x.heic", b"other-bytes")
    assert by_rel(loose.scan(proj, None))["uploads/IMG_2.HEIC"].in_seed


def test_distance_to_nearest_field_and_no_coordinates_in_output(proj):
    up = proj / "uploads"
    make_jpeg(up / "near.jpg", lat=LAT + 0.0001, lon=LON)  # 北から約 11 m
    make_jpeg(up / "south.jpg", lat=LAT + 0.0091, lon=LON, size=(41, 20))  # 南から約 11 m
    make_jpeg(up / "nogps.jpg", lat=None, lon=None, size=(42, 20))
    groups = loose.scan(proj)
    items = by_rel(groups)
    near, south, nogps = items["uploads/near.jpg"], items["uploads/south.jpg"], items["uploads/nogps.jpg"]
    assert near.field == "北" and 8 <= near.metres <= 14
    assert south.field == "南" and 8 <= south.metres <= 14
    assert nogps.field is None and nogps.metres is None
    assert not any(t in repr(groups) for t in COORD_TEXTS)


def test_project_without_fields_is_one_field(tmp_path):
    root = tmp_path / "rokuse"
    observation(root, "2026-11-05-142107.md", LAT, LON)
    make_jpeg(root / "photos" / "2026-11-05" / "142107.jpg")
    make_jpeg(root / "uploads" / "a.jpg", lat=LAT + 0.0001, taken="2026:10:01 09:00:00")
    assert loose.field_dirs(root) == [("rokuse", root)]
    (g,) = loose.scan(root)
    (it,) = g.items
    assert it.rel == "uploads/a.jpg" and it.field == "rokuse" and not it.in_seed


def test_removable_only_when_nothing_else_would_go(proj):
    north = proj / "fields" / "北"
    a = make_jpeg(north / "photos" / "2026-11-05" / "142107.jpg")
    touch(proj / "島根" / "a.jpg", a.read_bytes())
    touch(proj / "uploads" / "x" / "a.jpg", a.read_bytes())
    touch(proj / "uploads" / "x" / "memo.txt")  # 写真でない物を巻き込むので出さない
    touch(proj / "a.jpg", a.read_bytes())  # 根は出さない
    groups = loose.scan(proj)
    assert all(g.all_in for g in groups)
    assert loose.removable(groups) == [proj / "島根"]
    assert loose.rm_command(Path("/a/b'c")) == "rm -r '/a/b'\\''c'"


# ---------------------------------------------------------------- 言葉で答える


def groups_for_match(proj) -> list[loose.Group]:
    make_jpeg(proj / "島根" / "IMG_5663.jpg", lat=None, lon=None)
    make_jpeg(proj / "uploads" / "北側の畑" / "IMG_7001.JPG", lat=None, lon=None, size=(41, 20))
    make_jpeg(proj / "uploads" / "北側の畑" / "s.jpg", lat=None, lon=None, size=(43, 20))
    return loose.scan(proj)


def test_match_by_folder_and_name(proj):
    groups = groups_for_match(proj)
    fields = ["北", "南", "rokuse"]
    paths, name = loose.match("島根のは南", groups, fields)
    assert name == "南" and paths == [proj / "島根" / "IMG_5663.jpg"]
    # 「北側の畑」を除くと、畑の名は「南」だけ（「北」は写真を指す語の中）
    paths, name = loose.match("北側の畑の写真は 南 に", groups, fields)
    assert name == "南" and sorted(p.name for p in paths) == ["IMG_7001.JPG", "s.jpg"]
    paths, name = loose.match("img_7001.jpg を rokuse へ", groups, fields)  # 大きい字と小さい字は同じ
    assert name == "rokuse" and paths == [proj / "uploads" / "北側の畑" / "IMG_7001.JPG"]
    paths, name = loose.match("IMG_5663 は北", groups, fields)  # 名の幹でも
    assert name == "北" and paths == [proj / "島根" / "IMG_5663.jpg"]


def test_match_needs_photos_and_exactly_one_field(proj):
    groups = groups_for_match(proj)
    fields = ["北", "南", "rokuse"]
    assert loose.match("rokuse の草は？", groups, fields) is None  # 写真を指していない（s は語の中）
    assert loose.match("島根のは北か南", groups, fields) is None  # 畑が二つ
    assert loose.match("島根の写真は何？", groups, fields) is None  # 畑が無い
    assert loose.match("島根のは南", [], fields) is None


def test_match_ignores_photos_already_in_seed(proj):
    a = make_jpeg(proj / "fields" / "北" / "photos" / "2026-11-05" / "142107.jpg")
    touch(proj / "島根" / "a.jpg", a.read_bytes())
    assert loose.match("島根のは南", loose.scan(proj), ["北", "南"]) is None


# ---------------------------------------------------------------- アプリ（話すで知らせ、言葉で入れる）


@pytest.fixture(autouse=True)
def no_lookup(monkeypatch):
    from seed import lookup as L

    monkeypatch.setattr(L, "available", lambda: False)


@pytest.fixture
def app_proj(seedfolder):
    assert cli.main(["field", "new", "北", "--folder", str(seedfolder)]) == 0
    assert cli.main(["field", "new", "南", "--folder", str(seedfolder)]) == 0
    observation(seedfolder / "fields" / "北", "2026-11-05-142107.md", LAT, LON)
    make_jpeg(seedfolder / "島根" / "IMG_5663.jpg", lat=LAT + 0.0001, taken="2026:11:01 10:00:00")
    return seedfolder


def make_app(project, field: str = "") -> App:
    settings_mod.write_field(project, field)
    a = App(FakePage(), str(project))
    a.lang = "ja"
    a.settings.invite = "inv-test"
    return a


def fake_read(st, folder, obs):
    obs.reading = [Line("overall", "草が大半", 0.8)]
    obs.model = "fake"


def test_app_tells_once_and_places_by_words(app_proj, monkeypatch):
    monkeypatch.setattr(talk, "read_on_server", fake_read)
    app = make_app(app_proj)
    assert app.whole
    run(talk.tell_loose(app))
    told = app.state["talk"][-1]
    lines = told["text"].splitlines()
    assert lines[0] == "どの畑にも入っていない写真が 1 枚あります。"
    assert lines[1].startswith("島根/IMG_5663.jpg — 北の観察から ") and lines[1].endswith(" m")
    assert lines[-1] == "どの畑に入れるか、言葉で教えてください。例: 「島根のは北」"
    assert told["loose"] == [str(app_proj / "島根" / "IMG_5663.jpg")]
    assert not any(t in told["text"] for t in COORD_TEXTS)
    v = talk.view(app)  # 小さな絵も組める
    assert "どの畑にも入っていない写真が 1 枚あります。" in "\n".join(texts(v))
    n = len(app.state["talk"])
    run(talk.tell_loose(app))
    assert len(app.state["talk"]) == n  # 同じ顔ぶれは二度言わない

    src = app_proj / "島根" / "IMG_5663.jpg"
    before = src.read_bytes()
    run(talk.send(app, "島根のは南"))
    obs = Observation.read(app_proj / "fields" / "南" / "observations" / "2026-11-01-100000.md")
    assert obs.photos == ["photos/2026-11-01/100000.jpg"] and obs.model == "fake"
    assert src.read_bytes() == before  # 元は写して残す
    said = [i.get("text") for i in app.state["talk"]]
    assert "1 枚を南に入れます: IMG_5663.jpg" in said
    last = app.state["talk"][-1]
    assert last["commands"] == [f"rm -r '{app_proj / '島根'}'"]
    assert f"rm -r '{app_proj / '島根'}'" in texts(talk.view(app))
    assert app.state["loose_told"] == frozenset()


def test_plain_words_go_the_usual_way(app_proj, monkeypatch):
    app = make_app(app_proj)
    app.settings.invite = ""  # 言葉は、Claude を呼ぶ所が無いので観察に足すだけ（網に出ない）
    run(talk.tell_loose(app))
    called = []
    monkeypatch.setattr(talk, "add_picked", lambda *a: called.append(a))
    run(talk.send(app, "北の草は？"))
    run(talk.send(app, "島根のは北か南か"))
    assert called == []
    assert not list((app_proj / "fields").rglob("*.jpg"))  # 何も入れていない


def test_placing_into_another_field_shows_in_the_open_field(app_proj, monkeypatch):
    monkeypatch.setattr(talk, "read_on_server", fake_read)
    app = make_app(app_proj, "北")
    observation(app_proj / "fields" / "南", "2026-10-01-090000.md", LAT + 0.009, LON)
    run(talk.tell_loose(app))
    run(app.choose_field("北"))
    assert app.state.get("loose_told")  # 同じプロジェクトで開き直しても持ち越す
    run(talk.send(app, "IMG_5663 は 南"))
    words = texts(talk.view(app))
    assert app.t("loose_elsewhere", field="南") in words
    assert f"rm -r '{app_proj / '島根'}'" in words
    assert (app_proj / "fields" / "南" / "observations" / "2026-11-01-100000.md").is_file()


def test_placing_when_reading_fails_still_offers_rm(app_proj, monkeypatch):
    from seed.client import ClientError

    def fail(*a, **k):
        raise ClientError("unreachable", "unreachable")

    monkeypatch.setattr(talk, "read_on_server", fail)
    app = make_app(app_proj, "北")
    monkeypatch.setattr(App, "call", lambda self, *a: fail())
    run(talk.tell_loose(app))
    run(talk.send(app, "島根のは南"))
    words = texts(talk.view(app))
    assert app.t("loose_elsewhere", field="南") in words
    assert f"rm -r '{app_proj / '島根'}'" in words


def test_placing_when_the_import_breaks_still_offers_rm(app_proj, monkeypatch):
    """読みや照会が思わぬ形で落ちても、入った写真の消す命令と、別の畑に入れた一言は出す。"""

    def broken(*a, **k):
        raise RuntimeError("照会が落ちた")

    monkeypatch.setattr(talk, "read_on_server", fake_read)
    monkeypatch.setattr(talk, "place_data", broken)
    app = make_app(app_proj, "北")
    run(talk.tell_loose(app))
    run(talk.send(app, "島根のは南"))
    words = texts(talk.view(app))
    assert "照会が落ちた" in words
    assert app.t("loose_elsewhere", field="南") in words
    assert f"rm -r '{app_proj / '島根'}'" in words


def test_names_inside_japanese_and_named_folders(app_proj, monkeypatch):
    app = make_app(app_proj)
    assert (
        talk.loose_t(app, "loose_placing", n=1, field="知人の田", names="a.jpg")
        == "1 枚を知人の田に入れます: a.jpg"
    )
    assert (
        talk.loose_t(app, "loose_placing", n=1, field="rokuse", names="a.jpg")
        == "1 枚を rokuse に入れます: a.jpg"
    )
    hint = talk.loose_t(app, "loose_hint", name="北側の畑", field="rokuse")
    assert hint.endswith("「北側の畑のは rokuse」")
    north = app_proj / "fields" / "北"
    a = make_jpeg(north / "photos" / "2026-11-05" / "142107.jpg", size=(60, 20))
    touch(app_proj / "島根" / "copy.jpg", a.read_bytes())  # 島根は 2 枚のうち 1 枚が入っている
    touch(app_proj / "uploads" / "x" / "copy.jpg", a.read_bytes())  # 全部入っている
    lines = talk.loose_text(app, loose.scan(app_proj)).splitlines()
    assert "島根/ の 2 枚のうち 1 枚は、もう畑に入っています" in lines
    assert "uploads/x/ の写真は、全部畑に入っています" in lines
    app.lang = "en"
    assert (
        talk.loose_t(app, "loose_placing", n=1, field="rokuse", names="a.jpg")
        == "Putting 1 photo(s) into rokuse: a.jpg"
    )
