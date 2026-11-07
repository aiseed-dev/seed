# SPDX-License-Identifier: AGPL-3.0-or-later
"""天気の図（SVG）。純 Python で書き、外の図の部品は使わない。

描き方は同じ作者の weatherlib/svgchart.py（雨温図、当日の時系列）に倣う: 色、グリッド #e8edf2、
軸の字 #666、枠 #c8d2dc、目盛りは _nice_step、線は None で切り、積算量の棒は 0 から。
図は縮めずに幅を決めて描く（スマートフォンでは横に動かして見る）。
"""

from __future__ import annotations

import datetime as dt
import functools
import math

from .weather import Forecast, Hour

C_TMAX, C_TAVG, C_TMIN, C_RAIN = "#F92500", "#008000", "#0C00CC", "#1987E5"
C_SUN, C_WIND = "#e0a800", "#7a8896"
C_SOIL_T = ("#8b5a2b", "#a0522d", "#cd853f", "#deb887")
C_SOIL_M = ("#08306b", "#2171b5", "#4292c6", "#6baed6", "#9ecae1")
FONT = 'font-family="Helvetica Neue, Arial, Hiragino Sans, Noto Sans CJK JP, Meiryo, sans-serif"'
WEEKDAYS = {"ja": "月火水木金土日", "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}
LABELS = {
    "ja": {
        "rain": "降水 mm", "prob": "降水確率 %", "temp": "気温 ℃", "rh": "湿度 %", "tmax": "最高", "tmin": "最低",
        "sun": "日照 h", "et0": "蒸発散 ET₀ mm", "wind": "風 m/s", "gust": "突風", "hour": "{h}時",
        "soil_t": "地温 ℃", "soil_m": "水分 m³/m³",
    },
    "en": {
        "rain": "rain mm", "prob": "rain chance %", "temp": "temp ℃", "rh": "humidity %", "tmax": "max", "tmin": "min",
        "sun": "sunshine h", "et0": "ET₀ mm", "wind": "wind m/s", "gust": "gusts", "hour": "{h}h",
        "soil_t": "soil temp ℃", "soil_m": "moisture m³/m³",
    },
}  # fmt: skip


def _nice_step(lo: float, hi: float, target: int = 6) -> float:
    """目盛りの間隔を値域から決める（桁は log10 で取る）。"""
    span = hi - lo
    if span <= 0:
        span = max(abs(hi) * 0.02, 1.0)
    raw = span / target
    mag = 10.0 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= mag * m:
            return mag * m
    return mag * 10


def _line_runs(xs, vals):
    """None で切った (x, v) の連なり。"""
    runs, cur = [], []
    for x, v in zip(xs, vals, strict=False):
        if v is None:
            if cur:
                runs.append(cur)
            cur = []
        else:
            cur.append((x, v))
    if cur:
        runs.append(cur)
    return runs


def _axis(vals, zero: bool = False) -> tuple[float, float, float]:
    vals = [v for v in vals if v is not None]
    lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
    if zero:
        lo = 0.0
    step = _nice_step(lo, hi)
    v_lo = 0.0 if zero else math.floor(lo / step) * step - step
    v_hi = math.floor(hi / step) * step + step
    if v_hi <= v_lo:
        v_hi = v_lo + step
    return v_lo, v_hi, step


def _fmt(step: float) -> str:
    return "{:.0f}" if step >= 1 else "{:.2f}" if step < 0.1 else "{:.1f}"


class _Panel:
    """一枚の図。左右の軸、棒、線、凡例。x は 0〜n-1 の番号。"""

    def __init__(self, width, height, n, left=None, right=None, ml=48, mr=48, mt=34, mb=46):
        # left / right = (値の並び, 単位, 色, 0 起点か)。無ければ None
        self.w, self.h, self.n = width, height, max(n, 1)
        self.ml, self.mt = ml, mt
        self.pw, self.ph = width - ml - mr, height - mt - mb
        self.e: list[str] = []
        self.ax = {}
        for side, spec in (("l", left), ("r", right)):
            if spec is not None:
                vals, unit, color, zero = spec
                self.ax[side] = (*_axis(vals, zero), unit, color)
        self._grid()

    def x(self, i: float) -> float:
        return self.ml + self.pw * (i + 0.5) / self.n

    def y(self, v: float, side: str = "l") -> float:
        v_lo, v_hi = self.ax[side][:2]
        return self.mt + self.ph * (v_hi - v) / (v_hi - v_lo)

    def ypct(self, v: float) -> float:
        return self.mt + self.ph * (1 - min(max(v, 0), 100) / 100)

    def text(self, x, y, s, anchor="middle", fill="#666", size=11):
        self.e.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" fill="{fill}" {FONT}>{s}</text>'
        )

    def _grid(self) -> None:
        main = "l" if "l" in self.ax else "r" if "r" in self.ax else None
        for side in ("l", "r"):
            if side not in self.ax:
                continue
            v_lo, v_hi, step, _unit, color = self.ax[side]
            f = _fmt(step)
            t, guard = v_lo, 0
            while t <= v_hi + 1e-9 and guard < 40:
                guard += 1
                yy = self.y(t, side)
                if side == main:
                    self.e.append(
                        f'<line x1="{self.ml}" y1="{yy:.1f}" x2="{self.ml + self.pw}" y2="{yy:.1f}" '
                        f'stroke="{"#999" if abs(t) < 1e-9 else "#e8edf2"}"/>'
                    )
                if side == "l":
                    self.text(self.ml - 5, yy + 4, f.format(t), "end", color)
                else:
                    self.text(self.ml + self.pw + 5, yy + 4, f.format(t), "start", color)
                t += step

    def bars(self, vals, side="r", color=C_RAIN, opacity=0.85) -> None:
        bw = max(self.pw / self.n * 0.7, 1.0)
        for i, v in enumerate(vals):
            if v is None or v <= 0:
                continue
            top = self.y(v, side)
            self.e.append(
                f'<rect x="{self.x(i) - bw / 2:.1f}" y="{top:.1f}" width="{bw:.1f}" '
                f'height="{self.mt + self.ph - top:.1f}" fill="{color}" fill-opacity="{opacity}"/>'
            )

    def line(self, vals, side="l", color=C_TMAX, width=2.0, dash="", dots=False, pct=False) -> None:
        ym = self.ypct if pct else (lambda v: self.y(v, side))
        for run in _line_runs([self.x(i) for i in range(len(vals))], vals):
            pts = [(px, ym(v)) for px, v in run]
            d = " ".join(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}" for k, (px, py) in enumerate(pts))
            da = f' stroke-dasharray="{dash}"' if dash else ""
            self.e.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da}/>')
            if dots:
                self.e += [f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.8" fill="{color}"/>' for px, py in pts]

    def tick(self, i: int, label: str, row: int = 0, line: bool = False, anchor="middle") -> None:
        x = self.x(i)
        if line:
            self.e.append(
                f'<line x1="{x:.1f}" y1="{self.mt}" x2="{x:.1f}" y2="{self.mt + self.ph}" stroke="#d3dae2"/>'
            )
        self.text(x, self.mt + self.ph + 15 + 14 * row, label, anchor)

    def legend(self, items) -> None:
        x = self.ml + 8
        for label, color, kind in items:
            w = 24 + len(label) * 11
            if kind == "bar":
                self.e.append(
                    f'<rect x="{x}" y="{self.mt + 6}" width="10" height="10" fill="{color}" fill-opacity="0.85"/>'
                )
            else:
                da = ' stroke-dasharray="4 3"' if kind == "dash" else ""
                self.e.append(
                    f'<line x1="{x}" y1="{self.mt + 11}" x2="{x + 14}" y2="{self.mt + 11}" stroke="{color}" stroke-width="2"{da}/>'
                )
            self.text(x + 18, self.mt + 15, label, "start", "#333")
            x += w

    def body(self) -> str:
        frame = f'<rect x="{self.ml}" y="{self.mt}" width="{self.pw}" height="{self.ph}" fill="none" stroke="#c8d2dc"/>'
        return "".join([*self.e, frame])


def _svg(width: int, height: int, panels: list[_Panel]) -> str:
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
    ]
    y = 0
    for p in panels:
        out.append(f'<g transform="translate(0,{y})">{p.body()}</g>')
        y += p.h
    out.append("</svg>")
    return "".join(out)


