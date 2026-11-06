# SPDX-License-Identifier: AGPL-3.0-or-later
"""公開 /publish。公開は Claude を使って行う、という案内と、公開済みの一覧と取り下げ（利用マニュアル §7）。

公開ファイルを作るのは本人の手元の Claude（seed のスキルを読んだ Claude）。下書きを `seed publish … --local` で作り、
本人が全文を読んで「出す」と言ったら、同じファイルを `seed publish --file …` で送る（skill/SKILL.md）。
本人が読んだ文と送られる文を同じにするため、この画面では作らない。PC・Web・電話で同じ中身。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from seed.app import theme
from seed.app.strings import error_text
from seed.records import Public

if TYPE_CHECKING:
    from seed.app.main import App


def view(app: App) -> ft.View:
    t, st = app.t, app.state

    def unpublish_handler(pid: str):
        async def handler(e) -> None:
            try:
                await app.call("unpublish", pid)
            except Exception as ex:  # noqa: BLE001 — 本人に一文で見せる
                st["pub_msg"] = [error_text(ex, app.lang, server=app.settings.server)]
                app.refresh()
                return
            # 控えは公開している物の写し。取り下げたら消す（観察は残る）
            (app.folder.public / f"{pid}.md").unlink(missing_ok=True)
            app.index = None
            st["pub_msg"] = [t("unpublished", id=pid)]
            app.refresh()

        return handler

    published: list[ft.Control] = []
    for p in sorted(app.folder.public.glob("*.md")) if app.folder.public.exists() else []:
        try:
            pub = Public.read(p)
        except (ValueError, TypeError) as ex:
            published.append(theme.error(f"{p.name}: {ex}"))
            continue
        published.append(
            ft.ListTile(
                title=ft.Text(f"{pub.id} · {pub.since}"),
                subtitle=ft.Text(pub.word),
                trailing=ft.TextButton(t("unpublish"), on_click=unpublish_handler(pub.id)),
            )
        )

    controls: list[ft.Control] = [
        theme.heading(t("publish_title")),
        theme.note(t("publish_by_claude")),
        *[theme.body(m) for m in st.pop("pub_msg", [])],
    ]
    if published:
        controls += [ft.Divider(), theme.subheading(t("published_list")), *published]
    return app.view("/publish", controls)
