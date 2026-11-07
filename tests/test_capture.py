# SPDX-License-Identifier: AGPL-3.0-or-later
"""撮る画面の、Flet を起動せずに確かめられる所（位置の読み方、撮った写真に座標を書く、外す、片付ける）。"""

import datetime as dt
import io
from types import SimpleNamespace

import flet as ft
import pytest
from PIL import Image

from seed import photos
from seed.app import capture


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (160, 120), (80, 130, 60)).save(buf, "JPEG")
    return buf.getvalue()


def pos(**kw):
    base = {"latitude": 34.05, "longitude": 134.25, "altitude": 7.0, "heading": 0.0, "accuracy": 6.4}
    return SimpleNamespace(**{**base, **kw})


def test_position_fields():
    p = capture.position_fields(pos(heading=182.0))
    assert p == {"lat": 34.05, "lon": 134.25, "altitude": 7.0, "heading": 182.0, "accuracy": 6.4}
    assert capture.position_fields(pos())["heading"] is None  # 止まっている時の 0 は書かない
    assert capture.position_fields(pos(heading=-1.0))["heading"] is None
    assert capture.position_fields(pos(latitude=None)) is None
    assert capture.position_fields(None) is None


def test_session_stamps_each_shot_and_cleans_up():
    sess = capture.Session()
    try:
        with pytest.raises(photos.PhotoError) as e:
            sess.add(jpeg())  # 位置が一度も取れていなければ、足さない
        assert e.value.word == "capture_no_position" and sess.shots == []
        here = capture.position_fields(pos())
        a = sess.add(jpeg(), here, dt.datetime(2026, 11, 7, 6, 30, 0))
        b = sess.add(jpeg(), None, dt.datetime(2026, 11, 7, 6, 30, 5))  # 今取れなければ、最後に取れた位置
        assert [p.name for p in sess.paths()] == ["20261107-063000-1.jpg", "20261107-063005-2.jpg"]
        for shot in (a, b):
            info = photos.exif_info(shot.path)
            assert abs(info.lat - 34.05) < 1e-6 and abs(info.lon - 134.25) < 1e-6 and info.taken is not None
        assert a.accuracy == 6.4
        sess.remove(a)
        assert sess.paths() == [b.path] and not a.path.exists()
        for _ in range(capture.MAX_SHOTS - 1):
            sess.add(jpeg())
        with pytest.raises(photos.PhotoError) as e:
            sess.add(jpeg())
        assert e.value.word == "too_many_photos"
    finally:
        sess.close()
    assert not sess.dir.exists()


def test_available_only_on_phone_or_web():
    assert capture.available(SimpleNamespace(web=False, platform=ft.PagePlatform.LINUX)) is False
    assert capture.available(SimpleNamespace(web=False, platform=ft.PagePlatform.MACOS)) is False
    assert capture.available(SimpleNamespace(web=False, platform=ft.PagePlatform.IOS)) is True
    assert capture.available(SimpleNamespace(web=False, platform=ft.PagePlatform.ANDROID)) is True
    assert capture.available(SimpleNamespace(web=True, platform=ft.PagePlatform.LINUX)) is True


def test_strings_exist_in_both_languages():
    from seed.app.strings import s

    for word in (
        "capture_title", "capture_hint", "capture_open", "capture_shoot",
        "capture_waiting", "capture_position_plain", "capture_no_position", "capture_location_denied",
        "capture_no_camera", "capture_remove", "capture_retry_position", "capture_cancel",
    ):  # fmt: skip
        assert s(word, "ja") != word and s(word, "en") != word
    assert "3" in s("capture_done", "ja", n=3) and "8" in s("capture_position_ok", "en", m=8)


def test_page_column_fits_a_phone():
    from seed.app import theme

    assert theme.fit_width(None) == theme.MAX_WIDTH and theme.fit_width(1280) == theme.MAX_WIDTH
    assert theme.fit_width(390) == 390  # スマートフォンの幅では、窓の幅に合わせる（右が切れない）
    assert theme.page_column([], 390).width == 390


def test_keep_on_device(tmp_path, monkeypatch):
    out = tmp_path / "pics"
    monkeypatch.setenv("SEED_DEVICE_PICTURES", str(out))
    sess = capture.Session(dir=tmp_path / "tmp")
    sess.dir.mkdir()
    now = dt.datetime(2026, 11, 7, 9, 30, 0)
    shot = sess.add(jpeg(), {"lat": 34.05, "lon": 134.25}, now)
    assert shot.kept == out / "2026-11-07" / "20261107-093000-1.jpg"
    assert shot.kept.read_bytes() == shot.path.read_bytes()
    # 消すと Pictures/seed の写しも消える（作者 11-07「失敗した写真や動画を簡単に消せない」）。元に戻せる
    sess.remove(shot)
    assert not shot.path.exists() and not shot.kept.exists() and sess.shots == []
    sess.undo(shot)
    assert shot.path.exists() and shot.kept.exists() and sess.shots == [shot]


