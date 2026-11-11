# SPDX-License-Identifier: AGPL-3.0-or-later
"""畑に入っていない写真を探す（設計書 §5.17）。読むだけで、何も書かず、動かさず、消さない。

プロジェクトの根から、seed が見ない所（根と各畑の photos/ などの外）に在る写真を探し、もう畑に入っているか
（畑の photos/ か写真の元の置き場に中身の同じ物、または撮った時刻の同じ JPEG が畑の photos/ に在る）を見る。
入っていない写真には、一番近い観察の畑とそこまでの m を付ける。座標そのものは返さない（距離だけ）。
skill-folder/check.py も同じ物を使う。
"""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from . import photos
from . import settings as settings_mod
from .records import split_front

IMAGE_SUFFIXES = {".heic", ".heif", ".jpg", ".jpeg", ".png"}
# seed が見る所（根と fields/<名>/ の下）。originals は写真の元の置き場（keep が research）、observations は SAM の重ね画像（<id>.sam/<n>.jpg）の置き場で、どちらも seed の物
SEEN_DIRS = {
    "photos",
    "videos",
    "skill",
    "notes",
    "public",
    "public-home",
    "origin",
    "grow",
    "originals",
    "observations",
}
CHUNK = 1 << 20
_UNSET = object()


@dataclass(frozen=True)
class Item:
    """見つけた写真一枚。field と metres は入っていない写真だけ（座標が無ければ metres は None）。"""

    rel: str  # プロジェクトの根からの道（/ で区切る）
    path: Path
    in_seed: bool
    field: str | None = None
    metres: int | None = None


@dataclass
class Group:
    """写真の在るフォルダー一つ。"""

    folder: str  # プロジェクトの根からの道。根そのものは "."
    path: Path
    items: list[Item] = field(default_factory=list)

    @property
    def name(self) -> str:
        """本人が言葉で指す名（道の最後）。根は空。"""
        return "" if self.folder == "." else Path(self.folder).name

    @property
    def loose(self) -> list[Item]:
        return [i for i in self.items if not i.in_seed]

    @property
    def all_in(self) -> bool:
        return bool(self.items) and not self.loose

    @property
    def some_in(self) -> bool:
        return bool(self.loose) and len(self.loose) < len(self.items)


# ---------------------------------------------------------------- 共通（check.py も使う）


def is_image(name: str) -> bool:
    return Path(name).suffix.lower() in IMAGE_SUFFIXES


def sha256_stream(fh) -> str:
    h = hashlib.sha256()
    for b in iter(lambda: fh.read(CHUNK), b""):
        h.update(b)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    with open(path, "rb") as fh:
        return sha256_stream(fh)


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


def seen_by_seed(rel: Path) -> bool:
    """根からの道 rel が、seed の見る所（根か fields/<名>/ の SEEN_DIRS）の中か。"""
    parts = rel.parts
    if parts and parts[0] in SEEN_DIRS:
        return True
    return len(parts) > 2 and parts[0] == settings_mod.FIELDS_DIR and parts[2] in SEEN_DIRS


def walk_outside(root: Path, skip: Iterable[Path] = ()) -> Iterator[Path]:
    """seed が見ない所に在るファイル（. で始まる物とその下は見ない）。skip のフォルダーの下も見ない。"""
    skip = {Path(p) for p in skip}
    for dp, dns, fns in os.walk(root):
        here = Path(dp)
        dns[:] = sorted(d for d in dns if not d.startswith(".") and here / d not in skip)
        for f in sorted(fns):
            if f.startswith("."):
                continue
            p = here / f
            if p.is_symlink() or seen_by_seed(p.relative_to(root)):
                continue
            yield p


def taken_of(path: Path):
    """撮った時刻。読めない・無い時は None。"""
    try:
        return photos.exif_info(path).taken
    except Exception:  # noqa: BLE001 - 読めない写真は入っていない方に数える
        return None


