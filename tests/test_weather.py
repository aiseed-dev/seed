# SPDX-License-Identifier: AGPL-3.0-or-later
"""週の予報（weather.fetch_forecast、parse_forecast、weather_word）。"""

from __future__ import annotations

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
