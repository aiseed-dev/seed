# SPDX-License-Identifier: AGPL-3.0-or-later
"""まとめて入れる（作者 11-07「zipでまとめていれたいので、zipにも対応させて」「動画は単独でいれることもあるので、mp4に対応して」）。"""

import asyncio
import datetime as dt
import json
import struct
import zipfile
from pathlib import Path

import pytest
from test_photos import make_jpeg

from seed import bundle


def box(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(body), kind) + body


def mp4(taken_utc: dt.datetime | None = None, xyz: str | None = None, mdat: bytes = b"\0" * 64) -> bytes:
    """標準のカメラの形の小さな MP4（moov が後ろ。mvhd に時、udta/©xyz に所）。"""
    secs = int((taken_utc - bundle.MP4_EPOCH).total_seconds()) if taken_utc else 0
    mvhd = box(b"mvhd", b"\0\0\0\0" + struct.pack(">II", secs, secs) + b"\0" * 88)
    parts = [mvhd]
    if xyz:
        raw = xyz.encode()
        parts.append(box(b"udta", box(b"\xa9xyz", struct.pack(">HH", len(raw), 0x15C7) + raw)))
    return box(b"ftyp", b"isom\0\0\0\0isom") + box(b"mdat", mdat) + box(b"moov", b"".join(parts))


def test_mp4_where_reads_time_and_place():
    when = dt.datetime(2026, 11, 7, 8, 19, 51, tzinfo=dt.UTC)
    data = mp4(when, "+34.0802+134.4454/")
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "v.mp4"
        p.write_bytes(data)
        got = bundle.mp4_where(p)
        assert got["taken"] == when.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")
        assert got["lat"] == 34.0802 and got["lon"] == 134.4454
        p.write_bytes(mp4(None, None))
        assert bundle.mp4_where(p) == {}
        p.write_bytes(b"not a video")
        assert bundle.mp4_where(p) == {}


def test_place_video_copies_names_by_time_and_writes_where(tmp_path):
    when = dt.datetime(2026, 11, 7, 8, 19, 51, tzinfo=dt.UTC)
    local = when.astimezone().replace(tzinfo=None)
    src = tmp_path / "PXL_20261107_081951.mp4"
    src.write_bytes(mp4(when, "+34.0802+134.4454/"))
    root = tmp_path / "rec"
    got = bundle.place_video(root, src)
    assert got == root / "videos" / local.strftime("%Y-%m-%d") / (local.strftime("%H%M%S") + ".mp4")
    assert src.exists() and got.read_bytes() == src.read_bytes()  # 選んだ元は残す
    side = json.loads(got.with_suffix(".json").read_text(encoding="utf-8"))
    assert side["lat"] == 34.0802 and side["from"] == src.name
    assert bundle.place_video(root, src) == got  # 同じ物をもう一度入れても二本にしない
    other = tmp_path / "b.mp4"
    other.write_bytes(mp4(when, None, mdat=b"\1" * 80))
    assert bundle.place_video(root, other).name == local.strftime("%H%M%S") + "-2.mp4"


def test_place_video_without_inner_time_uses_file_time_and_keeps_mov(tmp_path):
    src = tmp_path / "clip.MOV"
    src.write_bytes(b"\0\0\0\x14ftypqt  " + b"\0" * 32)
    import os

    t = dt.datetime(2026, 10, 1, 9, 8, 7).timestamp()
    os.utime(src, (t, t))
    got = bundle.place_video(tmp_path / "rec", src, move=True)
    assert got.name == "090807.mov" and got.parent.name == "2026-10-01" and not src.exists()


def test_unpack_takes_only_photos_and_videos_and_never_writes_outside(tmp_path):
    z = tmp_path / "farm.zip"
    j = make_jpeg(tmp_path / "src" / "a.jpg").read_bytes()
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("2026-11-07/IMG_1.jpg", j)
        zf.writestr("../../escape.jpg", j)  # 道は使わず名だけ
        zf.writestr("/abs/IMG_1.jpg", j)  # 同じ名は -2
        zf.writestr("clip.mp4", mp4())
        zf.writestr("notes.txt", "hello")
        zf.writestr("__MACOSX/._IMG_1.jpg", "junk")
        zf.writestr(".hidden.jpg", j)
        zf.writestr("dir/", "")
    into = tmp_path / "into"
    got = bundle.unpack([z, tmp_path / "src" / "a.jpg", tmp_path / "x.pdf"], into)
    assert sorted(p.name for p in got.photos) == ["IMG_1-2.jpg", "IMG_1.jpg", "a.jpg", "escape.jpg"]
    assert [p.name for p in got.videos] == ["clip.mp4"]
    assert sorted(got.skipped) == ["notes.txt", "x.pdf"]
    assert all(p.parent == into for p in got.photos if p.name != "a.jpg")
    assert not (tmp_path / "escape.jpg").exists() and not Path("/abs").exists()


