# SPDX-License-Identifier: AGPL-3.0-or-later
"""この土地の成り立ちの画面の中身（AI 無し。land.py の資料を並べる）。プラグイン land が使う。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from seed import land
from seed.app import photo, theme

if TYPE_CHECKING:
    from seed.app.main import App


def frame_items(frames: list[land.Frame]) -> list[tuple[Path, str]]:
    return [(f.path, f.title) for f in frames]


async def make_past_frames(app: App) -> bool:
    """昔の地図と空中写真の絵を作る（seed origin の絵だけ。動画は作らない）。作れたら True、だめなら一文を出す。"""
    if land.center(app.folder) is None:
        app.toast(app.t("land_need_photo"))
        return False
    app.state["pending"] = {"text": "", "photos": [], "word": "land_fetching"}
    app.refresh()
    try:
        await asyncio.to_thread(land.make_frames, app.folder, app.lang)
    except Exception as ex:  # noqa: BLE001
        app.toast(app.t("land_past_failed", detail=type(ex).__name__))
        return False
    finally:
        app.state.pop("pending", None)
    if not land.frames(app.folder):
        app.toast(app.t("land_past_none"))
        return False
    return True


def controls(app: App) -> list[ft.Control]:
    """題、四つの組（事実と出典）、昔の地図と空中写真。無い物は取りに行く釦。"""
    t = app.t
    out: list[ft.Control] = [theme.subheading(t("land_title"))]
    centre = land.center(app.folder)
    groups = land.summary(app.folder, app.lang)
    for g in groups:
        out.append(ft.Text(t(f"land_{g.key}"), weight=ft.FontWeight.W_600, size=theme.BODY_SIZE))
        for f in g.facts:
            out.append(ft.Text(f.body, size=theme.BODY_SIZE, selectable=True))
            if f.source:
                out.append(theme.muted(f.source))
    frames = land.frames(app.folder)
    if centre is None:
        out.append(ft.Text(t("land_need_photo"), size=theme.BODY_SIZE))
    elif not app.folder.place_data():
        out.append(ft.Text(t("land_none"), size=theme.BODY_SIZE))

        async def lookup(e) -> None:
            from seed.app import talk

            if not await talk.place_data(app, quiet=True):
                app.toast(t("land_none"))
            app.refresh()

        out.append(ft.TextButton(t("land_lookup"), icon=ft.Icons.SEARCH, on_click=lookup))
    if frames:
        out.append(theme.muted(t("land_past")))
        out.append(photo.plain_tiles(app, frame_items(frames), photo.SMALL * 0.9))
    elif centre is not None:

        async def fetch(e) -> None:
            await make_past_frames(app)
            app.refresh()

        out.append(ft.TextButton(t("land_fetch_past"), icon=ft.Icons.MAP_OUTLINED, on_click=fetch))
    return out
