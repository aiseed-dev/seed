# SPDX-License-Identifier: AGPL-3.0-or-later
import datetime as dt
import os
from fractions import Fraction
from io import BytesIO
from pathlib import Path

import pytest
from PIL import ExifTags, Image, TiffImagePlugin

from seed import photos
from seed.records import Folder


def _dms(v: float) -> tuple:
    v = abs(v)
    d = int(v)
    m = int((v - d) * 60)
    s = (v - d - m / 60) * 3600
    return tuple(TiffImagePlugin.IFDRational(Fraction(x).limit_denominator(10000)) for x in (d, m, s))


def make_jpeg(
    path: Path,
    lat: float | None = 34.0512,
    lon: float | None = 134.2534,
    taken: str | None = "2026:11:05 14:21:07",
    size: tuple[int, int] = (40, 20),
    orientation: int | None = None,
) -> Path:
    """GPS と撮った時刻の入った小さな JPEG を作る。"""
    img = Image.new("RGB", size, (90, 140, 60))
    exif = Image.Exif()
    if lat is not None and lon is not None:
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps.update({1: "N" if lat >= 0 else "S", 2: _dms(lat), 3: "E" if lon >= 0 else "W", 4: _dms(lon)})
    if taken:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = taken
    if orientation:
        exif[ExifTags.Base.Orientation] = orientation
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", exif=exif)
    return path


def test_exif_info_reads_gps_and_time(tmp_path):
    info = photos.exif_info(make_jpeg(tmp_path / "a.jpg"))
    assert info.lat == pytest.approx(34.0512, abs=1e-4)
    assert info.lon == pytest.approx(134.2534, abs=1e-4)
    assert info.taken == dt.datetime(2026, 11, 5, 14, 21, 7)
    assert info.has_coord


def test_exif_info_southern_western(tmp_path):
    info = photos.exif_info(make_jpeg(tmp_path / "a.jpg", lat=-1.2921, lon=-36.8219))
    assert info.lat == pytest.approx(-1.2921, abs=1e-4)
    assert info.lon == pytest.approx(-36.8219, abs=1e-4)


def test_exif_info_without_gps(tmp_path):
    info = photos.exif_info(make_jpeg(tmp_path / "a.jpg", lat=None, lon=None, taken=None))
    assert info.lat is None and info.lon is None and info.taken is None
    assert not info.has_coord


def test_heic_without_pillow_heif_is_refused_with_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "heic_ready", lambda: False)
    p = tmp_path / "IMG_0001.HEIC"
    p.write_bytes(b"\x00\x00\x00\x18ftypheic")
    with pytest.raises(photos.PhotoError) as e:
        photos.exif_info(p)
    assert e.value.word == "heic"
    assert "pillow-heif" in str(e.value)


def test_heic_with_pillow_heif(tmp_path):
    pillow_heif = pytest.importorskip("pillow_heif")
    pillow_heif.register_heif_opener()
    p = tmp_path / "IMG_0001.HEIC"
    Image.new("RGB", (40, 30), "green").save(p, format="HEIF")
    assert photos.exif_info(p).lat is None
    assert photos.shrink(p).startswith(b"\xff\xd8")
    folder = Folder(tmp_path / "seed")
    folder.init()
    (rel,) = photos.import_photos(folder, [p])
    assert rel.endswith(".jpg")
    with Image.open(folder.root / rel) as img:
        assert img.format == "JPEG" and img.size == (40, 30)


def test_not_an_image(tmp_path):
    p = tmp_path / "note.jpg"
    p.write_text("not a photo")
    with pytest.raises(photos.PhotoError) as e:
        photos.exif_info(p)
    assert e.value.word == "not_image"


