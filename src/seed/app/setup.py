# SPDX-License-Identifier: AGPL-3.0-or-later
"""準備の画面（/setup。設計書 §5.19）と、話すの文の下の直し方のボタン。

足りない物を見るのと命令を走らせるのは seed.ready（Flet を使わない）。ここは並べて、押されたら呼ぶだけ。
アプリを開いた時に足りない物が在る時だけ、話すの前に出る。歯車の「準備を見直す」からはいつでも開ける。
状態は app.ready（畑を替えても残す。この窓の間だけ）。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import flet as ft

from seed import ready
from seed.app import capture, theme

if TYPE_CHECKING:
    from .main import App

ROUTE = "/setup"
LATER = "later"  # seed.toml の setup。「今はしない」を押した
LOGIN_WAIT_S = 600  # ログインの子を待つ長さ（1 秒ごとに見る）


def is_pc(app: App) -> bool:
    """PC か（この PC のブラウザで開いた時も PC。スマートフォンのアプリだけが違う）。"""
    return getattr(app.page, "platform", None) not in capture.MOBILE


def has_read(app: App) -> bool:
    return bool(app.settings.invite or app.settings.anthropic_key)


def state(app: App) -> dict:
    return app.ready


async def check(app: App) -> list[str]:
    """足りない物を見直す（claude auth status は別の糸で）。"""
    r = state(app)
    r["checking"] = True
    try:
        r["needs"] = await asyncio.to_thread(ready.needs, is_pc(app), has_read(app))
    finally:
        r["checking"] = False
    return r["needs"]


async def first(app: App) -> bool:
    """アプリを開いた時: 「今はしない」を押していなくて、足りない物が在れば True（準備の画面を先に出す）。"""
    if app.settings.setup == LATER and ready.preview() is None:
        return False
    return bool(await check(app))


async def open_setup(app: App) -> None:
    """歯車から開く。見直しの間は「確かめています」を出す。"""
    state(app)["checking"] = True
    state(app)["note"] = ""
    await app.go(ROUTE)
    await check(app)
    app.refresh()


async def later(app: App) -> None:
    """「今はしない」: 設定に残し、話すへ。"""
    app.settings.setup = LATER
    app.settings.save()
    await app.go("/")


# ---------------------------------------------------------------- 押した時


async def install(app: App) -> None:
    r = state(app)
    if r.get("busy"):
        return
    if ready.preview() is not None:
        r["note"] = app.t("setup_preview")
        app.refresh()
        return
    r["busy"], r["note"] = "install", ""
    app.refresh()
    try:
        ok, tail = await asyncio.to_thread(ready.run_install)
    finally:
        r["busy"] = None
    r["note"] = app.t("setup_install_done") if ok else "\n".join([app.t("setup_install_failed"), *tail])
    await check(app)
    app.refresh()


async def login(app: App, poll: bool = True) -> bool:
    """`claude auth login` を子として立て、終わるまで待つ。poll なら 1 秒ごとに描き直す（URL を出すため）。"""
    r = state(app)
    if r.get("busy"):
        return False
    if ready.preview() is not None:
        r["note"] = app.t("setup_preview")
        app.refresh()
        return False
    path = await asyncio.to_thread(ready.claude_path)
    if path is None:
        await check(app)
        app.refresh()
        return False
    r["busy"], r["note"] = "login", ""
    child = r["login"] = await asyncio.to_thread(ready.start_login, path)
    app.refresh()
    try:
        for _ in range(LOGIN_WAIT_S):
            if child.returncode is not None or r.get("login") is not child:
                break
            await asyncio.sleep(1)
            if poll:
                app.refresh()
    finally:
        child.stop()
        r["busy"] = None
        r["login"] = None
    ok = await asyncio.to_thread(ready.logged_in, path) is True
    r["note"] = app.t("setup_login_done") if ok else app.t("setup_login_failed")
    await check(app)
    app.refresh()
    return ok


async def recheck(app: App) -> None:
    r = state(app)
    if r.get("busy") == "login":  # ブラウザで済ませた後に押された: 子を止めて見直す
        r["login"] = None
    r["note"] = ""
    await check(app)
    app.refresh()


# ---------------------------------------------------------------- 画面


def _press(fn, *args):
    """押した時に fn(app, …) を待つ（Flet の on_click に渡す形）。"""

    async def h(e) -> None:
        await fn(*args)

    return h


def _row(text: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        ft.Column([theme.body(text), *controls], spacing=8, tight=True),
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=12,
        padding=12,
    )


def _busy(text: str) -> ft.Control:
    return ft.Row([ft.ProgressRing(width=18, height=18, stroke_width=2), theme.muted(text)], spacing=8)


def need_row(app: App, need: str) -> ft.Control:
    t, r = app.t, state(app)
    busy = r.get("busy")
    if need == "install":
        controls: list[ft.Control] = [theme.muted(t("setup_install_line")), theme.mono(ready.install_line())]
        if busy == "install":
            controls.append(_busy(t("setup_installing")))
        else:
            controls.append(
                ft.FilledButton(t("setup_install_run"), icon=ft.Icons.DOWNLOAD, on_click=_press(install, app))
            )
        return _row(t("setup_install"), controls)
    if need == "login":
        return _row(t("setup_login"), login_controls(app))
    return _row(  # phone_read
        t("setup_phone_read"),
        [ft.FilledButton(t("setup_phone_open"), icon=ft.Icons.SETTINGS_OUTLINED, on_click=app.show_settings)],
    )


def login_controls(app: App) -> list[ft.Control]:
    t, r = app.t, state(app)
    if r.get("busy") != "login":
        return [ft.FilledButton(t("setup_login_run"), icon=ft.Icons.LOGIN, on_click=_press(login, app))]
    out: list[ft.Control] = [_busy(t("setup_login_waiting"))]
    child = r.get("login")
    url = child.url if child is not None else None
    if url:
        out.append(ft.Text(url, size=theme.BODY_SIZE, selectable=True))
    return out


def view(app: App) -> ft.View:
    t, r = app.t, state(app)
    needs = r.get("needs") or []
    controls: list[ft.Control] = []
    if r.get("checking"):
        controls.append(_busy(t("setup_checking")))
    elif needs:
        controls.append(theme.body(t("setup_intro")))
        controls += [need_row(app, n) for n in needs]
    else:
        controls.append(theme.body(t("setup_ok")))
        # 話すの「ログインし直す」から来た時（status はまだ入っていると言う事がある）
        if r.get("busy") == "login":
            controls.append(_row(t("setup_login"), login_controls(app)))
    if r.get("note"):
        controls.append(theme.muted(r["note"]))
    actions: list[ft.Control] = [ft.TextButton(t("setup_recheck"), on_click=_press(recheck, app))]
    if needs and not r.get("checking"):
        actions.append(ft.TextButton(t("setup_later"), on_click=_press(later, app)))
    else:
        actions.append(ft.FilledTonalButton(t("setup_to_talk"), on_click=_press(app.go, "/")))
    controls.append(ft.Row(actions, wrap=True, spacing=8))
    if needs and not r.get("checking"):
        controls.append(theme.muted(t("setup_later_note")))
    return ft.View(
        route=ROUTE,
        appbar=ft.AppBar(title=ft.Text(f"{app.place_name} — {t('setup_title')}")),
        controls=[theme.page_column(controls, getattr(app.page, "width", None))],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        padding=0,
    )


# ---------------------------------------------------------------- 話すの文の下のボタン


def fix_of(app: App, word: str | None) -> str | None:
    """この文に付ける直し方。PC だけ（ログインと pip はこの PC の事）。"""
    return ready.fix_for(word) if is_pc(app) else None


def fix_button(app: App, fix: str) -> ft.Control:
    """「ログインし直す」（準備の画面でログインを立てる）か「部品を入れる」（この場で pip）。"""
    t = app.t
    if fix == "login":

        async def relogin(e) -> None:
            await app.go(ROUTE)
            await login(app)

        return ft.FilledTonalButton(t("fix_login"), icon=ft.Icons.LOGIN, on_click=relogin)
    extra = fix.split(":", 1)[1]

    async def parts(e) -> None:
        from seed.app.talk import say

        r = state(app)
        if r.get("busy"):
            return
        r["busy"] = "parts"
        say(app, t("fix_parts_running"))
        app.refresh()
        try:
            ok, tail = await asyncio.to_thread(ready.run_parts, extra)
        finally:
            r["busy"] = None
        say(app, t("fix_parts_done") if ok else "\n".join([t("fix_parts_failed"), *tail]))
        app.refresh()

    return ft.FilledTonalButton(t("fix_parts"), icon=ft.Icons.EXTENSION_OUTLINED, on_click=parts)
