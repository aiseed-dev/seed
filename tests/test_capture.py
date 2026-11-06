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
        "capture_button", "capture_title", "capture_hint", "capture_open", "capture_shoot",
        "capture_waiting", "capture_position_plain", "capture_no_position", "capture_location_denied",
        "capture_no_camera", "capture_remove", "capture_retry_position", "capture_cancel",
    ):  # fmt: skip
        assert s(word, "ja") != word and s(word, "en") != word
    assert "3" in s("capture_done", "ja", n=3) and "8" in s("capture_position_ok", "en", m=8)


def test_page_column_fits_a_phone():
    from seed.app import theme

    assert theme.fit_width(None) == theme.MAX_WIDTH and theme.fit_width(1280) == theme.MAX_WIDTH
    assert theme.fit_width(390) == 390  # 電話の幅では、窓の幅に合わせる（右が切れない）
    assert theme.page_column([], 390).width == 390
