# SPDX-License-Identifier: AGPL-3.0-or-later
"""天気の図（chart.py）。"""

from __future__ import annotations

import datetime as dt

from seed import chart
from seed import weather as W

NOW = dt.datetime(2026, 11, 8, 7, 30)


def hours(rain_every=5):
    return {
        f"2026-11-{d:02d}": [
            W.Hour(
                f"2026-11-{d:02d}T{h:02d}:00",
                0,
                9.0 + h / 4,
                80,
                7.0,
                1.5 if h % rain_every == 0 else 0.0,
                40,
                2.0,
                5.0,
                90,
            )
            for h in range(24)
        ]
        for d in (8, 9)
    }


def rows(n=16, **kw):
    base = {"sunshine_h": 5.0, "et0": 2.0, "wind": 3.0, "gust": 8.0, "wind_dir": 90}
    base.update(kw)
    return [
        W.Forecast(f"2026-11-{8 + i:02d}", 0, 18.0, 9.0, 2.5 if i % 2 == 0 else 0.0, 70, **base)
        for i in range(n)
    ]


def soil_hours(n=48):
    return [
        (f"2026-11-{8 + i // 24:02d}T{i % 24:02d}:00", dict.fromkeys(("0 cm", "6 cm", "18 cm", "54 cm"), 15.0 + i % 24 / 4),
         dict.fromkeys(("0-1 cm", "1-3 cm", "3-9 cm", "9-27 cm", "27-81 cm"), 0.3))
        for i in range(n)
    ]  # fmt: skip


def test_hourly_from_now_to_end_of_tomorrow():
    svg = chart.hourly_svg(hours(), NOW, "ja")
    assert svg.startswith("<svg") and "11/9（月）" in svg and "9時" in svg
    n = 17 + 24  # 今日の 07〜23 時と明日の 24 時間
    assert svg.count('fill-opacity="0.85"') == 8 + 1  # 雨の棒 8 本（今日 3、明日 5）と凡例の印
    assert svg.count("<path") == 3  # 気温、降水確率、湿度
    assert chart.size(svg)[0] == 96 + 20 * n
    assert "<text" in chart.hourly_svg(hours(), NOW, "en") and "Mon 11/9" in chart.hourly_svg(
        hours(), NOW, "en"
    )


def test_hourly_none_and_empty():
    h = hours()
    h["2026-11-09"][3] = W.Hour("2026-11-09T03:00", None, None, None, None, None, None, None, None, None)
    svg = chart.hourly_svg(h, NOW, "ja")
    assert svg.startswith("<svg") and svg.count("<path") >= 4  # 気温の線が一か所で切れる
    assert chart.hourly_svg({}, NOW, "ja") == ""
    assert chart.hourly_svg(hours(), dt.datetime(2030, 1, 1), "ja") == ""


def test_daily_lines_dots_and_bars():
    svg = chart.daily_svg(rows(), "ja")
    assert svg.startswith("<svg") and svg.count("<path") == 2
    assert svg.count("<circle") == 32 and svg.count('fill-opacity="0.85"') == 8 + 1  # 雨の日 8 本と凡例の印
    assert "11/8" in svg and "（日）" in svg
    assert chart.daily_svg([], "ja") == ""
    none = chart.daily_svg(
        rows(
            3,
        )
        and [W.Forecast("2026-11-08", 0, None, None, None, None)],
        "en",
    )
    assert none.startswith("<svg") and none.count("<path") == 0


def test_work_two_panels():
    svg = chart.work_svg(rows(), "ja")
    assert svg.startswith("<svg") and svg.count("<path") == 3 and chart.size(svg)[1] == 480
    assert svg.count('fill-opacity="0.85"') == 16 + 1  # 日照の棒 16 本と凡例の印
    missing = chart.work_svg(rows(sunshine_h=None, et0=None, wind=None, gust=None), "ja")
    assert missing.startswith("<svg") and missing.count("<path") == 0
    assert chart.work_svg([], "ja") == ""


def test_soil_two_panels():
    svg = chart.soil_svg(soil_hours(), "ja")
    assert svg.startswith("<svg") and svg.count("<path") == 4 + 5 and "11/9（月）" in svg
    assert chart.soil_svg([], "ja") == ""
    holes = soil_hours()
    holes[5] = (holes[5][0], dict.fromkeys(holes[5][1]), dict.fromkeys(holes[5][2]))
    assert chart.soil_svg(holes, "en").count("<path") == 4 * 2 + 5 * 2


def test_png_renders_text_when_resvg_is_there():
    svg = chart.daily_svg(rows(), "ja")
    got = chart.png(svg)
    assert got is None or got[:4] == b"\x89PNG"
