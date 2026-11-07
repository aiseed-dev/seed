# SPDX-License-Identifier: AGPL-3.0-or-later
"""プラグイン procedure（手続き）。"""

from __future__ import annotations

import asyncio

import flet as ft
import pytest
from test_app import FakePage, texts, walk

from seed import procedure
from seed.app import plugins
from seed.app.main import App
from seed.plugins import procedure as P


@pytest.fixture(autouse=True)
def no_lookup(monkeypatch):
    from seed import lookup as L

    monkeypatch.setattr(L, "available", lambda: False)


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


def test_listed_between_land_and_weather(app):
    assert [p.name for p in plugins.shipped()] == ["land", "procedure", "weather"]
    (p,) = [p for p in app.plugins if p.name == "procedure"]
    assert p.route == "/p/procedure" and p.title["ja"] == "手続き"


def test_road_parsed_from_chapter(app):
    steps = P.road(app.folder)
    names = [n for n, _ in steps]
    assert len(steps) in (7, 8) and all(line for _, line in steps)
    assert names[-1].startswith("その次") and "候補地の観察" in names
    assert any(n.startswith("手続き") for n in names)


def test_road_includes_zero_step(app, seedfolder):
    sk = seedfolder / "skill"
    sk.mkdir(exist_ok=True)
    (sk / "SKILL.md").write_text("x", encoding="utf-8")
    (sk / "13-手続きと農地.md").write_text(
        "## 読み方\n\n### 〇 貸し農園から始める\n\nまず貸し農園で始めます。次の文。\n\n"
        "### 一 候補地の観察\n\n- 本人がすること: 道から撮る。人の土地に入らない\n",
        encoding="utf-8",
    )
    assert P.road(app.folder) == [
        ("貸し農園から始める", "まず貸し農園で始めます"),
        ("候補地の観察", "道から撮る"),
    ]


def test_none_then_make(app, seedfolder):
    ctrls = P.build(app)
    assert any(c.value == app.t("procedure_none") for c in ctrls if isinstance(c, ft.Text))
    (btn,) = [c for c in ctrls if isinstance(c, ft.FilledTonalButton)]
    asyncio.run(btn.on_click(None))
    assert (seedfolder / "procedures" / "nochi-3jo" / "checklist.md").is_file()
    assert app.page.dialogs


def test_with_procedures(app, seedfolder):
    procedure.nochi_3jo(app.folder)
    ctrls = P.build(app)
    boxes = [b for c in ctrls for b in walk(c) if isinstance(b, ft.Checkbox)]
    assert len(boxes) == len(procedure.CHECKLIST)
    assert any(isinstance(b, ft.Markdown) and "applicant" in b.value for c in ctrls for b in walk(c))
    spans = [sp for c in ctrls for b in walk(c) if isinstance(b, ft.Text) for sp in b.spans or []]
    assert len(spans) == len(procedure.SOURCES) - 1 and all(sp.url.startswith("https://") for sp in spans)

    path = seedfolder / "procedures" / "nochi-3jo" / "checklist.md"
    before = path.read_text(encoding="utf-8").split("\n")
    boxes[1].value = True

    class E:
        control = boxes[1]

    boxes[1].on_change(E())
    after = path.read_text(encoding="utf-8").split("\n")
    diff = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert len(diff) == 1 and diff[0][1].startswith("- [x] application: ")
    assert texts(ft.Column(P.build(app)))  # 描き直しても読める
