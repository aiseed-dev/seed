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
API_URL = "https://open-meteo.com/en/docs"
ECMWF_URL = "https://open-meteo.com/en/docs/ecmwf-api"

WEEKDAYS = {"ja": "月火水木金土日", "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}


def now() -> dt.datetime:
    return dt.datetime.now()


def today() -> dt.date:
    return now().date()


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


def far_line(f: weather.Forecast, language: str) -> ft.Control:
    """二週間先までの一日 = 一行。"""
    rain = "—" if f.rain is None else f"{f.rain:.1f} mm"
    prob = number(f.rain_prob, " %")
    tmax, tmin = number(f.tmax, " ℃"), number(f.tmin, " ℃")
    head = f"{day_label(f.date, language)}  {weather.weather_word(f.code, language)}"
    if language == "ja":
        return ft.Text(f"{head}  最高 {tmax} / 最低 {tmin}  降水 {rain}（{prob}）", size=theme.BODY_SIZE)
    return ft.Text(f"{head}  max {tmax} / min {tmin}  rain {rain} ({prob})", size=theme.BODY_SIZE)


def short_hour_line(h: weather.Hour, language: str) -> ft.Control:
    """今日と明日の一時間の行（雨が先。雨のある時は薄くしない）。"""
    ja = language == "ja"
    word = "—" if h.code is None else weather.weather_word(h.code, language)
    rain = "—" if h.rain is None else f"{h.rain:.1f} mm"
    prob = number(h.rain_prob, " %")
    wind = number(h.wind, " m/s")
    if h.wind_dir is not None:
        wind += f" {weather.wind_name(h.wind_dir, language)}"
    temp, rh = number(h.temp, " ℃"), number(h.humidity, " %")
    if ja:
        text = f"{h.time[-5:]}  雨 {rain}（{prob}）  {word}  {temp}  風 {wind}  湿度 {rh}"
    else:
        text = f"{h.time[-5:]}  rain {rain} ({prob})  {word}  {temp}  wind {wind}  RH {rh}"
    if h.rain:
        return ft.Text(text, size=13, selectable=True)
    return theme.muted(text)


def hourly_now(app, hours: dict[str, list[weather.Hour]]) -> list[ft.Control]:
    """今の時から明日の終わりまで、一時間ごとの行。"""
    n = now()
    out: list[ft.Control] = []
    for date, first in ((n.date(), n.hour), (n.date() + dt.timedelta(days=1), 0)):
        picked = [h for h in hours.get(date.isoformat(), []) if int(h.time[11:13]) >= first]
        if picked:
            out += [
                theme.muted(day_label(date.isoformat(), app.lang)),
                *(short_hour_line(h, app.lang) for h in picked),
            ]
    return out


def row(f: weather.Forecast, language: str) -> list[ft.Control]:
    """一日 = 三行。一行目は日と天気、二行目は気温と降水、三行目は日照・蒸発散・風。"""
    ja = language == "ja"
    rain = "—" if f.rain is None else f"{f.rain:.1f} mm"
    prob = number(f.rain_prob, " %")
    tmax, tmin = number(f.tmax, " ℃"), number(f.tmin, " ℃")
    if ja:
        detail = f"最高 {tmax} / 最低 {tmin}  降水 {rain}（{prob}）"
    else:
        detail = f"max {tmax} / min {tmin}  rain {rain} ({prob})"
    head = f"{day_label(f.date, language)}  {weather.weather_word(f.code, language)}"
    sun = "—" if f.sunshine_h is None else f"{f.sunshine_h:.1f} h"
    et0 = "—" if f.et0 is None else f"{f.et0:.1f} mm"
    wind = number(f.wind, " m/s")
    if f.wind_dir is not None:
        wind += f" {weather.wind_name(f.wind_dir, language)}"
    gust = number(f.gust, "")
    if ja:
        farm = f"日照 {sun}  蒸発散 {et0}  風 {wind}（突風 {gust}）"
    else:
        farm = f"sun {sun}  ET₀ {et0}  wind {wind} (gusts {gust})"
    return [ft.Text(head, size=theme.BODY_SIZE), theme.muted(detail), theme.muted(farm)]


def soil_controls(app, soil: weather.Soil | None) -> list[ft.Control]:
    if soil is None:
        return []
    t = app.t
    when = soil.time or (soil.surface[0] if soil.surface else "")
    out: list[ft.Control] = [theme.subheading(t("weather_soil", time=when[-5:]))]
    if soil.surface:
        tm, v = soil.surface
        out.append(ft.Text(t("weather_surface", value=f"{v:.0f}", time=tm[-5:]), size=theme.BODY_SIZE))
    if soil.temp:
        temp = " · ".join(f"{k} {number(v, ' ℃')}" for k, v in soil.temp.items())
        moist = " · ".join(f"{k} {'—' if v is None else f'{v:.2f}'}" for k, v in soil.moisture.items())
        out += [
            ft.Text(f"{t('weather_soil_temp')}: {temp}", size=theme.BODY_SIZE),
            ft.Text(f"{t('weather_soil_moist')}: {moist} m³/m³", size=theme.BODY_SIZE),
        ]
    return out


def hour_line(h: weather.Hour, language: str) -> ft.Control:
    ja = language == "ja"
    word = "—" if h.code is None else weather.weather_word(h.code, language)
    rain = "—" if h.rain is None else f"{h.rain:.1f} mm"
    prob = number(h.rain_prob, " %")
    wind = number(h.wind, " m/s")
    if h.wind_dir is not None:
        wind += f" {weather.wind_name(h.wind_dir, language)}"
    temp, dew, rh = number(h.temp, " ℃"), number(h.dewpoint, " ℃"), number(h.humidity, " %")
    if ja:
        text = f"{h.time[-5:]}  {word}  {temp}  湿度 {rh}  露点 {dew}  雨 {rain}（{prob}）  風 {wind}"
    else:
        text = f"{h.time[-5:]}  {word}  {temp}  RH {rh}  dew {dew}  rain {rain} ({prob})  wind {wind}"
    return theme.muted(text)


def credits(app) -> list[ft.Control]:
    """画面の一番下の二行: 出典（リンク）と計算の仕方。"""
    t = app.t
    style = ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)
    sep = "、" if app.lang == "ja" else "; "
    colon = "：" if app.lang == "ja" else ": "
    source = ft.Text(
        spans=[
            ft.TextSpan(f"{t('weather_source')}{colon}"),
            ft.TextSpan(t("weather_source_api"), url=API_URL, style=style),
            ft.TextSpan(sep),
            ft.TextSpan(t("weather_source_surface"), url=ECMWF_URL, style=style),
        ],
        size=13,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )
    return [source, theme.muted(t("weather_calc"))]


