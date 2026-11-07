# SPDX-License-Identifier: AGPL-3.0-or-later
"""「話す」の入力の上の印を押した時に、やり取りの下に出す札。

計画を見る、公開した物、この畑で見つけた草、ほかの人の畑、設定。どれも見せるだけか、押すだけ。文字を打つのは下の入力。
細かい作業（計画を立てる、公開の下書き、行を直す）は、下の入力から Claude に頼む。
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

import flet as ft

from seed import __version__, client, local
from seed import fields as fields_mod
from seed import highlights as H
from seed import records as R
from seed.app import capture, photo, theme
from seed.app.strings import DISCORD_URL, error_text
from seed.cli import load_plan
from seed.records import Connection, Observation, Public

if TYPE_CHECKING:
    from seed.app.main import App

SOURCE_URL = "https://github.com/aiseed-dev/seed"
PLANT_PHOTOS = 6
BIG_W = 560  # 公開された記録の写真の幅の上限（話すの今日の一枚と同じ）


def frame(app: App, key: str, body: list[ft.Control]) -> ft.Control:
    return ft.Container(
        ft.Column([theme.subheading(app.t(f"card_{key}")), *body], spacing=10, tight=True),
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        padding=16,
        border_radius=16,
    )


def card(app: App, key: str) -> ft.Control:
    if key.startswith("record:"):
        return record_card(app, key.removeprefix("record:"))
    build = {
        "plan": plan_card,
        "published": published_card,
        "plants": plants_card,
        "others": others_card,
        "settings": settings_card,
    }[key]
    return frame(app, key, build(app))


def claude_hint(app: App, word: str) -> ft.Control:
    """細かい作業は Claude に頼む、の一行。Claude を呼べない時（鍵も招待コードも無い）は PC の Claude Code へ。"""
    from seed.app.talk import can_talk

    return theme.note(app.t(f"{word}_here" if can_talk(app) else f"{word}_pc"))


# ---------------------------------------------------------------- 計画


def plan_card(app: App) -> list[ft.Control]:
    plan = load_plan(app.settings, app.folder)
    out: list[ft.Control] = []
    if plan.reading:
        if plan.season:
            out.append(theme.muted(plan.season))
        out += [theme.line_text(l, app.lang) for l in plan.reading]
        out += [theme.line_text(l, app.lang) for l in plan.record]
    else:
        out.append(theme.body(app.t("plan_none")))
    out.append(claude_hint(app, "talk_plan"))
    return out


# ---------------------------------------------------------------- 公開した物


def published_card(app: App) -> list[ft.Control]:
    t, st = app.t, app.state

    def withdraw(pid: str):
        async def h(e) -> None:
            if st.get("confirm") != ("unpublish", pid):  # 一度目は確かめる。二度目で取り下げる
                st["confirm"] = ("unpublish", pid)
                app.refresh()
                return
            st["confirm"] = None
            try:
                await app.call("unpublish", pid)
            except Exception as ex:  # noqa: BLE001 — 本人に一文で見せる
                app.toast(error_text(ex, app.lang, server=app.settings.server))
                return
            (app.folder.public / f"{pid}.md").unlink(missing_ok=True)  # 控えは消す（観察は残る）
            app.index = None
            app.toast(t("unpublished", id=pid))
            app.refresh()

        return h

    out: list[ft.Control] = []
    for p in sorted(app.folder.public.glob("*.md")) if app.folder.public.exists() else []:
        try:
            pub = Public.read(p)
        except (ValueError, TypeError) as ex:
            out.append(theme.error(f"{p.name}: {ex}"))
            continue
        sure = st.get("confirm") == ("unpublish", pub.id)
        out.append(
            ft.Row(
                [
                    ft.Column(
                        [ft.Text(f"{pub.id} · {pub.since}"), theme.muted(pub.word)], spacing=2, expand=True
                    ),
                    (ft.FilledButton if sure else ft.TextButton)(
                        t("unpublish_sure") if sure else t("unpublish"), on_click=withdraw(pub.id)
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    if not out:
        out.append(theme.body(t("published_none")))
    out.append(claude_hint(app, "talk_publish"))
    return out


# ---------------------------------------------------------------- この畑で見つけた草


def plants_card(app: App) -> list[ft.Control]:
    observations: list[tuple[str, Observation]] = []
    for path in app.folder.list_observations():
        try:
            observations.append((path.stem, Observation.read(path)))
        except (ValueError, TypeError, OSError):
            continue
    by_name = dict(observations)
    out: list[ft.Control] = []
    for p in H.plants(observations):
        shots = [photo.Shot(by_name[oid], rel) for oid, rel in p.photos if rel][:PLANT_PHOTOS]
        out.append(ft.Text(p.name, size=theme.BODY_SIZE, weight=ft.FontWeight.W_500, selectable=True))
        if shots:
            out.append(photo.strip(app, shots, photo.TINY))
    if not out:
        out.append(theme.body(app.t("plants_none")))
    return out


# ---------------------------------------------------------------- ほかの人の畑（公開された記録）


def others_card(app: App) -> list[ft.Control]:
    t, st = app.t, app.state
    if app.index is None:
        if st.get("index_error"):
            return [theme.error(st["index_error"])]
        if not st.get("index_loading"):
            st["index_loading"] = True

            async def load() -> None:
                try:
                    await app.load_index()
                    st["index_error"] = None
                except Exception as ex:  # noqa: BLE001
                    st["index_error"] = error_text(ex, app.lang, server=app.settings.server)
                st["index_loading"] = False
                app.refresh()

            app.page.run_task(load)
        return [theme.muted(t("loading"))]

    def open_it(rid: str):
        def h(e) -> None:
            from seed.app.talk import add

            add(app, card=f"record:{rid}")
            app.refresh()

        return h

    def to_whom(rid: str):
        def h(e) -> None:
            st["talk_to"] = rid
            app.refresh()

        return h

    recs = sorted(app.index.get("records", []), key=lambda r: str(r.get("since", "")), reverse=True)
    out: list[ft.Control] = []
    for r in recs:
        if not r.get("id"):
            continue
        head = " · ".join(x for x in (r.get("name"), r.get("place"), r.get("since")) if x)
        cover = r.get("photo")
        pic = (
            [web_image(server_url(app, cover), photo.SMALL, photo.SMALL * 0.75)]
            if isinstance(cover, str) and cover.startswith("/photos/")
            else []
        )
        out.append(
            ft.Column(
                [
                    *pic,
                    theme.muted(head),
                    theme.body(r.get("word", "")),
                    theme.muted(
                        "  ".join(
                            [
                                t("observations_n", n=r.get("observations", 0)),
                                t("connections_n", n=r.get("connections", 0)),
                            ]
                        )
                    ),
                    ft.Row(
                        [
                            ft.TextButton(t("open"), icon=ft.Icons.OPEN_IN_FULL, on_click=open_it(r["id"])),
                            ft.TextButton(
                                t("talk_to_button"), icon=ft.Icons.CHAT_OUTLINED, on_click=to_whom(r["id"])
                            ),
                        ],
                        wrap=True,
                        spacing=4,
                    ),
                ],
                spacing=4,
            )
        )
    if not out:
        out.append(theme.body(t("index_empty")))
    out += [
        theme.muted(t("continue_discord")),
        discord_button(app),
    ]
    return out


def discord_button(app: App) -> ft.Control:
    """Discord に入る釦。名（「…」）は一つの塊にして、狭い幅では「Discord」の後で行を変える（一字だけ折り返さない）。"""
    label = app.t("discord")
    head, sep, rest = label.partition("「")
    parts = [ft.Text(head.strip())] + ([ft.Text(sep + rest)] if sep else [])
    return ft.TextButton(
        content=ft.Row(parts, wrap=True, spacing=4, run_spacing=0, tight=True),
        icon=ft.Icons.FORUM_OUTLINED,
        url=DISCORD_URL,
    )


def server_url(app: App, path: str) -> str:
    """サーバーの上の道（/photos/<id>/<名>）を、設定のサーバーの URL に。"""
    return app.settings.server.rstrip("/") + path


def web_image(url: str, w: float, h: float) -> ft.Control:
    """公開された写真（サーバーから）。"""
    return ft.Container(
        ft.Image(src=url, width=w, height=h, fit=ft.BoxFit.COVER),
        width=w,
        height=h,
        border_radius=12,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def record_card(app: App, rid: str) -> ft.Control:
    """公開された記録を一つ開いた札。"""
    t, st = app.t, app.state
    cache: dict = st.setdefault("public_cache", {})
    body: list[ft.Control]
    if rid not in cache:
        cache[rid] = None

        async def load() -> None:
            try:
                cache[rid] = ("ok", await app.call("public", rid))
            except Exception as ex:  # noqa: BLE001
                cache[rid] = ("error", error_text(ex, app.lang, server=app.settings.server))
            app.refresh()

        app.page.run_task(load)
    got = cache.get(rid)
    if got is None:
        body = [theme.muted(t("loading"))]
    elif got[0] == "error":
        body = [theme.error(got[1])]
    else:
        try:
            pub = Public.parse(got[1])
            body = [
                theme.subheading(" · ".join(x for x in (pub.name, pub.place, pub.since) if x)),
                theme.body(pub.word),
            ]
            if pub.contact:
                body.append(theme.muted(pub.contact))
            w = min(BIG_W, theme.fit_width(getattr(app.page, "width", None)) - 72)
            for day in sorted(pub.days):
                shots, lines = pub.day_parts(day)  # 分け方はページと同じ（Public.day_parts）
                body.append(theme.muted(day))
                body += [web_image(server_url(app, R.photo_url(pub.id, n)), w, w * 0.75) for n in shots]
                body += [theme.line_text(l, app.lang) for l in lines]
        except (ValueError, TypeError):
            body = [theme.mono(got[1])]

    def to_whom(e) -> None:
        st["talk_to"] = rid
        app.refresh()

    body.append(ft.TextButton(t("talk_to_button"), icon=ft.Icons.CHAT_OUTLINED, on_click=to_whom))
    return ft.Container(
        ft.Column(body, spacing=8, tight=True),
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        padding=16,
        border_radius=16,
    )


def my_public_id(app: App) -> str:
    """自分の公開の id（新しい物）。無ければ呼び名。"""
    pubs = (
        sorted(app.folder.public.glob("*.md"), key=lambda p: p.stat().st_mtime)
        if app.folder.public.exists()
        else []
    )
    return pubs[-1].stem if pubs else app.settings.name


async def send_word(app: App, rid: str, word: str) -> None:
    """ほかの人の畑へ一言を送る（下の入力から）。"""
    from seed.app.talk import add, say

    src = my_public_id(app) or app.t("talk_no_name")
    add(app, who="me", text=f"→ {rid}: {word}")
    try:
        n = await app.call("connect", rid, src, word)
    except Exception as ex:  # noqa: BLE001
        say(app, error_text(ex, app.lang, server=app.settings.server))
        app.refresh()
        return
    app.folder.add_connection(Connection(dt.date.today().isoformat(), src, rid, word.replace("\n", " ")))
    app.index = None  # 数が変わったので次は取り直す
    say(app, app.t("sent", n=n))
    app.refresh()


# ---------------------------------------------------------------- 設定


def setting_row(label: str, value: str, actions: list[ft.Control]) -> ft.Control:
    return ft.Column(
        [
            theme.muted(label),
            ft.Row([ft.Text(value, size=theme.BODY_SIZE, selectable=True), *actions], wrap=True, spacing=6),
        ],
        spacing=2,
    )


def remote_rows(app: App) -> list[ft.Control]:
    """「スマートフォンから使う」の行（PC のアプリだけ）。状態は remote.Remote が持つ。"""
    import base64

    from seed import remote

    t, r = app.t, app.state.get("remote")

    def do(method: str):
        async def h(e) -> None:
            await getattr(app, method)()

        return h

    def btn(word: str, method: str) -> ft.Control:
        return ft.TextButton(t(word), on_click=do(method))

    label = t("set_remote")
    if r is None:
        return [setting_row(label, t("set_remote_none"), [btn("set_remote_start", "remote_start")])]
    st = r.state
    if st == "starting":
        return [setting_row(label, t("set_remote_starting"), [btn("set_remote_stop", "remote_stop")])]
    if st == "asking":
        return [
            setting_row(
                label,
                t("set_remote_asking"),
                [btn("set_remote_yes", "remote_yes"), btn("set_remote_stop", "remote_stop")],
            )
        ]
    if st == "untrusted":
        return [
            setting_row(label, t("set_remote_untrusted"), [btn("set_remote_stop", "remote_stop")]),
            theme.muted(app.folder_label),
        ]
    if st == "stopped":
        return [
            setting_row(label, t("set_remote_stopped"), [btn("set_remote_again", "remote_start")]),
            *[theme.muted(x) for x in r.lines[-3:]],
        ]
    out = [setting_row(label, t("set_remote_running"), [btn("set_remote_stop", "remote_stop")])]
    url = r.url
    if url:
        png = remote.qr_png(url)
        if png:
            out.append(ft.Image(src=base64.b64encode(png).decode(), width=160, height=160))
        out.append(ft.Text(url, size=theme.BODY_SIZE, selectable=True))
    out.append(theme.muted(t("set_remote_how", name=app.state.get("remote_name", ""))))
    return out


def settings_card(app: App) -> list[ft.Control]:
    t, st = app.t, app.state
    out: list[ft.Control] = []

    def again(e) -> None:
        from seed.app.talk import ask_invite

        ask_invite(app)
        app.refresh()

    # 招待コード（サーバーで読む、公開、一言に要る）
    have = bool(app.settings.invite)
    out.append(
        setting_row(
            t("invite"),
            t("set_invite_in") if have else t("set_invite_out"),
            [ft.TextButton(t("set_invite_again") if have else t("set_invite_put"), on_click=again)],
        )
    )

    # 自分の Claude の鍵（Anthropic の API の鍵）。値は出さない。入れるのは下の入力から、外すのは二度押し
    have_key = bool(app.settings.anthropic_key)

    def put_key(e) -> None:
        from seed.app.talk import ask_key

        ask_key(app)
        app.refresh()

    def drop_key(e) -> None:
        from seed.app.talk import forget_key

        if st.get("confirm") != ("forget_key",):
            st["confirm"] = ("forget_key",)
            app.refresh()
            return
        st["confirm"] = None
        forget_key(app)
        app.refresh()

    key_actions: list[ft.Control] = [
        ft.TextButton(t("set_key_put") if not have_key else t("set_invite_again"), on_click=put_key)
    ]
    if have_key:
        sure = st.get("confirm") == ("forget_key",)
        key_actions.append(
            (ft.FilledButton if sure else ft.TextButton)(
                t("set_key_remove_sure") if sure else t("set_key_remove"), on_click=drop_key
            )
        )
    out.append(
        setting_row(t("set_key"), t("set_invite_in") if have_key else t("set_invite_out"), key_actions)
    )

    # Claude を呼ぶ所（読み取りと話す）。使える物が二つ以上あれば、押して次へ
    from seed.app.talk import route, routes

    now, have = route(app), routes(app)
    label = {
        "local": t("set_read_local"),
        "key": t("set_read_key", model=app.settings.model),
        "server": t("set_read_server"),
        None: t("set_read_none"),
    }[now]
    actions: list[ft.Control] = []
    if now is not None and len(have) >= 2:
        nxt = have[(have.index(now) + 1) % len(have)]

        def flip(e, nxt=nxt) -> None:
            app.settings.read = nxt
            app.settings.save()
            app.state.pop("direct_messages", None)
            app.refresh()

        actions.append(ft.TextButton(t(f"set_read_to_{nxt}"), on_click=flip))
    out.append(setting_row(t("set_read"), label, actions))

    # 今見ている畑（自分の畑か、候補地か）。次に撮る写真に付く
    kind = st.get("kind", "own")

    def flip_kind(e) -> None:
        st["kind"] = "candidate" if kind == "own" else "own"
        app.refresh()

    out.append(
        setting_row(
            t("set_kind"),
            t(kind),
            [
                ft.TextButton(
                    t("set_kind_to_candidate") if kind == "own" else t("set_kind_to_own"), on_click=flip_kind
                )
            ],
        )
    )

    # 畑を二つ以上持っていれば、切り替え
    fl = fields_mod.load_fields()
    if len(fl.fields) >= 2:
        now = fields_mod.selected_name(fl, app.project)

        def switch(name: str):
            async def h(e) -> None:
                await app.switch_field(name)

            return h

        out.append(
            setting_row(
                t("set_field"),
                now or app.folder_label,
                [ft.TextButton(t("set_field_to", name=n), on_click=switch(n)) for n in fl.names if n != now],
            )
        )
    # フォルダーを開くのは PC のアプリだけ（スマートフォンと Web 版は箱が一つ）
    pc = capture.is_pc(app)

    async def pick(e) -> None:
        await app.pick_folder()

    out.append(
        setting_row(
            t("set_folder"),
            app.folder_label,
            [ft.TextButton(t("set_folder_open"), on_click=pick)] if pc else [],
        )
    )

    if pc and local.available():
        out += remote_rows(app)

    # 家のサーバー（seed home。設計書 §5.13）に送っているなら一行。まだ聞いていなければ一度だけ聞きに行く
    if route(app) == "server" and app.settings.invite and not st.get("home_asked"):
        st["home_asked"] = True

        async def ask_home() -> None:
            import asyncio

            if await asyncio.to_thread(client.is_home, app.settings.server):
                app.refresh()

        app.page.run_task(ask_home)
    if client.known_home(app.settings.server):
        out.append(theme.muted(t("set_home", url=app.settings.server)))
    out.append(theme.muted(t("set_server", server=app.settings.server, version=__version__)))

    def change_server(e) -> None:
        from seed.app.talk import ask_server

        ask_server(app)
        app.refresh()

    def find_pc(e) -> None:
        from seed.app.talk import find_home

        app.page.run_task(find_home, app)

    out.append(ft.TextButton(t("set_find_home"), on_click=find_pc))
    out.append(ft.TextButton(t("set_server_change"), on_click=change_server))
    out.append(
        ft.Row(
            [
                discord_button(app),
                ft.TextButton(t("set_source"), icon=ft.Icons.CODE, url=SOURCE_URL),
            ],
            wrap=True,
        )
    )
    return out


def project_sheet(app: App) -> ft.BottomSheet:
    """プロジェクトフォルダーを選ぶ下の板。今のフォルダー、畑の一覧（今のは印をつけて押せない）、PC なら別のフォルダーを開く。

    畑が幾つもあるプロジェクトでは、上に「プロジェクト全体」と畑の並び（設計書 §5.12）、細い線の下に別のプロジェクト。
    """
    t = app.t
    fl = fields_mod.load_fields()
    now = app.project_name

    def close() -> None:
        app.page.pop_dialog()

    def switch(name: str):
        async def h(e) -> None:
            close()
            await app.switch_field(name)

        return h

    async def pick(e) -> None:
        close()
        await app.pick_folder()

    def choose(name: str):
        async def h(e) -> None:
            close()
            await app.choose_field(name)

        return h

    rows: list[ft.Control] = [
        ft.Text(t("project_current"), weight=ft.FontWeight.BOLD),
        theme.muted(app.folder_label),
    ]
    if app.fields:
        here = app.field_name
        for name, label in [("", t("project_whole")), *((f.root.name, f.root.name) for f in app.fields)]:
            on = name == (here or "")
            rows.append(
                ft.TextButton(label, icon=ft.Icons.CHECK if on else None, disabled=on, on_click=choose(name))
            )
        rows.append(ft.Divider(height=1, thickness=1))
    for n in fl.names:
        here = n == now
        rows.append(
            ft.TextButton(
                n,
                icon=ft.Icons.CHECK if here else None,
                disabled=here,
                on_click=switch(n),
            )
        )
    if capture.is_pc(app):
        rows.append(ft.TextButton(t("set_folder_open"), icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=pick))
    return ft.BottomSheet(ft.Container(ft.Column(rows, tight=True), padding=16))
