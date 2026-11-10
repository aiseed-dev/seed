# SPDX-License-Identifier: AGPL-3.0-or-later
"""確かめ。土地の仮説と、写真がそれに何を言ったか、写真の覆い％を測る名詞（11-11 に fieldnotes の「土地」と「名詞」の
画面から）。本人は合う／違うを押すだけ。仮説を足すのと、写真で確かめるのは、話すの画面か seed hypothesis / seed check。"""

from __future__ import annotations

import flet as ft

from seed import concepts
from seed.app import theme
from seed.records import Hypotheses, Observation

TITLE = {"ja": "確かめ", "en": "Checks"}
ICON = "FACT_CHECK_OUTLINED"


def latest_checks(folder) -> dict[str, tuple[str, str]]:
    """h → (観察の日, その確かめの文)。新しい観察の物が勝つ。"""
    out: dict[str, tuple[str, str]] = {}
    for path in folder.list_observations():
        try:
            obs = Observation.read(path)
        except (ValueError, OSError):
            continue
        for l in obs.checks:
            out[l.key] = (obs.date, l.text)
    return out


def verdict_buttons(app, on_mark, current: str | None) -> ft.Row:
    t = app.t

    def button(verdict: str) -> ft.Control:
        icon = ft.Icons.CHECK if verdict == "right" else ft.Icons.CLOSE
        if current == verdict:  # 付けた方は塗った釦にして、どちらを付けたか一目で分かるように
            return ft.FilledTonalButton(t(verdict), icon=icon, on_click=lambda e, v=verdict: on_mark(v))
        return ft.TextButton(t(verdict), icon=icon, on_click=lambda e, v=verdict: on_mark(v))

    return ft.Row([button("right"), button("wrong")], spacing=4)


def hypotheses_controls(app, folder) -> list[ft.Control]:
    t = app.t
    h = Hypotheses.read(folder.hypotheses)
    out: list[ft.Control] = [theme.subheading(t("checks_h_hypotheses"))]
    if not h.lines:
        return [*out, theme.muted(t("checks_no_hypotheses"))]
    seen = latest_checks(folder)
    expect = {l.key: l.text for l in h.expect}

    def mark(key: str, verdict: str) -> None:
        h.mark(key, verdict)
        h.write(folder.hypotheses)
        app.refresh()

    for l in h.lines:
        rows: list[ft.Control] = [theme.body(f"{l.key}: {l.text}")]
        if l.key in seen:
            day, text = seen[l.key]
            rows.append(theme.muted(t("checks_seen", day=day, text=text)))
        elif "visible: no" in expect.get(l.key, ""):
            rows.append(theme.muted(t("checks_not_visible")))
        rows.append(verdict_buttons(app, lambda v, k=l.key: mark(k, v), l.verdict))
        out.append(ft.Column(rows, spacing=2))
    return out


def concepts_controls(app, folder) -> list[ft.Control]:
    t = app.t
    fc = concepts.FieldConcepts.load(folder)
    out: list[ft.Control] = [theme.subheading(t("checks_h_nouns")), theme.muted(t("checks_nouns_note"))]

    def mark(noun: str, verdict: str) -> None:
        concepts.mark(folder, noun, verdict)
        app.refresh()

    for c in fc.items:
        rows = [theme.body(f"{c.noun} — {c.target}"), theme.muted(c.last)]
        if c.active:
            rows.append(verdict_buttons(app, lambda v, n=c.noun: mark(n, v), c.verdict))
        else:
            rows.append(theme.muted(t("checks_noun_wrong", reason=c.reason or "-")))
        out.append(ft.Column(rows, spacing=2))
    return out


def build(app) -> list[ft.Control]:
    if getattr(app, "whole", False):
        return [ft.Text(app.t("checks_pick_field"), size=theme.BODY_SIZE)]
    folder = app.folder
    return [*hypotheses_controls(app, folder), ft.Divider(), *concepts_controls(app, folder)]
