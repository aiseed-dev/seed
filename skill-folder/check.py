# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed のフォルダーを読むだけで確かめる道具（手引き skill-folder/ の 01・02 の歩で使う）。

何も書かず、動かさず、消しません。座標は出さず、距離（m）だけを出します。
seed の venv の python で走らせます: <seed の venv>/bin/python skill-folder/check.py <命令> ...
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path

from seed import photos
from seed.records import split_front

IMAGE_SUFFIXES = {".heic", ".heif", ".jpg", ".jpeg", ".png"}
VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v"}
SEEN_DIRS = {"photos", "videos", "skill", "notes", "public", "public-home", "origin", "grow"}
LIST_LIMIT = 50
CHUNK = 1 << 20

SAME = "同じ物が在る"
AS_JPEG = "JPEG で入っている"
NOT_FOUND = "見つからない"


# ---------------------------------------------------------------- 共通


def walk_files(root: Path) -> Iterator[Path]:
    """root の下の素のファイル（リンクは辿らない）。root がファイルならそれ一つ。"""
    if root.is_file() and not root.is_symlink():
        yield root
        return
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for f in sorted(fns):
            p = Path(dp) / f
            if p.is_file() and not p.is_symlink():
                yield p


def sha256_stream(fh) -> str:
    h = hashlib.sha256()
    for b in iter(lambda: fh.read(CHUNK), b""):
        h.update(b)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    with open(path, "rb") as fh:
        return sha256_stream(fh)