def test_unpack_stops_at_a_too_big_zip(tmp_path, monkeypatch):
    z = tmp_path / "big.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("v.mp4", b"\0" * 5000)
    monkeypatch.setattr(bundle, "MEMBER_MAX", 1000)
    with pytest.raises(bundle.TooBig):
        bundle.unpack([z], tmp_path / "into")


def test_photo_groups_by_day_and_six_at_most(tmp_path):
    paths = []
    for i in range(8):
        paths.append(make_jpeg(tmp_path / f"d1-{i}.jpg", taken=f"2026:11:07 10:00:{i:02d}"))
    paths.append(make_jpeg(tmp_path / "d2.jpg", taken="2026:11:08 07:00:00"))
    groups = bundle.photo_groups(list(reversed(paths)))
    assert [len(g) for g in groups] == [6, 2, 1]
    assert groups[0][0].name == "d1-0.jpg" and groups[2][0].name == "d2.jpg"


# ---------------------------------------------------------------- 画面から


def test_app_adds_a_zip_of_photos_and_a_loose_mp4(seedfolder, tmp_path, monkeypatch):
    from test_app import FakePage

    from seed.app import talk
    from seed.app.main import App

    app = App(FakePage(), str(seedfolder))
    app.lang = "ja"
    sent = []

    async def fake_send(app_, text, paths=None, as_example=True):
        sent.append((text, [p.name for p in paths], all(p.exists() for p in paths)))

    monkeypatch.setattr(talk, "send", fake_send)
    z = tmp_path / "farm.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for i in range(7):
            zf.writestr(
                f"p{i}.jpg",
                make_jpeg(tmp_path / "s" / f"p{i}.jpg", taken=f"2026:11:07 10:00:{i:02d}").read_bytes(),
            )
        zf.writestr("in-zip.mp4", mp4(dt.datetime(2026, 11, 7, 1, 0, 0, tzinfo=dt.UTC)))
    loose = tmp_path / "loose.mp4"
    loose.write_bytes(mp4(dt.datetime(2026, 11, 7, 2, 0, 0, tzinfo=dt.UTC)))

    asyncio.run(talk.add_picked(app, "畑の様子", [z, loose]))
    assert [(t, len(n), ok) for t, n, ok in sent] == [("畑の様子", 6, True), ("", 1, True)]
    vids = sorted(p.name for p in (app.folder.root / "videos").rglob("*.mp4"))
    assert len(vids) == 2 and loose.exists()  # 選んだ mp4 の元は残す
    assert not list(app.folder.root.glob(".unzip-*"))  # 一時の場所は消える


def test_zip_with_a_zero_date_or_a_locked_entry_still_imports_the_rest(tmp_path, monkeypatch):
    z = tmp_path / "odd.zip"
    j = make_jpeg(tmp_path / "s" / "a.jpg").read_bytes()
    with zipfile.ZipFile(z, "w") as zf:
        info = zipfile.ZipInfo("zero.jpg", date_time=(1980, 1, 1, 0, 0, 0))
        zf.writestr(info, j)
        zf.writestr("locked.jpg", j)
        zf.writestr("fine.jpg", j)
    real_open = zipfile.ZipFile.open

    def fake_open(self, name, *a, **kw):
        if getattr(name, "filename", name) == "locked.jpg":
            raise RuntimeError("File is encrypted, password required for extraction")
        return real_open(self, name, *a, **kw)

    monkeypatch.setattr(zipfile.ZipFile, "open", fake_open)
    real_dt = bundle.dt.datetime

    class ZeroDay(real_dt):
        def __new__(cls, *a, **kw):
            if a[:3] == (1980, 1, 1):
                raise ValueError("month must be in 1..12")
            return real_dt.__new__(cls, *a, **kw)

    monkeypatch.setattr(bundle.dt, "datetime", ZeroDay)
    got = bundle.unpack([z], tmp_path / "into")
    assert sorted(p.name for p in got.photos) == ["fine.jpg", "zero.jpg"]
    assert got.skipped == ["locked.jpg"] and not (tmp_path / "into" / "locked.jpg").exists()


def test_clean_leftovers_only_removes_old_ones(tmp_path):
    import os
    import time

    old = tmp_path / ".unzip-old"
    old.mkdir()
    new = tmp_path / ".unzip-new"
    new.mkdir()
    t = time.time() - 7200
    os.utime(old, (t, t))
    bundle.clean_leftovers(tmp_path, ".unzip-*")
    assert not old.exists() and new.exists()


def test_app_says_why_a_broken_zip_did_not_go_in(seedfolder, tmp_path):
    from test_app import FakePage

    from seed.app import talk
    from seed.app.main import App

    app = App(FakePage(), str(seedfolder))
    app.lang = "ja"
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"PK\x03\x04 not really a zip")
    asyncio.run(talk.add_picked(app, "", [bad]))
    said = [m.get("text", "") for m in talk.talk_state(app)]
    assert any("zip を開けませんでした" in t for t in said)
    assert not list(app.folder.root.glob(".unzip-*"))