def jpeg_in_fields(taken, fields: Iterable[Path]) -> bool:
    """<畑>/photos/<日>/<時分秒>.jpg（同じ秒なら -1, -2 …）が在るか。"""
    if taken is None:
        return False
    day = taken.strftime("%Y-%m-%d")
    stem = taken.strftime("%H%M%S")
    for f in fields:
        d = f / "photos" / day
        if (d / f"{stem}.jpg").is_file():
            return True
        if d.is_dir() and any(d.glob(f"{stem}-*.jpg")):
            return True
    return False


def read_front(path: Path) -> dict:
    try:
        front, _ = split_front(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, TypeError, ValueError):
        return {}
    return front if isinstance(front, dict) else {}


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


def centres(field_dir: Path) -> list[tuple[float, float]]:
    """畑の観察の真ん中（前書きの location.center）。"""
    out = []
    for p in sorted((field_dir / "observations").glob("*.md")):
        c = centre_of(read_front(p))
        if c is not None:
            out.append(c)
    return out


# ---------------------------------------------------------------- 畑と置き場


def field_dirs(project: Path) -> list[tuple[str, Path]]:
    """(畑の名, 畑のフォルダー)。fields/ の無いプロジェクトは根が一つの畑（名は根のフォルダーの名）。"""
    names = settings_mod.field_names(project)
    if names:
        return [(n, project / settings_mod.FIELDS_DIR / n) for n in names]
    return [(project.name, project)]


