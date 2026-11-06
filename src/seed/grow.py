# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed grow — 計画の絵（仮説）。畑が季節ごとにどう見えるはずかを、線と色と字の図にする（設計書 §16.3 の 1 と 2）。

Claude（A の道は claude -p、C の道は Claude Code）がシナリオ（scenario.json）を書き、seed が検証して、
決まった語彙で SVG に描く。Claude は SVG を直接書かない。理由は設計書 §16.3。

- 場面の中身は、全部 plan.md の `## Plan` の行に対応する。対応しない場面と要素は落とし、理由を captions.md に書く。
- 図には「計画の絵（仮説）」の印を必ず焼く。写真と見間違えないよう、線と色と字だけ。ラスタ化しない。
- 出力は本人のフォルダーの grow/<日>/ だけ。seed publish では送らない。
- 本文に実在の地名が入っていないかは、seed には検証できない（手引きで書かせない）。
- 場面の `prompt`（英語、Claude が書く絵の指示）は `seed grow --draw`（draw.py）が halo に渡す。validate は有無を見ない。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from . import records as R
from .app.strings import s

MAX_SCENES = 6
MAX_SEE = 5
PREFIX_CHARS = 30  # from.text はこの字数（空白を詰めて）以上か、行が一つに決まるまで
PREFIX_MIN = 8  # 行が一つに決まっても、これより短い from.text は受けない（行がそれより短ければ行の全部）
STATES = ("uncut", "cut", "sown", "ridge", "bare")
MARK_KINDS = ("pool", "hole", "probe")
WHEN_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
COORD_RE = re.compile(
    r"-?\d{1,3}\.\d{4,}"
)  # 座標らしい数（小数 4 桁以上）。prompt に入っていれば prompt を落とす
WIDTH, HEIGHT = 1280, 720
DEPTH_MAX_CM = 50  # 断面の目盛の深さ
SCENARIO = "scenario.json"
CAPTIONS = "captions.md"

# 固定の色（写真に見えない、平らな塗り）
INK = "#222222"
MUTED = "#777777"
PAPER = "#fbfaf6"
MARK_RED = "#b3261e"
GREEN_DARK = "#3d6b35"
GREEN_LIGHT = "#8fbf6a"
BROWN_LIGHT = "#dcc7a1"
BROWN = "#8a6a3f"
BROWN_DARK = "#5b4326"
GREY = "#bdbdbd"
WATER = "#5b8fc7"
SOIL = "#e9dcc3"


# ---------------------------------------------------------------- 形


@dataclass
class Source:
    key: str
    text: str  # シナリオの from.text（行の先頭）


@dataclass
class Strip:
    state: str
    label: str
    width: float = 1.0
    crop: str | None = None
    rows: int = 0
    grass: str | None = None
    grass_cm: float | None = None


@dataclass
class MarkSign:
    kind: str
    label: str


@dataclass
class Root:
    name: str
    depth_cm: float


@dataclass
class Side:
    hard_layer: tuple[float, float | None] | None = None
    mulch_label: str | None = None
    mulch_cm: float | None = None
    ridge_cm: float | None = None
    roots: list[Root] = field(default_factory=list)
    holes_cm: float | None = None


@dataclass
class Scene:
    when: str
    title: str
    sources: list[Source]
    see: list[str]
    confidence: float
    unsure: str | None = None
    strips: list[Strip] = field(default_factory=list)
    marks: list[MarkSign] = field(default_factory=list)
    side: Side = field(default_factory=Side)
    prompt: str | None = None  # 絵の指示（英語、Claude が書く）。--draw だけが使う
    negative: str | None = None


@dataclass
class Skipped:
    scene: str  # 「2026-12 題」
    what: str | None  # 要素（None は場面ごと）
    reason: str


@dataclass
class Checked:
    scenes: list[Scene]
    skipped: list[Skipped]
    adjusted: list[Skipped]  # 確からしさを下げた所など、落とさずに直した物


# ---------------------------------------------------------------- 検証


def _norm(text: str) -> str:
    t = re.sub(r"\s+", "", str(text))
    return re.sub(r"(…|\.\.\.)$", "", t)


def _num(v, lo: float = 0, hi: float = 1000) -> float | None:
    if isinstance(v, bool) or not isinstance(v, int | float):
        return None
    return float(v) if lo <= v <= hi else None


