# SPDX-License-Identifier: AGPL-3.0-or-later
"""索引。public/*.md の前書きを集めて index.json にする（docs/記録の形.md §8）。

contact は入れない（公開ファイルを開いた人だけが見る）。photo は記録ごとの一枚の道（/photos/<id>/<名>。Public.cover）。connections は
connections/<id>/*.md の行の数。検査（Public.check）が通らないファイルは飛ばして warn する。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import warnings
from pathlib import Path

from . import records as R


def count_connections(connections_dir: Path, record_id: str) -> int:
    """connections/<id>/ の下の繋がりの行の数。"""
    d = Path(connections_dir) / record_id
    if not d.is_dir():
        return 0
    n = 0
    for f in d.glob("*.md"):
        n += sum(1 for s in f.read_text(encoding="utf-8").splitlines() if R.Connection.parse(s))
    return n


def build_index(public_dir: Path, connections_dir: Path) -> dict:
    """public/*.md → 索引の dict。新しい公開（since）が先。"""
    records = []
    for path in sorted(Path(public_dir).glob("*.md")):
        try:
            pub = R.Public.read(path)
        except (ValueError, TypeError, OSError) as e:
            warnings.warn(f"{path.name} を読めない: {e}", stacklevel=2)
            continue
        bad = pub.check()
        if bad:
            warnings.warn(f"{path.name} を索引に入れない: {'、'.join(bad)}", stacklevel=2)
            continue
        if R.fine_coords(pub.render()):
            warnings.warn(f"{path.name} を索引に入れない: 小数 3 桁以上の座標らしい数がある", stacklevel=2)
            continue
        if path.stem != pub.id:
            warnings.warn(f"{path.name} の id が名前と違う: {pub.id}", stacklevel=2)
            continue
        entry = pub.front(for_index=True)
        cover = pub.cover()  # 一番新しい日の一枚（前書きの古い photo の欄は使わない）
        entry.pop("photo", None)
        if cover:
            entry["photo"] = R.photo_url(pub.id, cover)
        entry["connections"] = count_connections(connections_dir, pub.id)
        records.append(entry)
    records.sort(key=lambda r: (r["since"], r["id"]), reverse=True)
    return {
        "built": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "records": records,
        "total": {"records": len(records), "connections": sum(r["connections"] for r in records)},
    }


def write_index(public_dir: Path, connections_dir: Path, out: Path | None = None) -> dict:
    """索引を作って書く。既定は public_dir/index.json。途中で読まれても壊れないよう置き換えで書く。"""
    index = build_index(public_dir, connections_dir)
    out = Path(out) if out else Path(public_dir) / "index.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    return index
