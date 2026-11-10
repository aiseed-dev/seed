"""records/lookup.md for the old fieldnotes farm folder, on top of seed.sources (the sources moved to seed 11-11).

This file goes when the fieldnotes package is folded into seed; seed itself keeps the lines in place.md.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from seed.sources import jp as lookup_jp  # noqa: F401 — tests and walk.py patch and read it here
from seed.sources import world
from seed.sources.world import JAPAN_ONLY, NAMES, SECTIONS, SOURCES, get_json  # noqa: F401

from .site import Site

FILE = "lookup.md"
RAW = "lookup"


def lookup(records_root: Path) -> Path:
    """Ask every source, keep the raw answers, write records/lookup.md.
    A source that fails (down, in maintenance) is named in the file, not fatal."""
    site = Site.load(records_root)
    if not site.located:
        raise ValueError("no lat/lon in records/site.md (fieldnotes init)")
    raw_dir = records_root / RAW
    raw_dir.mkdir(parents=True, exist_ok=True)
    got: dict[str, list[str]] = {}
    for key, fn in SOURCES.items():
        if key in JAPAN_ONLY and site.country != "JP":
            continue
        try:
            lines, raw = fn(site)
            (raw_dir / f"{key}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
            got[key] = lines
        except Exception as e:  # noqa: BLE001 - a missing source should not lose the others
            got[key] = [f"- ({NAMES[key]}: not reached on {date.today()}, {e if isinstance(e, RuntimeError) else type(e).__name__}; run lookup again later)"]
    out = ["---", f"place: {site.place}", f"lat: {site.lat}", f"lon: {site.lon}",
           f"fetched: {date.today().isoformat()}", "---", "",
           "# Public data looked up for this farm", "",
           "Fetched from open services by `fieldnotes lookup`; raw answers in records/lookup/.",
           "`data` lines are measurements or maps (world maps are coarse); `reference` lines are",
           "places with a name near the farm, worth reading about. Mark or correct them like any other line.", ""]
    for title, keys in SECTIONS:
        lines = [x for k in keys for x in got.get(k, [])]
        if lines:
            out += [f"## {title}", "", *lines, ""]
    path = records_root / FILE
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def search(records_root: Path, words: str, radius_m: int = 10000) -> list[str]:
    return world.search(Site.load(records_root), words, radius_m)