def day_label(date: str, language: str) -> tuple[str, str]:
    """（11/8, 土）。"""
    d = dt.date.fromisoformat(date[:10])
    wd = WEEKDAYS["ja" if language == "ja" else "en"][d.weekday()]
    return f"{d.month}/{d.day}", f"（{wd}）" if language == "ja" else wd


def hourly_svg(hours: dict[str, list[Hour]], now: dt.datetime, language: str) -> str:
    """今日と明日: 今の時から明日の終わりまで。降水量の棒、降水確率、気温、湿度。"""
    lab = LABELS["ja" if language == "ja" else "en"]
    tomorrow = now.date() + dt.timedelta(days=1)
    seq: list[Hour] = []
    for date, first in ((now.date(), now.hour), (tomorrow, 0)):
        seq += [h for h in hours.get(date.isoformat(), []) if int(h.time[11:13]) >= first]
    if not seq:
        return ""
    width, height = max(420, 96 + 20 * len(seq)), 240
    p = _Panel(
        width,
        height,
        len(seq),
        left=([h.temp for h in seq], "℃", C_TMAX, False),
        right=([h.rain for h in seq], "mm", C_RAIN, True),
    )
    for i, h in enumerate(seq):
        hh = int(h.time[11:13])
        if hh % 3 == 0:
            p.tick(i, lab["hour"].format(h=hh), line=hh == 0)
        if hh == 0 or i == 0:
            if i == 0 and any(int(x.time[11:13]) == 0 for x in seq[1:4]):
                continue
            md, wd = day_label(h.time, language)
            p.tick(
                i,
                f"{md}{wd}" if language == "ja" else f"{wd} {md}",
                row=1,
                anchor="start" if i == 0 else "middle",
            )
    p.bars([h.rain for h in seq])
    p.line([h.rain_prob for h in seq], color=C_RAIN, width=1.2, dash="4 3", pct=True)
    p.line([h.humidity for h in seq], color=C_TAVG, width=1.2, pct=True)
    p.line([h.temp for h in seq], color=C_TMAX, width=2.2)
    p.legend(
        [
            (lab["temp"], C_TMAX, "line"),
            (lab["rain"], C_RAIN, "bar"),
            (lab["prob"], C_RAIN, "dash"),
            (lab["rh"], C_TAVG, "line"),
        ]
    )
    return _svg(width, height, [p])


