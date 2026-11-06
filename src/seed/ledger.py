# SPDX-License-Identifier: AGPL-3.0-or-later
"""帳簿 ledger.md と請求書の下書き ledger/invoice-<日>-<相手>.md（docs/記録の形.md §16）。

一行一件。本人が書く。`- <日> | <種類> | <円> | <何> | lot: … | to: …`。
円は整数で、掛かった物（cost）は負。税の計算はしない（消費税や所得税の扱いは本人と税理士が決める）。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from .lots import LotError, append_to_section, plain

H_LEDGER = "Ledger"
KINDS = ("sale", "cost", "help", "other")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
ENTRY_RE = re.compile(
    r"^- (?P<date>\d{4}-\d{2}-\d{2}) \| (?P<kind>[a-z]+) \| (?P<yen>-?\d+) \| (?P<rest>.*)$"
)
NAME_UNSAFE_RE = re.compile(r"[\\/:*?\"<>|\s]+")


class LedgerError(LotError):
    pass


def check_date(text: str) -> str:
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError:
        raise LedgerError("field_bad_date", value=text) from None


def check_month(text: str) -> str:
    if not MONTH_RE.match(text or ""):
        raise LedgerError("field_bad_month", value=text)
    try:
        dt.date.fromisoformat(f"{text}-01")
    except ValueError:
        raise LedgerError("field_bad_month", value=text) from None
    return text


@dataclass
class Entry:
    date: str
    kind: str
    yen: int
    what: str
    lot: str = ""
    to: str = ""

    def render(self) -> str:
        parts = [self.date, self.kind, str(self.yen), plain(self.what)]
        if self.lot:
            parts.append(f"lot: {plain(self.lot)}")
        if self.to:
            parts.append(f"to: {plain(self.to)}")
        return "- " + " | ".join(parts)

    @classmethod
    def parse(cls, line: str) -> Entry | None:
        m = ENTRY_RE.match(line.rstrip())
        if not m or m["kind"] not in KINDS:
            return None
        cols = [c.strip() for c in m["rest"].split(" | ")]
        what, extra = (cols[0] if cols else ""), {}
        for c in cols[1:]:
            k, sep, v = c.partition(": ")
            if sep and k in ("lot", "to"):
                extra[k] = v.strip()
        return cls(
            m["date"], m["kind"], int(m["yen"]), what.rstrip(" |"), extra.get("lot", ""), extra.get("to", "")
        )


def make_entry(date: str, kind: str, yen: int, what: str, lot: str = "", to: str = "") -> Entry:
    """本人の入れた物から一件を作る。cost は負に揃える（記録の形 §16）。"""
    if kind not in KINDS:
        raise LedgerError("ledger_bad_kind", kind=kind)
    if not what.strip():
        raise LedgerError("ledger_no_what")
    yen = -abs(yen) if kind == "cost" else yen
    e = Entry(check_date(date), kind, int(yen), what.strip(), (lot or "").strip(), (to or "").strip())
    e.render()  # '|' が無いかを先に確かめる
    return e


def ledger_path(root: Path) -> Path:
    return Path(root) / "ledger.md"


def read_entries(path: Path) -> list[Entry]:
    if not path.exists():
        return []
    return [e for e in map(Entry.parse, path.read_text(encoding="utf-8").splitlines()) if e]


def add_entry(root: Path, entry: Entry) -> Path:
    path = ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    append_to_section(path, H_LEDGER, entry.render())
    return path


def month_entries(entries: list[Entry], month: str) -> list[Entry]:
    prefix = check_month(month) + "-"
    return [e for e in entries if e.date.startswith(prefix)]


def sums(entries: list[Entry]) -> dict[str, int]:
    """種類ごとの合計と、全部を足した差引（'net'）。"""
    out = {k: 0 for k in KINDS}
    for e in entries:
        out[e.kind] += e.yen
    out["net"] = sum(e.yen for e in entries)
    return out


def invoice_items(entries: list[Entry], to: str, month: str) -> list[Entry]:
    """相手に請求する行: その月の、相手が to の、掛かった物（cost）でない行。"""
    return [e for e in month_entries(entries, month) if e.to == to.strip() and e.kind != "cost"]


def invoice_path(root: Path, to: str, today: str) -> Path:
    name = NAME_UNSAFE_RE.sub("-", to.strip()).strip("-.") or "to"
    return Path(root) / "ledger" / f"invoice-{today}-{name}.md"


def render_invoice(
    texts: dict[str, str], name: str, to: str, month: str, today: str, items: list[Entry]
) -> str:
    """請求書の下書き。texts は strings.py の文（本人の言語）。税の計算はしない。"""
    lines = [
        f"# {texts['title']}",
        "",
        f"- from: {name or texts['self_writes']}",
        f"- to: {to}",
        f"- month: {month}",
        f"- date: {today}",
        "",
        "## Items",
        "",
    ]
    for e in items:
        cols = [e.date, e.kind, str(e.yen), e.what] + ([f"lot: {e.lot}"] if e.lot else [])
        lines.append("- " + " | ".join(cols))
    lines += [
        "",
        "## Total",
        "",
        f"- total: {sum(e.yen for e in items)} {texts['yen']}",
        "",
        texts["no_tax"],
        "",
    ]
    return "\n".join(lines)


def write_invoice(
    root: Path, texts: dict[str, str], name: str, to: str, month: str, today: str | None = None
) -> tuple[Path, list[Entry]]:
    """ledger.md から請求書の下書きを書く。行が無ければ LedgerError（何も書かない）。"""
    today = today or dt.date.today().isoformat()
    to = plain(to)
    if not to:
        raise LedgerError("invoice_no_items", to=to, month=month)
    items = invoice_items(read_entries(ledger_path(root)), to, month)
    if not items:
        raise LedgerError("invoice_no_items", to=to, month=month)
    path = invoice_path(root, to, today)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_invoice(texts, name, to, month, today, items), encoding="utf-8")
    return path, items
