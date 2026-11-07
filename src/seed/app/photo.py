# SPDX-License-Identifier: AGPL-3.0-or-later
"""写真を出す。縮めた物を覚えておく、押すと大きく開く、大きく見た所の三つの操作。

写真はアプリの仕事（文字の細かい作業は Claude Code）。大きく見た所でできるのは三つだけ:
「この草の名前は？」「今日の一枚にする」「この写真を外す」（二度押し。外した後に「戻す」）。
"""

from __future__ import annotations

import asyncio
import functools
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft
from PIL import Image

from seed import album, identify, photos
from seed import highlights as H
from seed.app import theme
from seed.app.strings import error_text
from seed.cli import identify_photos
from seed.client import ClientError
from seed.records import Observation

if TYPE_CHECKING:
    from seed.app.main import App

BIG = 1280  # 今日の一枚
MEDIUM = 480  # これまでの観察の札、前と今
SMALL = 160  # 一覧に並べる物
TINY = 96  # 行の左
FULL = photos.MAX_SIDE  # 大きく開いた所


@functools.lru_cache(maxsize=256)
def _shrunk(path: str, mtime_ns: int, size: int, side: int) -> tuple[bytes, int, int]:
    data = photos.shrink(path, max_side=side)
    with Image.open(io.BytesIO(data)) as im:
        w, h = im.size
    return data, w, h


def load(path: Path, side: int) -> tuple[bytes, int, int] | None:
    """縮めた JPEG と、その幅と高さ。道・更新時刻・大きさ・長辺を鍵に覚えておく（同じ写真を毎回縮めない）。"""
    try:
        st = Path(path).stat()
        return _shrunk(str(path), st.st_mtime_ns, st.st_size, side)
    except (photos.PhotoError, OSError):
        return None


def fitted(w: int, h: int, max_w: float, max_h: float) -> tuple[float, float]:
    """縦横の比を保って、max_w × max_h に収まる一番大きな大きさ。"""
    scale = min(max_w / w, max_h / h)
    return w * scale, h * scale


@dataclass
class Shot:
    """大きく見る一枚。どの観察の、どの写真か。"""

    obs: Observation
    rel: str
    tags: list[str] = field(default_factory=list)


def picture(app: App, path: Path, side: int, max_w: float, max_h: float, on_click=None) -> ft.Control | None:
    """角の丸い写真。押すと on_click。読めない写真は None。"""
    got = load(path, side)
    if got is None:
        return None
    data, w, h = got
    dw, dh = fitted(w, h, max_w, max_h)
    return ft.Container(
        ft.Image(src=data, width=dw, height=dh, fit=ft.BoxFit.CONTAIN),
        width=dw,
        height=dh,
        border_radius=12,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        on_click=on_click,
    )


def _page_fit(app: App) -> float:
    """スマートフォンで写真が画面からはみ出さない幅（本文の幅から余白を引いた物）。"""
    return max(96.0, theme.fit_width(getattr(app.page, "width", None)) - 32)


def viewer_box(app: App, below: int) -> tuple[float, float]:
    """大きく見る枠。幅は窓の幅いっぱい、高さは下の操作の分を引いた残り。"""
    pw = getattr(app.page, "width", None) or 1000
    ph = getattr(app.page, "height", None) or 760
    return max(240.0, pw - 40), max(240.0, ph - below)


def zoomable(src: bytes, box_w: float, box_h: float) -> ft.InteractiveViewer:
    """つまんで拡大・縮小、指で動かせる絵。中の絵は枠いっぱい（縦横の比は保つ）。"""
    return ft.InteractiveViewer(
        content=ft.Image(src=src, width=box_w, height=box_h, fit=ft.BoxFit.CONTAIN),
        min_scale=1,
        max_scale=8,
        pan_enabled=True,
        scale_enabled=True,
        boundary_margin=ft.Margin.all(40),
        width=box_w,
        height=box_h,
    )


def tile(app: App, shots: list[Shot], i: int, size: float = SMALL) -> ft.Control | None:
    """正方形に切った小さな写真。押すと大きく開く（前後へ送れる）。"""
    got = load(app.folder.root / shots[i].rel, SMALL if size <= SMALL else MEDIUM)
    if got is None:
        return None
    size = min(size, _page_fit(app) - 8)

    def open_it(e) -> None:
        open_viewer(app, shots, i)

    return ft.Container(
        ft.Image(src=got[0], width=size, height=size, fit=ft.BoxFit.COVER),
        width=size,
        height=size,
        border_radius=10,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        on_click=open_it,
    )


