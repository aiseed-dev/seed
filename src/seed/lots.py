# SPDX-License-Identifier: AGPL-3.0-or-later
"""種のロット lots.md（docs/記録の形.md §15）。

一行一ロット。本人が書く行だけで、AI の行（確からしさ付き）は無い。
`- lot: <id> | crop: … | variety: … | place: … | year: … | from: … | note: …`
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .records import EMPTY, HEADING_RE

H_LOTS = "Lots"
LOT_ID_RE = re.compile(r"^[a-z0-9-]+$")
YEAR_RE = re.compile(r"^\d{4}$")
SEP = " | "
FIELDS = ("lot", "crop", "variety", "place", "year", "from", "note")
REQUIRED = ("lot", "crop", "variety", "place", "year")
LOT_LINE_RE = re.compile(r"^- lot: ")


class LotError(ValueError):
    """本人に一行で返す誤り。word は strings.py の語。"""

    def __init__(self, word: str, **kw):
        super().__init__(word)
        self.word = word
        self.kw = kw


def plain(value: str) -> str:
    """一行の欄に入れる文。改行と区切りの '|' は入れない（行が割れるため）。"""
    v = " ".join(str(value).split())
    if "|" in v:
        raise LotError("field_bar", value=v)
    return v


@dataclass
class Lot:
    lot: str
    crop: str
    variety: str
    place: str
    year: str
    from_: str = ""
    note: str = ""

    def check(self) -> None:
        if not LOT_ID_RE.match(self.lot):
            raise LotError("lot_bad_id", lot=self.lot)
        if not YEAR_RE.match(self.year):
            raise LotError("lot_bad_year", year=self.year)
        for name in ("crop", "variety", "place"):
            if not getattr(self, name).strip():
                raise LotError("lot_missing", field=name)

    def render(self) -> str:
        parts = [f"- lot: {self.lot}"]
        for name in FIELDS[1:]:
            v = getattr(self, "from_" if name == "from" else name)
            if v:
                parts.append(f"{name}: {plain(v)}")
        return SEP.join(parts)

    @classmethod
    def parse(cls, line: str) -> Lot | None:
        """一行を読む。ロットの行でなければ None。知らない欄は読み飛ばす。"""
        if not LOT_LINE_RE.match(line):
            return None
        got: dict[str, str] = {}
        for part in line[2:].split(" | "):
            k, sep, v = part.partition(": ")
            if sep and k.strip() in FIELDS:
                got[k.strip()] = v.strip()
        if not got.get("lot"):
            return None
        return cls(
            lot=got["lot"],
            crop=got.get("crop", ""),
            variety=got.get("variety", ""),
            place=got.get("place", ""),
            year=got.get("year", ""),
            from_=got.get("from", ""),
            note=got.get("note", ""),
        )


def lots_path(root: Path) -> Path:
    return Path(root) / "lots.md"


def read_lots(path: Path) -> list[Lot]:
    if not path.exists():
        return []
    return [lot for lot in map(Lot.parse, path.read_text(encoding="utf-8").splitlines()) if lot]


def append_to_section(path: Path, heading: str, line: str) -> None:
    """見出しの下の最後の行の後ろに一行足す。ほかの文（本人が書いた物）は触らない。

    ファイルか見出しが無ければ作る。見出しの下の (none) は外す。
    """
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines()
    start = next((i for i, raw in enumerate(lines) if raw.strip() == f"## {heading}"), None)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines += [f"## {heading}", "", line]
    else:
        end = next((i for i in range(start + 1, len(lines)) if HEADING_RE.match(lines[i])), len(lines))
        body = [i for i in range(start + 1, end) if lines[i].strip() == EMPTY]
        for i in reversed(body):
            del lines[i]
            end -= 1
        last = max((i for i in range(start + 1, end) if lines[i].startswith("- ")), default=None)
        if last is None:
            lines[start + 1 : start + 1] = ["", line]
        else:
            lines.insert(last + 1, line)
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def add_lot(root: Path, lot: Lot) -> Path:
    """ロットを一行足す。同じ名のロットがあれば LotError。"""
    lot.check()
    path = lots_path(root)
    if any(old.lot == lot.lot for old in read_lots(path)):
        raise LotError("lot_exists", lot=lot.lot)
    path.parent.mkdir(parents=True, exist_ok=True)
    append_to_section(path, H_LOTS, lot.render())
    return path
