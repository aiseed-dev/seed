# SPDX-License-Identifier: AGPL-3.0-or-later
"""この土地の成り立ち。照会の data 行（place.md）と、昔の地図と空中写真（seed origin の絵）から。AI は使わない。

作者 2026-11-06「土壌や歴史が抜けていませんか？」。地質、地形、土、災害の区域、歴史、昔の地図と空中写真は
seed の元の考えの芯。アプリの「話す」では、やり取りの一番上（一番古い所）にこれを置き、昔 → 今 → 自分の観察を
一本の時の流れにする。

- data 行は四つにまとめる: 土地と地形（地名、筆、標高、地形）、土（土壌、地質）、水と災害の区域、歴史。
- 文の中の細かい座標は「…」にする（地名までは出してよい）。
- 昔の地図と空中写真は、記録のフォルダーの origin/<日>/frames/ の絵。地図を先に、空中写真を古い順に。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import records as R

GROUPS = (
    ("where", ("place_name", "parcel", "elevation", "landform")),
    ("soil", ("soil", "geology")),
    ("water", ("hazard",)),
    ("history", ("history",)),
)
DATA_SRC_RE = re.compile(r"^(?P<body>.*?)（出典: (?P<src>.+?)、確認日 (?P<day>\d{4}-\d{2}-\d{2})）$")
ERAS = ("1936", "1945", "1961", "1974", "1979", "1984", "1987", "latest")  # origin の空中写真の時代の順
ROW_RE = re.compile(r"^\| (?P<i>\d+) \| (?P<title>.*?) \| \[(?P<file>[^\]]+)\]\(frames/[^)]+\) \|")


@dataclass
class Fact:
    key: str
    body: str  # 本人の言語の文（細かい座標は外した物）
    source: str  # 出典（確認日）


@dataclass
class Group:
    key: str  # where, soil, water, history
    facts: list[Fact] = field(default_factory=list)


def scrub(text: str) -> str:
    """文の中の細かい座標（小数 3 桁以上の緯度経度の対）を「…」に。"""
    for c in R.fine_coords(text):
        text = text.replace(c, "…")
    return text


def facts(lines: list[R.Line], language: str) -> list[Fact]:
    """place.md の data 行 → Fact。日本語なら照会の英語の枠を日本語に（lookup_ja）。出典の無い行も文だけは使う。"""
    from .server import lookup_ja

    out = []
    for l in lines:
        m = DATA_SRC_RE.match(l.text.strip())
        body, src = (m["body"].strip(), f"{m['src'].strip()}（{m['day']}）") if m else (l.text.strip(), "")
        if lookup_ja.is_ja(language):
            body = lookup_ja.to_ja(body)
        out.append(Fact(l.key, scrub(body), src))
    return out


def summary(folder: R.Folder, language: str) -> list[Group]:
    """place.md の data 行を四つにまとめる（行の無い組は出さない）。知らない key の行は「土地と地形」の後ろに。"""
    fs = facts(folder.place_data(), language)
    known = {k for _, keys in GROUPS for k in keys}
    out = []
    for name, keys in GROUPS:
        g = Group(name, [f for k in keys for f in fs if f.key == k])
        if name == "where":
            g.facts += [f for f in fs if f.key not in known]
        if g.facts:
            out.append(g)
    return out


# ---------------------------------------------------------------- 昔の地図と空中写真（seed origin の絵）


@dataclass
class Frame:
    path: Path
    title: str
    name: str  # std-z11、photo-1961 など

    @property
    def era(self) -> str | None:
        return self.name.removeprefix("photo-") if self.name.startswith("photo-") else None


def origin_dir(folder: R.Folder) -> Path | None:
    """一番新しい origin/<日>/（frames が在る物）。"""
    root = folder.root / "origin"
    days = (
        sorted((d for d in root.iterdir() if d.is_dir() and (d / "frames").is_dir()), reverse=True)
        if root.is_dir()
        else []
    )
    return days[0] if days else None


def frames(folder: R.Folder) -> list[Frame]:
    """絵の並び: 地図（標準、標高、地形、土、災害、史跡）を先に、空中写真を古い順に。本人の写真の場面は入れない。"""
    d = origin_dir(folder)
    if d is None:
        return []
    titles: dict[str, str] = {}
    cap = d / "captions.md"
    if cap.is_file():
        for line in cap.read_text(encoding="utf-8").splitlines():
            m = ROW_RE.match(line)
            if m:
                titles[m["file"]] = m["title"].replace("\\|", "|")
    out = []
    for p in sorted((d / "frames").glob("*.png")):
        name = re.sub(r"^\d+-", "", p.stem)
        if name == "own":
            continue
        out.append(Frame(p, titles.get(p.name, name), name))
    maps = [f for f in out if f.era is None]
    photos = sorted(
        (f for f in out if f.era is not None), key=lambda f: ERAS.index(f.era) if f.era in ERAS else len(ERAS)
    )
    return maps + photos


def make_frames(folder: R.Folder, language: str, fetch=None) -> list[Frame]:
    """昔の地図と空中写真の絵を作る（動画は作らない）。座標の在る観察が無ければ []。fetch はテストで差し替える。"""
    from . import origin

    plan = origin.make_plan(folder, language)
    if plan is None:
        return []
    day = dt.date.today().isoformat()
    out = folder.root / "origin" / day
    own = fetch is None
    fetch = fetch or origin.HttpFetch()
    try:
        tiles = origin.Tiles(folder.root / "origin" / "tiles", fetch)
        origin.run(plan, tiles, origin.Fonts(origin.find_font()), out, day=day, video=False)
    finally:
        if own:
            fetch.close()
    return frames(folder)


# ---------------------------------------------------------------- 照会（まだ data 行が無い時）


def center(folder: R.Folder) -> tuple[float, float] | None:
    """座標の在る一番新しい観察の中心。"""
    for path in reversed(folder.list_observations()):
        try:
            obs = R.Observation.read(path)
        except (ValueError, TypeError, OSError):
            continue
        if obs.location and obs.location.get("center"):
            lat, lon = obs.location["center"]
            return float(lat), float(lon)
    return None
