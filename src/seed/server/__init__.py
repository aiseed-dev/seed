# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed.aiseed.dev のサーバー（設計書 §7）。読み、照会、公開の受け取り、索引、繋がり。"""

from __future__ import annotations

from ..prompts import clean_text  # noqa: F401 — 端末と同じ物（seed/prompts.py）
