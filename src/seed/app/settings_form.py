# SPDX-License-Identifier: AGPL-3.0-or-later
"""設定のフォーム（上の端の歯車）。Claude に繋がっていなくても、ここで繋ぎ先を入れられる。

作者 2026-11-07「スマートフォンの歯車を押したらきちんとフォームが表示されるようにして。現在の状態では入力をするところがない」。
話すの画面は欄を置かない作りのままで、繋ぐための値（PC の URL、招待コード、読む所、自分の鍵）だけはここで入れる。
鍵と招待コードの値は、画面に伏せ字で出し、やり取りにも記録にもログにも残さない。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import flet as ft

from seed import client, local
from seed.app import capture, pc_rows, theme

if TYPE_CHECKING:
    from .main import App

KEY_MIN, KEY_MAX = 20, 400


def route_choices(app: App) -> list[str]:
    """選べる読む所。手元の Claude Code は、この端末に claude がある時だけ。"""
    out = ["local"] if (capture.is_pc(app) and local.available() is not None) else []
    return [*out, "key", "server"]


def check(url: str, invite: str, key: str) -> list[str]:
    """入れた値の誤り（strings の鍵）。空の欄は「変えない」。"""
    bad = []
    if url and (not url.startswith(("http://", "https://")) or any(c.isspace() for c in url)):
        bad.append("server_url_bad")
    if key and (any(c.isspace() for c in key) or not KEY_MIN <= len(key) <= KEY_MAX):
        bad.append("talk_key_bad_shape")
    return bad


def apply(app: App, url: str, invite: str, key: str, read: str | None) -> None:
    """保存する。空の欄はそのまま（鍵と招待コードは、入れた時だけ替える）。"""
    s = app.settings
    url = url.strip().rstrip("/")
    if url and url != s.server_url:
        s.server_url = url
        client.forget_home(url)
    if invite.strip():
        s.invite = "".join(invite.split())
    if key.strip():
        s.anthropic_key = key.strip()
    if read in ("local", "key", "server"):
        s.read = read
    s.save()
    for k in ("await_server", "await_invite", "await_key", "invite_digits", "home_asked", "direct_messages"):
        app.state.pop(k, None)


def open_form(app: App) -> None:
    t = app.t
    s = app.settings
    url = ft.TextField(
        label=t("form_url"),
        value=s.server_url or "",
        keyboard_type=ft.KeyboardType.URL,
        autocorrect=False,
        dense=True,
    )
    invite = ft.TextField(
        label=t("form_invite"),
        hint_text=t("form_keep") if s.invite else t("form_invite_hint"),
        password=True,
        can_reveal_password=True,
        keyboard_type=ft.KeyboardType.NUMBER,
        autocorrect=False,
        dense=True,
    )
    key = ft.TextField(
        label=t("form_key"),
        hint_text=t("form_keep") if s.anthropic_key else t("form_key_hint"),
        password=True,
        can_reveal_password=True,
        autocorrect=False,
        dense=True,
    )
    choices = route_choices(app)
    from .talk import route  # 設定の札と同じく、今実際に使う所を選んでおく

    used = route(app) or s.read
    now = used if used in choices else ("server" if "server" in choices else choices[0])

    def choice(c: str) -> ft.Control:
        """丸と名。名は折り返す（Radio の label は折り返さず、スマートフォンの幅では枠の外へ出る）。"""

        def pick(e) -> None:
            read.value = c
            app.page.update()

        return ft.Row(
            [
                ft.Radio(value=c),
                ft.Container(ft.Text(t(f"set_read_{c}", model=s.model)), expand=True, on_click=pick),
            ],
            spacing=4,
        )

    read = ft.RadioGroup(
        value=now,
        content=ft.Column([choice(c) for c in choices], tight=True, spacing=0),
    )
    status = ft.Text("", size=13)

    async def find(e) -> None:
        from seed import discover

        status.value = t("form_finding")
        app.page.update()
        got = await asyncio.to_thread(discover.find_home)
        if got:
            url.value = got.rstrip("/")
            read.value = "server"
            status.value = t("form_found")
        else:
            status.value = t("home_not_found")
        app.page.update()

    def close(e=None) -> None:
        app.page.pop_dialog()

    def save(e) -> None:
        bad = check(url.value or "", invite.value or "", key.value or "")
        if bad:
            status.value = "\n".join(t(b) for b in bad)
            app.page.update()
            return
        apply(app, url.value or "", invite.value or "", key.value or "", read.value)
        invite.value = key.value = ""  # 値を部品に残さない
        close()
        app.toast(t("form_saved"))
        app.refresh()

    remover = (
        ft.Container()
    )  # 「鍵を外す」。消すと戻せないので、設定の札と同じく二度押し（一度目で「本当に外す」）

    def remove_key(e) -> None:
        if not isinstance(remover.content, ft.FilledButton):
            remover.content = ft.FilledButton(t("set_key_remove_sure"), on_click=remove_key)
            app.page.update()
            return
        s.anthropic_key = ""
        s.save()
        app.state.pop("direct_messages", None)
        key.hint_text = t("form_key_hint")
        status.value = t("talk_key_removed")
        remover.visible = False
        app.page.update()

    remover.content = ft.TextButton(t("form_key_remove"), on_click=remove_key)

    async def setup(e) -> None:  # 準備の画面（設計書 §5.19）。「今はしない」を押した後もここから開ける
        from seed.app import setup as setup_view

        close()
        await setup_view.open_setup(app)

    body: list[ft.Control] = [
        ft.TextButton(t("form_setup"), icon=ft.Icons.CHECKLIST, on_click=setup),
        theme.subheading(t("form_pc")),
        ft.FilledTonalButton(t("set_find_home"), icon=ft.Icons.WIFI_FIND, on_click=find),
        url,
        invite,
        theme.muted(t("form_pc_note")),
        theme.subheading(t("form_read")),
        read,
        theme.subheading(t("form_key_title")),
        key,
    ]
    if s.anthropic_key:
        body.append(remover)
    if pc_rows.shown(app):  # PC のアプリだけ: スマートフォンから写真を受ける、新しくする（設計書 §5.19）
        body += pc_rows.section(app)
    body.append(status)
    app.page.show_dialog(
        ft.AlertDialog(
            title=ft.Text(t("nav_settings")),
            content=ft.Column(
                body,
                tight=True,
                spacing=10,
                width=min(420, theme.fit_width(getattr(app.page, "width", None)) - 48),
            ),
            actions=[
                ft.TextButton(t("form_close"), on_click=close),
                ft.FilledButton(t("form_save"), on_click=save),
            ],
            scrollable=True,
        )
    )