def _day_ticks(p: _Panel, rows: list[Forecast], language: str) -> None:
    for i, f in enumerate(rows):
        md, wd = day_label(f.date, language)
        p.tick(i, md)
        p.text(p.x(i), p.mt + p.ph + 29, wd, fill="#888")


def daily_svg(rows: list[Forecast], language: str) -> str:
    """二週間: 最高・最低気温の線と点、降水量の棒。"""
    lab = LABELS["ja" if language == "ja" else "en"]
    if not rows:
        return ""
    width, height = 96 + 46 * len(rows), 240
    temps = [f.tmax for f in rows] + [f.tmin for f in rows]
    p = _Panel(
        width,
        height,
        len(rows),
        left=(temps, "℃", C_TMAX, False),
        right=([f.rain for f in rows], "mm", C_RAIN, True),
    )
    _day_ticks(p, rows, language)
    p.bars([f.rain for f in rows])
    p.line([f.tmax for f in rows], color=C_TMAX, dots=True)
    p.line([f.tmin for f in rows], color=C_TMIN, dots=True)
    p.legend([(lab["tmax"], C_TMAX, "line"), (lab["tmin"], C_TMIN, "line"), (lab["rain"], C_RAIN, "bar")])
    return _svg(width, height, [p])


def work_svg(rows: list[Forecast], language: str) -> str:
    """作業の目安: 日照（棒）と蒸発散（線）、その下に風（最大と突風）。"""
    lab = LABELS["ja" if language == "ja" else "en"]
    if not rows:
        return ""
    width, height = 96 + 46 * len(rows), 240
    top = _Panel(
        width,
        height,
        len(rows),
        left=([f.sunshine_h for f in rows], "h", C_SUN, True),
        right=([f.et0 for f in rows], "mm", C_TAVG, True),
    )
    _day_ticks(top, rows, language)
    top.bars([f.sunshine_h for f in rows], side="l", color=C_SUN)
    top.line([f.et0 for f in rows], side="r", color=C_TAVG, dots=True)
    top.legend([(lab["sun"], C_SUN, "bar"), (lab["et0"], C_TAVG, "line")])
    wind = _Panel(
        width, height, len(rows), left=([f.gust for f in rows] + [f.wind for f in rows], "m/s", C_WIND, True)
    )
    _day_ticks(wind, rows, language)
    wind.line([f.gust for f in rows], color=C_WIND, width=1.6, dash="4 3", dots=True)
    wind.line([f.wind for f in rows], color=C_WIND, dots=True)
    wind.legend([(lab["wind"], C_WIND, "line"), (lab["gust"], C_WIND, "dash")])
    return _svg(width, height * 2, [top, wind])


