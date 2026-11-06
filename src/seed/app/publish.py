# SPDX-License-Identifier: AGPL-3.0-or-later
"""公開 /publish。観察を選び、行にチェックし、場所の粗さと一言を決めて送る（利用マニュアル §7）。

写真は付けない。Public.check() が空のときだけ送る。公開済みの一覧から取り下げもできる。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from seed import lang
from seed.app import theme
from seed.app.strings import error_text, next_words
from seed.cli import default_lines, make_public, split_tags
from seed.records import Line, Observation, Public
from seed.settings import PLACE_LEVELS

if TYPE_CHECKING:
    from seed.app.main import App


def candidates(obs: Observation) -> list[Line]:
    return [*obs.reading, *obs.data, *obs.record]


def view(app: App) -> ft.View:
    t, st = app.t, app.state
    chosen: dict[str, set[int]] = st.setdefault("pub_lines", {})  # 観察の名 → 選んだ行の番号
    form: dict = st.setdefault(
        "pub_form",
        {
            "place_level": app.settings.place_level,
            "name": app.settings.name,
            "next": set(),
            "with_coord": False,
        },
    )
    status = ft.Column(spacing=4)
    observations = {p.stem: Observation.read(p) for p in reversed(app.folder.list_observations())}

    # --- 観察と行
    def toggle_obs(name: str):
        def handler(e) -> None:
            if e.control.value:
                obs = observations[name]
                keep = default_lines(obs)
                chosen[name] = {i for i, l in enumerate(candidates(obs)) if any(l is k for k in keep)}
            else:
                chosen.pop(name, None)
            app.refresh()

        return handler

    def toggle_line(name: str, i: int):
        def handler(e) -> None:
            (chosen[name].add if e.control.value else chosen[name].discard)(i)

        return handler

    obs_rows: list[ft.Control] = []
    for name, obs in observations.items():
        obs_rows.append(
            ft.Checkbox(
                label=f"{obs.date} {obs.time}  ({len(obs.reading)} / {len(obs.data)} / {len(obs.record)})"
                + (f"  {t('candidate')}" if obs.kind == "candidate" else ""),
                value=name in chosen,
                on_change=toggle_obs(name),
            )
        )
        if name in chosen:
            for i, line in enumerate(candidates(obs)):
                obs_rows.append(
                    ft.Container(
                        ft.Row(
                            [
                                ft.Checkbox(value=i in chosen[name], on_change=toggle_line(name, i)),
                                ft.Container(theme.line_text(line, app.lang), expand=True),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                        padding=ft.Padding.only(left=28),
                    )
                )

    # --- 書く欄
    def field(key: str, label: str, **kw) -> ft.TextField:
        tf = ft.TextField(label=t(label), value=form.get(key, ""), **kw)

        def changed(e) -> None:
            form[key] = tf.value

        tf.on_change = changed
        return tf

    level = ft.Dropdown(
        label=t("place_level"),
        value=form["place_level"],
        options=[ft.DropdownOption(key=k, text=lang.t(k, app.lang)) for k in PLACE_LEVELS],
        width=220,
    )

    def level_changed(e) -> None:
        form["place_level"] = level.value

    level.on_select = level_changed
    coord = ft.Checkbox(label=t("with_coord"), value=form["with_coord"])

    def coord_changed(e) -> None:
        form["with_coord"] = bool(coord.value)

    coord.on_change = coord_changed

    def next_handler(word: str):
        def handler(e) -> None:
            form["next"].symmetric_difference_update({word})

        return handler

    next_chips = ft.Row(
        [
            ft.Chip(label=ft.Text(w), selected=w in form["next"], on_select=next_handler(w))
            for w in next_words(app.lang)
        ],
        wrap=True,
        spacing=6,
    )

    async def do_publish(e) -> None:
        picked = [(observations[n], sorted(ix)) for n, ix in chosen.items() if n in observations]
        picked.sort(key=lambda x: (x[0].date, x[0].time))
        obs_list = [o for o, _ in picked]
        selected = [[candidates(o)[i] for i in ix] for o, ix in picked]
        pub = make_public(
            app.settings,
            obs_list,
            selected,
            public_id=form.get("id", ""),
            place=form.get("place", ""),
            word=form.get("word", ""),
            what=split_tags(form.get("what")),
            next_=sorted(form["next"]),
            with_coord=form["with_coord"],
            contact=(form.get("contact") or "").strip() or None,
            name=form.get("name", ""),
        )
        bad = pub.check()
        if not pub.days:
            bad.append(t("nothing_selected"))
        if bad:
            status.controls = [theme.error(t("fix_these")), *[theme.error(f"- {b}") for b in bad]]
            app.page.update()
            return
        # 呼び名と場所の粗さは次も使う
        app.settings.name, app.settings.place_level = pub.name, form["place_level"]
        app.settings.save()
        app.folder.public.mkdir(parents=True, exist_ok=True)
        path = app.folder.public / f"{pub.id}.md"
        pub.write(path)
        try:
            got = await app.call("publish", pub.render())
        except Exception as ex:  # noqa: BLE001 — 本人に一文で見せる
            st["pub_msg"] = [
                error_text(ex, app.lang, server=app.settings.server),
                t("published_local", path=path),
            ]
            app.refresh()
            return
        app.index = None
        st["pub_msg"] = [t("published", url=got.get("url") or got.get("id"))]
        app.refresh()

    def unpublish_handler(pid: str):
        async def handler(e) -> None:
            try:
                await app.call("unpublish", pid)
            except Exception as ex:  # noqa: BLE001
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

    controls: list[ft.Control] = [theme.heading(t("publish_title"))]
    controls += [
        theme.subheading(t("choose_obs")),
        *(obs_rows or [theme.muted(t("no_observations"))]),
        *(
            [theme.note(t("owner_warning"))]
            if any(observations[n].kind == "candidate" for n in chosen if n in observations)
            else []
        ),
        theme.muted(t("select_lines")),
        theme.muted(t("no_photos_public")),
        ft.Divider(),
        ft.Row([level, coord], wrap=True),
        field("place", "place"),
        field("id", "public_id"),
        field("name", "name"),
        field("what", "what"),
        theme.muted(t("next")),
        next_chips,
        field("contact", "contact"),
        field("word", "word", multiline=True, min_lines=2, max_length=200),
        ft.FilledButton(t("publish_button"), icon=ft.Icons.PUBLIC, on_click=do_publish),
        status,
        *[theme.body(m) for m in st.pop("pub_msg", [])],
    ]
    if published:
        controls += [ft.Divider(), theme.subheading(t("published_list")), *published]
    return app.view("/publish", controls)
