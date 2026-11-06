# SPDX-License-Identifier: AGPL-3.0-or-later
"""見た目。色は少なく、本文が読めることを優先する。文は strings.py から。"""

from __future__ import annotations

import flet as ft

from .. import lang
from ..records import Line
from .strings import key_label

SEED_COLOR = "#5B7A3A"  # 草の緑。ほかの色はこれから Material が作る
BODY_SIZE = 16
MAX_WIDTH = 760  # 一行が長すぎると読みにくい


FONT = "Roboto"  # Flet 1.1 の既定の字体は日本語の字形を持たず □ になる（2026-11-06 に Web 版で確かめた）。Roboto なら足りない字形は端末の字体に落ちる


def apply(page: ft.Page) -> None:
    page.theme = ft.Theme(color_scheme_seed=SEED_COLOR, font_family=FONT)
    page.dark_theme = ft.Theme(color_scheme_seed=SEED_COLOR, font_family=FONT)
    page.theme_mode = ft.ThemeMode.SYSTEM


def heading(text: str) -> ft.Text:
    return ft.Text(text, theme_style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.W_600)


def subheading(text: str) -> ft.Text:
    return ft.Text(text, theme_style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.W_600)


def body(text: str, selectable: bool = True) -> ft.Text:
    return ft.Text(text, size=BODY_SIZE, selectable=selectable)


def muted(text: str) -> ft.Text:
    return ft.Text(text, size=13, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True)


def error(text: str) -> ft.Text:
    return ft.Text(text, size=BODY_SIZE, color=ft.Colors.ERROR, selectable=True)


def note(text: str) -> ft.Container:
    """目立たせたい一文（Web 版の「この記録は残りません」など）。"""
    return ft.Container(
        content=ft.Text(text, size=BODY_SIZE, color=ft.Colors.ON_TERTIARY_CONTAINER),
        bgcolor=ft.Colors.TERTIARY_CONTAINER,
        padding=12,
        border_radius=8,
    )


def mono(text: str) -> ft.Container:
    """ファイルの文をそのまま見せる。"""
    return ft.Container(
        content=ft.Text(text, font_family="monospace", size=14, selectable=True),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        padding=12,
        border_radius=8,
    )


def line_text(line: Line, language: str) -> ft.Text:
    """一行を表示の形に。key は小さく、本文は大きく、確からしさは添える。"""
    spans = [
        ft.TextSpan(
            f"{key_label(line.key, language)}  ", ft.TextStyle(size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        )
    ]
    spans.append(ft.TextSpan(line.text, ft.TextStyle(size=BODY_SIZE)))
    if line.confidence is not None:
        spans.append(
            ft.TextSpan(f"  [{line.confidence:.2f}]", ft.TextStyle(size=12, color=ft.Colors.OUTLINE))
        )
    if line.verdict:
        v = lang.t(line.verdict, language) + (f"（{line.reason}）" if line.reason else "")
        spans.append(ft.TextSpan(f"  → {v}", ft.TextStyle(size=13, color=ft.Colors.PRIMARY)))
    return ft.Text(spans=spans, selectable=True)


def page_column(controls: list[ft.Control]) -> ft.Container:
    """画面の本文。幅を抑えて中央に置き、縦に流す。"""
    return ft.Container(
        content=ft.Column(controls, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True),
        width=MAX_WIDTH,
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        expand=True,
    )
