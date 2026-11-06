# SPDX-License-Identifier: AGPL-3.0-or-later
"""写真の整理（アプリの仕事。文字の細かい作業は Claude Code、写真はアプリ）。

外した写真は消さない。記録のフォルダーの photos/removed/ に、同じ日のフォルダーの形で移す。
`seed prune` はここを消さない。要らなければ本人がフォルダーごと消す。観察の読みの行は書き換えない
（外した写真を指す行は、写真無しで文だけになる）。前書きの写真の一覧と、座標の広がり（location）だけを直す。
"""

from __future__ import annotations

import datetime as dt
import functools
import math
import shutil
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path

from . import photos
from .records import Folder, Observation

REMOVED = "removed"  # photos/ の下の片付け用の場所


def removed_dir(folder: Folder) -> Path:
    return folder.photos / REMOVED


def removed_path(folder: Folder, rel: str) -> Path:
    """外した写真の置き場。photos/2026-11-02/153402.jpg → photos/removed/2026-11-02/153402.jpg。"""
    inside = Path(rel).relative_to("photos") if Path(rel).parts[:1] == ("photos",) else Path(rel)
    return removed_dir(folder) / inside


def _relocate(folder: Folder, obs: Observation) -> None:
    infos = []
    for r in obs.photos:
        try:
            infos.append(photos.exif_info(folder.root / r))
        except (photos.PhotoError, OSError):
            continue
    obs.location = photos.location(infos) if infos else None


