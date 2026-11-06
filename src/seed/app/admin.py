# SPDX-License-Identifier: AGPL-3.0-or-later
"""管理 /admin。サーバーを動かす人の画面（設計書 §5.10）。範囲 admin の token を入れた人にだけ出る。

作者 2026-11-06「管理用を seed に追加しろ」「普通の人用には、管理用画面が必須です」
「できるだけ AI に聞かなくてもいいように作って」。

上から、今の状態、気を付ける事（何が起きているか → サーバーで打つコマンド）、人に渡す token、公開された記録、
誰が何をしたか。受け付けを止める・再開するボタンは気を付ける事の札に、token を全部取り消すボタンは token の札に。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from seed.app import theme
from seed.app.strings import error_text
from seed.server.gate import EXPIRING_DAYS  # overview の tokens.expiring を数える日数（文に出す）

if TYPE_CHECKING:
    from seed.app.main import App

SCOPES = ("member", "buyer", "admin")
AUDIT_LINES = 40
DENIED_MANY = 20  # 今日、断った要求がこの回数以上なら「気を付ける事」に出す


def state_rows(app: App, o: dict) -> list[tuple[str, str]]:
    """今の状態の行（名、値）。"""
    t = app.t
    left = o.get("remaining", {})
    tk = o.get("tokens", {})
    keys = o.get("keys", {})

    def have(k: str) -> str:
        return t("admin_have") if keys.get(k) else t("admin_have_not")

    return [
        (t("admin_server"), t("admin_running", version=o.get("version", "?"))),
        (t("admin_accept"), t("admin_accept_off") if o.get("paused") else t("admin_accept_on")),
        (t("admin_read"), t("admin_yes") if o.get("read") else t("admin_no")),
        (t("admin_keys"), t("admin_keys_n", claude=have("claude"), plantnet=have("plantnet"))),
        (t("admin_audit"), t(f"admin_audit_{o.get('audit', 'off')}")),
        (t("admin_today"), t("admin_reads_left", n=left.get("reads", "?"))),
        (t("admin_public"), t("admin_public_n", records=o.get("records", 0), connections=o.get("connections", 0))),
        (t("admin_people"), t("admin_people_n", tokens=tk.get("live", 0), invites=o.get("invites", 0), boxes=o.get("boxes", 0))),
    ]  # fmt: skip


def attention(app: App, o: dict, audit: dict | None = None) -> list[tuple[str, list[str]]]:
    """気を付ける事。（何が起きているかの文、サーバーで打つコマンドの行）の並び。無ければ空。

    コマンドは画面でそのまま写せるよう、文と分けて返す。打つ物の無い事は行が空。
    """
    t = app.t
    out: list[tuple[str, list[str]]] = []

    def warn(word: str, do: str | None = None, **kw) -> None:
        out.append((t(word, **kw), t(do).splitlines() if do else []))

    if o.get("paused"):
        warn("admin_warn_paused")
    if not o.get("read"):
        warn("admin_warn_read", "admin_do_read")
    if o.get("audit") == "off":
        warn("admin_warn_audit_off", "admin_do_audit_off")
    elif o.get("audit") == "error":
        warn("admin_warn_audit_error", "admin_do_audit_error")
    if audit and audit.get("verified") is False:
        warn("admin_warn_tampered", "admin_do_tampered")
    denied = o.get("denied_today", 0)
    if isinstance(denied, int) and denied >= DENIED_MANY:
        warn("admin_warn_denied", n=denied)
    tk = o.get("tokens", {})
    if tk.get("expired", 0):
        warn("admin_warn_expired", n=tk["expired"])
    if tk.get("expiring", 0):
        warn("admin_warn_expiring", n=tk["expiring"], days=EXPIRING_DAYS)
    reads = o.get("remaining", {}).get("reads")
    if isinstance(reads, int) and reads <= 0:
        warn("admin_warn_limit")
    return out


def token_rows(app: App, tokens: list[dict]) -> list[dict]:
    """token の一覧。生きている物が先。"""
    t = app.t
    order = {"live": 0, "expired": 1, "revoked": 2}
    rows = []
    for tk in sorted(tokens, key=lambda x: (order.get(x.get("state"), 9), x.get("name", ""))):
        rows.append(
            {
                "name": tk.get("name", ""),
                "scope": "、".join(t(f"admin_scope_{s}") for s in tk.get("scope", [])),
                "state": t(f"admin_state_{tk.get('state', 'expired')}"),
                "period": f"{tk.get('created', '')} 〜 {tk.get('expires', '')}",
                "note": tk.get("note", ""),
                "live": tk.get("state") == "live",
            }
        )
    return rows


def record_rows(app: App, records: list[dict]) -> list[dict]:
    """公開された記録の行。名前・場所・始めた年、公開した人、公開した日、寄せられた一言の数、公開の頁。"""
    t = app.t
    out = []
    for rec in records:
        out.append(
            {
                "id": str(rec.get("id", "")),
                "head": " · ".join(
                    str(x) for x in (rec.get("name"), rec.get("place"), rec.get("since")) if x
                ),
                "meta": t(
                    "admin_record_meta",
                    owner=rec.get("owner") or t("admin_unknown_owner"),
                    published=rec.get("published") or "?",
                    connections=rec.get("connections", 0),
                ),
                "url": str(rec.get("url", "")),
            }
        )
    return out


def connection_rows(conns: list[dict]) -> list[dict]:
    """寄せられた一言の行（日と送った人、言葉、消す時の name）。"""
    return [
        {
            "name": str(c.get("name", "")),
            "head": f"{c.get('date', '')}　{c.get('from', '')}",
            "word": str(c.get("word", "")),
        }
        for c in conns
    ]


def audit_rows(app: App, lines: list[dict]) -> list[list[str]]:
    """誰が何をしたか（時、誰、何、どうなった）。した事は人の言葉に直す。"""
    t = app.t
    out = []
    for ln in lines[:AUDIT_LINES]:
        action = str(ln.get("action", ""))
        word = t(f"admin_act_{action.replace('.', '_')}")
        ts = str(ln.get("ts", ""))[:16].replace("T", " ")
        who = str(ln.get("actor", ""))
        out.append([ts, t("admin_stranger") if who == "?" else who, word, str(ln.get("detail", ""))])
    return out


def view(app: App) -> ft.View:
    t = app.t
    st: dict = app.state.setdefault("admin", {})
    controls: list[ft.Control] = [theme.heading(t("admin_title"))]

    async def load() -> None:
        try:
            st["overview"] = await app.call("admin_overview")
            st["tokens"] = await app.call("admin_tokens")
            st["audit"] = await app.call("admin_audit", AUDIT_LINES)
            st["records"] = await app.call("admin_records")
            st["error"] = None
        except Exception as ex:  # noqa: BLE001 — 本人に一文で見せる
            st["error"] = error_text(ex, app.lang, server=app.settings.server)
        st["loaded"] = True
        app.refresh()

    async def reload(e=None) -> None:
        st["loaded"] = False
        app.refresh()

    if not st.get("loaded"):
        controls.append(ft.Row([ft.ProgressRing(width=20, height=20), theme.muted(t("admin_loading"))]))
        app.page.run_task(load)
        return app.view("/admin", controls)
    if st.get("error"):
        controls += [theme.error(st["error"]), ft.OutlinedButton(t("admin_reload"), on_click=reload)]
        return app.view("/admin", controls)

    o, audit = st.get("overview") or {}, st.get("audit") or {}

    def pairs(rows: list[tuple[str, str]]) -> ft.Control:
        return ft.Column(
            [
                ft.Row(
                    [ft.Container(theme.muted(a), width=110), ft.Text(b, selectable=True, expand=True)],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
                for a, b in rows
            ],
            spacing=6,
        )

    def card(title: str, body: list[ft.Control]) -> ft.Control:
        inner = ft.Container(ft.Column([theme.subheading(title), *body], spacing=10), padding=16)
        return ft.Row([ft.Card(content=inner, expand=True)])  # 札の幅を揃える

    # ---- 今の状態と、気を付ける事
    async def pause(e) -> None:
        try:  # 一度押しで切り替える（止めている間も、管理の操作は通る）
            await app.call("admin_pause", not o.get("paused"))
        except Exception as ex:  # noqa: BLE001
            app.toast(error_text(ex, app.lang, server=app.settings.server))
            return
        await reload()

    at_body: list[ft.Control] = []
    for text, cmds in attention(app, o, audit):
        at_body.append(theme.error(text))
        if cmds:
            at_body.append(theme.mono("\n".join(cmds)))  # 等幅、選べる、一行に一つ
    if not at_body:
        at_body.append(theme.body(t("admin_nothing")))
    at_body.append(
        ft.OutlinedButton(
            t("admin_resume") if o.get("paused") else t("admin_pause"),
            icon=ft.Icons.PLAY_ARROW if o.get("paused") else ft.Icons.PAUSE,
            on_click=pause,
        )
    )
    controls.append(card(t("admin_state"), [pairs(state_rows(app, o))]))
    controls.append(card(t("admin_attention"), at_body))

    # ---- 人に渡す token
    name = ft.TextField(label=t("admin_token_name"), dense=True, width=220)
    scope = ft.Dropdown(
        label=t("admin_token_scope"),
        value="member",
        options=[ft.DropdownOption(key=s, text=t(f"admin_scope_{s}")) for s in SCOPES],
        dense=True,
        width=200,
    )
    days = ft.TextField(label=t("admin_token_days"), value="90", dense=True, width=110)
    note = ft.TextField(label=t("admin_token_note"), dense=True, width=260)

    async def issue(e) -> None:
        try:
            n = int((days.value or "").strip())
        except ValueError:
            app.toast(t("admin_days_number"))
            return
        try:
            code = await app.call(
                "admin_token_add", (name.value or "").strip(), scope.value or "member", n, note.value or ""
            )
        except Exception as ex:  # noqa: BLE001
            app.toast(error_text(ex, app.lang, server=app.settings.server))
            return
        st["new_token"] = {"name": (name.value or "").strip(), "code": code}
        await reload()

    def revoker(who: str):
        async def h(e) -> None:
            if st.get("confirm") != ("revoke", who):  # 一度目は確かめる。二度目で取り消す
                st["confirm"] = ("revoke", who)
                app.refresh()
                return
            st["confirm"] = None
            try:
                await app.call("admin_token_revoke", who)
            except Exception as ex:  # noqa: BLE001
                app.toast(error_text(ex, app.lang, server=app.settings.server))
                return
            await reload()

        return h

    async def revoke_all(e) -> None:
        if st.get("confirm") != ("revoke_all", ""):  # 一度目は確かめる。二度目で取り消す
            st["confirm"] = ("revoke_all", "")
            app.refresh()
            return
        st["confirm"] = None
        try:
            n = await app.call("admin_token_revoke_all")
        except Exception as ex:  # noqa: BLE001
            app.toast(error_text(ex, app.lang, server=app.settings.server))
            return
        app.toast(t("admin_revoked_all", n=n))
        await reload()

    async def copy_new(e) -> None:
        await app.page.clipboard.set(st["new_token"]["code"])
        app.toast(t("admin_copied"))

    tk_body: list[ft.Control] = []
    new = st.get("new_token")
    if new:
        tk_body.append(
            ft.Container(
                ft.Column(
                    [
                        theme.body(t("admin_token_once", name=new["name"])),
                        ft.Row(
                            [
                                ft.Text(new["code"], font_family="monospace", size=16, selectable=True),
                                ft.IconButton(
                                    ft.Icons.CONTENT_COPY, tooltip=t("admin_copy"), on_click=copy_new
                                ),
                            ],
                            wrap=True,
                        ),
                    ],
                    spacing=6,
                ),
                bgcolor=ft.Colors.SECONDARY_CONTAINER,
                padding=12,
                border_radius=8,
            )
        )
    tk_body += [
        ft.Row([name, scope, days, note], wrap=True),
        ft.FilledButton(t("admin_token_issue"), icon=ft.Icons.KEY_OUTLINED, on_click=issue),
    ]
    for r in token_rows(app, st.get("tokens") or []):
        asking = st.get("confirm") == ("revoke", r["name"])
        line: list[ft.Control] = [
            ft.Column(
                [
                    ft.Text(f"{r['name']}　{r['scope']}　{r['state']}", selectable=True),
                    theme.muted("　".join(x for x in (r["period"], r["note"]) if x)),
                ],
                spacing=2,
                expand=True,
            )
        ]
        if r["live"]:
            line.append(
                (ft.FilledButton if asking else ft.TextButton)(
                    t("admin_revoke_sure") if asking else t("admin_revoke"), on_click=revoker(r["name"])
                )
            )
        tk_body.append(ft.Row(line, vertical_alignment=ft.CrossAxisAlignment.START))
    asking_all = st.get("confirm") == ("revoke_all", "")
    tk_body.append(
        (ft.FilledButton if asking_all else ft.TextButton)(
            t("admin_revoke_all_sure") if asking_all else t("admin_revoke_all"), on_click=revoke_all
        )
    )
    controls.append(card(t("admin_tokens"), tk_body))

    # ---- 公開された記録
    def withdrawer(rid: str):
        async def h(e) -> None:
            if st.get("confirm") != ("withdraw", rid):
                st["confirm"] = ("withdraw", rid)
                app.refresh()
                return
            st["confirm"] = None
            try:
                await app.call("admin_withdraw", rid)
            except Exception as ex:  # noqa: BLE001
                app.toast(error_text(ex, app.lang, server=app.settings.server))
                return
            app.index = None
            await reload()

        return h

    conns: dict = st.setdefault("conns", {})  # 開いている記録の、寄せられた一言（開いた時だけ取りに行く）

    def opener(url: str):
        async def h(e) -> None:
            await ft.UrlLauncher().launch_url(url)

        return h

    def shower(rid: str):
        async def h(e) -> None:
            if rid in conns:
                conns.pop(rid)
                app.refresh()
                return
            try:
                conns[rid] = await app.call("admin_connections", rid)
            except Exception as ex:  # noqa: BLE001
                app.toast(error_text(ex, app.lang, server=app.settings.server))
                return
            app.refresh()

        return h

    def remover(rid: str, name: str):
        async def h(e) -> None:
            if st.get("confirm") != ("connection", f"{rid}/{name}"):  # 一度目は確かめる。二度目で消す
                st["confirm"] = ("connection", f"{rid}/{name}")
                app.refresh()
                return
            st["confirm"] = None
            try:
                await app.call("admin_connection_remove", rid, name)
                conns[rid] = await app.call("admin_connections", rid)
            except Exception as ex:  # noqa: BLE001
                app.toast(error_text(ex, app.lang, server=app.settings.server))
                return
            app.index = None
            await reload()

        return h

    rec_body: list[ft.Control] = []
    for r in record_rows(app, st.get("records") or []):
        rid = r["id"]
        asking = st.get("confirm") == ("withdraw", rid)
        buttons: list[ft.Control] = []
        if r["url"]:
            buttons.append(
                ft.TextButton(t("admin_open_page"), icon=ft.Icons.OPEN_IN_NEW, on_click=opener(r["url"]))
            )
        buttons += [
            ft.TextButton(
                t("admin_hide_connections") if rid in conns else t("admin_show_connections"),
                on_click=shower(rid),
            ),
            (ft.FilledButton if asking else ft.TextButton)(
                t("admin_withdraw_sure") if asking else t("admin_withdraw"), on_click=withdrawer(rid)
            ),
        ]
        one: list[ft.Control] = [
            ft.Text(r["head"], selectable=True),
            theme.muted(rid),
            theme.muted(r["meta"]),
            ft.Row(buttons, wrap=True, spacing=4),
        ]
        if rid in conns:
            rows_c = connection_rows(conns[rid])
            for c in rows_c:
                sure = st.get("confirm") == ("connection", f"{rid}/{c['name']}")
                one.append(
                    ft.Row(
                        [
                            ft.Column(
                                [theme.muted(c["head"]), ft.Text(c["word"], selectable=True)],
                                spacing=0,
                                expand=True,
                            ),
                            (ft.FilledButton if sure else ft.TextButton)(
                                t("admin_connection_remove_sure") if sure else t("admin_connection_remove"),
                                on_click=remover(rid, c["name"]),
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                )
            if not rows_c:
                one.append(theme.muted(t("admin_no_connections")))
        rec_body.append(ft.Column(one, spacing=4))
    controls.append(card(t("admin_records"), rec_body or [theme.muted(t("admin_no_records"))]))

    # ---- 誰が何をしたか
    rows = audit_rows(app, audit.get("lines") or [])
    au_body: list[ft.Control] = [
        ft.Column(
            [
                ft.Text(f"{ts}　{who}　{what}", selectable=True, size=14),
                *([theme.muted(detail)] if detail and detail != "通した" else []),
            ],
            spacing=0,
        )
        for ts, who, what, detail in rows
    ] or [theme.muted(t("admin_no_audit"))]
    controls.append(card(t("admin_journal"), au_body))
    controls.append(ft.OutlinedButton(t("admin_reload"), icon=ft.Icons.REFRESH, on_click=reload))
    return app.view("/admin", controls)