def _str(v) -> str:
    return str(v).strip() if isinstance(v, str | int | float) and not isinstance(v, bool) else ""


def match_lines(plan: R.Plan, key: str, text: str) -> list[R.Line] | str:
    """from の一項に対応する `## Plan` の行。無ければ理由の語（no_from、short）。"""
    want = _norm(text)
    if not want:
        return "no_from"
    hits = [l for l in plan.reading if l.key == key and _norm(l.text).startswith(want)]
    if not hits:
        return "no_from"
    if any(len(want) < min(PREFIX_MIN, len(_norm(l.text))) for l in hits):
        return "short"
    if len(hits) > 1 and any(len(want) < min(PREFIX_CHARS, len(_norm(l.text))) for l in hits):
        return "short"
    return hits


def validate(scenario: dict, plan: R.Plan, max_scenes: int = MAX_SCENES) -> Checked:
    """シナリオを plan.md の行と照らす。対応しない場面と要素を落とし、理由を残す。理由の文は plan の言語。"""
    lg = plan.language
    skipped: list[Skipped] = []
    adjusted: list[Skipped] = []
    max_scenes = max(1, min(int(max_scenes), MAX_SCENES))
    raw = scenario.get("scenes") if isinstance(scenario, dict) else None
    good: list[Scene] = []
    for i, item in enumerate(raw if isinstance(raw, list) else [], 1):
        if not isinstance(item, dict):
            skipped.append(Skipped(f"#{i}", None, s("grow_reason_shape", lg)))
            continue
        scene = _scene(item, i, plan, skipped, adjusted)
        if scene is not None:
            good.append(scene)
    good.sort(key=lambda sc: sc.when)
    for sc in good[max_scenes:]:
        skipped.append(Skipped(_name(sc.when, sc.title), None, s("grow_reason_over", lg, max=max_scenes)))
    return Checked(good[:max_scenes], skipped, adjusted)


def _name(when: str, title: str) -> str:
    return f"{when} {title}".strip()


def _scene(item: dict, i: int, plan: R.Plan, skipped: list[Skipped], adjusted: list[Skipped]) -> Scene | None:
    lg = plan.language
    when, title = _str(item.get("when")), _str(item.get("title"))
    name = _name(when, title) or f"#{i}"
    if not WHEN_RE.match(when):
        skipped.append(Skipped(name, None, s("grow_reason_when", lg, when=when or "-")))
        return None
    if not title:
        skipped.append(Skipped(name, None, s("grow_reason_title", lg)))
        return None
    if R.DIRECTIVE_RE.search(title):
        skipped.append(Skipped(name, None, s("grow_reason_directive", lg)))
        return None
    froms = item.get("from")
    if not isinstance(froms, list) or not froms:
        skipped.append(Skipped(name, None, s("grow_reason_no_from_at_all", lg)))
        return None
    sources: list[Source] = []
    lines: list[R.Line] = []
    for f in froms:
        key = _str(f.get("key")) if isinstance(f, dict) else ""
        text = _str(f.get("text")) if isinstance(f, dict) else ""
        got = match_lines(plan, key, text)
        if isinstance(got, str):
            skipped.append(
                Skipped(name, None, s(f"grow_reason_{got}", lg, key=key or "-", text=text[:PREFIX_CHARS]))
            )
            return None
        if any(l.verdict == "wrong" for l in got):
            skipped.append(Skipped(name, None, s("grow_reason_wrong", lg, key=key, text=text[:PREFIX_CHARS])))
            return None
        sources.append(Source(key, text))
        lines += got
    words = "".join(_norm(l.text) for l in lines)

    def known(word: str) -> bool:
        return bool(_norm(word)) and _norm(word) in words

    conf = _num(item.get("confidence"), 0, 1)
    floor = min((l.confidence for l in lines if l.confidence is not None), default=None)
    if conf is None:
        conf = floor if floor is not None else 0.0
        adjusted.append(Skipped(name, "confidence", s("grow_reason_conf_missing", lg, to=f"{conf:.2f}")))
    elif floor is not None and conf > floor:
        adjusted.append(
            Skipped(name, "confidence", s("grow_reason_conf", lg, was=f"{conf:.2f}", to=f"{floor:.2f}"))
        )
        conf = floor

    see = []
    for t in item.get("see") or []:
        t = _str(t)
        if not t:
            continue
        if R.DIRECTIVE_RE.search(t):
            skipped.append(Skipped(name, t, s("grow_reason_directive", lg)))
            continue
        see.append(t)
    unsure = _str(item.get("unsure")) or None
    if unsure and R.DIRECTIVE_RE.search(unsure):
        skipped.append(Skipped(name, unsure, s("grow_reason_directive", lg)))
        unsure = None

    scene = Scene(when, title, sources, see, conf, unsure)
    prompt = _str(item.get("prompt")) or None
    if prompt and COORD_RE.search(prompt):
        adjusted.append(Skipped(name, "prompt", s("grow_reason_prompt_coord", lg)))
        prompt = None
    scene.prompt = prompt
    scene.negative = (_str(item.get("negative")) or None) if prompt else None
    top = item.get("top") if isinstance(item.get("top"), dict) else {}
    for st in top.get("strips") or []:
        strip = _strip(st, name, lg, known, skipped)
        if strip is not None:
            scene.strips.append(strip)
    for m in top.get("marks") or []:
        kind = _str(m.get("kind")) if isinstance(m, dict) else ""
        label = _str(m.get("label")) if isinstance(m, dict) else ""
        if kind not in MARK_KINDS:
            skipped.append(Skipped(name, label or kind, s("grow_reason_mark", lg, kind=kind or "-")))
            continue
        scene.marks.append(MarkSign(kind, label))
    side = item.get("side") if isinstance(item.get("side"), dict) else {}
    scene.side = _side(side, name, lg, known, skipped)
    return scene


