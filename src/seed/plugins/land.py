# SPDX-License-Identifier: AGPL-3.0-or-later
"""この土地。土地の資料から分かる事と、昔の地図と空中写真。"""

from __future__ import annotations

import flet as ft

from seed.app import landview

TITLE = {"ja": "この土地", "en": "This land"}
ICON = "MAP_OUTLINED"


def build(app) -> list[ft.Control]:
    return landview.controls(app)
