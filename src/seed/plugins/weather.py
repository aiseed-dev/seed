# SPDX-License-Identifier: AGPL-3.0-or-later
"""天気。畑の座標の、この一週間の予報（Open-Meteo。AI 無し）。"""

from __future__ import annotations

import asyncio
import datetime as dt

import flet as ft

from seed import land, weather
from seed.app import theme

TITLE = {"ja": "天気", "en": "Weather"}
ICON = "WB_SUNNY_OUTLINED"

WEEKDAYS = {"ja": "月火水木金土日", "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}


def centre(app) -> tuple[float, float] | None:
    """畑の座標。プロジェクト全体の時は、座標のある最初の畑。"""
    if getattr(app, "whole", False):
        for f in app.fields:
            c = land.center(f)
            if c:
                return c
        return None
    return land.center(app.folder)


def day_label(date: str, language: str) -> str:
    try:
        d = dt.date.fromisoformat(date)
    except ValueError:
        return date
    wd = WEEKDAYS["ja" if language == "ja" else "en"][d.weekday()]
    if language == "ja":
        return f"{d:%m/%d}（{wd}）"
    return f"{wd} {d:%m/%d}"


def number(v: float | None, unit: str) -> str:
    return "—" if v is None else f"{v:.0f}{unit}"


def row(f: weather.Forecast, language: str) -> ft.Control:
    """一日 = 二行。一行目は日と天気、二行目は小さく気温と降水。"""
    ja = language == "ja"
    rain = "—" if f.rain is None else f"{f.rain:.1f} mm"
    prob = number(f.rain_prob, " %")
    tmax, tmin = number(f.tmax, " ℃"), number(f.tmin, " ℃")
    if ja:
        detail = f"最高 {tmax} / 最低 {tmin}  降水 {rain}（{prob}）"
    else:
        detail = f"max {tmax} / min {tmin}  rain {rain} ({prob})"
    head = f"{day_label(f.date, language)}  {weather.weather_word(f.code, language)}"
    return ft.Column([ft.Text(head, size=theme.BODY_SIZE), theme.muted(detail)], tight=True, spacing=2)


def soil_controls(app, soil: weather.Soil | None) -> list[ft.Control]:
    if soil is None:
        return []
    t = app.t
    temp = " · ".join(f"{k} {number(v, ' ℃')}" for k, v in soil.temp.items())
    moist = " · ".join(f"{k} {'—' if v is None else f'{v:.2f}'}" for k, v in soil.moisture.items())
    return [
        theme.subheading(t("weather_soil", time=soil.time[-5:])),
        ft.Text(f"{t('weather_soil_temp')}: {temp}", size=theme.BODY_SIZE),
        ft.Text(f"{t('weather_soil_moist')}: {moist} m³/m³", size=theme.BODY_SIZE),
        theme.muted(t("weather_soil_note")),
    ]


def build(app) -> list[ft.Control]:
    t, st = app.t, app.state
    c = centre(app)
    if c is None:
        return [ft.Text(t("weather_need_photo"), size=theme.BODY_SIZE)]
    key = (*c, dt.date.today().isoformat())
    cached = st.get("forecast")
    failed = st.get("forecast_failed")

    def refresh(e) -> None:
        st.pop("forecast", None)
        st.pop("forecast_failed", None)
        app.refresh()

    button = ft.TextButton(t("weather_refresh"), icon=ft.Icons.REFRESH, on_click=refresh)
    if cached and cached[0] == key:
        rows, soil = cached[1]
        return [
            *soil_controls(app, soil),
            theme.subheading(TITLE.get(app.lang, TITLE["en"])),
            ft.Column([row(f, app.lang) for f in rows], spacing=8),
            theme.muted(t("weather_source")),
            button,
        ]
    if failed and failed[0] == key:
        return [theme.error(t("weather_failed", detail=failed[1])), button]
    if st.get("forecast_loading") != key:
        st["forecast_loading"] = key

        async def load() -> None:
            try:
                got = await asyncio.to_thread(weather.fetch_week, *c)
                st["forecast"] = (key, got)
            except weather.WeatherError as ex:
                st["forecast_failed"] = (key, ex.detail or ex.word)
            except Exception as ex:  # noqa: BLE001
                st["forecast_failed"] = (key, type(ex).__name__)
            st.pop("forecast_loading", None)
            app.refresh()

        app.page.run_task(load)
    return [theme.muted(t("weather_fetching"))]
