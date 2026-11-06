# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed.aiseed.dev のサーバー（設計書 §7）。読み、照会、公開の受け取り、索引、繋がり。"""

from __future__ import annotations

import re

from .. import records as R


def clean_text(text: str) -> str:
    """行の text に入れる前に、一行の文法を壊す物（改行、判定の矢印、末尾の確からしさ）を除く。"""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("→ farmer:", "→ farmer;")
    return R.CONFIDENCE_RE.sub("", text).strip()
