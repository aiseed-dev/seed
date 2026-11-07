# SPDX-License-Identifier: AGPL-3.0-or-later
"""気象の実績の記録: 行の形（新旧）、穴埋め（過去データと予報の過去の値）。"""

from __future__ import annotations

import datetime as dt

from seed import cli
from seed import weather as W
from seed.records import Folder, Observation

REAL_FILL = W.fill_missing  # conftest の差し替えより前の本物
LAT, LON = 34.0512, 134.2534
OLD = (
    "- 2026-11-05: 最高 18.2 ℃、最低 9.1 ℃、降水 0.0 mm、日照 7.4 h"
    "（出典: Open-Meteo 過去データ https://open-meteo.com/ 、確認日 2026-11-06）"
)
NEW = (
    "- 2026-11-05: 最高 18.2 ℃、最低 9.1 ℃、平均 13.4 ℃、降水 0.0 mm、日照 7.4 h、蒸発散 2.1 mm、"
    "風 4.2 m/s（突風 9.8）、地温 0-7cm 15.1 / 7-28cm 15.8 / 28-100cm 17.0 / 100-255cm 19.2 ℃、"
    "水分 0-7cm 0.31 / 7-28cm 0.30 / 28-100cm 0.29 / 100-255cm 0.28"
    "（出典: Open-Meteo 過去データ https://open-meteo.com/ 、確認日 2026-11-06）"
)


def test_parse_line_both_forms():
    old = W.parse_line(OLD)
    assert (old.tmax, old.tmin, old.rain, old.sun_h) == (18.2, 9.1, 0.0, 7.4)
    assert old.tavg is None and old.wind is None and old.soil_t == (None,) * 4 and old.source == "archive"
    new = W.parse_line(NEW)
    assert (new.tavg, new.et0, new.wind, new.gust) == (13.4, 2.1, 4.2, 9.8)
    assert new.soil_t == (15.1, 15.8, 17.0, 19.2) and new.soil_m == (0.31, 0.30, 0.29, 0.28)
    assert W.parse_line("- note: 本人の行") is None
    fc = W.parse_line(NEW.replace("過去データ", "予報の過去の値"))
    assert fc.source == "forecast"


def test_render_roundtrip_ja_en():
    day = W.parse_line(NEW)
    assert day.render("ja", "2026-11-06") == NEW
    en = day.render("en", "2026-11-06")
    assert "mean 13.4 °C" in en and "wind 4.2 m/s (gusts 9.8)" in en and "soil temp 0-7cm 15.1" in en
    assert W.parse_line(en) == day
    assert (
        W.Day("2026-11-05", 18.2, 9.1, 0.0, 7.4).render("ja", "2026-11-06") == OLD
    )  # 足した値が無ければ古い形


def answer(days, soil=True, forecast=False):
    n = len(days)
    d = {
        "time": list(days),
        "temperature_2m_max": [20.0] * n,
        "temperature_2m_min": [10.0] * n,
        "precipitation_sum": [1.0] * n,
        "sunshine_duration": [3600.0] * n,
        "temperature_2m_mean": [15.0] * n,
        "et0_fao_evapotranspiration": [2.0] * n,
        "wind_speed_10m_max": [3.0] * n,
        "wind_gusts_10m_max": [8.0] * n,
    }
    for k in (*W.SOIL_T_DAILY, *W.SOIL_M_DAILY):
        d[k] = [16.0 if "temperature" in k else 0.3] * n
    return {"daily": d}


class Resp:
    def __init__(self, data):
        self.data, self.status_code = data, 200

    def json(self):
        return self.data


def make_folder(seedfolder, first="2026-11-03"):
    folder = Folder(seedfolder)
    folder.observations.mkdir(parents=True)
    obs = Observation(first, "10:00:00", location={"center": [LAT, LON], "points": 1, "extent_m": 5})
    obs.write(folder.observation_path(obs))
    return folder


def test_fill_missing_archive_then_forecast_gap_and_replace(seedfolder):
    folder = make_folder(seedfolder)
    today = dt.date(2026, 11, 7)  # 昨日は 11-06
    calls = []

    def get(url, params=None, timeout=None):
        calls.append((url, params))
        if url == W.ARCHIVE_URL:  # 過去データは 11-05 までしか無い（11-06 は値が空）
            days = ["2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
            a = answer(days)
            for k in a["daily"]:
                if k != "time":
                    a["daily"][k][3] = None
            return Resp(a)
        return Resp(answer(["2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07"]))

    assert REAL_FILL(folder, "ja", get=get, today=today) == 4  # 過去データ 3 日 + 予報の過去の値 1 日
    text = (seedfolder / "weather" / "2026-11.md").read_text(encoding="utf-8")
    assert text.count("過去データ https") == 3 and text.count("予報の過去の値") == 1
    assert "- 2026-11-06:" in text and "- 2026-11-07:" not in text  # 昨日まで。予報は書かない
    assert [c[0] for c in calls] == [W.ARCHIVE_URL, W.FORECAST_URL]
    assert calls[0][1]["latitude"] == "34.05" and calls[0][1]["start_date"] == "2026-11-03"
    assert calls[1][1]["past_days"] == 7 and calls[1][1]["forecast_days"] == 1

    # 過去データが 11-06 を持ったら、予報の過去の値の行を置き換える
    def get2(url, params=None, timeout=None):
        assert url == W.ARCHIVE_URL and params["start_date"] == params["end_date"] == "2026-11-06"
        return Resp(answer(["2026-11-06"]))

    assert REAL_FILL(folder, "ja", get=get2, today=today) == 1
    text = (seedfolder / "weather" / "2026-11.md").read_text(encoding="utf-8")
    assert text.count("予報の過去の値") == 0 and text.count("過去データ https") == 4

    # 何も足りなければ網に出ない
    def never(*a, **k):
        raise AssertionError("fetched")

    assert REAL_FILL(folder, "ja", get=never, today=today) == 0


def test_fill_missing_never_raises_and_needs_center(seedfolder):
    folder = make_folder(seedfolder)

    def down(*a, **k):
        raise OSError("no network")

    assert REAL_FILL(folder, "ja", get=down, today=dt.date(2026, 11, 7)) == 0
    assert not (seedfolder / "weather").exists()
    empty = Folder(seedfolder.parent / "empty")
    assert REAL_FILL(empty, "ja", get=down, today=dt.date(2026, 11, 7)) == 0


def test_cli_weather_fill_and_observe_calls_it(seedfolder, monkeypatch, capsys):
    from test_fieldwork import run

    monkeypatch.setattr(W, "fill_missing", lambda folder, lg, **k: 3)
    assert run(seedfolder, "weather", "fill") == 0
    assert "3 日分足した" in capsys.readouterr().out
    monkeypatch.setattr(W, "fill_missing", lambda folder, lg, **k: 0)
    assert run(seedfolder, "weather", "fill") == 0
    assert "足す日は無い" in capsys.readouterr().out
    assert hasattr(cli, "_fill_weather")