def soil_svg(soil_hours: list[tuple[str, dict, dict]], language: str) -> str:
    """土: 七日分の時ごとの地温（四つの深さ）と水分（五つの深さ）。soil_hours = [(時, 地温, 水分)]。"""
    lab = LABELS["ja" if language == "ja" else "en"]
    if not soil_hours:
        return ""
    width, height = 960, 240
    n = len(soil_hours)
    temp_keys = list(soil_hours[0][1])
    moist_keys = list(soil_hours[0][2])
    panels = []
    for idx, (keys, colors, name, unit, pos) in enumerate(
        ((temp_keys, C_SOIL_T, "soil_t", "℃", 1), (moist_keys, C_SOIL_M, "soil_m", "", 2))
    ):
        series = [[row[pos].get(k) for row in soil_hours] for k in keys]
        p = _Panel(width, height, n, left=([v for s in series for v in s], unit, "#555", False))
        for i, row in enumerate(soil_hours):
            hh = int(row[0][11:13])
            if hh == 0:
                md, wd = day_label(row[0], language)
                p.tick(i, lab["hour"].format(h=0), line=True)
                p.tick(i, f"{md}{wd}" if language == "ja" else f"{wd} {md}", row=1, anchor="start")
            elif hh == 12:
                p.tick(i, lab["hour"].format(h=hh))
        for s, c in zip(series, colors, strict=False):
            p.line(s, color=c, width=1.8)
        p.legend([(f"{k}", c, "line") for k, c in zip(keys, colors, strict=False)])
        p.text(p.ml + p.pw, p.mt - 8, lab[name], "end", "#333")
        panels.append(p)
    return _svg(width, height * 2, panels)


def size(svg: str) -> tuple[int, int]:
    """図の幅と高さ（描いた大きさ）。"""
    import re

    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    return (int(m[1]), int(m[2])) if m else (640, 240)


@functools.lru_cache(maxsize=16)
def png(svg: str, scale: int = 2) -> bytes | None:
    """SVG を PNG に（resvg。文字を描ける）。resvg が無ければ None。"""
    try:
        import resvg_py
    except ImportError:
        return None
    w, h = size(svg)
    try:
        return bytes(
            resvg_py.svg_to_bytes(svg_string=svg, width=w * scale, height=h * scale, background="#ffffff")
        )
    except Exception:  # noqa: BLE001
        return None