def test_shrink_applies_orientation_and_drops_exif(tmp_path):
    # 向き 6（右に 90 度）: 横長 3000x1000 → 縦長に直してから縮める
    src = make_jpeg(tmp_path / "big.jpg", size=(3000, 1000), orientation=6)
    out = photos.shrink(src, max_side=600, quality=80)
    img = Image.open(BytesIO(out))
    assert img.format == "JPEG"
    assert img.size == (200, 600)
    assert not img.getexif().get_ifd(ExifTags.IFD.GPSInfo)
    assert len(img.getexif()) == 0


def test_shrink_keeps_small_images(tmp_path):
    out = photos.shrink(make_jpeg(tmp_path / "s.jpg", size=(40, 20)))
    assert Image.open(BytesIO(out)).size == (40, 20)


def test_strip_exif(tmp_path):
    src = make_jpeg(tmp_path / "a.jpg")
    dst = tmp_path / "clean.jpg"
    photos.strip_exif(src, dst)
    info = photos.exif_info(dst)
    assert info.lat is None and info.taken is None


def test_center_and_extent():
    (lat, lon), extent = photos.center_and_extent([(34.0, 134.0)])
    assert (lat, lon) == (34.0, 134.0) and extent == 0
    # 緯度 0.001 度 ≒ 111 m。重心から両端まで 55.6 m、その 2 倍
    (lat, lon), extent = photos.center_and_extent([(34.000, 134.0), (34.001, 134.0)])
    assert lat == pytest.approx(34.0005)
    assert extent == pytest.approx(111.2, abs=0.5)
    with pytest.raises(ValueError):
        photos.center_and_extent([])


def test_location():
    infos = [photos.PhotoInfo(34.0, 134.0, None), photos.PhotoInfo(None, None, None)]
    loc = photos.location(infos)
    assert loc == {"center": [34.0, 134.0], "points": 1, "extent_m": 0}
    assert photos.location([photos.PhotoInfo(None, None, None)]) is None


def test_import_photos(tmp_path):
    folder = Folder(tmp_path / "seed")
    folder.init()
    b = make_jpeg(tmp_path / "in" / "b.jpg", taken="2026:11:05 14:21:31")
    a = make_jpeg(tmp_path / "in" / "a.jpg", taken="2026:11:05 14:21:07")
    same_second = make_jpeg(tmp_path / "in" / "c.jpg", taken="2026:11:05 14:21:07", size=(41, 20))
    got = photos.import_photos(folder, [b, a, same_second])
    assert got[0] == "photos/2026-11-05/142107.jpg"
    assert set(got[1:]) == {"photos/2026-11-05/142107-1.jpg", "photos/2026-11-05/142131.jpg"}
    # そのまま写す（EXIF の座標は本人の物として残る）
    assert (folder.root / got[0]).read_bytes() == a.read_bytes()
    # 同じ写真をもう一度入れても増えない
    assert photos.import_photos(folder, [a]) == ["photos/2026-11-05/142107.jpg"]


def test_import_photos_uses_file_time_without_exif(tmp_path):
    folder = Folder(tmp_path / "seed")
    folder.init()
    p = make_jpeg(tmp_path / "x.jpg", taken=None)
    t = dt.datetime(2026, 10, 1, 8, 9, 10).timestamp()
    os.utime(p, (t, t))
    assert photos.import_photos(folder, [p]) == ["photos/2026-10-01/080910.jpg"]


def test_import_png_becomes_jpeg(tmp_path):
    folder = Folder(tmp_path / "seed")
    folder.init()
    p = tmp_path / "x.png"
    Image.new("RGBA", (10, 10)).save(p)
    (rel,) = photos.import_photos(folder, [p])
    assert rel.endswith(".jpg")
    assert Image.open(folder.root / rel).format == "JPEG"


def test_far_photos_flags_the_one_far_away():
    near = [photos.PhotoInfo(34.0500 + i * 0.00001, 134.2534, None) for i in range(4)]
    far = photos.PhotoInfo(34.0503, 134.2540, None)  # 約 60 m 東
    rel = [f"photos/d/{i}.jpg" for i in range(5)]
    got = photos.far_photos(rel, [*near, far])
    assert [r for r, _ in got] == ["photos/d/4.jpg"]
    assert 50 < got[0][1] < 80
    assert photos.far_photos(rel[:2], near[:2]) == []  # 3 枚未満は見ない


