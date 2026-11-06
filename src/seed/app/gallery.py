# SPDX-License-Identifier: AGPL-3.0-or-later
"""写真 /photos。この畑の写真を全部、日ごと・観察ごとに並べる。文字は日付だけ。

押すと大きく開く（左右で前後へ、つまんで拡大）。大きく開いた所でできるのは三つだけ（photo.open_viewer）。
作者 2026-11-06「Claude Code でやりづらいのが、写真の管理」「記録で写真が見られないのはおかしい」。
"""

from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING

import flet as ft

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
    shots: list[photo.Shot] = []
    for path in reversed(app.folder.list_observations()):
        try:
            obs = Observation.read(path)
        except (ValueError, TypeError, OSError):
            continue
        shots += photo.shots_of(obs)
    return shots


def view(app: App) -> ft.View:
    shots = all_shots(app)
    size = max(96.0, min(photo.SMALL, (theme.fit_width(getattr(app.page, "width", None)) - 32 - 16) / 3))
    controls: list[ft.Control] = []
    for date, by_obs in groups(shots):
        controls.append(theme.subheading(date))
        for idx in by_obs:
            tiles = [x for x in (photo.tile(app, shots, i, size) for i in idx) if x is not None]
            controls.append(ft.Row(tiles, wrap=True, spacing=8, run_spacing=8))
    if not controls:
        controls.append(theme.body(app.t("photos_none")))
    return app.view("/photos", controls)
