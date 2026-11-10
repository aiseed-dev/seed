# SPDX-License-Identifier: AGPL-3.0-or-later
"""歯車のフォームの PC の行（設計書 §5.19）: 「スマートフォンから写真を受ける」と「新しくする」。

子を立てる・止める・状態を見るのは seed.homerun、版を見る・入れ替えるのは seed.update（どちらも Flet を使わない）。
ここは並べて、押されたら呼ぶだけ。状態は app.pc（畑を替えても残す。この窓の間だけ）。
PC のアプリの時だけ出す。画面の見本（ready.ENV_PC_PREVIEW）が在れば Web でも出し、押しても何も走らせない。
招待コードの値は app.pc に持たない。「見せる」の間だけ、描くたびに home.toml から読んで部品に置く。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from seed import homerun, ready, update
from seed.app import capture, theme

if TYPE_CHECKING:
    from .main import App

AUTO = "auto"  # seed.toml の home_start。「アプリを開いたら始める」
START_WAIT_S = 30  # 立つまで 1 秒ごとに描き直す長さ
PREVIEW_URL = "http://192.0.2.1:8800"  # 見本の URL（文書用の番地）
PREVIEW_CODE = "000000"  # 見本の招待コード（本物ではない）


def new_state() -> dict:
    """home（子）、show（コードを見せる）、already（口がもう使われている）、home_note、
    check（update.Check）、busy、update_note、version（今の版の文字）。"""
    return {
        "home": None,
        "show": False,
        "already": None,
        "home_note": "",
        "check": None,
        "busy": None,
        "update_note": "",
        "version": None,
    }


def shown(app: App) -> bool:
    return capture.is_pc(app) or ready.pc_preview() is not None


def _preview(key: str) -> str | None:
    pv = ready.pc_preview()
    return pv.get(key, "none" if key == "home" else "unknown") if pv is not None else None


def _note_preview(app: App, key: str, redraw: Callable[[], None] | None) -> bool:
    if ready.pc_preview() is None:
        return False
    app.pc[key] = app.t("setup_preview")
    if redraw:
        redraw()
    return True


# ---------------------------------------------------------------- スマートフォンから写真を受ける


def home_state(app: App) -> str:
    """none、starting、running、stopped、already、port_used、need_server。"""
    pv = _preview("home")
    if pv is not None:
        return pv
    child = app.pc["home"]
    if child is not None:
        return child.state
    if not homerun.has_server():
        return "need_server"
    if app.pc["already"] == "home":
        return "already"
    if app.pc["already"] == "other":
        return "port_used"
    return "none"


async def home_start(app: App, redraw: Callable[[], None] | None = None) -> None:
    """プロジェクトの根で seed home を子として立てる。同じ口がもう使われていれば立てない。"""
    if _note_preview(app, "home_note", redraw):
        return
    old = app.pc["home"]
    if old is not None and old.state != "stopped":
        return
    app.pc["home_note"] = ""
    port = homerun.PORT
    got = await asyncio.to_thread(homerun.already, port)
    app.pc["already"] = got
    if got is not None:
        if redraw:
            redraw()
        return
    child = await asyncio.to_thread(homerun.HomeChild.start, app.project, port)
    app.pc["home"], app.pc["show"] = child, False
    if redraw:
        redraw()
    for _ in range(START_WAIT_S):
        if app.pc["home"] is not child or child.state != "starting":
            break
        await asyncio.sleep(1)
        if redraw:
            redraw()


async def home_stop(app: App, redraw: Callable[[], None] | None = None) -> None:
    if _note_preview(app, "home_note", redraw):
        return
    child = app.pc["home"]
    app.pc["home"], app.pc["show"], app.pc["already"] = None, False, None
    if child is not None:
        await asyncio.to_thread(child.stop)
    if redraw:
        redraw()


async def _noop(app: App, redraw: Callable[[], None] | None = None) -> None:
    _note_preview(app, "home_note", redraw)


async def auto_start(app: App) -> None:
    """アプリを開いた時（seed.toml の home_start が auto で、PC のアプリの時）。"""
    if app.settings.home_start == AUTO and capture.is_pc(app) and homerun.has_server():
        await home_start(app)


async def probe(app: App, redraw: Callable[[], None]) -> None:
    """フォームを開いた時、子が無ければ、端末で始めた seed home が動いているかを一度見る。"""
    if app.pc["home"] is not None or ready.pc_preview() is not None:
        return
    before = app.pc["already"]
    app.pc["already"] = await asyncio.to_thread(homerun.already, homerun.PORT)
    if app.pc["already"] != before and app.pc["home"] is None:
        redraw()


def home_controls(app: App, redraw: Callable[[], None]) -> list[ft.Control]:
    t = app.t
    st = home_state(app)

    def press(fn):
        async def h(e) -> None:
            await fn(app, redraw)

        return h

    def btn(word: str, fn) -> ft.Control:
        return ft.TextButton(t(word), on_click=press(fn))

    out: list[ft.Control] = [theme.subheading(t("pc_home"))]
    if st == "need_server":
        out.append(theme.muted(t("home_need_server")))
        if ready.pc_preview() is not None:  # 見本: 同じ名のボタンで、押しても走らせない
            out.append(
                ft.FilledTonalButton(t("fix_parts"), icon=ft.Icons.EXTENSION_OUTLINED, on_click=press(_noop))
            )
        elif (fix := ready.fix_for("home_need_server")) is not None:
            from seed.app.setup import fix_button

            out.append(fix_button(app, fix))
        if app.pc["home_note"]:
            out.append(theme.muted(app.pc["home_note"]))
        return out
    status = {
        "none": ("pc_home_none", [btn("pc_home_start", home_start)]),
        "starting": ("pc_home_starting", [btn("pc_home_stop", home_stop)]),
        "running": ("pc_home_running", [btn("pc_home_stop", home_stop)]),
        "stopped": ("pc_home_stopped", [btn("pc_home_again", home_start)]),
        "already": ("pc_home_already", []),
        "port_used": ("pc_home_port_used", [btn("pc_home_start", home_start)]),
    }
    word, actions = status.get(st, status["none"])
    out.append(
        ft.Row([ft.Text(t(word, port=homerun.PORT), size=theme.BODY_SIZE), *actions], wrap=True, spacing=6)
    )
    if st == "running":
        out += running_controls(app, redraw)
    elif st == "stopped" and app.pc["home"] is not None:
        out += [theme.muted(x) for x in app.pc["home"].lines[-3:]]  # 6 桁は覚える時に伏せてある
    if st in ("running", "already"):
        out.append(theme.muted(t("pc_home_how")))

    def auto(e) -> None:
        app.settings.home_start = AUTO if box.value else ""
        app.settings.save()

    box = ft.Checkbox(label=t("pc_home_auto"), value=app.settings.home_start == AUTO, on_change=auto)
    out.append(box)
    if app.pc["home_note"]:
        out.append(theme.muted(app.pc["home_note"]))
    return out


def running_controls(app: App, redraw: Callable[[], None]) -> list[ft.Control]:
    """動いている時: URL と、招待コード（「見せる」を押した時だけ）。"""
    t = app.t
    preview = ready.pc_preview() is not None
    child = app.pc["home"]
    url = PREVIEW_URL if preview else (child.url if child is not None else None)
    out: list[ft.Control] = []
    if url:
        out.append(ft.Text(url, size=theme.BODY_SIZE, selectable=True))

    def toggle(e) -> None:
        app.pc["show"] = not app.pc["show"]
        redraw()

    if app.pc["show"]:
        code = PREVIEW_CODE if preview else homerun.invite_code(app.project)
        out.append(
            ft.Row(
                [
                    ft.Text(t("pc_home_code", code=code), size=theme.BODY_SIZE, selectable=True),
                    ft.TextButton(t("pc_home_hide"), on_click=toggle),
                ],
                wrap=True,
                spacing=6,
            )
        )
    else:
        out.append(ft.TextButton(t("pc_home_show"), icon=ft.Icons.VISIBILITY_OUTLINED, on_click=toggle))
    return out


# ---------------------------------------------------------------- 新しくする


def update_state(app: App) -> str:
    """unknown、same、behind、dirty、diverged、failed、nogit、zip、done。"""
    pv = _preview("update")
    if pv is not None:
        return pv
    root = ready.repo_root()
    if root is None:
        return "nogit"
    if not update.is_git(root):
        return "zip"
    got = app.pc["check"]
    return got.state if got is not None else "unknown"


def version_text(app: App) -> str:
    if app.pc["version"] is None:
        root = ready.repo_root()
        v = update.version(root)
        commit = update.head(root) if root is not None and ready.pc_preview() is None else None
        app.pc["version"] = f"{v} ({commit})" if commit else v
    return app.pc["version"]


async def update_check(app: App, redraw: Callable[[], None] | None = None) -> None:
    if _note_preview(app, "update_note", redraw) or app.pc["busy"]:
        return
    root = ready.repo_root()
    if root is None:
        return
    app.pc["busy"], app.pc["update_note"] = "check", ""
    if redraw:
        redraw()
    try:
        app.pc["check"] = await asyncio.to_thread(update.check, root)
    finally:
        app.pc["busy"] = None
    if redraw:
        redraw()


async def update_run(app: App, redraw: Callable[[], None] | None = None) -> None:
    if _note_preview(app, "update_note", redraw) or app.pc["busy"]:
        return
    root = ready.repo_root()
    if root is None:
        return
    app.pc["busy"], app.pc["update_note"] = "run", ""
    if redraw:
        redraw()
    try:
        got, tail = await asyncio.to_thread(update.run_update, root)
    finally:
        app.pc["busy"] = None
    if got in ("pull_failed", "pip_failed"):
        app.pc["update_note"] = "\n".join([app.t(f"pc_update_{got}"), *tail])
    else:
        app.pc["check"] = update.Check(got)  # done、または見直したら入れ替えられなかった（same、dirty など）
        app.pc["version"] = None
    if redraw:
        redraw()


def update_controls(app: App, redraw: Callable[[], None]) -> list[ft.Control]:
    t = app.t
    st = update_state(app)

    def press(fn):
        async def h(e) -> None:
            await fn(app, redraw)

        return h

    check_btn = ft.TextButton(t("pc_update_check"), on_click=press(update_check))
    out: list[ft.Control] = [
        theme.subheading(t("pc_update")),
        theme.muted(t("pc_update_version", version=version_text(app))),
    ]
    busy = app.pc["busy"]
    if busy:
        word = "pc_update_checking" if busy == "check" else "pc_update_running"
        out.append(
            ft.Row([ft.ProgressRing(width=18, height=18, stroke_width=2), theme.muted(t(word))], spacing=8)
        )
    elif st == "unknown":
        out.append(check_btn)
    elif st == "behind":
        got = app.pc["check"]
        n = got.behind if got is not None else 1
        out.append(
            ft.Row(
                [
                    ft.Text(t("pc_update_behind", n=n), size=theme.BODY_SIZE),
                    ft.FilledTonalButton(
                        t("pc_update_run"), icon=ft.Icons.SYSTEM_UPDATE_ALT, on_click=press(update_run)
                    ),
                ],
                wrap=True,
                spacing=6,
            )
        )
    elif st in ("zip", "nogit"):
        out.append(theme.body(t(f"pc_update_{st}")))
        out.append(ft.FilledTonalButton(t("pc_update_github"), icon=ft.Icons.OPEN_IN_NEW, url=update.GITHUB))
    elif st == "done":
        out.append(theme.body(t("pc_update_done")))
    else:  # same、dirty、diverged、failed
        out.append(
            ft.Row([ft.Text(t(f"pc_update_{st}"), size=theme.BODY_SIZE), check_btn], wrap=True, spacing=6)
        )
    if app.pc["update_note"]:
        out.append(theme.muted(app.pc["update_note"]))
    return out


# ---------------------------------------------------------------- フォームに置く


def section(app: App) -> list[ft.Control]:
    """歯車のフォームに置く物。押すたびに中を作り直す（フォームは開いたまま）。"""
    box = ft.Column(spacing=10, tight=True)
    app.pc["show"] = False  # 開くたびに隠した形から
    app.pc["home_note"] = app.pc["update_note"] = ""

    def redraw() -> None:
        box.controls = [*home_controls(app, redraw), *update_controls(app, redraw)]
        app.page.update()

    box.controls = [*home_controls(app, redraw), *update_controls(app, redraw)]
    if app.pc["home"] is None and ready.pc_preview() is None and homerun.has_server():
        app.page.run_task(probe, app, redraw)
    return [box]