def test_import_same_heic_twice_does_not_duplicate(tmp_path):
    pillow_heif = pytest.importorskip("pillow_heif")
    pillow_heif.register_heif_opener()
    p = tmp_path / "IMG_0002.HEIC"
    Image.new("RGB", (40, 30), "blue").save(p, format="HEIF")
    folder = Folder(tmp_path / "seed")
    folder.init()
    first = photos.import_photos(folder, [p])
    second = photos.import_photos(folder, [p])
    assert first == second
    assert len(list((folder.photos).rglob("*.jpg"))) == 1


def test_direction_word():
    assert photos.direction_word(None) is None
    assert photos.direction_word(0) == "N"
    assert photos.direction_word(359) == "N"
    assert photos.direction_word(264.9, "ja") == "西"
    assert photos.direction_word(41.8, "ja") == "北東"
    assert photos.direction_word(189.3, "ja") == "南"


def test_location_excludes_gps_outliers():
    near = [photos.PhotoInfo(34.0500 + i * 0.00001, 134.2534, None) for i in range(4)]
    far = photos.PhotoInfo(34.0490, 134.2534, None)  # 約 110 m 南
    loc = photos.location([*near, far])
    assert loc["points"] == 4 and loc["excluded"] == 1 and loc["extent_m"] < 10
    assert "excluded" not in photos.location(near)


def test_import_text_level_shrinks_and_keeps_gps(tmp_path):
    folder = Folder(tmp_path / "seed")
    folder.init()
    big = make_jpeg(tmp_path / "in" / "big.jpg", size=(3000, 1500))
    (rel,) = photos.import_photos(folder, [big], keep="text")
    with Image.open(folder.root / rel) as im:
        assert max(im.size) == 2000
    info = photos.exif_info(folder.root / rel)
    assert info.has_coord and info.taken is not None
    # 同じ写真をもう一度入れても増えない（縮めた形で比べる）
    assert photos.import_photos(folder, [big], keep="text") == [rel]
    assert not folder.originals.exists()


def test_import_research_keeps_originals_only_when_they_differ(tmp_path):
    folder = Folder(tmp_path / "seed")
    folder.init()
    png = tmp_path / "x.png"
    Image.new("RGBA", (10, 10)).save(png)
    # EXIF の無い PNG はファイルの時刻で並ぶ。JPEG の撮影時刻（14:21:07）より前に固定して、順が日時で変わらないようにする
    fixed = dt.datetime(2026, 11, 5, 14, 0, 0).timestamp()
    os.utime(png, (fixed, fixed))
    jpg = make_jpeg(tmp_path / "in" / "a.jpg")
    rel_png, _ = photos.import_photos(folder, [png, jpg], keep="research")
    origs = sorted(p.relative_to(folder.root).as_posix() for p in folder.originals.rglob("*.*"))
    assert origs == ["originals/" + rel_png[len("photos/") :].removesuffix(".jpg") + ".png"]
    assert (folder.root / origs[0]).read_bytes() == png.read_bytes()
    # JPEG は photos/ がそのままの中身なので、originals/ には写さない
    assert not any(p.suffix == ".jpg" for p in folder.originals.rglob("*"))


def test_import_research_with_bulk_puts_originals_on_the_other_disk(tmp_path):
    folder = Folder(tmp_path / "seed", bulk=tmp_path / "hdd" / "field")
    folder.init()
    png = tmp_path / "x.png"
    Image.new("RGBA", (10, 10)).save(png)
    (rel,) = photos.import_photos(folder, [png], keep="research")
    assert (folder.root / rel).exists()
    origs = list((tmp_path / "hdd" / "field" / "originals").rglob("*.png"))
    assert len(origs) == 1 and not (folder.root / "originals").exists()