def bulk_of(project: Path) -> Path | None:
    """seed.toml の bulk（写真の元を置く別の盤）だけを読む。無いか読めなければ None。"""
    try:
        data = tomllib.loads(settings_mod.settings_path(project).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    got = str(data.get("bulk") or "")
    return Path(got).expanduser() if got else None


def originals_dirs(project: Path, bulk: Path | None) -> list[Path]:
    """写真の元の置き場（records.Folder.originals と同じ決め方）。"""
    names = settings_mod.field_names(project)
    if not names:
        return [(bulk or project) / "originals"]
    base = bulk if bulk else project
    return [base / settings_mod.FIELDS_DIR / n / "originals" for n in names]


def _hashes_of_size(dirs: Iterable[Path], sizes: set[int]) -> tuple[set[str], set[int]]:
    """dirs の下のファイルのうち、大きさが sizes に在る物だけの sha256 と、その大きさ（中身が同じなら大きさも同じ）。"""
    out, seen = set(), set()
    for d in dirs:
        if not d.exists():
            continue
        for p in walk_files(d):
            try:
                size = p.stat().st_size
                if size in sizes:
                    out.add(sha256_file(p))
                    seen.add(size)
            except OSError:
                continue
    return out, seen


# ---------------------------------------------------------------- 探す


def candidates(project: Path, bulk: Path | None = None) -> list[Path]:
    """seed が見ない所に在る写真（安い歩きだけ。中は読まない）。"""
    project = Path(project)
    skip = [bulk] if bulk is not None else []
    return [p for p in walk_outside(project, skip) if is_image(p.name)]


def scan(project: Path | str, bulk=_UNSET) -> list[Group]:
    """プロジェクトの根から、seed が見ない所の写真をフォルダーごとに。写真が無ければ []。

    bulk を渡さなければ seed.toml の bulk を読む。何も書かない。
    """
    project = Path(project).expanduser()
    if bulk is _UNSET:
        bulk = bulk_of(project)
    bulk = Path(bulk).expanduser() if bulk else None
    found = candidates(project, bulk)
    if not found:
        return []
    fields = field_dirs(project)
    sizes = set()
    for p in found:
        try:
            sizes.add(p.stat().st_size)
        except OSError:
            continue
    keep, keep_sizes = _hashes_of_size(
        [f / "photos" for _, f in fields] + originals_dirs(project, bulk), sizes
    )
    near = [(name, centres(f)) for name, f in fields]
    groups: dict[str, Group] = {}
    for p in found:
        rel = p.relative_to(project)
        parent = rel.parent.as_posix()
        g = groups.setdefault(parent, Group(parent, project / rel.parent))
        g.items.append(_item(p, rel.as_posix(), keep, keep_sizes, fields, near))
    return [groups[k] for k in sorted(groups)]


def _item(p: Path, rel: str, keep: set[str], keep_sizes: set[int], fields, near) -> Item:
    try:
        same = p.stat().st_size in keep_sizes and sha256_file(p) in keep  # 大きさが違えば読まない
    except OSError:
        same = False
    if same:
        return Item(rel, p, True)
    try:
        info = photos.exif_info(p)
    except Exception:  # noqa: BLE001 - 読めない写真は、場所の分からない入っていない写真
        info = None
    if info is not None and jpeg_in_fields(info.taken, [f for _, f in fields]):
        return Item(rel, p, True)
    if info is None or not info.has_coord:
        return Item(rel, p, False)
    best: tuple[float, str] | None = None
    for name, cs in near:
        for c in cs:
            d = photos._distance_m((info.lat, info.lon), c)
            if best is None or d < best[0]:
                best = (d, name)
    if best is None:  # どの畑の観察にも座標が無い
        return Item(rel, p, False)
    return Item(rel, p, False, best[1], round(best[0]))


def loose_items(groups: Iterable[Group]) -> list[Item]:
    return [i for g in groups for i in g.loose]


def removable(groups: Iterable[Group]) -> list[Path]:
    """消してよいフォルダー: 写真が全部畑に入り、下のファイルが全部その写真（ほかの物を巻き込まない）。

    根と、畑やほかの物を含むフォルダーは返さない。消すのは本人（アプリも Claude も消さない）。
    """
    groups = list(groups)
    in_seed = {i.path for g in groups for i in g.items if i.in_seed}
    out = []
    for g in groups:
        if g.folder == "." or not g.all_in:
            continue
        try:
            files = list(walk_all(g.path))
        except OSError:
            continue
        if files and all(p in in_seed or p.name == ".DS_Store" for p in files):
            out.append(g.path)
    return out


def walk_all(root: Path) -> Iterator[Path]:
    """root の下の全部（. で始まる物も、リンクも）。消す命令が巻き込む物を見るため。"""
    for dp, dns, fns in os.walk(root):
        for d in dns:
            if (Path(dp) / d).is_symlink():
                yield Path(dp) / d
        for f in fns:
            yield Path(dp) / f


def rm_command(path: Path) -> str:
    """写せる消す命令 rm -r '<フォルダー>'（' は閉じて \\' で挟む）。"""
    return "rm -r '" + str(path).replace("'", "'\\''") + "'"


# ---------------------------------------------------------------- 言葉で答える


def _word(word: str) -> re.Pattern:
    """語の前後が英数字でない所だけに当たる形（「s.jpg」が「rokuse」に当たらない。日本語の語は続けて書ける）。"""
    return re.compile(r"(?<![0-9a-z_])" + re.escape(word) + r"(?![0-9a-z_])")


def match(text: str, groups: Iterable[Group], field_names: Iterable[str]) -> tuple[list[Path], str] | None:
    """本人の言葉が、入っていない写真（フォルダーの名か写真の名）と、畑の名一つを指していれば (写真, 畑の名)。

    写真を指す語を除いた残りに、畑の名がちょうど一つ在る時だけ。どちらかが欠ける、畑が二つの時は None。
    """
    low = text.casefold()
    refs: list[tuple[str, list[Item]]] = []
    for g in groups:
        loose = g.loose
        if not loose:
            continue
        if g.name:
            refs.append((g.name.casefold(), loose))
        for it in loose:
            name = Path(it.rel).name
            refs.append((name.casefold(), [it]))
            refs.append((Path(name).stem.casefold(), [it]))
    picked: dict[Path, None] = {}
    for word, items in sorted(refs, key=lambda r: -len(r[0])):  # 長い語から（IMG_1.HEIC を IMG_1 より先に）
        if not word:
            continue
        pat = _word(word)
        if pat.search(low):
            picked.update(dict.fromkeys(it.path for it in items))
            low = pat.sub(" ", low)
    if not picked:
        return None
    hits = []
    for name in sorted(set(field_names), key=len, reverse=True):  # 長い名から（「北側」を「北」より先に）
        key = name.casefold()
        pat = _word(key) if key else None
        if pat is not None and pat.search(low):
            hits.append(name)
            low = pat.sub(" ", low)
    if len(hits) != 1:
        return None
    return list(picked), hits[0]
