# SPDX-License-Identifier: AGPL-3.0-or-later
"""プラグイン画面（同梱の land、本人の <フォルダー>/plugins/*.py）。"""

from __future__ import annotations

import asyncio
import logging
import re

import flet as ft
import pytest
from test_app import FakePage, texts, walk

from seed import weather as W
from seed.app import plugins
from seed.app.main import App


@pytest.fixture(autouse=True)
def no_lookup(monkeypatch):
    from seed import lookup as L

    monkeypatch.setattr(L, "available", lambda: False)


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


GOOD = """
import flet as ft

TITLE = {"ja": "収穫", "en": "Harvest"}
ICON = "AGRICULTURE"


def build(app):
    return [ft.Text("収穫の画面です")]
"""


def put(folder, name, body):
    d = folder / "plugins"
    d.mkdir(exist_ok=True)
    (d / f"{name}.py").write_text(body, encoding="utf-8")


def test_shipped_land_is_found(app):
    (land,) = [p for p in plugins.load(app.folder) if p.name == "land"]
    assert land.route == "/p/land" and land.title["ja"] == "この土地"
    assert [p.name for p in app.plugins] == ["land", "land_checks", "procedure", "weather"]


def test_own_plugin_comes_after_shipped(app, seedfolder):
    put(seedfolder, "harvest", GOOD)
    app.open_folder(str(seedfolder))
    assert [sc.route for sc in app.screens()] == [
        "/",
        "/photos",
        "/p/land",
        "/p/land_checks",
        "/p/procedure",
        "/p/weather",
        "/p/harvest",
    ]
    app.route_change(path="/p/harvest")
    v = app.page.views[-1]
    assert v.route == "/p/harvest" and "seed — 収穫" in texts(v) and "収穫の画面です" in texts(v)
    app.lang = "fr"  # 無い言語は en へ
    app.route_change(path="/p/harvest")
    assert "seed — Harvest" in texts(app.page.views[-1])


def test_broken_plugins_are_skipped(app, seedfolder, caplog):
    put(seedfolder, "nobuild", GOOD.replace("def build", "def other"))
    put(seedfolder, "boom", "raise RuntimeError('x')")
    put(seedfolder, "badicon", GOOD.replace("AGRICULTURE", "NO_SUCH_ICON"))
    put(seedfolder, "_private", GOOD)
    put(seedfolder, "ok", GOOD)
    with caplog.at_level(logging.WARNING, logger="seed.app"):
        got = plugins.load(app.folder)
    assert [p.name for p in got] == ["land", "land_checks", "procedure", "weather", "ok"]
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 3


def test_plugin_build_failure_shows_one_line(app, seedfolder):
    put(seedfolder, "bad", GOOD.replace("return [", "raise ValueError('x')\n    return ["))
    app.open_folder(str(seedfolder))
    app.route_change(path="/p/bad")
    assert "このプラグインは動きません（bad: ValueError）。" in texts(app.page.views[-1])


def test_switching_folders_reloads(app, seedfolder, tmp_path):
    put(seedfolder, "harvest", GOOD)
    app.open_folder(str(seedfolder))
    assert "harvest" in [p.name for p in app.plugins]
    other = tmp_path / "other"
    other.mkdir()
    app.open_folder(str(other))
    assert [p.name for p in app.plugins] == ["land", "land_checks", "procedure", "weather"]
    app2 = App(FakePage(), str(seedfolder))
    assert "harvest" in [p.name for p in app2.plugins]


def test_plugins_written_while_running_are_picked_up(app, seedfolder):
    import os

    assert [sc.route for sc in app.screens()] == [
        "/",
        "/photos",
        "/p/land",
        "/p/land_checks",
        "/p/procedure",
        "/p/weather",
    ]
    put(seedfolder, "harvest", GOOD)
    app.refresh()
    assert "/p/harvest" in [sc.route for sc in app.screens()]
    path = seedfolder / "plugins" / "harvest.py"
    path.write_text(GOOD.replace("収穫", "刈り取り"), encoding="utf-8")
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    app.route_change(path="/p/harvest")
    assert "seed — 刈り取り" in texts(app.page.views[-1])


def run_tasks(app):
    while app.page.tasks:
        asyncio.run(app.page.tasks.pop(0)())


def soil():
    return W.Soil(
        "2026-11-08T14:00",
        {"0 cm": 15.2, "6 cm": 14.0, "18 cm": 15.4, "54 cm": 17.0},
        {"0-1 cm": 0.31, "1-3 cm": 0.30, "3-9 cm": 0.29, "9-27 cm": 0.28, "27-81 cm": 0.27},
        ("2026-11-08T14:00", 16.4),
        [
            (
                f"2026-11-{8 + i // 24:02d}T{i % 24:02d}:00",
                {"0 cm": 15.0 + i % 24 / 4, "6 cm": 14.0},
                {"0-1 cm": 0.3},
            )
            for i in range(48)
        ],
    )


def hours():
    return {
        "2026-11-08": [
            W.Hour(f"2026-11-08T{h:02d}:00", 0, 9.4, 85, 7.2, 0.0, 10, 2.1, 5.0, 315) for h in range(24)
        ],
        "2026-11-09": [W.Hour("2026-11-09T06:00", 61, 8.0, 90, 6.0, 1.2, 80, 3.0, 6.0, 90)],
    }


def forecast_rows(n=16):
    return [
        W.Forecast(f"2026-11-{8 + i:02d}", 61, 18.4, 9.6, 2.5, 70, 18720.0 / 3600, 2.14, 3.2, 8.1, 315)
        for i in range(n)
    ]


