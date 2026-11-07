# SPDX-License-Identifier: AGPL-3.0-or-later
"""天気。畑の座標の、二週間の予報と土の図（Open-Meteo。AI 無し）。"""

from __future__ import annotations

import asyncio
import datetime as dt

import flet as ft

from seed import chart, land, weather
from seed.app import theme

TITLE = {"ja": "天気", "en": "Weather"}
ICON = "WB_SUNNY_OUTLINED"
API_URL = "https://open-meteo.com/en/docs"
ECMWF_URL = "https://open-meteo.com/en/docs/ecmwf-api"


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


def number(v: float | None, unit: str) -> str:
    return "—" if v is None else f"{v:.0f}{unit}"


def picture(app, svg: str) -> list[ft.Control]:
    """図。縮めず自分の幅で出し、横に動かして見る。"""
    if not svg:
        return []
    w, h = chart.size(svg)
    data = chart.png(svg) or svg.encode("utf-8")
    return [ft.Row([ft.Image(src=data, width=w, height=h, fit=ft.BoxFit.CONTAIN)], scroll=ft.ScrollMode.AUTO)]


def soil_controls(app, soil: weather.Soil | None) -> list[ft.Control]:
    """土: 今の値は一行（地表面と地温）、あとは図。"""
    if soil is None:
        return []
    t = app.t
    when = soil.time or (soil.surface[0] if soil.surface else "")
    parts = []
    if soil.surface:
        tm, v = soil.surface
        parts.append(t("weather_surface", value=f"{v:.0f}", time=tm[-5:]))
    if soil.temp:
        temp = " · ".join(f"{k} {number(v, ' ℃')}" for k, v in soil.temp.items())
        parts.append(f"{t('weather_soil_temp')}: {temp}")
    out: list[ft.Control] = [theme.subheading(t("weather_soil", time=when[-5:]))]
    if parts:
        out.append(ft.Text("  ".join(parts), size=theme.BODY_SIZE))
    return [*out, *picture(app, chart.soil_svg(soil.hourly, app.lang))]


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
        return [
            *soil_controls(app, soil),
            theme.subheading(t("weather_h_hourly")),
            *picture(app, chart.hourly_svg(hours, now(), app.lang)),
            theme.subheading(t("weather_h_days")),
            *picture(app, chart.daily_svg(rows, app.lang)),
            theme.subheading(t("weather_h_work")),
            *picture(app, chart.work_svg(rows, app.lang)),
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
            if st.get("weather_filled") != key[2]:  # 実績の記録の穴埋めは、一日に一度
                st["weather_filled"] = key[2]
                folders = app.fields if getattr(app, "whole", False) else [app.folder]
                for f in folders:
                    await asyncio.to_thread(weather.fill_missing, f, app.lang)

        app.page.run_task(load)
    return [theme.muted(t("weather_fetching"))]