def _strip(st, name: str, lg: str, known, skipped: list[Skipped]) -> Strip | None:
    if not isinstance(st, dict):
        skipped.append(Skipped(name, None, s("grow_reason_shape", lg)))
        return None
    state, label = _str(st.get("state")), _str(st.get("label"))
    if state not in STATES:
        skipped.append(Skipped(name, label or state, s("grow_reason_state", lg, state=state or "-")))
        return None
    width = _num(st.get("width"), 0.01, 100) or 1.0
    strip = Strip(state, label, width)
    crop = _str(st.get("crop"))
    if crop:
        if known(crop):
            strip.crop = crop
        else:
            skipped.append(Skipped(name, crop, s("grow_reason_word", lg, name=crop)))
    rows = st.get("rows")
    strip.rows = int(rows) if isinstance(rows, int) and not isinstance(rows, bool) and 0 < rows <= 12 else 0
    grass = st.get("grass") if isinstance(st.get("grass"), dict) else None
    if grass:
        gname = _str(grass.get("name"))
        if gname and known(gname):
            strip.grass, strip.grass_cm = gname, _num(grass.get("height_cm"), 0, 1000)
        elif gname:
            skipped.append(Skipped(name, gname, s("grow_reason_word", lg, name=gname)))
    return strip


def _side(side: dict, name: str, lg: str, known, skipped: list[Skipped]) -> Side:
    out = Side()
    hl = side.get("hard_layer_cm")
    if isinstance(hl, list) and len(hl) == 2:
        top = _num(hl[0], 0, 300)
        bottom = None if hl[1] is None else _num(hl[1], 0, 300)
        if top is not None and (hl[1] is None or (bottom is not None and bottom > top)):
            out.hard_layer = (top, bottom)
        else:
            skipped.append(Skipped(name, "hard_layer_cm", s("grow_reason_layer", lg)))
    elif hl is not None:
        skipped.append(Skipped(name, "hard_layer_cm", s("grow_reason_layer", lg)))
    mulch = side.get("mulch") if isinstance(side.get("mulch"), dict) else None
    if mulch:
        out.mulch_label = _str(mulch.get("label")) or None
        out.mulch_cm = _num(mulch.get("thickness_cm"), 0, 100)
    out.ridge_cm = _num(side.get("ridge_cm"), 1, 100)
    out.holes_cm = _num(side.get("holes_cm"), 1, 300)
    for r in side.get("roots") or []:
        rname = _str(r.get("name")) if isinstance(r, dict) else ""
        depth = _num(r.get("depth_cm"), 0, 1000) if isinstance(r, dict) else None
        if not rname or depth is None:
            skipped.append(Skipped(name, rname or "roots", s("grow_reason_shape", lg)))
        elif not known(rname):
            skipped.append(Skipped(name, rname, s("grow_reason_word", lg, name=rname)))
        else:
            out.roots.append(Root(rname, depth))
    return out


# ---------------------------------------------------------------- SVG