def strip(app: App, shots: list[Shot], size: float = SMALL) -> ft.Control:
    """写真を折り返して並べる。"""
    tiles = [x for x in (tile(app, shots, i, size) for i in range(len(shots))) if x is not None]
    return ft.Row(tiles, wrap=True, spacing=8, run_spacing=8)


def captioned_strip(app: App, shots: list[Shot], captions: dict[str, str], size: float = SMALL) -> ft.Control:
    """写真を折り返して並べ、各写真の下に短い一言（無ければタグ。どちらも無ければ何も）。"""
    sep = "、" if app.lang == "ja" else ", "
    cells = []
    for i, s in enumerate(shots):
        t = tile(app, shots, i, size)
        if t is None:
            continue
        text = captions.get(s.rel) or sep.join(s.tags)
        cells.append(
            ft.Column(
                [
                    t,
                    *(
                        [
                            ft.Container(
                                ft.Text(
                                    text,
                                    size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                width=size,
                            )
                        ]
                        if text
                        else []
                    ),
                ],
                spacing=4,
                tight=True,
            )
        )
    return ft.Row(cells, wrap=True, spacing=8, run_spacing=8, vertical_alignment=ft.CrossAxisAlignment.START)


def shots_of(obs: Observation) -> list[Shot]:
    tags = H.tags_of(obs)
    return [Shot(obs, r, tags.get(H.stem(r), [])) for r in obs.photos]


def taken_text(app: App, shot: Shot) -> str:
    try:
        when = photos.exif_info(app.folder.root / shot.rel).taken
    except (photos.PhotoError, OSError):
        when = None
    if when is not None:
        return when.strftime("%Y-%m-%d %H:%M")
    return f"{shot.obs.date} {shot.obs.time[:5]}"


def open_viewer(app: App, shots: list[Shot], index: int) -> None:
    """画面いっぱいに大きく。つまんで拡大でき、左右で前後へ送れる。"""
    t = app.t
    box_w, box_h = viewer_box(app, 300)
    state = {"i": index, "confirm": False, "changed": False}
    body = ft.Column(spacing=8, tight=True)
    said = ft.Text("", selectable=True)
    actions = ft.Row(wrap=True, spacing=8)

    def shot() -> Shot:
        return shots[state["i"]]

    def draw() -> None:
        s = shot()
        got = load(app.folder.root / s.rel, FULL)
        image: ft.Control
        if got is None:
            image = ft.Text(t("photo_missing"))
        else:
            image = zoomable(got[0], box_w, box_h)
        info: list[ft.Control] = [ft.Text(taken_text(app, s), size=13)]
        if not album.has_coord(app.folder.root / s.rel):
            info.append(no_coord_mark(app))
        if s.tags:
            info.append(ft.Text(("、" if app.lang == "ja" else ", ").join(s.tags), size=12, italic=True))
        nav: list[ft.Control] = []
        if len(shots) > 1:
            nav = [
                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=step(-1), disabled=state["i"] == 0),
                ft.Text(f"{state['i'] + 1} / {len(shots)}", size=13),
                ft.IconButton(
                    ft.Icons.CHEVRON_RIGHT, on_click=step(1), disabled=state["i"] == len(shots) - 1
                ),
            ]
        body.controls = [
            ft.Container(image, width=box_w, height=box_h, alignment=ft.Alignment.CENTER),
            ft.Row([*nav, *info], wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            said,
        ]
        actions.controls = [
            ft.TextButton(t("photo_name_it"), icon=ft.Icons.GRASS_OUTLINED, on_click=name_it),
            ft.TextButton(t("photo_make_today"), icon=ft.Icons.STAR_OUTLINE, on_click=make_today),
            ft.TextButton(
                t("photo_remove_sure") if state["confirm"] else t("photo_remove"),
                icon=ft.Icons.HIDE_IMAGE_OUTLINED,
                on_click=remove,
            ),
            ft.TextButton(t("close"), icon=ft.Icons.CLOSE, on_click=close),
        ]

    def step(d: int):
        def h(e) -> None:
            state["i"] = max(0, min(len(shots) - 1, state["i"] + d))
            state["confirm"] = False
            said.value = ""
            draw()
            app.page.update()

        return h

    def obs_path(s: Shot) -> Path:
        return app.folder.observation_path(s.obs)

    async def name_it(e) -> None:
        s = shot()
        said.value = t("identifying")
        app.page.update()
        via = "local" if identify.available() else "server"
        try:
            added = await asyncio.to_thread(
                identify_photos, app.settings, app.folder, s.obs, [H.stem(s.rel)], via
            )
            s.obs.write(obs_path(s))
            state["changed"] = True
            names = [H.plant_name(l) for l in added]
            said.value = "、".join(n[1] for n in names if n) if any(names) else t("identify_none")
        except (ClientError, photos.PhotoError) as ex:
            said.value = error_text(ex, app.lang, server=app.settings.server)
        app.page.update()

    def make_today(e) -> None:
        s = shot()
        line = H.chosen_line(H.stem(s.rel), app.lang)
        s.obs.say(line.key, line.text)
        s.obs.write(obs_path(s))
        state["changed"] = True
        said.value = t("photo_today_set")
        app.page.update()

    def remove(e) -> None:
        if not state["confirm"]:  # 一度目は確かめる。二度目で外す
            state["confirm"] = True
            draw()
            app.page.update()
            return
        s = shot()
        at = album.remove_photo(app.folder, s.obs, s.rel)
        app.page.pop_dialog()

        def undo(e=None) -> None:
            album.restore_photo(app.folder, s.obs, s.rel, at)
            app.refresh()

        app.refresh()
        app.page.show_dialog(
            ft.SnackBar(ft.Text(t("photo_removed")), action=ft.SnackBarAction(t("photo_undo"), on_click=undo))
        )

    def close(e=None) -> None:
        app.page.pop_dialog()
        if state["changed"]:
            app.refresh()

    draw()
    app.page.show_dialog(
        ft.AlertDialog(
            content=body,
            actions=[actions],
            inset_padding=ft.Padding.all(8),
            content_padding=ft.Padding.all(12),
            scrollable=False,
        )
    )


def no_coord_mark(app: App) -> ft.Control:
    """位置の入っていない写真の小さな印。"""
    return ft.Container(
        ft.Row(
            [ft.Icon(ft.Icons.LOCATION_OFF_OUTLINED, size=14), ft.Text(app.t("photo_no_coord"), size=12)],
            spacing=4,
            tight=True,
        ),
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=10,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )


def open_plain(app: App, items: list[tuple[Path, str]], index: int) -> None:
    """操作の無い絵（昔の地図と空中写真）を大きく。つまんで拡大でき、左右で前後へ。"""
    box_w, box_h = viewer_box(app, 260)
    state = {"i": index}
    body = ft.Column(spacing=8, tight=True)

    def draw() -> None:
        path, title = items[state["i"]]
        got = load(path, FULL)
        image: ft.Control = ft.Text(app.t("photo_missing"))
        if got is not None:
            image = zoomable(got[0], box_w, box_h)
        nav: list[ft.Control] = []
        if len(items) > 1:
            nav = [
                ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=step(-1), disabled=state["i"] == 0),
                ft.Text(f"{state['i'] + 1} / {len(items)}", size=13),
                ft.IconButton(
                    ft.Icons.CHEVRON_RIGHT, on_click=step(1), disabled=state["i"] == len(items) - 1
                ),
            ]
        body.controls = [
            ft.Container(image, width=box_w, height=box_h, alignment=ft.Alignment.CENTER),
            ft.Row(
                [*nav, ft.Text(title, size=13)], wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
        ]

    def step(d: int):
        def h(e) -> None:
            state["i"] = max(0, min(len(items) - 1, state["i"] + d))
            draw()
            app.page.update()

        return h

    def close(e=None) -> None:
        app.page.pop_dialog()

    draw()
    app.page.show_dialog(
        ft.AlertDialog(
            content=body,
            actions=[ft.TextButton(app.t("close"), icon=ft.Icons.CLOSE, on_click=close)],
            inset_padding=ft.Padding.all(8),
            content_padding=ft.Padding.all(12),
            scrollable=False,
        )
    )


def plain_tiles(app: App, items: list[tuple[Path, str]], size: float = SMALL) -> ft.Control:
    """絵を題と一緒に折り返して並べる。押すと大きく（open_plain）。"""
    cells = []
    for i, (path, title) in enumerate(items):
        got = load(path, SMALL if size <= SMALL else MEDIUM)
        if got is None:
            continue

        def open_it(e, i=i) -> None:
            open_plain(app, items, i)

        cells.append(
            ft.Column(
                [
                    ft.Container(
                        ft.Image(src=got[0], width=size, height=size * 0.62, fit=ft.BoxFit.COVER),
                        width=size,
                        height=size * 0.62,
                        border_radius=10,
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        on_click=open_it,
                    ),
                    ft.Container(ft.Text(title, size=12, color=ft.Colors.ON_SURFACE_VARIANT), width=size),
                ],
                spacing=4,
                tight=True,
            )
        )
    return ft.Row(cells, wrap=True, spacing=10, run_spacing=10)