def is_image(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_SUFFIXES


def taken_of(path: Path):
    """撮った時刻。読めない・無い時は None。"""
    try:
        return photos.exif_info(path).taken
    except Exception:  # noqa: BLE001 - 読めない写真は「見つからない」に数える
        return None


def jpeg_in_fields(taken, fields: list[Path]) -> bool:
    """<畑>/photos/<日>/<時分秒>.jpg（同じ秒なら -1, -2 …）が在るか。"""
    if taken is None:
        return False
    day = taken.strftime("%Y-%m-%d")
    stem = taken.strftime("%H%M%S")
    for field in fields:
        d = field / "photos" / day
        if (d / f"{stem}.jpg").is_file():
            return True
        if d.is_dir() and any(d.glob(f"{stem}-*.jpg")):
            return True
    return False


# ---------------------------------------------------------------- compare


def keep_hashes(dirs: list[Path]) -> set[str]:
    out = set()
    for d in dirs:
        for p in walk_files(d):
            out.add(sha256_file(p))
    return out


def classify_candidate(cand: Path, keep: set[str], fields: list[Path]) -> list[tuple[str, str]]:
    """CAND の中のファイル一つずつに (名, 状態)。zip は中の一つずつ（zip:中の名）。"""
    out: list[tuple[str, str]] = []
    base = cand if cand.is_dir() else cand.parent
    for p in walk_files(cand):
        rel = p.relative_to(base).as_posix()
        if p.suffix.lower() == ".zip" and zipfile.is_zipfile(p):
            out.extend(classify_zip(p, rel, keep, fields))
            continue
        if sha256_file(p) in keep:
            out.append((rel, SAME))
        elif fields and is_image(p.name) and jpeg_in_fields(taken_of(p), fields):
            out.append((rel, AS_JPEG))
        else:
            out.append((rel, NOT_FOUND))
    return out


def classify_zip(path: Path, rel: str, keep: set[str], fields: list[Path]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    with zipfile.ZipFile(path) as zf, tempfile.TemporaryDirectory() as tmp:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = f"{rel}:{info.filename}"
            with zf.open(info) as fh:
                digest = sha256_stream(fh)
            if digest in keep:
                out.append((name, SAME))
                continue
            if fields and is_image(info.filename):
                # exif_info は道を取るので、一時のフォルダーに一つだけ書いて読む（終われば消える）
                tmp_path = Path(tmp) / f"entry{Path(info.filename).suffix.lower()}"
                with zf.open(info) as src, open(tmp_path, "wb") as dst:
                    shutil.copyfileobj(src, dst, CHUNK)
                found = jpeg_in_fields(taken_of(tmp_path), fields)
                tmp_path.unlink()
                if found:
                    out.append((name, AS_JPEG))
                    continue
            out.append((name, NOT_FOUND))
    return out


def cmd_compare(args) -> int:
    keep = keep_hashes(args.keep)
    print(f"残す方: {len(args.keep)} か所、中身の違う物 {len(keep)}")
    for cand in args.cand:
        rows = classify_candidate(cand, keep, args.photos)
        counts = Counter(state for _, state in rows)
        print(f"{cand}: {len(rows)} 個")
        print(f"  {SAME} {counts[SAME]}、{AS_JPEG} {counts[AS_JPEG]}、{NOT_FOUND} {counts[NOT_FOUND]}")
        missing = [name for name, state in rows if state == NOT_FOUND]
        for name in missing[:LIST_LIMIT]:
            print(f"  {NOT_FOUND}: {name}")
        if len(missing) > LIST_LIMIT:
            print(f"  ほか {len(missing) - LIST_LIMIT} 個")
    return 0


# ---------------------------------------------------------------- near


def read_front(path: Path) -> dict:
    try:
        front, _ = split_front(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, TypeError, ValueError):
        return {}
    return front


def observation_fronts(field: Path) -> list[tuple[Path, dict]]:
    return [(p, read_front(p)) for p in sorted((field / "observations").glob("*.md"))]


def centre_of(front: dict) -> tuple[float, float] | None:
    loc = front.get("location")
    if not isinstance(loc, dict):
        return None
    c = loc.get("center")
    try:
        lat, lon = float(c[0]), float(c[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    return lat, lon


def extent_of(front: dict) -> float | None:
    loc = front.get("location")
    if not isinstance(loc, dict):
        return None
    try:
        return float(loc.get("extent_m"))
    except (TypeError, ValueError):
        return None


def cmd_near(args) -> int:
    fronts = observation_fronts(args.field)
    centres = [c for _, f in fronts if (c := centre_of(f)) is not None]
    extents = [e for _, f in fronts if (e := extent_of(f)) is not None]
    print(f"畑 {args.field.name}: 座標の在る観察 {len(centres)} / {len(fronts)}")
    if not centres:
        print("観察に座標が無いので、距離を出せません")
        return 0
    spread = max(
        (photos._distance_m(a, b) for i, a in enumerate(centres) for b in centres[i + 1 :]),
        default=0.0,
    )
    print(f"観察の広がり（extent_m）の最大: {round(max(extents)) if extents else 0} m")
    print(f"観察の真ん中どうしの最大の距離: {round(spread)} m")
    for target in args.targets:
        for p in walk_files(target):
            if not is_image(p.name):
                continue
            try:
                info = photos.exif_info(p)
            except Exception:  # noqa: BLE001 - 読めない物は名だけ返す
                print(f"{p.name}: 読めない")
                continue
            if not info.has_coord:
                print(f"{p.name}: 座標が無い")
                continue
            d = min(photos._distance_m((info.lat, info.lon), c) for c in centres)
            print(f"{p.name}: 一番近い観察まで {round(d)} m")
    return 0


# ---------------------------------------------------------------- refs


def cmd_refs(args) -> int:
    fronts = observation_fronts(args.field)
    total_ok = total_missing = 0
    for path, front in fronts:
        refs = front.get("photos") or []
        if not isinstance(refs, list):
            refs = []
        missing = [r for r in refs if not (args.field / str(r)).is_file()]
        ok = len(refs) - len(missing)
        total_ok += ok
        total_missing += len(missing)
        print(f"{path.name}: 在る {ok}、無い {len(missing)}")
        for r in missing:
            print(f"  無い: {r}")
    print(f"観察 {len(fronts)}: 写真が在る {total_ok}、無い {total_missing}")
    return 0


# ---------------------------------------------------------------- outside


def seen_by_seed(rel: Path) -> bool:
    parts = rel.parts
    if parts and parts[0] in SEEN_DIRS:
        return True
    return len(parts) > 2 and parts[0] == "fields" and parts[2] in SEEN_DIRS


def kind_of(name: str) -> str | None:
    s = Path(name).suffix.lower()
    if s in IMAGE_SUFFIXES:
        return "写真"
    if s in VIDEO_SUFFIXES:
        return "動画"
    if s == ".zip":
        return "zip"
    return None


def cmd_outside(args) -> int:
    root = args.project
    groups: dict[str, Counter] = defaultdict(Counter)
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if not d.startswith("."))
        for f in fns:
            if f.startswith("."):
                continue
            kind = kind_of(f)
            if kind is None:
                continue
            rel = (Path(dp) / f).relative_to(root)
            if seen_by_seed(rel):
                continue
            groups[rel.parent.as_posix()][kind] += 1
    total = sum(sum(c.values()) for c in groups.values())
    print(f"seed が見ない写真・動画・zip: {total} 個（{len(groups)} か所）")
    for parent in sorted(groups):
        c = groups[parent]
        parts = "、".join(f"{k} {c[k]}" for k in ("写真", "動画", "zip") if c[k])
        print(f"  {parent}: {parts}")
    return 0


# ---------------------------------------------------------------- 引数


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check.py",
        description="seed のフォルダーを読むだけで確かめる。何も書かず、動かさず、消さない。座標は出さず距離（m）だけ。",
    )
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compare", help="片付けたい物が、残す方に中身の同じ物で在るか（sha256）")
    c.add_argument("--keep", type=Path, action="append", required=True, help="残す方のフォルダー（何度でも）")
    c.add_argument(
        "--photos",
        type=Path,
        action="append",
        default=[],
        help="畑のフォルダー（何度でも。撮った時刻の JPEG を探す）",
    )
    c.add_argument(
        "cand", type=Path, nargs="+", help="片付けたい方（ファイルかフォルダー。zip は中を比べる）"
    )
    c.set_defaults(func=cmd_compare)

    n = sub.add_parser("near", help="写真が畑の観察から何 m 離れているか")
    n.add_argument("field", type=Path, help="畑のフォルダー")
    n.add_argument("targets", type=Path, nargs="+", help="写真かフォルダー")
    n.set_defaults(func=cmd_near)

    r = sub.add_parser("refs", help="観察の photos: が指す写真が在るか")
    r.add_argument("field", type=Path, help="畑のフォルダー")
    r.set_defaults(func=cmd_refs)

    o = sub.add_parser("outside", help="seed が見ない所に在る写真・動画・zip")
    o.add_argument("project", type=Path, help="プロジェクトのフォルダー")
    o.set_defaults(func=cmd_outside)
    return p


def check_paths(parser: argparse.ArgumentParser, args) -> None:
    paths: list[Path] = []
    for key in ("keep", "photos", "cand", "targets"):
        paths.extend(getattr(args, key, None) or [])
    for key in ("field", "project"):
        if getattr(args, key, None) is not None:
            paths.append(getattr(args, key))
    for p in paths:
        if not p.exists():
            parser.error(f"無い: {p}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    check_paths(parser, args)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
