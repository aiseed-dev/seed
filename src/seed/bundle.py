# SPDX-License-Identifier: AGPL-3.0-or-later
"""まとめて入れる（PC のアプリの「写真を足す」）。写真、動画（mp4 など）、zip。

作者 2026-11-07「zipでまとめていれたいので、zipにも対応させて」「動画は単独でいれることもあるので、mp4に対応して」。

- zip の中からは写真と動画だけを取り出す。zip の中のフォルダーの道は使わず、名だけで一時の場所に書く（外に書かない）。
- 写真は、撮った日ごとに 6 枚ずつの観察にする（一度に読める数）。
- 動画は記録の videos/<日>/<時刻>.<拡張子> に置き、撮った時と所を同じ名の .json に書く。
  時は動画の mvhd（UTC）、所は moov/udta/©xyz（標準のカメラが書く ISO 6709 の文字）。無ければファイルの時刻。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import photos

PHOTO_EXT = (".jpg", ".jpeg", ".png", ".heic", ".heif")
VIDEO_EXT = (".mp4", ".mov", ".m4v")
ZIP_EXT = (".zip",)
MEMBER_MAX = 4 * 1024**3  # zip の中の一つ
TOTAL_MAX = 16 * 1024**3  # zip から取り出す全体
MEMBERS_MAX = 2000
GROUP = 6  # 一つの観察の写真の数（アプリで一度に選べる数と同じ）
MP4_EPOCH = dt.datetime(1904, 1, 1, tzinfo=dt.UTC)


class TooBig(Exception):
    """zip の中身が大きすぎる（取り出しを止める）。"""


@dataclass
class Picked:
    photos: list[Path] = field(default_factory=list)
    videos: list[Path] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # 写真でも動画でもない物の名


def clean_leftovers(root: Path, pattern: str, older_s: float = 3600) -> None:
    """落ちた時に残った一時の物（.unzip-*、.video-*.part）を消す。今使っている物は消さない（古い物だけ）。"""
    import time

    now = time.time()
    for p in Path(root).glob(pattern):
        try:
            if now - p.stat().st_mtime < older_s:
                continue
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        except OSError:
            continue


def kind_of(name: str) -> str | None:
    low = name.lower()
    if low.endswith(PHOTO_EXT):
        return "photo"
    if low.endswith(VIDEO_EXT):
        return "video"
    if low.endswith(ZIP_EXT):
        return "zip"
    return None


def _unique(into: Path, name: str) -> Path:
    path = into / name
    n = 1
    while path.exists():
        n += 1
        path = into / f"{Path(name).stem}-{n}{Path(name).suffix}"
    return path


def unpack(paths: list[Path | str], into: Path) -> Picked:
    """選んだ物を写真と動画に分ける。zip は into に取り出す（写真と動画だけ）。写真と動画はそのままの道。"""
    out = Picked()
    used = [0]
    for p in map(Path, paths):
        k = kind_of(p.name)
        if k == "photo":
            out.photos.append(p)
        elif k == "video":
            out.videos.append(p)
        elif k == "zip":
            _extract(p, Path(into), out, used)
        else:
            out.skipped.append(p.name)
    return out


def _extract(zpath: Path, into: Path, out: Picked, used: list[int]) -> None:
    into.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath) as zf:
        members = [i for i in zf.infolist() if not i.is_dir()]
        if len(members) > MEMBERS_MAX:
            raise TooBig(f"{zpath.name}: {len(members)} files")
        for info in members:
            name = Path(info.filename.replace("\\", "/")).name  # 道は使わない（../ や / を外へ書かない）
            if not name or name.startswith(".") or "__MACOSX" in info.filename:
                continue
            k = kind_of(name)
            if k not in ("photo", "video"):
                out.skipped.append(name)
                continue
            if info.file_size > MEMBER_MAX or used[0] + info.file_size > TOTAL_MAX:
                raise TooBig(f"{zpath.name}: {name}")
            dst = _unique(into, name)
            try:
                with zf.open(info) as src, dst.open("wb") as f:
                    n = 0
                    while chunk := src.read(1024 * 1024):
                        n += len(chunk)
                        if n > MEMBER_MAX or used[0] + n > TOTAL_MAX:  # 書かれた大きさより実際が大きい zip
                            raise TooBig(f"{zpath.name}: {name}")
                        f.write(chunk)
            except (RuntimeError, NotImplementedError, zipfile.BadZipFile, EOFError):
                # 鍵の掛かった物、開けない縮め方、壊れた物は、その一つだけ外す
                dst.unlink(missing_ok=True)
                out.skipped.append(name)
                continue
            used[0] += n
            try:
                ts = dt.datetime(*info.date_time).timestamp()  # zip の時刻を写す（EXIF の無い物の撮った時に）
                os.utime(dst, (ts, ts))
            except (ValueError, OverflowError, OSError):
                pass  # 0 月 0 日などの時刻は写さない
            (out.photos if k == "photo" else out.videos).append(dst)


# ---------------------------------------------------------------- 写真


def photo_groups(paths: list[Path], size: int = GROUP) -> list[list[Path]]:
    """撮った順に並べ、日ごとに size 枚ずつに分ける（一つが一つの観察）。"""

    def when(p: Path) -> dt.datetime:
        try:
            info = photos.exif_info(p)
        except Exception:  # noqa: BLE001  読めない物は import_photos が理由を言う。並びはファイルの時刻で
            info = None
        taken = info.taken if info is not None else None
        return taken or dt.datetime.fromtimestamp(p.stat().st_mtime)

    dated = sorted(((when(p), p) for p in paths), key=lambda x: x[0])
    groups: list[list[Path]] = []
    day = None
    for when_, p in dated:
        if not groups or when_.date() != day or len(groups[-1]) >= size:
            groups.append([])
            day = when_.date()
        groups[-1].append(p)
    return groups


# ---------------------------------------------------------------- 動画


def _boxes(f, start: int, end: int):
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        head = f.read(8)
        if len(head) < 8:
            return
        size, kind = struct.unpack(">I4s", head)
        hl = 8
        if size == 1:
            size = struct.unpack(">Q", f.read(8))[0]
            hl = 16
        elif size == 0:
            size = end - pos
        if size < hl:
            return
        yield kind, pos + hl, pos + size
        pos += size


ISO6709 = re.compile(r"([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)")


def mp4_where(path: Path) -> dict:
    """動画の中の撮った時（mvhd、UTC → この PC の時刻）と所（©xyz）。読めない物は空。"""
    out: dict = {}
    try:
        with Path(path).open("rb") as f:
            f.seek(0, 2)
            end = f.tell()
            for kind, s, e in _boxes(f, 0, end):
                if kind != b"moov":
                    continue
                for k2, s2, e2 in _boxes(f, s, e):
                    if k2 == b"mvhd":
                        f.seek(s2)
                        version = f.read(1)[0]
                        f.read(3)
                        secs = struct.unpack(
                            ">Q" if version == 1 else ">I", f.read(8 if version == 1 else 4)
                        )[0]
                        if secs > 0:
                            taken = MP4_EPOCH + dt.timedelta(seconds=secs)
                            out["taken"] = (
                                taken.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")
                            )
                    elif k2 == b"udta":
                        for k3, s3, e3 in _boxes(f, s2, e2):
                            if k3 == b"\xa9xyz":
                                f.seek(s3)
                                raw = f.read(min(e3 - s3, 64))
                                m = ISO6709.search(raw[4:].decode("ascii", "ignore"))
                                if m:
                                    lat, lon = float(m.group(1)), float(m.group(2))
                                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                                        out["lat"], out["lon"] = lat, lon
                break
    except (OSError, struct.error, IndexError):
        return out
    return out


def place_video(root: Path, src: Path, move: bool = False) -> Path:
    """動画を記録の videos/<日>/<時刻>.<拡張子> に置き、同じ名の .json に撮った時と所を書く。

    時は動画の中（無ければファイルの時刻）。同じ名で同じ大きさの物が在れば、同じ動画とみなし在る物の道を返す。
    move なら動かす（zip から取り出した一時の物）、でなければ写す（選んだ元は残す）。
    """
    src = Path(src)
    where = mp4_where(src)
    taken = (
        dt.datetime.fromisoformat(where["taken"])
        if where.get("taken")
        else dt.datetime.fromtimestamp(src.stat().st_mtime)
    )
    where["taken"] = taken.isoformat(timespec="seconds")
    day = Path(root) / "videos" / taken.strftime("%Y-%m-%d")
    day.mkdir(parents=True, exist_ok=True)
    stem, ext = taken.strftime("%H%M%S"), src.suffix.lower()
    size = src.stat().st_size
    path, n = day / f"{stem}{ext}", 1
    while path.exists():
        if path.stat().st_size == size:
            return path
        n += 1
        path = day / f"{stem}-{n}{ext}"
    if move:
        shutil.move(str(src), path)
    else:
        shutil.copy2(src, path)
    side = {"taken": where["taken"], **{k: where[k] for k in ("lat", "lon") if k in where}, "from": src.name}
    path.with_suffix(".json").write_text(json.dumps(side, ensure_ascii=False, indent=1), encoding="utf-8")
    return path