def test_keep_on_device_failure(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("SEED_DEVICE_PICTURES", str(blocker))
    sess = capture.Session(dir=tmp_path / "tmp")
    sess.dir.mkdir()
    assert sess.add(jpeg(), {"lat": 34.05, "lon": 134.25}).kept is None


def test_keep_on_device_none_on_linux(tmp_path, monkeypatch):
    monkeypatch.delenv("SEED_DEVICE_PICTURES", raising=False)
    sess = capture.Session(dir=tmp_path / "tmp")
    sess.dir.mkdir()
    assert sess.add(jpeg(), {"lat": 34.05, "lon": 134.25}).kept is None


def test_keep_video_writes_mp4_and_where(tmp_path, monkeypatch):
    """動画は記録の videos/<日>/<時刻>.mp4 に、撮った所と時は同じ名の .json に。Pictures/seed にも残す。"""
    import datetime as dt
    import json

    from seed.app import capture

    pics = tmp_path / "pics"
    monkeypatch.setenv("SEED_DEVICE_PICTURES", str(pics))
    now = dt.datetime(2026, 11, 7, 16, 5, 9)
    path = capture.keep_video(
        tmp_path / "rec", b"mp4-bytes", {"lat": 34.08, "lon": 134.45, "accuracy": 5.0}, now
    )
    assert path == tmp_path / "rec" / "videos" / "2026-11-07" / "160509.mp4"
    assert path.read_bytes() == b"mp4-bytes"
    where = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    assert where["taken"] == "2026-11-07T16:05:09" and where["lat"] == 34.08 and where["accuracy"] == 5.0
    assert (pics / "2026-11-07" / "160509.mp4").read_bytes() == b"mp4-bytes"


def test_send_video_home_sends_the_where_and_the_field(tmp_path):
    from contextlib import contextmanager

    seen = {}

    class FakeClient:
        def video(self, path, where, field=None):
            seen.update(path=path, where=where, field=field)
            return "videos/2026-11-07/150405.mp4"

    class FakeApp:
        field_name = "畑"

        @contextmanager
        def client(self):
            yield FakeClient()

    path = capture.keep_video(
        tmp_path, b"\0\0\0\x18ftypmp42", {"lat": 34.1, "lon": 134.5}, dt.datetime(2026, 11, 7, 15, 4, 5)
    )
    assert capture.send_video_home(FakeApp(), path) == "videos/2026-11-07/150405.mp4"
    assert seen["path"] == path and seen["field"] == "畑"
    assert seen["where"] == {"taken": "2026-11-07T15:04:05", "lat": 34.1, "lon": 134.5}
    assert '"sent"' in path.with_suffix(".json").read_text(encoding="utf-8")


def test_unsent_videos_are_sent_once(tmp_path):
    """送れた動画は .json に sent が付き、次からは送らない。送っていない物は古い順に残る。"""
    from contextlib import contextmanager

    seen = []

    class FakeClient:
        def video(self, path, where, field=None):
            assert "sent" not in where
            seen.append(path.name)
            return f"videos/2026-11-07/{path.name}"

    class FakeApp:
        field_name = None

        @contextmanager
        def client(self):
            yield FakeClient()

    root = tmp_path / "rec"
    a = capture.keep_video(root, b"a", None, dt.datetime(2026, 11, 7, 17, 19, 51))
    b = capture.keep_video(root, b"b", None, dt.datetime(2026, 11, 7, 17, 20, 43))
    assert capture.unsent_videos(root) == [a, b]
    capture.send_video_home(FakeApp(), a)
    assert capture.unsent_videos(root) == [b]
    assert '"sent": "videos/2026-11-07/171951.mp4"' in a.with_suffix(".json").read_text(encoding="utf-8")
    assert capture.unsent_videos(tmp_path / "none") == []


def test_deleted_video_goes_with_its_where_and_copy_and_is_never_sent(tmp_path, monkeypatch):
    pics = tmp_path / "pics"
    monkeypatch.setenv("SEED_DEVICE_PICTURES", str(pics))
    root = tmp_path / "rec"
    sess = capture.Session(dir=tmp_path / "tmp")
    try:
        path = capture.keep_video(root, b"v", None, dt.datetime(2026, 11, 7, 18, 30, 0))
        shot = sess.add_video(path)
        assert shot.kind == "video" and shot.kept == pics / "2026-11-07" / "183000.mp4"
        assert sess.paths() == []  # 動画は観察の写真に入らない
        assert capture.unsent_videos(root) == [path]
        sess.remove(shot)
        assert not path.exists() and not path.with_suffix(".json").exists() and not shot.kept.exists()
        assert capture.unsent_videos(root) == []  # 消した物は PC へ送らない
        sess.undo(shot)
        assert path.exists() and path.with_suffix(".json").exists() and shot.kept.exists()
        sess.remove(shot)
    finally:
        sess.close()
    assert not path.exists()  # カメラを出たら、消した物は本当に消える


def test_videos_do_not_count_toward_the_photo_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DEVICE_PICTURES", str(tmp_path / "pics"))
    sess = capture.Session(dir=tmp_path / "tmp")
    sess.dir.mkdir()
    try:
        here = capture.position_fields(pos())
        sess.add_video(capture.keep_video(tmp_path / "rec", b"v", here, dt.datetime(2026, 11, 7, 18, 0, 0)))
        for i in range(capture.MAX_SHOTS):
            sess.add(jpeg(), here, dt.datetime(2026, 11, 7, 18, 1, i))
        assert len(sess.paths()) == capture.MAX_SHOTS and len(sess.shots) == capture.MAX_SHOTS + 1
    finally:
        sess.close()


def test_zoom_steps_like_the_standard_camera():
    assert capture.zoom_steps(0.5, 10.0) == [0.5, 1.0, 2.0, 5.0, 10.0]
    assert capture.zoom_steps(1.0, 8.0) == [1.0, 2.0, 5.0]
    assert capture.zoom_steps(0.6, 4.0) == [0.6, 1.0, 2.0]  # 最小が 0.5 でない機種は最小を出す
    assert capture.zoom_steps(1.0, 1.0) == []  # 倍率を持たない機種は印を出さない
    assert capture.zoom_label(1.0) == "1×" and capture.zoom_label(2.5) == "2.5×"
    assert capture.clamp(12, 0.5, 10) == 10 and capture.clamp(0.1, 0.5, 10) == 0.5


def test_landscape_and_clock():
    assert capture.is_landscape(2400, 1080) and not capture.is_landscape(1080, 2400)
    assert not capture.is_landscape(None, None)
    assert capture.clock(0) == "0:00" and capture.clock(75.9) == "1:15"


def test_capture_strings_exist_in_both_languages():
    from seed.app.strings import s

    for word in (
        "capture_back", "capture_photo", "capture_video", "capture_review", "capture_delete",
        "capture_deleted", "capture_undo", "capture_leave_drop", "capture_pos_ok_short",
    ):  # fmt: skip
        assert s(word, "ja") != word and s(word, "en") != word
    assert "3" in s("capture_leave", "ja", n=3) and "46" in s("capture_pos_m", "en", m=46)


# ---------------------------------------------------------------- 見直し（11-07 夜）


def test_undo_does_not_go_past_six_photos(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DEVICE_PICTURES", str(tmp_path / "pics"))
    sess = capture.Session(dir=tmp_path / "tmp")
    sess.dir.mkdir()
    try:
        here = capture.position_fields(pos())
        shots = [sess.add(jpeg(), here, dt.datetime(2026, 11, 7, 19, 0, i)) for i in range(capture.MAX_SHOTS)]
        sess.remove(shots[0])
        sess.add(jpeg(), here, dt.datetime(2026, 11, 7, 19, 1, 0))
        with pytest.raises(photos.PhotoError) as e:
            sess.undo(shots[0])
        assert e.value.word == "too_many_photos" and len(sess.paths()) == capture.MAX_SHOTS
    finally:
        sess.close()


def test_trash_sits_beside_the_file_and_goes_on_close(tmp_path, monkeypatch):
    pics = tmp_path / "pics"
    monkeypatch.setenv("SEED_DEVICE_PICTURES", str(pics))
    root = tmp_path / "rec"
    sess = capture.Session(dir=tmp_path / "tmp")
    sess.dir.mkdir()
    path = capture.keep_video(root, b"v", None, dt.datetime(2026, 11, 7, 19, 2, 0))
    shot = sess.add_video(path)
    sess.remove(shot)
    beside = path.parent / capture.TRASH
    assert beside.is_dir() and (pics / "2026-11-07" / capture.TRASH).is_dir()
    assert capture.unsent_videos(root) == []  # ごみ箱の中は送らない
    sess.close()
    assert not beside.exists() and not (pics / "2026-11-07" / capture.TRASH).exists()


def test_photo_keeps_a_small_thumb():
    sess = capture.Session()
    try:
        shot = sess.add(jpeg(), capture.position_fields(pos()))
        assert shot.thumb and len(shot.thumb) < shot.path.stat().st_size + 1
    finally:
        sess.close()


def test_keep_video_does_not_overwrite_the_same_second(tmp_path):
    now = dt.datetime(2026, 11, 7, 19, 3, 0)
    a = capture.keep_video(tmp_path, b"a", None, now)
    b = capture.keep_video(tmp_path, b"b", None, now)
    assert a.name == "190300.mp4" and b.name == "190300-2.mp4" and a.read_bytes() == b"a"


def test_refused_video_is_marked_and_not_sent_again(tmp_path):
    root = tmp_path / "rec"
    a = capture.keep_video(root, b"a", None, dt.datetime(2026, 11, 7, 19, 4, 0))
    b = capture.keep_video(root, b"b", None, dt.datetime(2026, 11, 7, 19, 5, 0))
    capture.mark_refused(a, "server_rejected")
    assert capture.unsent_videos(root) == [b]


def test_sending_skips_a_refused_video_and_goes_on(tmp_path, monkeypatch):
    import asyncio

    from seed.app import talk
    from seed.client import ClientError

    root = tmp_path / "rec"
    big = capture.keep_video(root, b"big", None, dt.datetime(2026, 11, 7, 19, 6, 0))
    ok = capture.keep_video(root, b"ok", None, dt.datetime(2026, 11, 7, 19, 7, 0))
    toasts = []

    def fake_send(app, path):
        if path == big:
            raise ClientError("server_rejected", "the server did not accept it", None, 413)
        return "videos/2026-11-07/190700.mp4"

    async def yes(app):
        return True

    monkeypatch.setattr(capture, "send_video_home", fake_send)
    monkeypatch.setattr(talk, "home_server", yes)
    app = SimpleNamespace(
        state={}, folder=SimpleNamespace(root=root), toast=toasts.append, t=lambda k, **kw: k
    )
    asyncio.run(capture.send_pending_videos(app))
    assert toasts == ["capture_video_sent", "capture_video_refused"]
    assert capture.unsent_videos(root) == [ok]  # 送った物の印は fake では付かない。big は断られた印
    assert app.state == {}


def test_sending_to_an_old_home_without_the_video_door_keeps_it_for_later(tmp_path, monkeypatch):
    """動画を受ける口の無い古い seed home は 404 を返す。断られた印は付けず、PC を新しくした後にまた送る。"""
    import asyncio

    from seed.app import talk
    from seed.client import ClientError

    root = tmp_path / "rec"
    a = capture.keep_video(root, b"a", None, dt.datetime(2026, 11, 7, 19, 8, 0))
    toasts = []

    def old_home(app, path):
        raise ClientError("server_rejected", "not found", None, 404)

    async def yes(app):
        return True

    monkeypatch.setattr(capture, "send_video_home", old_home)
    monkeypatch.setattr(talk, "home_server", yes)
    app = SimpleNamespace(
        state={}, folder=SimpleNamespace(root=root), toast=toasts.append, t=lambda k, **kw: k
    )
    asyncio.run(capture.send_pending_videos(app))
    assert toasts == ["capture_video_not_sent"]
    assert capture.unsent_videos(root) == [a]  # refused の印は無い
    assert "refused" not in capture._side(a)


def test_sending_while_the_gate_waits_keeps_videos_for_later(tmp_path, monkeypatch):
    """招待コードを何度も間違えて門が止めている間（429 too_many_tries）は、印を付けずに止め、次にまた送る。"""
    import asyncio

    from seed.app import talk
    from seed.client import ClientError

    root = tmp_path / "rec"
    a = capture.keep_video(root, b"a", None, dt.datetime(2026, 11, 7, 19, 9, 0))
    b = capture.keep_video(root, b"b", None, dt.datetime(2026, 11, 7, 19, 10, 0))
    tried = []
    toasts = []

    def gate(app, path):
        tried.append(path)
        raise ClientError("server_tries", "too many wrong invite codes; wait a while", None, 429)

    async def yes(app):
        return True

    monkeypatch.setattr(capture, "send_video_home", gate)
    monkeypatch.setattr(talk, "home_server", yes)
    app = SimpleNamespace(
        state={}, folder=SimpleNamespace(root=root), toast=toasts.append, t=lambda k, **kw: k
    )
    asyncio.run(capture.send_pending_videos(app))
    assert tried == [a]  # そこで止める（後ろの動画で門を叩き続けない）
    assert toasts == ["capture_video_not_sent"]
    assert capture.unsent_videos(root) == [a, b]
