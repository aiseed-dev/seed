# SPDX-License-Identifier: AGPL-3.0-or-later
"""どれだけ残すか（seed.toml の keep）。docs/使い方とデータの置き方.md §4。

text      観察、読み、判定、手引き。写真は読み用の大きさ（長辺 READ_SIDE。EXIF の座標は残す）
photos    写真を元の大きさの JPEG で（既定。今までの作り）
research  上に加えて、写真の元（originals/。HEIC など、写した JPEG と中身が違うとき）と、
          読みの生の出力（observations/<id>.raw/: system.md、prompt.md、answer.json、meta.json）

効くのはほぼディスクの空きなので、init が空きを測って見せ、本人が選ぶ。上げるのは自由。下げても seed は
何も消さない。消すのは prune で、何を何 MB 消すかを見せてから、本人が頷いたときだけ。photos/ は prune でも
縮めない（取り込んだときの大きさのまま）。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .records import Folder

LEVELS = ("text", "photos", "research")
DEFAULT = "photos"
READ_SIDE = 2000  # text のときの写真の長辺（読みに足りる大きさ）
PER_OBSERVATION_MB = {"text": 5, "photos": 80, "research": 120}  # 写真 10 枚の一回の観察の目安
MB = 1_000_000


def rank(level: str) -> int:
    return LEVELS.index(level)


def full_jpeg(level: str) -> bool:
    """写真を元の大きさで残すか（text だけ縮める）。"""
    return rank(level) >= 1


def originals(level: str) -> bool:
    return level == "research"


def raw(level: str) -> bool:
    return level == "research"


def free_bytes(path: Path | str) -> int:
    p = Path(path).expanduser()
    while not p.exists():
        p = p.parent
    return shutil.disk_usage(p).free


def dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def sizes(folder: Folder) -> dict[str, int]:
    """今の大きさ（バイト）。photos、originals、raw（読みの生の出力の合計）、total。"""
    raw_total = sum(dir_bytes(d) for d in raw_dirs(folder))
    return {
        "photos": dir_bytes(folder.photos),
        "originals": dir_bytes(folder.originals),
        "raw": raw_total,
        "total": dir_bytes(folder.root),
    }


def raw_dirs(folder: Folder) -> list[Path]:
    if not folder.observations.exists():
        return []
    return sorted(d for d in folder.observations.glob("*.raw") if d.is_dir())


def prune_plan(folder: Folder, level: str) -> list[tuple[Path, int]]:
    """この keep では残さない物の一覧（道、バイト）。消すのは prune()。"""
    out: list[tuple[Path, int]] = []
    if not originals(level) and dir_bytes(folder.originals) > 0:
        out.append((folder.originals, dir_bytes(folder.originals)))
    if not raw(level):
        out += [(d, dir_bytes(d)) for d in raw_dirs(folder)]
    return out


def prune(plan: list[tuple[Path, int]]) -> int:
    """一覧の物を消し、消したバイトを返す。呼ぶ側が本人に見せて頷きをもらってから。"""
    freed = 0
    for path, size in plan:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        freed += size
    return freed


def mb(n: int) -> int:
    return round(n / MB)
