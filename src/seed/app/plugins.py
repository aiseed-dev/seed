# SPDX-License-Identifier: AGPL-3.0-or-later
"""プラグイン画面を集める（設計書 §5.11）。

同梱は src/seed/plugins/*.py、本人のは <記録のフォルダー>/plugins/*.py。どちらも一つの .py が一つの画面で、
TITLE（言語 → 名）、ICON（ft.Icons の名）、build(app) を持つ。読めない物は一行の警告で飛ばし、アプリは止めない。
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import flet as ft

log = logging.getLogger("seed.app")


@dataclass
class Plugin:
    name: str
    route: str
    title: dict[str, str]
    icon: ft.IconData
    build: Callable


def make(name: str, mod) -> Plugin | None:
    """モジュールから Plugin を作る。三つが揃っていなければ None。"""
    title, icon, build = (getattr(mod, k, None) for k in ("TITLE", "ICON", "build"))
    if not isinstance(title, dict) or not title or not callable(build):
        log.warning("プラグイン %s を飛ばす: TITLE か build が無い", name)
        return None
    if not isinstance(icon, str) or not hasattr(ft.Icons, icon):
        log.warning("プラグイン %s を飛ばす: ICON が ft.Icons に無い", name)
        return None
    return Plugin(name, f"/p/{name}", title, getattr(ft.Icons, icon), build)


def shipped() -> list[Plugin]:
    import seed.plugins as pkg

    out = []
    for name in sorted(m.name for m in pkgutil.iter_modules(pkg.__path__)):
        if name.startswith("_"):
            continue
        try:
            p = make(name, importlib.import_module(f"seed.plugins.{name}"))
        except Exception as ex:  # noqa: BLE001
            log.warning("プラグイン %s を飛ばす: %s", name, type(ex).__name__)
            continue
        if p:
            out.append(p)
    return out


def plugins_dir(folder) -> Path:
    """本人のプラグインの置き場。畑に plugins/ が在ればそれ、無ければプロジェクトの根の物（設計書 §5.12）。"""
    shared = getattr(folder, "shared", None)
    return shared("plugins") if shared else Path(folder.root) / "plugins"


def own(folder) -> list[Plugin]:
    d = plugins_dir(folder)
    out = []
    for path in sorted(d.glob("*.py")) if d.is_dir() else []:
        if path.stem.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"seed_user_plugin_{path.stem}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            p = make(path.stem, mod)
        except Exception as ex:  # noqa: BLE001
            log.warning("プラグイン %s を飛ばす: %s", path.stem, type(ex).__name__)
            continue
        if p:
            out.append(p)
    return out


def load(folder) -> list[Plugin]:
    """同梱を先に、次に本人の。それぞれ名の順。"""
    got = shipped()
    taken = {p.route for p in got}
    return [*got, *(p for p in own(folder) if p.route not in taken)]  # 同梱と同じ名は同梱を


def stamp(folder) -> frozenset[tuple[str, int]]:
    """本人のプラグインの今の姿（名と更新の時）。前と違えば読み直す。"""
    d = plugins_dir(folder)
    if not d.is_dir():
        return frozenset()
    return frozenset((p.name, p.stat().st_mtime_ns) for p in d.glob("*.py"))