def build(app) -> list[ft.Control]:
    t, st = app.t, app.state
    c = centre(app)
    if c is None:
        return [ft.Text(t("weather_need_photo"), size=theme.BODY_SIZE)]
    key = (*c, today().isoformat())
    cached = st.get("forecast")
    failed = st.get("forecast_failed")

    def refresh(e) -> None:
        st.pop("forecast", None)
        st.pop("forecast_failed", None)
        app.refresh()

    button = ft.TextButton(t("weather_refresh"), icon=ft.Icons.REFRESH, on_click=refresh)
    if cached and cached[0] == key:
        rows, soil, hours = cached[1]
        opened = st.get("weather_open", {today().isoformat()})  # 触るまでは今日が開いている

        def toggler(date: str):
            def h(e) -> None:
                now = set(st.get("weather_open", {today().isoformat()}))
                now ^= {date}
                st["weather_open"] = now
                app.refresh()

            return h

        days = [
            ft.Container(
                ft.Column(
                    [
                        *row(f, app.lang),
                        *(hour_line(x, app.lang) for x in hours.get(f.date, []) if f.date in opened),
                    ],
                    tight=True,
                    spacing=2,
                ),
                on_click=toggler(f.date),
            )
            for f in rows[:7]
        ]
        far = rows[7:]
        return [
            *soil_controls(app, soil),
            theme.subheading(t("weather_h_hourly")),
            *hourly_now(app, hours),
            theme.subheading(t("weather_h_week")),
            ft.Column(days, spacing=8),
            *([theme.subheading(t("weather_h_far"))] if far else []),
            *(far_line(f, app.lang) for f in far),
            *credits(app),
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