def _w(text: str, size: float) -> float:
    """字の幅の目安（全角は size、半角は 0.55 size）。"""
    return sum(size if ord(c) > 0x2000 else size * 0.55 for c in text)


def fit(text: str, px: float, size: float) -> str:
    """幅 px に収まるよう切って「…」。"""
    if _w(text, size) <= px:
        return text
    out = ""
    for c in text:
        if _w(out + c + "…", size) > px:
            break
        out += c
    return out + "…"


def _t(
    x: float,
    y: float,
    text: str,
    size: float = 16,
    fill: str = INK,
    anchor: str = "start",
    weight: str = "normal",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
        f' font-weight="{weight}">{escape(text)}</text>'
    )


def _rect(x, y, w, h, fill, stroke="none", sw=1, extra="") -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"'
        f' stroke="{stroke}" stroke-width="{sw}"{extra}/>'
    )


def _line(x1, y1, x2, y2, stroke=INK, sw=1, extra="") -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{extra}/>'


def wrap2(text: str, px: float, size: float) -> list[str]:
    """幅 px に収まらなければ二行に折る。二行でも余れば二行目を「…」で切る。"""
    if _w(text, size) <= px:
        return [text]
    first = ""
    for c in text:
        if _w(first + c, size) > px:
            break
        first += c
    return [first, fit(text[len(first) :], px, size)]


def _label2(x, y, text, w, size=14) -> list[str]:
    """筋の札。狭ければ二行（上の y から下へ）。"""
    lines = wrap2(text, w - 8, size)
    tw = max(_w(t, size) for t in lines) + 8
    lh = size + 4
    out = [_rect(x - tw / 2, y - size, tw, lh * len(lines) + 2, "#ffffff", extra=' fill-opacity="0.85"')]
    out += [_t(x, y + k * lh, t, size, anchor="middle") for k, t in enumerate(lines)]
    return out


def _label(x, y, text, w, size=14) -> list[str]:
    """白地の札に字（狭い筋でも読めるように）。"""
    text = fit(text, w - 8, size)
    tw = _w(text, size) + 8
    return [
        _rect(x - tw / 2, y - size, tw, size + 6, "#ffffff", extra=' fill-opacity="0.85"'),
        _t(x, y, text, size, anchor="middle"),
    ]


def _top_view(scene: Scene, lg: str) -> list[str]:
    x0, y0, w, h = 40, 118, 570, 330
    out = [_t(x0, 104, s("grow_top", lg), 15, MUTED)]
    out.append(_rect(x0, y0, w, h, PAPER, INK, 1.5))
    total = sum(st.width for st in scene.strips) or 1
    x = x0
    for st in scene.strips:
        sw = w * st.width / total
        out += _strip_svg(st, x, y0, sw, h, lg)
        x += sw
    if not scene.strips:
        out.append(_t(x0 + w / 2, y0 + h / 2, s("grow_no_strips", lg), 15, MUTED, "middle"))
    out.append(_rect(x0, y0, w, h, "none", INK, 1.5))
    # 印は図の下に、記号と札で
    mx, my = x0, y0 + h + 32
    for m in scene.marks:
        out += _mark_svg(m.kind, mx + 8, my - 5)
        label = fit(m.label, 170, 14)
        out.append(_t(mx + 22, my, label, 14))
        mx += 22 + _w(label, 14) + 18
        if mx > x0 + w - 60:
            break
    return out


