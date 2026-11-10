# SPDX-License-Identifier: AGPL-3.0-or-later
"""読みの依頼に添える、この畑の物（11-11 に fieldnotes から）: 歩いた写真の位置（walk.py）、写真の覆い％（SAM 3.1）、
優占する草の読み（plants/）。手元の claude（local.prompt）と自分の鍵（direct.read_with_key）の両方が使う。

座標そのものは書かない（位置の語と距離だけ）。網には出ない。
"""

from __future__ import annotations

from pathlib import Path

from . import concepts, plants, walk
from .records import Folder, Observation


def walk_entries(folder: Folder, obs: Observation) -> list[dict]:
    """観察の写真ごとに file（名の幹）、time、lat、lon、facing（EXIF に無ければ None）。"""
    from . import photos

    out = []
    for rel in obs.photos:
        e = {"file": Path(rel).stem, "time": None, "lat": None, "lon": None, "facing": None}
        try:
            info = photos.exif_info(folder.root / rel)
        except (photos.PhotoError, OSError):
            info = None
        if info is not None:
            e.update(lat=info.lat, lon=info.lon, facing=info.heading)
            if info.taken:
                e["time"] = info.taken.strftime("%H:%M:%S")
        out.append(e)
    return out


def lines(folder: Folder, obs: Observation, previous: Observation | None = None) -> list[str]:
    """依頼に足す節（無ければ []）。"""
    out: list[str] = []
    entries = walk_entries(folder, obs)
    rings = walk.parcels(folder.root)
    if len(entries) > 1 or rings:
        lab = walk.labels(entries, rings)
        out += ["", "## 写真の位置（歩いた順。zone と emerging の行はこの語と (photos n, m) で書く）"]
        out.append(walk.frame_note(entries, rings))
        out += [f"- {e['file']}: {lab[e['file']]}" for e in entries]
    if obs.coverage:
        out += [
            "",
            f"## 写真の覆い％（{obs.cover_model or 'SAM'}。写真の何％をその句が覆ったか、写真の平均）",
            (
                "0 はその句が何にも当たらなかったということで、その草が無いということではない。"
                "basis には、割合が SAM の数か、写真からの読みかを書く。"
            ),
        ]
        for noun, pct in obs.coverage.items():
            rng = obs.cover_range.get(noun)
            out.append(f"- {noun}: {pct}%" + (f"（{rng[0]}〜{rng[1]}）" if rng else ""))
    species = concepts.species_in(previous) if previous is not None else []
    species = species or plants.species_of(folder)
    notes = plants.notes_for_prompt(folder, species)
    if notes:
        out += ["", "## 優占する草がなぜ優占するか（前に調べた読み。事実ではない。写真と照らす）", *notes]
    return out
