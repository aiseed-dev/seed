# SPDX-License-Identifier: AGPL-3.0-or-later
"""週の予報（weather.fetch_forecast、parse_forecast、weather_word）。"""

from __future__ import annotations

import datetime as dt

import pytest

from seed import weather as W

SAMPLE = {
    "daily": {
        "time": ["2026-11-08", "2026-11-09"],
        "weather_code": [0, 95],
        "temperature_2m_max": [18.4, None],
        "temperature_2m_min": [9.6, 8.0],
        "precipitation_sum": [0.0, 12.5],
        "precipitation_probability_max": [10, 80],
    }
}


class Resp:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        if self.data is None:
            raise ValueError("x")
        return self.data


def test_parse_forecast():
    a, b = W.parse_forecast(SAMPLE)
    assert a == W.Forecast("2026-11-08", 0, 18.4, 9.6, 0.0, 10)
    assert b.tmax is None and b.rain == 12.5 and b.rain_prob == 80
    with pytest.raises(W.WeatherError):
        W.parse_forecast({"daily": {"time": ["x"]}})


def test_fetch_forecast_rounds_and_asks_daily():
    seen = {}

    def get(url, params=None, timeout=None):
        seen.update(url=url, params=params, timeout=timeout)
        return Resp(SAMPLE)

    rows = W.fetch_forecast(34.05678, 134.24321, get=get)
    assert len(rows) == 2 and seen["url"] == W.FORECAST_URL
    assert seen["params"]["latitude"] == "34.06" and seen["params"]["longitude"] == "134.24"
    assert "precipitation_probability_max" in seen["params"]["daily"] and seen["params"]["forecast_days"] == 7
    assert seen["timeout"] == 10.0


def test_fetch_forecast_errors():
    with pytest.raises(W.WeatherError) as e:
        W.fetch_forecast(1, 2, get=lambda *a, **k: Resp({}, 500))
    assert e.value.word == "weather_http"
    with pytest.raises(W.WeatherError):
        W.fetch_forecast(1, 2, get=lambda *a, **k: Resp(None))


def test_weather_word():
    assert [W.weather_word(c, "ja") for c in (0, 2, 3, 45, 53, 63, 73, 81, 95)] == [
        "快晴", "晴れ", "くもり", "霧", "霧雨", "雨", "雪", "にわか雨", "雷雨",
    ]  # fmt: skip
    assert [W.weather_word(c, "en") for c in (0, 3, 63, 95)] == ["Clear", "Cloudy", "Rain", "Thunder"]
    assert W.weather_word(999, "ja") == "—"


def soil_payload():
    h = {"time": ["2026-11-08T13:00", "2026-11-08T14:00", "2026-11-08T15:00"]}
    for i, k in enumerate(W.HOURLY):
        h[k] = [1.0 + i, 2.0 + i, None]
    return {**SAMPLE, "hourly": h}


def test_parse_soil_picks_latest_hour_not_after_now():
    s = W.parse_soil(soil_payload(), now=dt.datetime(2026, 11, 8, 14, 30))
    assert s.time == "2026-11-08T14:00"
    assert s.temp == {"0 cm": 2.0, "6 cm": 3.0, "18 cm": 4.0, "54 cm": 5.0}
    assert s.moisture["0-1 cm"] == 6.0 and s.moisture["27-81 cm"] == 10.0
    assert W.parse_soil(soil_payload(), now=dt.datetime(2026, 11, 8, 15, 0)).temp["0 cm"] is None
    assert W.parse_soil(soil_payload(), now=dt.datetime(2026, 11, 8, 12, 0)) is None
    assert W.parse_soil(SAMPLE) is None


def test_fetch_week_asks_hourly_soil():
    seen = {}

    def get(url, params=None, timeout=None):
        if url == W.FORECAST_URL:
            seen.update(params)
        return Resp(soil_payload())

    rows, soil = W.fetch_week(34.05, 134.25, get=get)
    assert (
        len(rows) == 2
        and "soil_temperature_54cm" in seen["hourly"]
        and "soil_moisture_27_to_81cm" in seen["hourly"]
    )
    assert soil is None or soil.time.startswith("2026-11-08")


def test_fetch_surface():
    seen = {}
    data = {
        "hourly": {
            "time": ["2026-11-08T12:00", "2026-11-08T15:00", "2026-11-08T18:00"],
            "surface_temperature": [15.1, 16.4, 12.0],
        }
    }

    def get(url, params=None, timeout=None):
        seen.update(url=url, params=params)
        return Resp(data)

    got = W.fetch_surface(34.05678, 134.24321, get=get, now=dt.datetime(2026, 11, 8, 16, 0))
    assert got == ("2026-11-08T15:00", 16.4) and seen["url"] == W.ECMWF_URL
    assert seen["params"]["latitude"] == "34.06" and seen["params"]["hourly"] == "surface_temperature"
    assert W.fetch_surface(1, 2, get=get, now=dt.datetime(2026, 11, 8, 9, 0)) is None
    assert W.fetch_surface(1, 2, get=lambda *a, **k: Resp({}, 500)) is None
    assert W.fetch_surface(1, 2, get=lambda *a, **k: Resp(None)) is None

    def boom(*a, **k):
        raise RuntimeError("x")

    assert W.fetch_surface(1, 2, get=boom) is None


def test_fetch_week_includes_surface():
    def get(url, params=None, timeout=None):
        if url == W.ECMWF_URL:
            return Resp({"hourly": {"time": ["2000-01-01T00:00"], "surface_temperature": [7.5]}})
        return Resp(SAMPLE)  # hourly の無い答え

    rows, soil = W.fetch_week(34.05, 134.25, get=get)
    assert len(rows) == 2 and soil.surface == ("2000-01-01T00:00", 7.5) and soil.temp == {}


def test_parse_forecast_farm_fields():
    data = {"daily": {**SAMPLE["daily"]}}
    data["daily"].update(
        sunshine_duration=[18720.0, None],
        et0_fao_evapotranspiration=[2.14, 1.0],
        wind_speed_10m_max=[3.2, 5.0],
        wind_gusts_10m_max=[8.1, None],
        wind_direction_10m_dominant=[315, 90],
    )
    a, b = W.parse_forecast(data)
    assert (a.sunshine_h, a.et0, a.wind, a.gust, a.wind_dir) == (5.2, 2.14, 3.2, 8.1, 315)
    assert b.sunshine_h is None and b.gust is None and b.wind_dir == 90
    c = W.parse_forecast(SAMPLE)[0]  # 無い列は None
    assert (c.sunshine_h, c.et0, c.wind, c.gust, c.wind_dir) == (None,) * 5


def test_fetch_asks_farm_variables_in_ms():
    seen = {}

    def get(url, params=None, timeout=None):
        if url == W.FORECAST_URL:
            seen.update(params)
        return Resp(SAMPLE)

    W.fetch_forecast(34.05, 134.25, get=get)
    assert seen["wind_speed_unit"] == "ms" and "et0_fao_evapotranspiration" in seen["daily"]


def test_wind_name():
    assert [W.wind_name(d, "ja") for d in (0, 22.5, 45, 90, 180, 315, 350, 360)] == [
        "北", "北北東", "北東", "東", "南", "北西", "北", "北",
    ]  # fmt: skip
    assert [W.wind_name(d, "en") for d in (0, 45, 202, 315, 349)] == ["N", "NE", "SSW", "NW", "N"]