def _strip_svg(st: Strip, x: float, y: float, w: float, h: float, lg: str) -> list[str]:
    out: list[str] = []
    cx = x + w / 2
    if st.state == "uncut":
        out.append(_rect(x, y, w, h, GREEN_DARK))
        step = 18
        for gy in range(int(y + 14), int(y + h - 6), step):
            for gx in range(int(x + 8), int(x + w - 6), step):
                off = 6 if (gy // step) % 2 else 0
                out.append(_line(gx + off, gy, gx + off - 3, gy - 10, GREEN_LIGHT, 1.5))
        if st.grass:
            g = st.grass if st.grass_cm is None else s("grow_grass", lg, name=st.grass, cm=f"{st.grass_cm:g}")
            out += _label(cx, y + h - 16, g, w)
    elif st.state == "cut":
        out.append(_rect(x, y, w, h, BROWN_LIGHT))
        for gy in range(int(y + 16), int(y + h - 6), 16):
            for gx in range(int(x + 8), int(x + w - 6), 14):
                out.append(_line(gx, gy, gx + 4, gy, BROWN, 1.2))
    elif st.state == "sown":
        out.append(_rect(x, y, w, h, BROWN_LIGHT))
        n = max(1, st.rows or 1)
        for k in range(n):
            rx = x + w * (k + 1) / (n + 1)
            out.append(_line(rx, y + 8, rx, y + h - 8, GREEN_DARK, 3, ' stroke-dasharray="4 7"'))
        if st.crop:
            out += _label(cx, y + h - 16, st.crop, w)
    elif st.state == "ridge":
        out.append(_rect(x, y, w, h, BROWN_LIGHT))
        n = max(1, int(w // 60))
        bw = w / (2 * n + 1)
        for k in range(n):
            out.append(_rect(x + bw * (2 * k + 1), y + 4, bw, h - 8, BROWN, BROWN_DARK, 1))
        if st.crop:
            out += _label(cx, y + h - 16, st.crop, w)
    else:  # bare
        out.append(_rect(x, y, w, h, GREY))
    out.append(_line(x, y, x, y + h, INK, 1))
    out += _label2(cx, y + 26, st.label, w)
    return out


def _mark_svg(kind: str, x: float, y: float) -> list[str]:
    if kind == "pool":
        return [
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="9" ry="5" fill="{WATER}" stroke="{INK}" stroke-width="1"/>'
        ]
    if kind == "hole":
        return [
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#ffffff" stroke="{INK}" stroke-width="1.5"/>',
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{INK}"/>',
        ]
    return [
        _line(x, y - 9, x, y + 7, INK, 2),
        f'<path d="M{x - 4:.1f},{y + 3:.1f} L{x:.1f},{y + 9:.1f} L{x + 4:.1f},{y + 3:.1f}" fill="{INK}"/>',
    ]


def _side_view(scene: Scene, lg: str) -> list[str]:
    side = scene.side
    x0, x1 = 740, 1240  # 土の幅
    ground = 210
    px = 4.6  # 1 cm の高さ
    bottom = ground + DEPTH_MAX_CM * px

    def y_of(cm: float) -> float:
        return ground + min(cm, DEPTH_MAX_CM) * px

    out = [_t(670, 104, s("grow_side", lg), 15, MUTED)]
    out.append(_rect(x0, ground, x1 - x0, bottom - ground, SOIL, INK, 1))
    if side.hard_layer:
        top, bot = side.hard_layer
        yb = y_of(bot) if bot is not None else min(y_of(top) + 12 * px, bottom)
        out.append(_rect(x0, y_of(top), x1 - x0, yb - y_of(top), "url(#hatch)"))
        out.append(_line(x0, y_of(top), x1, y_of(top), INK, 1))
        if bot is None:  # 下端は分からない: 斜線の下の縁を破線に
            out.append(_line(x0, yb, x1, yb, INK, 1.5, ' stroke-dasharray="6 5"'))
        else:
            out.append(_line(x0, yb, x1, yb, INK, 1))
        if bot is None:
            text = s("grow_layer_open", lg, top=f"{top:g}")
        else:
            text = s("grow_layer", lg, top=f"{top:g}", bottom=f"{bot:g}")
        out += _label(x1 - 170, y_of(top) + 20, text, 320, 14)
    # 目盛
    out.append(_line(x0 - 10, ground, x0 - 10, bottom, INK, 1))
    for cm in range(0, DEPTH_MAX_CM + 1, 10):
        y = y_of(cm)
        out.append(_line(x0 - 16, y, x0 - 10, y, INK, 1))
        out.append(_t(x0 - 20, y + 5, s("grow_cm", lg, cm=cm), 13, INK, "end"))
    # 畝
    ridge_x0, ridge_x1 = 880, 1100
    ridge_h = min(side.ridge_cm * px, 90) if side.ridge_cm else 0
    if ridge_h:
        out.append(
            f'<path d="M{ridge_x0},{ground} L{ridge_x0 + 30},{ground - ridge_h:.1f} L{ridge_x1 - 30},{ground - ridge_h:.1f} '
            f'L{ridge_x1},{ground} Z" fill="{SOIL}" stroke="{INK}" stroke-width="1"/>'
        )
        out.append(_t(ridge_x1 + 6, ground - ridge_h / 2, s("grow_ridge", lg, cm=f"{side.ridge_cm:g}"), 13))
    # 敷いた草
    if side.mulch_cm is not None or side.mulch_label:
        mh = max(4.0, min((side.mulch_cm or 3) * px * 0.6, 30))
        top_y = ground - ridge_h if ridge_h else ground
        if ridge_h:
            out.append(_rect(x0, ground - mh, ridge_x0 - x0, mh, "url(#straw)", BROWN, 1))
            out.append(
                _rect(ridge_x0 + 30, top_y - mh, ridge_x1 - ridge_x0 - 60, mh, "url(#straw)", BROWN, 1)
            )
            out.append(_rect(ridge_x1, ground - mh, x1 - ridge_x1, mh, "url(#straw)", BROWN, 1))
        else:
            out.append(_rect(x0, ground - mh, x1 - x0, mh, "url(#straw)", BROWN, 1))
        mtext = side.mulch_label or ""
        if side.mulch_cm is not None:
            mtext = f"{mtext} {s('grow_cm', lg, cm=f'{side.mulch_cm:g}')}".strip()
        out.append(_t(x0 + 8, ground + 18, fit(mtext, 300, 13), 13, BROWN_DARK))
    # 地表
    out.append(_line(x0 - 10, ground, x1 + 10, ground, INK, 2))
    # 穴
    if side.holes_cm:
        hx, hw = x1 - 50, 26
        out.append(_rect(hx, ground, hw, y_of(side.holes_cm) - ground, PAPER, INK, 1.5))
        out.append(
            _t(
                hx + hw / 2,
                y_of(side.holes_cm) + 18,
                s("grow_hole", lg, cm=f"{side.holes_cm:g}"),
                13,
                INK,
                "middle",
            )
        )
    # 根
    n = len(side.roots)
    span_x0, span_x1 = x0 + 40, x1 - 90
    for k, r in enumerate(side.roots):
        rx = span_x0 + (span_x1 - span_x0) * (k + 0.5) / max(n, 1)
        start = ground - ridge_h if ridge_h and ridge_x0 + 30 <= rx <= ridge_x1 - 30 else ground
        end = y_of(r.depth_cm)
        out.append(_line(rx, start - 26, rx, start, GREEN_DARK, 3))
        out.append(_line(rx, start, rx, end, BROWN_DARK, 2.5))
        out.append(_line(rx, end - 10, rx - 6, end - 2, BROWN_DARK, 1.5))
        out.append(_line(rx, end - 10, rx + 6, end - 2, BROWN_DARK, 1.5))
        depth = s("grow_cm", lg, cm=f"{r.depth_cm:g}")
        text = fit(f"{r.name} {depth}", (span_x1 - span_x0) / max(n, 1) + 30, 13)
        out.append(_t(rx, start - 32 - (k % 2) * 16, text, 13, INK, "middle"))
    return out


def render_scene(scene: Scene, index: int, language: str, meta: dict) -> str:
    """一場面の図（1280×720）。meta: model, day, since。"""
    lg = language
    out = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}"'
            f' font-family="sans-serif">'
        ),
        f"<title>{escape(s('grow_mark', lg) + ' ' + _name(scene.when, scene.title))}</title>",
        "<defs>",
        (
            f'<pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="10" height="10" fill="{BROWN_LIGHT}"/>{_line(0, 0, 0, 10, BROWN_DARK, 2)}</pattern>'
        ),
        (
            f'<pattern id="straw" width="12" height="6" patternUnits="userSpaceOnUse">'
            f'<rect width="12" height="6" fill="#e8d28a"/>{_line(0, 3, 9, 1, BROWN, 1)}</pattern>'
        ),
        "</defs>",
        _rect(0, 0, WIDTH, HEIGHT, PAPER),
    ]
    # 上の帯
    out.append(_rect(0, 0, WIDTH, 70, "#ffffff"))
    out.append(_line(0, 70, WIDTH, 70, INK, 1))
    mark = s("grow_mark", lg)
    mw = _w(mark, 20) + 24
    out.append(_rect(16, 16, mw, 38, "#ffffff", MARK_RED, 2.5))
    out.append(_t(16 + mw / 2, 42, mark, 20, MARK_RED, "middle", "bold"))
    out.append(_t(WIDTH / 2, 30, f"{index:02d}  {scene.when}", 18, MUTED, "middle"))
    out.append(_t(WIDTH / 2, 58, fit(scene.title, 760, 22), 22, INK, "middle", "bold"))
    out.append(_t(WIDTH - 20, 44, f"[{scene.confidence:.2f}]", 22, INK, "end"))
    out += _top_view(scene, lg)
    out.append(_line(640, 90, 640, 520, GREY, 1))
    out += _side_view(scene, lg)
    # 下の帯
    out.append(_line(0, 530, WIDTH, 530, INK, 1))
    y = 556
    out.append(_t(24, y, s("grow_see", lg), 15, MUTED))
    for t in scene.see[:MAX_SEE]:
        y += 24
        out.append(_t(40, y, "・" + fit(t, WIDTH - 80, 17), 17))
    if scene.unsure:
        y += 24
        out.append(_t(40, y, fit(s("grow_unsure", lg, text=scene.unsure), WIDTH - 80, 15), 15, MUTED))
    foot = s(
        "grow_footer",
        lg,
        model=meta.get("model") or "?",
        day=meta.get("day") or "?",
        since=meta.get("since") or "?",
    )
    out.append(_t(WIDTH - 16, HEIGHT - 10, foot, 12, MUTED, "end"))
    out.append("</svg>")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- 書く


