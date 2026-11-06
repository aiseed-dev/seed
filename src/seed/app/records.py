# SPDX-License-Identifier: AGPL-3.0-or-later
"""記録 /records。観察の一覧、開くと行と判定。place.md と next.md の文はそのまま見せる。

毎回ファイルから読む。自分の Claude が書いた観察も、エディターで直した所も、そのまま出る。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from seed.app import theme
from seed.app.observe import lines_block, reading_rows, record_adder, summary
from seed.records import Observation

if TYPE_CHECKING:
    from seed.app.main import App


def _read(path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def is_candidate(obs: Observation) -> bool:
    return obs.kind == "candidate"


def row_texts(t, obs: Observation) -> tuple[str, str]:
    """一覧の一行の題と副題。候補地（kind: candidate）の観察は題の頭に印を付ける（記録の形 §19）。"""
    judged = sum(1 for l in obs.reading if l.judged)
    sub = "  ".join(
        [
            f"{t('Reading')}: {obs.model or t('(none)')}",
            t("judged", judged=judged, total=len(obs.reading)),
            t("photos_n", n=len(obs.photos)),
            *([t("candidate")] if is_candidate(obs) else []),
        ]
    )
    mark = f"{t('candidate_mark')}  " if is_candidate(obs) else ""
    return f"{mark}{obs.date} {obs.time}", sub


def view(app: App) -> ft.View:
    t, st = app.t, app.state
    if st.get("rec_open"):
        return opened(app, st["rec_open"])

    def open_handler(name: str):
        def handler(e) -> None:
            st["rec_open"] = name
            app.refresh()

        return handler

    items: list[ft.Control] = []
    for path in reversed(app.folder.list_observations()):
        try:
            obs = Observation.read(path)
        except (ValueError, TypeError) as ex:
            items.append(theme.error(f"{path.name}: {ex}"))
            continue
        title, sub = row_texts(t, obs)
        items.append(
            ft.ListTile(
                title=ft.Text(title),
                subtitle=ft.Text(sub),
                leading=ft.Icon(
                    ft.Icons.TRAVEL_EXPLORE if is_candidate(obs) else ft.Icons.DESCRIPTION_OUTLINED
                ),
                on_click=open_handler(path.stem),
            )
        )
    controls: list[ft.Control] = [theme.heading(t("records_title"))]
    controls += items or [theme.muted(t("no_observations"))]
    controls += [
        ft.Divider(),
        theme.subheading(t("place_md")),
        theme.mono(_read(app.folder.place)),
        theme.subheading(t("next_md")),
        theme.mono(_read(app.folder.next)),
        theme.muted(t("edit_hint")),
    ]
    return app.view("/records", controls)


def opened(app: App, name: str) -> ft.View:
    t, st = app.t, app.state
    path = app.folder.observations / f"{name}.md"

    def back(e) -> None:
        st.pop("rec_open", None)
        app.refresh()

    controls: list[ft.Control] = [ft.TextButton(t("back"), icon=ft.Icons.ARROW_BACK, on_click=back)]
    if not path.exists():
        return app.view("/records", [*controls, theme.error(t("observation_not_found", name=name))])
    obs = Observation.read(path)
    controls += summary(app, obs)
    controls.append(theme.subheading(f"{t('Reading')} ({obs.model or t('(none)')})"))
    controls += reading_rows(app, obs, path) if obs.reading else [theme.muted(t("(none)"))]
    controls += lines_block(app, "Earlier reading", obs.earlier)
    controls += lines_block(app, "Data", obs.data)
    controls += lines_block(app, "Record", obs.record)
    controls += record_adder(app, obs, path)
    controls += [ft.Divider(), theme.muted(str(path))]
    return app.view("/records", controls)
