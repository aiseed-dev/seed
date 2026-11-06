# SPDX-License-Identifier: AGPL-3.0-or-later
"""入口 /。一行、何をする物か、テスター募集、Discord、公開された記録と一言の列（設計書 §6）。"""

from __future__ import annotations

import contextlib
import datetime as dt
from typing import TYPE_CHECKING

import flet as ft

from seed.app import theme
from seed.app.find import record_card
from seed.app.strings import DISCORD_URL, error_text

if TYPE_CHECKING:
    from seed.app.main import App

WORDS_SHOWN = 8


def invite_block(app: App) -> list[ft.Control]:
    """招待コード。PC 版は入れる欄、Web 版はログイン中の表示と出る釦（設計書 §7.5、§6.2）。"""
    t = app.t
    if app.web and app.web_user is not None:

        async def logout(e) -> None:
            with contextlib.suppress(Exception):  # 覚えていなくても出られる
                await app.page.shared_preferences.remove("seed.invite")
            await app.page.launch_url("/")  # 読み直すとログインの画面に戻る

        return [
            ft.Row(
                [
                    theme.muted(t("logged_in_as", name=app.web_user.name)),
                    ft.TextButton(t("logout"), on_click=logout),
                ],
                wrap=True,
            ),
            *mine_block(app),
        ]
    code = ft.TextField(label=t("invite"), value=app.settings.invite, dense=True, width=320)

    def save(e=None) -> None:
        app.settings.invite = (code.value or "").strip()
        app.settings.save()
        app.toast(t("invite_set") if app.settings.invite else t("invite_unset"))

    code.on_submit = save
    return [
        theme.subheading(t("invite")),
        theme.muted(t("invite_hint")),
        ft.Row([code, ft.Button(t("invite_save"), on_click=save)], wrap=True),
    ]


def mine_block(app: App) -> list[ft.Control]:
    """Web 版だけ: 自分の箱を zip で持ち帰る、全部消す（設計書 §5.3）。消す前に一度確かめる。"""
    t = app.t

    async def take_home(e) -> None:
        app.toast(t("export_working"))
        try:
            data = await app.call("export")
        except Exception as ex:  # noqa: BLE001 — 本人に一文で見せる
            app.toast(error_text(ex, app.lang, server=app.settings.server))
            return
        name = f"seed-{dt.date.today().isoformat()}.zip"
        await app.picker.save_file(dialog_title=t("export_button"), file_name=name, src_bytes=data)
        app.toast(t("export_done", name=name))

    async def really_delete(e) -> None:
        app.page.pop_dialog()
        try:
            got = await app.call("delete_me")
        except Exception as ex:  # noqa: BLE001
            app.toast(error_text(ex, app.lang, server=app.settings.server))
            return
        app.toast(t("deleted", n=len(got.get("withdrawn") or [])))
        with contextlib.suppress(Exception):  # 箱が無いので、このブラウザからも出る
            await app.page.shared_preferences.remove("seed.invite")
        await app.page.launch_url("/")

    def cancel(e) -> None:
        app.page.pop_dialog()

    def ask_delete(e) -> None:
        app.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(t("delete_confirm_title")),
                content=ft.Text(t("delete_confirm_body")),
                actions=[
                    ft.TextButton(t("delete_cancel"), on_click=cancel),
                    ft.FilledButton(
                        t("delete_confirm_yes"), icon=ft.Icons.DELETE_FOREVER, on_click=really_delete
                    ),
                ],
            )
        )

    return [
        ft.Row(
            [
                ft.Button(t("export_button"), icon=ft.Icons.DOWNLOAD, on_click=take_home),
                ft.TextButton(t("delete_button"), icon=ft.Icons.DELETE_OUTLINE, on_click=ask_delete),
            ],
            wrap=True,
        )
    ]


def view(app: App) -> ft.View:
    t = app.t
    totals = theme.muted(t("loading"))
    words = ft.Column(spacing=6)
    listing = ft.Column(spacing=8)

    async def to_observe(e) -> None:
        await app.go("/observe")

    def open_handler(rid: str):
        async def handler(e) -> None:
            app.state["find_open"] = rid
            await app.go("/find")

        return handler

    async def load() -> None:
        try:
            idx = await app.load_index()
        except Exception as ex:  # noqa: BLE001 — 本人に一文で見せる
            totals.value = error_text(ex, app.lang, server=app.settings.server)
            app.page.update()
            return
        recs = sorted(idx.get("records", []), key=lambda r: str(r.get("since", "")), reverse=True)
        total = idx.get("total", {})
        totals.value = t(
            "totals", records=total.get("records", len(recs)), connections=total.get("connections", 0)
        )
        words.controls = [
            ft.Text(f"「{r['word']}」 — {r.get('name', '')}", size=15, italic=True, selectable=True)
            for r in recs[:WORDS_SHOWN]
            if r.get("word")
        ]
        listing.controls = [record_card(app, r, open_handler(r["id"])) for r in recs if r.get("id")] or [
            theme.muted(t("index_empty"))
        ]
        app.page.update()

    controls: list[ft.Control] = [
        theme.heading(t("tagline")),
        theme.body(t("about")),
        theme.muted(t("not_do")),
        theme.muted(t("why_connect")),
    ]
    controls += [
        ft.FilledButton(t("observe_button"), icon=ft.Icons.PHOTO_CAMERA_OUTLINED, on_click=to_observe),
        theme.muted(t("web_records_note") if app.web else t("privacy", folder=app.folder_label)),
    ]
    controls += invite_block(app)
    controls += [
        ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        theme.body(t("testers")),
                        ft.Button(t("discord"), icon=ft.Icons.FORUM_OUTLINED, url=DISCORD_URL),
                    ],
                    spacing=10,
                ),
                padding=16,
            )
        ),
        theme.subheading(t("public_records")),
        totals,
        words,
        listing,
    ]
    app.page.run_task(load)
    return app.view("/", controls)
