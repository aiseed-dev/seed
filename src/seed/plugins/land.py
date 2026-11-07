# SPDX-License-Identifier: AGPL-3.0-or-later
"""この土地。土地の資料から分かる事と、昔の地図と空中写真。"""

from __future__ import annotations

import flet as ft

from seed.app import landview, theme

TITLE = {"ja": "この土地", "en": "This land"}
ICON = "MAP_OUTLINED"


def build(app) -> list[ft.Control]:
    if getattr(app, "whole", False):  # プロジェクト全体: 土地は畑の物なので、畑ごとに並べる（設計書 §5.12）
        out: list[ft.Control] = []
        for f in app.fields:
            out += [theme.subheading(f.root.name), *landview.controls(app.for_field(f))]
        return out
    return landview.controls(app)
