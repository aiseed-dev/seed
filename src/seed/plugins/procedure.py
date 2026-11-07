# SPDX-License-Identifier: AGPL-3.0-or-later
"""手続き。耕作放棄地から始める道のり（手引き 13 章）と、農地法 3 条の下書き（procedures/nochi-3jo/）。"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import flet as ft

from seed import procedure
from seed.app import theme

TITLE = {"ja": "手続き", "en": "Paperwork"}
ICON = "CHECKLIST"

STEP_RE = re.compile(r"^### (?P<n>[〇一二三四五六七八九十]+) (?P<title>.+?)\s*$")
URL_RE = re.compile(r"https?://[^\s）]+")


def chapter(folder) -> Path | None:
    """13 章の道。本人のフォルダーの手引き、無ければ包みの物。"""
    from seed.cli import package_skill

    for base in (folder.skill, package_skill()):
        if base is None:
            continue
        for p in sorted(Path(base).glob("13-*.md")):
            return p
    return None


def road(folder) -> list[tuple[str, str]]:
    """（段の名、本人がすることの一文）を並びのまま。"""
    p = chapter(folder)
    if p is None:
        return []
    out: list[tuple[str, str]] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        m = STEP_RE.match(raw)
        if m:
            out.append((m["title"], ""))
        elif out and not out[-1][1] and raw.strip():
            if raw.startswith("- 本人がすること:"):
                text = raw.split(":", 1)[1]
            elif raw.startswith(("- ", "#")):
                continue
            else:  # 「〇 貸し農園から始める」のような、段落で始まる段
                text = raw
            out[-1] = (out[-1][0], text.strip().split("。")[0].replace("`", ""))
    return out


def sources(folder, slug: str) -> list[tuple[str, str]]:
    """sources.md の出典の行から（名、url）。"""
    path = folder.root / "procedures" / slug / "sources.md"
    if not path.is_file():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not procedure.SOURCE_RE.match(raw):
            continue
        m = URL_RE.search(raw)
        if m:
            name = raw.split(": ", 1)[1].split(" ")[0]
            out.append((name, m.group(0)))
    return out


def items(folder, slug: str) -> list[tuple[str, bool, str, str]]:
    """checklist.md の（key、済み、文、出典）。"""
    path = folder.root / "procedures" / slug / "checklist.md"
    if not path.is_file():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = procedure.CHECK_RE.match(raw)
        if not m:
            continue
        text = raw[m.end() :]
        src = ""
        if "（出典:" in text:
            text, src = text.split("（出典:", 1)
            src = "（出典:" + src
        out.append((m["key"], m["mark"] in "xX", text.strip(), src))
    return out


def draft_text(folder, slug: str) -> str:
    path = folder.root / "procedures" / slug / "draft.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def pick_folder(app):
    if getattr(app, "whole", False) and app.fields:
        return app.fields[0]
    return app.folder


def check_row(app, folder, key: str, done: bool, text: str, src: str) -> ft.Control:
    def changed(e) -> None:
        procedure.toggle(folder, procedure.SLUG, key, bool(e.control.value))

    box = ft.Checkbox(label=text, value=done, on_change=changed)
    col: list[ft.Control] = [box]
    if src:
        col.append(ft.Container(theme.muted(src), padding=ft.Padding.only(left=40)))
    return ft.Column(col, spacing=0)


def build(app) -> list[ft.Control]:
    t = app.t
    folder = pick_folder(app)
    out: list[ft.Control] = [theme.subheading(t("procedure_road"))]
    for i, (title, line) in enumerate(road(folder), 1):
        out.append(ft.Text(f"{i}. {title}" + (f" — {line}" if line else ""), size=theme.BODY_SIZE))
    if getattr(app, "whole", False) and app.fields:
        out.append(theme.muted(folder.root.name))

    slug = procedure.SLUG
    if not (folder.root / "procedures" / slug / "checklist.md").is_file():
        out.append(ft.Text(t("procedure_none"), size=theme.BODY_SIZE))

        async def make(e) -> None:
            await asyncio.to_thread(procedure.PROCEDURES[slug], folder)
            app.toast(t("procedure_made"))
            app.refresh()

        out.append(ft.FilledTonalButton(t("procedure_make"), icon=ft.Icons.EDIT_NOTE, on_click=make))
        out.append(theme.muted(t("procedure_note")))
        return out

    out.append(theme.subheading(t("procedure_checklist")))
    out += [check_row(app, folder, k, d, text, src) for k, d, text, src in items(folder, slug)]
    out.append(theme.subheading(t("procedure_draft")))
    out.append(ft.Markdown(draft_text(folder, slug), selectable=True))
    out.append(theme.subheading(t("procedure_sources")))
    for name, url in sources(folder, slug):
        out.append(ft.Text(spans=[ft.TextSpan(name, url=url)], size=theme.BODY_SIZE))
    out.append(theme.muted(t("procedure_note")))
    return out