def md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def svg_name(index: int, scene: Scene) -> str:
    return f"{index:02d}-{scene.when}.svg"


def captions_md(
    checked: Checked,
    language: str,
    meta: dict,
    pictures: dict[int, str] | None = None,
    notes: list[str] | None = None,
    tail: list[str] | None = None,
) -> str:
    """captions.md。pictures（順 → 絵の PNG の名）があれば列「絵」を足す。notes は冒頭の文の後、tail は最後の節（--draw）。"""
    lg = language
    out = [
        s("grow_md_title", lg, date=meta.get("day")),
        "",
        s("grow_md_about", lg),
        "",
        s("grow_md_from", lg, since=meta.get("since"), model=meta.get("model")),
        "",
    ]
    for n in notes or []:
        out += [n, ""]
    if pictures is None:
        out += [s("grow_md_head", lg), "|---|---|---|---|---|---|---|"]
    else:
        out += [s("grow_md_head_draw", lg), "|---|---|---|---|---|---|---|---|"]
    for i, sc in enumerate(checked.scenes, 1):
        src = "<br>".join(md_cell(f"{f.key}: {f.text.strip()[:PREFIX_CHARS]}") for f in sc.sources)
        see = "<br>".join(md_cell(t) for t in sc.see)
        if sc.unsure:
            see += ("<br>" if see else "") + md_cell(s("grow_unsure", lg, text=sc.unsure))
        name = svg_name(i, sc)
        pic = ""
        if pictures is not None:
            png = pictures.get(i)
            pic = f" [{png}]({png}) |" if png else " — |"
        out.append(
            f"| {i} | {sc.when} | {md_cell(sc.title)} | [{name}]({name}) |{pic} {src} | {see} | [{sc.confidence:.2f}] |"
        )
    out += ["", s("grow_md_skipped", lg), ""]
    items = [
        f"- {md_cell(k.scene)}" + (f" / {md_cell(k.what)}" if k.what else "") + f": {k.reason}"
        for k in checked.skipped
    ]
    out += items or [s("grow_md_none", lg)]
    out += ["", s("grow_md_adjusted", lg), ""]
    items = [f"- {md_cell(k.scene)}: {k.reason}" for k in checked.adjusted]
    out += items or [s("grow_md_none", lg)]
    out.append("")
    if tail:
        out += tail
        if out[-1] != "":
            out.append("")
    return "\n".join(out)


@dataclass
class Result:
    out: Path
    checked: Checked
    svgs: list[Path]
    captions: Path


def write(checked: Checked, out: Path, language: str, meta: dict) -> Result:
    """grow/<日>/ に SVG と captions.md を書く。前の回の SVG は消す（同じ日に描き直したとき）。"""
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("[0-9][0-9]-*.svg"):
        old.unlink()
    svgs = []
    for i, sc in enumerate(checked.scenes, 1):
        p = out / svg_name(i, sc)
        p.write_text(render_scene(sc, i, language, meta), encoding="utf-8")
        svgs.append(p)
    cap = out / CAPTIONS
    cap.write_text(captions_md(checked, language, meta), encoding="utf-8")
    return Result(out, checked, svgs, cap)


def output_dir(folder: R.Folder, day: str | None = None) -> Path:
    return folder.root / "grow" / (day or dt.date.today().isoformat())
