# SPDX-License-Identifier: AGPL-3.0-or-later
"""写真 /photos。この畑の写真を全部、日ごと・観察ごとに並べる。文字は日付だけ。

押すと大きく開く（左右で前後へ、つまんで拡大）。大きく開いた所でできるのは三つだけ（photo.open_viewer）。
作者 2026-11-06「Claude Code でやりづらいのが、写真の管理」「記録で写真が見られないのはおかしい」。
"""

from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING

import flet as ft

from seed import highlights as H
from seed.app import photo, theme
from seed.records import Observation

if TYPE_CHECKING:
    from seed.app.main import App


def groups(shots: list[photo.Shot]) -> list[tuple[str, list[list[int]]]]:
    """(日付, [観察ごとの写真の番号の並び]) を新しい日から。番号は shots の中の位置。"""
    out = []
    keyed = [(s.obs.date, s.obs.filename, i) for i, s in enumerate(shots)]
    for date, items in groupby(keyed, key=lambda x: x[0]):
        by_obs = [[i for _, _, i in g] for _, g in groupby(items, key=lambda x: x[1])]
        out.append((date, by_obs))
    return out


def all_shots(app: App) -> list[photo.Shot]:
    """全部の写真（新しい観察から）。大きく開いた所で、左右にこの順で送る。"""
    return [s for _, shots in _observed(app) for s in shots]


def _observed(app: App) -> list[tuple[Observation, list[photo.Shot]]]:
    out = []
    for path in reversed(app.folder.list_observations()):
        try:
            obs = Observation.read(path)
        except (ValueError, TypeError, OSError):
            continue
        out.append((obs, photo.shots_of(obs)))
    return out


def tag_chips(app: App, tags: list[tuple[str, int]]) -> ft.Control:
    """語ごとの小さな札（語と枚数）。押すとその語の写真だけ。選んだ札をもう一度押すと全部に戻る。"""
    chosen = app.state.get("photo_tag")

    def pick(word: str):
        def h(e) -> None:
            app.state["photo_tag"] = None if app.state.get("photo_tag") == word else word
            app.refresh()

        return h

    chips = [
        ft.Chip(label=f"{w} {n}", selected=w == chosen, show_checkmark=False, on_click=pick(w))
        for w, n in tags
    ]
    return ft.Row(chips, wrap=True, spacing=6, run_spacing=6)


def day_rows(app: App, shown: list[photo.Shot], size: float) -> list[ft.Control]:
    """日の見出しと、観察ごとの写真の並び。"""
    out: list[ft.Control] = []
    for date, by_obs in groups(shown):
        out.append(theme.subheading(date))
        for idx in by_obs:
            tiles = [x for x in (photo.tile(app, shown, i, size) for i in idx) if x is not None]
            out.append(ft.Row(tiles, wrap=True, spacing=8, run_spacing=8))
    return out


def view(app: App) -> ft.View:
    # プロジェクト全体の時は畑ごと（設計書 §5.12）。部品は畑一つ分の app で作る（写真の道が畑の中なので）
    parts = [(f.root.name, app.for_field(f)) for f in app.fields] if app.whole else [(None, app)]
    observed_by = [(name, a, _observed(a)) for name, a in parts]
    observed = [x for _, _, obs in observed_by for x in obs]
    shots = [s for _, group in observed for s in group]
    tags = H.all_tags([(o.filename, o) for o, _ in observed])
    chosen = app.state.get("photo_tag")
    if chosen not in {w for w, _ in tags}:
        chosen = app.state["photo_tag"] = None  # 付いた写真が無くなった語は外す
    size = max(96.0, min(photo.SMALL, (theme.fit_width(getattr(app.page, "width", None)) - 32 - 16) / 3))
    controls: list[ft.Control] = []
    if tags:
        controls.append(tag_chips(app, tags))
    shown = [s for s in shots if chosen in s.tags] if chosen else shots
    for name, a, obs in observed_by:
        mine = [s for _, group in obs for s in group]
        mine = [s for s in mine if chosen in s.tags] if chosen else mine
        if name is not None:
            if not mine:
                continue
            controls.append(theme.subheading(name))
        controls += day_rows(a, mine, size)
    if not shots:
        controls.append(theme.body(app.t("photos_none")))
    elif not shown:
        controls.append(theme.body(app.t("photos_tag_none")))
    return app.view("/photos", controls)
