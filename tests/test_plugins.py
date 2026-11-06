# SPDX-License-Identifier: AGPL-3.0-or-later
"""プラグイン画面（同梱の land、本人の <フォルダー>/plugins/*.py）。"""

from __future__ import annotations

import logging

import pytest
from test_app import FakePage, texts

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
    assert [p.name for p in app.plugins] == ["land"]


def test_own_plugin_comes_after_shipped(app, seedfolder):
    put(seedfolder, "harvest", GOOD)
    app.open_folder(str(seedfolder))
    assert [sc.route for sc in app.screens()] == ["/", "/photos", "/p/land", "/p/harvest"]
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
    assert [p.name for p in got] == ["land", "ok"]
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
    assert [p.name for p in app.plugins] == ["land"]
    app2 = App(FakePage(), str(seedfolder))
    assert "harvest" in [p.name for p in app2.plugins]


def test_plugins_written_while_running_are_picked_up(app, seedfolder):
    import os

    assert [sc.route for sc in app.screens()] == ["/", "/photos", "/p/land"]
    put(seedfolder, "harvest", GOOD)
    app.refresh()
    assert "/p/harvest" in [sc.route for sc in app.screens()]
    path = seedfolder / "plugins" / "harvest.py"
    path.write_text(GOOD.replace("収穫", "刈り取り"), encoding="utf-8")
    st = path.stat()
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    app.route_change(path="/p/harvest")
    assert "seed — 刈り取り" in texts(app.page.views[-1])
