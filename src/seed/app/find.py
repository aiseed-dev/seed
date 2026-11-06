# SPDX-License-Identifier: AGPL-3.0-or-later
"""探す・繋がる /find。index.json を取り、手元で絞り、記録を開いて一言を送る（利用マニュアル §8）。"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import flet as ft

from seed.app import theme
from seed.app.strings import DISCORD_URL, error_text, next_words
from seed.records import Connection, Public

if TYPE_CHECKING:
    from seed.app.main import App

WORD_MAX = 200


def record_card(app: App, rec: dict, on_open) -> ft.Card:
    """索引の一件。入口と探すで使う。"""
    tags = [ft.Chip(label=ft.Text(w), on_click=None) for w in [*rec.get("what", []), *rec.get("next", [])]]
    head = " · ".join(x for x in (rec.get("name"), rec.get("place"), rec.get("since")) if x)
    return ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    theme.muted(head),
                    theme.body(rec.get("word", ""), selectable=False),
                    ft.Row(tags, wrap=True, spacing=6, run_spacing=6) if tags else ft.Container(),
                    theme.muted(
                        "  ".join(
                            [
                                app.t("observations_n", n=rec.get("observations", 0)),
                                app.t("connections_n", n=rec.get("connections", 0)),
                            ]
                        )
                    ),
                ],
                spacing=6,
            ),
            padding=14,
            on_click=on_open,
        )
    )


def matches(rec: dict, query: str, tags: set[str]) -> bool:
    words = (
        [rec.get(k) or "" for k in ("id", "place", "name", "word")]
        + rec.get("what", [])
        + rec.get("next", [])
    )
    hay = " ".join(words).lower()
    return all(q in hay for q in query.lower().split()) and tags <= set(
        rec.get("what", []) + rec.get("next", [])
    )


def my_public_id(app: App) -> str:
    """自分の公開の id（新しい物）。無ければ呼び名。"""
    pubs = (
        sorted(app.folder.public.glob("*.md"), key=lambda p: p.stat().st_mtime)
        if app.folder.public.exists()
        else []
    )
    return pubs[-1].stem if pubs else app.settings.name


def view(app: App) -> ft.View:
    t, st = app.t, app.state
    status = ft.Column(spacing=6)
    listing = ft.Column(spacing=8)
    tag_row = ft.Row(wrap=True, spacing=6, run_spacing=6)
    query = ft.TextField(label=t("search"), prefix_icon=ft.Icons.SEARCH, value=st.get("find_q", ""))
    chosen: set[str] = st.setdefault("find_tags", set())

    def fill() -> None:
        recs = (app.index or {}).get("records", [])
        shown = [r for r in recs if matches(r, query.value or "", chosen)]
        listing.controls = [record_card(app, r, open_handler(r["id"])) for r in shown if r.get("id")] or [
            theme.muted(t("no_match") if recs else t("index_empty"))
        ]
        fill_tags(recs)

    def fill_tags(recs: list[dict]) -> None:
        # 「その次」の札（貸す、借りる、手伝う も）はいつも出し、ほかの札は索引にある物を足す
        fixed = next_words(app.lang)
        seen = {w for r in recs for w in r.get("what", []) + r.get("next", [])}
        all_tags = fixed + sorted(seen - set(fixed))
        tag_row.controls = [
            ft.Chip(label=ft.Text(w), selected=w in chosen, on_select=tag_handler(w)) for w in all_tags
        ]

    def tag_handler(w: str):
        def handler(e) -> None:
            chosen.symmetric_difference_update({w})
            fill()
            app.page.update()

        return handler

    def open_handler(rid: str):
        async def handler(e) -> None:
            st["find_open"] = rid
            app.refresh()

        return handler

    def on_query(e) -> None:
        st["find_q"] = query.value
        fill()
        app.page.update()

    query.on_change = on_query
    fill_tags([])

    async def load() -> None:
        try:
            await app.load_index()
        except Exception as ex:  # noqa: BLE001 — 本人に一文で見せる
            status.controls = [theme.error(error_text(ex, app.lang, server=app.settings.server))]
            app.page.update()
            return
        fill()
        app.page.update()

    if st.get("find_open"):
        return opened(app, st["find_open"])
    app.page.run_task(load)
    return app.view(
        "/find",
        [theme.heading(t("find_title")), query, tag_row, status, listing, theme.muted(t("continue_discord"))],
    )


def opened(app: App, rid: str) -> ft.View:
    """記録を一つ開く。公開ファイルそのままと、一言を送る欄。"""
    t, st = app.t, app.state
    content = ft.Column([theme.muted(t("loading"))])
    status = ft.Column(spacing=6)
    me = ft.TextField(label=t("your_id"), value=my_public_id(app))
    word = ft.TextField(label=t("words"), max_length=WORD_MAX, multiline=True, min_lines=2)

    async def back(e) -> None:
        st.pop("find_open", None)
        app.refresh()

    async def load() -> None:
        try:
            text = await app.call("public", rid)
            try:
                pub = Public.parse(text)
                head = " · ".join(x for x in (pub.name, pub.place, pub.since) if x)
                content.controls = [theme.subheading(head), theme.body(pub.word)]
                if pub.contact:
                    content.controls.append(theme.muted(pub.contact))
                for day, lines in sorted(pub.days.items()):
                    content.controls.append(theme.subheading(day))
                    content.controls += [theme.line_text(l, app.lang) for l in lines]
            except (ValueError, TypeError):
                content.controls = [theme.mono(text)]
        except Exception as ex:  # noqa: BLE001
            content.controls = [theme.error(error_text(ex, app.lang, server=app.settings.server))]
        app.page.update()

    async def send(e) -> None:
        src, w = (me.value or "").strip(), (word.value or "").strip()
        if not src or not w:
            return
        try:
            n = await app.call("connect", rid, src, w)
        except Exception as ex:  # noqa: BLE001
            status.controls = [theme.error(error_text(ex, app.lang, server=app.settings.server))]
            app.page.update()
            return
        app.folder.add_connection(Connection(dt.date.today().isoformat(), src, rid, w.replace("\n", " ")))
        word.value = ""
        status.controls = [theme.body(t("sent", n=n))]
        app.index = None  # 数が変わったので次は取り直す
        app.page.update()

    app.page.run_task(load)
    return app.view(
        "/find",
        [
            ft.TextButton(t("back"), icon=ft.Icons.ARROW_BACK, on_click=back),
            content,
            ft.Divider(),
            theme.subheading(t("send_word")),
            me,
            word,
            ft.FilledButton(t("send_word"), icon=ft.Icons.SEND, on_click=send),
            status,
            ft.Button(t("discord"), icon=ft.Icons.FORUM_OUTLINED, url=DISCORD_URL),
            theme.muted(t("continue_discord")),
        ],
    )