def remove_photo(folder: Folder, obs: Observation, rel: str) -> int:
    """観察から写真を外し、ファイルを片付け用の場所へ移す。返すのは元の並びの位置（戻す時に使う）。

    同じ写真をほかの観察も使っていれば、ファイルは動かさない。
    """
    index = obs.photos.index(rel)
    obs.photos.pop(index)
    used = False
    for p in folder.list_observations():
        if p.name == obs.filename:
            continue
        try:
            if rel in Observation.read(p).photos:
                used = True
                break
        except (ValueError, TypeError, OSError):
            continue
    src = folder.root / rel
    if not used and src.exists():
        dst = removed_path(folder, rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
    _relocate(folder, obs)
    obs.write(folder.observation_path(obs))
    return index


def restore_photo(folder: Folder, obs: Observation, rel: str, index: int | None = None) -> None:
    """外した写真を戻す（ファイルを元の場所へ、前書きの一覧の元の位置へ）。"""
    src = removed_path(folder, rel)
    dst = folder.root / rel
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
    if rel not in obs.photos:
        obs.photos.insert(len(obs.photos) if index is None else min(index, len(obs.photos)), rel)
    _relocate(folder, obs)
    obs.write(folder.observation_path(obs))


@functools.lru_cache(maxsize=512)
def _has_coord(path: str, mtime_ns: int, size: int) -> bool:
    try:
        return photos.exif_info(Path(path)).has_coord
    except (photos.PhotoError, OSError):
        return False


def has_coord(path: Path) -> bool:
    """写真に位置が入っているか（道・更新時刻・大きさを鍵に覚えておく）。"""
    try:
        st = Path(path).stat()
    except OSError:
        return False
    return _has_coord(str(path), st.st_mtime_ns, st.st_size)


# ---------------------------------------------------------------- 写真を場所ごとに、時の順に（AI は使わない）
#
# 写真に入っている座標で、近い物（SPOT_M ほど）を一つの「撮った場所」にまとめ、場所ごとに撮った時の順に並べる。
# 場所は細かい座標でなく「中心から北西へ 44 m」の様に言う。座標の無い写真は「位置なし」にまとめる。
# 同じ物かどうかは、座標と向きだけでは決まらない（同じ場所で近くの物を何枚も撮る）。それは写真を見る Claude の仕事。

SPOT_M = 20.0


@dataclass
class Shot:
    rel: str  # 記録のフォルダーからの相対の道
    taken: dt.datetime
    lat: float | None = None
    lon: float | None = None
    heading: float | None = None


@dataclass
class Spot:
    number: int  # 1 から。位置なしは 0
    shots: list[Shot] = field(default_factory=list)
    where: tuple[float, float] | None = None  # (北へ m, 東へ m)。全体の中心から

    def center(self) -> tuple[float, float]:
        pts = [(s.lat, s.lon) for s in self.shots if s.lat is not None and s.lon is not None]
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _metres(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """b から a への（北へ m, 東へ m）。近い所だけなので平面で足りる。"""
    k = math.cos(math.radians((a[0] + b[0]) / 2))
    return (a[0] - b[0]) * 111_320, (a[1] - b[1]) * 111_320 * k


def all_shots(folder: Folder) -> list[Shot]:
    """観察の写真を全部（同じ写真は一度）。撮った時は EXIF、無ければ観察の日と時刻。"""
    seen: set[str] = set()
    out: list[Shot] = []
    for p in folder.list_observations():
        try:
            obs = Observation.read(p)
        except (ValueError, TypeError, OSError):
            continue
        for rel in obs.photos:
            if rel in seen or not (folder.root / rel).exists():
                continue
            seen.add(rel)
            try:
                info = photos.exif_info(folder.root / rel)
            except (photos.PhotoError, OSError):
                info = None
            when = (info.taken if info else None) or dt.datetime.fromisoformat(f"{obs.date}T{obs.time}")
            out.append(
                Shot(
                    rel,
                    when,
                    info.lat if info else None,
                    info.lon if info else None,
                    info.heading if info else None,
                )
            )
    return out


def by_place(folder: Folder, within_m: float = SPOT_M) -> list[Spot]:
    """撮った場所ごと（見つかった順に 1, 2, …）に、時の順。最後に位置なし（在れば）。"""
    shots = sorted(all_shots(folder), key=lambda s: (s.taken, s.rel))
    spots: list[Spot] = []
    nowhere = Spot(0)
    for s in shots:
        if s.lat is None or s.lon is None:
            nowhere.shots.append(s)
            continue
        for sp in spots:
            if math.hypot(*_metres((s.lat, s.lon), sp.center())) < within_m:
                sp.shots.append(s)
                break
        else:
            spots.append(Spot(len(spots) + 1, [s]))
    if spots:
        pts = [sp.center() for sp in spots for _ in sp.shots]
        mid = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        for sp in spots:
            sp.where = _metres(sp.center(), mid)
    return spots + ([nowhere] if nowhere.shots else [])


def where_text(spot: Spot, language: str) -> str:
    """「中心から北西へ 44 m」。位置なしは「位置なし」。"""
    ja = language == "ja"
    if spot.where is None:
        return "位置なし" if ja else "no location"
    north, east = spot.where
    dist = math.hypot(north, east)
    if dist < 1:
        return "中心" if ja else "the center"
    word = photos.direction_word(math.degrees(math.atan2(east, north)) % 360, language)
    return f"中心から{word}へ {dist:.0f} m" if ja else f"{dist:.0f} m {word} of the center"


def spot_heading(sp: Spot, language: str) -> str:
    """場所の一行: 番号、枚数、どこか、向き（在れば）。"""
    ja = language == "ja"
    order = photos.COMPASS.get(language, photos.COMPASS["en"])
    facing = sorted(
        {photos.direction_word(s.heading, language) for s in sp.shots if s.heading is not None},
        key=order.index,
    )
    if sp.number:
        head = (
            f"場所 {sp.number}: {len(sp.shots)} 枚、{where_text(sp, language)}"
            if ja
            else f"Place {sp.number}: {len(sp.shots)} photos, {where_text(sp, language)}"
        )
    else:
        head = f"位置なし: {len(sp.shots)} 枚" if ja else f"No location: {len(sp.shots)} photos"
    if facing:
        head += f"、向き {'・'.join(facing)}" if ja else f", facing {'/'.join(facing)}"
    return head


def days(sp: Spot) -> list[tuple[str, list[Shot]]]:
    """場所の写真を日ごとに（時の順）。"""
    return [(d, list(g)) for d, g in groupby(sp.shots, key=lambda s: s.taken.date().isoformat())]


def render_places(spots: list[Spot], language: str) -> str:
    """seed photos --by-place の文。場所の一行と、日ごとの写真の道。"""
    lines: list[str] = []
    for sp in spots:
        lines.append(spot_heading(sp, language))
        lines += [f"  {d}: " + ", ".join(s.rel for s in group) for d, group in days(sp)]
    return "\n".join(lines)
