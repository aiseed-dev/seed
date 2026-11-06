# SPDX-License-Identifier: AGPL-3.0-or-later
"""計画 /plan。借りる・買うことができた畑の栽培計画 plan.md（記録の形 §10、手引き 09 章）。

AI の行は仮説で、合う／違うを付ける。決めたこと（decided）としたこと（did）は本人が書く。
立てるのはこの PC の claude（無ければ Claude Code の手順）。サーバーでは立てない。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import flet as ft

from seed import local
from seed.app import theme
from seed.app.observe import lines_block, reading_rows, record_adder
from seed.app.strings import error_text
from seed.cli import load_plan, plan_local, plan_steps
from seed.client import ClientError
from seed.records import PLAN_RECORD_KEYS

if TYPE_CHECKING:
    from seed.app.main import App


def view(app: App) -> ft.View:
    t, st = app.t, app.state
    plan = load_plan(app.settings, app.folder)
    path = app.folder.plan
    busy = ft.Row([ft.ProgressRing(width=20, height=20), theme.body(t("planning_now"))], visible=False)
    season = ft.TextField(label=t("season"), value=plan.season, dense=True)

    def season_changed(e) -> None:
        plan.season = (season.value or "").strip()
        plan.write(path)

    season.on_blur = season_changed
    season.on_submit = season_changed

    async def make(e) -> None:
        busy.visible = True
        for b in buttons.controls:
            b.disabled = True
        st.update(plan_err=None, plan_msg=None)
        app.page.update()
        plan.season = (season.value or "").strip()
        try:
            await asyncio.to_thread(plan_local, app.settings, app.folder, plan)
            plan.write(path)
            st.update(plan_err=None, plan_msg=t("saved_to", path=path))
        except ClientError as ex:
            st.update(plan_err=error_text(ex, app.lang), plan_msg=None)
        app.refresh()

    def steps(e) -> None:
        if not path.exists():
            plan.write(path)
        st["plan_steps"] = plan_steps(app.lang, app.folder, app.folder_label)
        app.refresh()

    has_local = local.available() is not None and not app.web  # Web 版ではサーバーで立てる口はまだ無い
    make_word = t("plan_remake") if plan.reading else t("plan_make")
    buttons = ft.Row(
        [
            (ft.FilledButton if has_local else ft.OutlinedButton)(
                make_word, icon=ft.Icons.COMPUTER_OUTLINED, on_click=make, disabled=not has_local
            ),
            ft.OutlinedButton(t("plan_claude"), icon=ft.Icons.TERMINAL, on_click=steps),
        ],
        wrap=True,
    )
    controls: list[ft.Control] = [
        theme.heading(t("plan_title")),
        theme.note(t("plan_hint")),
        season,
        buttons,
        busy,
    ]
    if st.get("plan_err"):
        controls.append(theme.error(st["plan_err"]))
    if st.get("plan_msg"):
        controls.append(theme.muted(st["plan_msg"]))
    if st.get("plan_steps"):
        controls.append(theme.mono(st["plan_steps"]))
    if plan.reading:
        controls += [
            theme.subheading(f"{t('Plan')} ({plan.model or t('(none)')})"),
            theme.muted(t("plan_since", since=plan.since)),
            theme.muted(t("ai_hint")),
        ]
        controls += reading_rows(app, plan, path)
    else:
        controls.append(theme.muted(t("plan_none")))
    controls += lines_block(app, "Earlier plan", plan.earlier)
    controls += lines_block(app, "Data", plan.data)
    controls += lines_block(app, "Record", plan.record)
    controls += record_adder(app, plan, path, keys=PLAN_RECORD_KEYS, hint="plan_record_hint")
    controls += [ft.Divider(), theme.muted(str(path))]
    return app.view("/plan", controls)