def test_weather_plugin_after_land(app):
    got = [p.name for p in plugins.load(app.folder)]
    assert got.index("land") < got.index("weather")
    (w,) = [p for p in plugins.load(app.folder) if p.name == "weather"]
    assert w.title["ja"] == "天気" and w.route == "/p/weather"


def test_weather_renders_week_and_caches(app, monkeypatch):
    from seed import land

    calls = []
    from seed.plugins import weather as P

    monkeypatch.setattr(P, "now", lambda: __import__("datetime").datetime(2026, 11, 8, 7, 30))
    monkeypatch.setattr(land, "center", lambda folder: (34.051, 134.249))
    monkeypatch.setattr(
        W, "fetch_week", lambda lat, lon, **k: calls.append((lat, lon)) or (forecast_rows(), soil(), hours())
    )
    app.page.route = "/p/weather"
    app.route_change(path="/p/weather")
    assert "取って来ています…" in texts(app.page.views[-1])
    run_tasks(app)
    got = texts(app.page.views[-1])
    for h in ("土（14:00 の値）", "今日と明日", "二週間", "作業の目安"):
        assert h in got
    # 数と単位の間（「15」と「℃」）では行を変えない（間は改行しない空白）
    line = "地表面 16 ℃（ECMWF、14:00）  地温: 0 cm 15 ℃ · 6 cm 14 ℃ · 18 cm 15 ℃ · 54 cm 17 ℃"
    assert line in [x.replace("\u00a0", " ") for x in got]
    assert any("0\u00a0cm\u00a015\u00a0℃" in x for x in got)
    # 字の一覧は無く、四つの図が横に動かせる行に入っている
    assert not any(re.match(r"\d\d:\d\d  ", x) or x.startswith(("最高", "日照")) for x in got)
    images = [c for c in walk(app.page.views[-1]) if isinstance(c, ft.Image)]
    assert len(images) == 4
    rows = [
        c
        for c in walk(app.page.views[-1])
        if isinstance(c, ft.Row) and any(isinstance(x, ft.Image) for x in walk(c) if x is not c)
    ]
    assert len(rows) == 4 and all(c.scroll == ft.ScrollMode.ALWAYS for c in rows)  # 続きがある事を棒で見せる
    assert all(img.width and img.width > 400 and isinstance(img.src, bytes) for img in images)
    assert "Open-Meteo 天気予報 API" in got and "地表面: ECMWF IFS（Open-Meteo）" in got
    assert any(x.startswith("計算: 畑の座標") for x in got)
    assert not any("実測" in x for x in got)
    links = [
        sp.url for c in walk(app.page.views[-1]) if isinstance(c, ft.Text) for sp in c.spans or [] if sp.url
    ]
    assert links == ["https://open-meteo.com/en/docs", "https://open-meteo.com/en/docs/ecmwf-api"]
    app.refresh()
    assert not app.page.tasks and len(calls) == 1  # 同じ日の開き直しは取り直さない
    app.state.pop("weather_forecast")  # 「取り直す」と同じ
    app.refresh()
    run_tasks(app)
    assert len(calls) == 2


def test_weather_failure_and_no_coordinates(app, monkeypatch):
    from seed import land

    app.page.route = "/p/weather"
    app.route_change(path="/p/weather")
    assert "位置の入った写真が一枚あると、その場所の天気を出せます。" in texts(app.page.views[-1])
    monkeypatch.setattr(land, "center", lambda folder: (34.05, 134.25))

    def boom(*a, **k):
        raise W.WeatherError("weather_unreachable", "ConnectError")

    monkeypatch.setattr(W, "fetch_week", boom)
    app.page.route = "/p/weather"
    app.route_change(path="/p/weather")
    run_tasks(app)
    assert "天気を取れませんでした（ConnectError）。" in texts(app.page.views[-1])


def test_weather_without_soil(app, monkeypatch):
    from seed import land

    monkeypatch.setattr(land, "center", lambda folder: (34.05, 134.25))
    monkeypatch.setattr(W, "fetch_week", lambda *a, **k: (forecast_rows(), None, {}))
    app.page.route = "/p/weather"
    app.route_change(path="/p/weather")
    run_tasks(app)
    got = texts(app.page.views[-1])
    assert not any(x.startswith("土（") for x in got) and "Open-Meteo 天気予報 API" in got


def test_weather_plugin_fills_record_once_a_day(app, monkeypatch):
    from seed import land
    from seed.plugins import weather as P

    calls = []
    monkeypatch.setattr(land, "center", lambda folder: (34.05, 134.25))
    monkeypatch.setattr(W, "fetch_week", lambda *a, **k: (forecast_rows(), soil(), hours()))
    monkeypatch.setattr(W, "fill_missing", lambda folder, lg, **k: calls.append(folder.root) or 0)
    monkeypatch.setattr(P, "now", lambda: __import__("datetime").datetime(2026, 11, 8, 7, 30))
    app.page.route = "/p/weather"
    app.route_change(path="/p/weather")
    run_tasks(app)
    assert len(calls) == 1
    app.state.pop("weather_forecast")  # 取り直しても、同じ日は埋め直さない
    app.refresh()
    run_tasks(app)
    assert len(calls) == 1
    monkeypatch.setattr(P, "now", lambda: __import__("datetime").datetime(2026, 11, 9, 7, 30))
    app.refresh()
    run_tasks(app)
    assert len(calls) == 2
