# SPDX-License-Identifier: AGPL-3.0-or-later
"""座標からの照会（設計書 §2.2、§7.2）。元の資料は `seed.sources`（seed-farm[lookup] が入っていれば使え、無ければ空の data）。

結果は `- <key>: <text>（出典: <名前>、確認日 <日>）` の data 行にする。本人の言語が日本語なら、英語の枠だけを日本語にする（`lookup_ja`）。
照会はネットに出るので、座標を小数 3 桁に丸めた鍵で 24 時間メモリに置く（置くのは照会の元の行で、
言語ごとの文はそのつど作る）。元の座標はどこにも書かない。
"""

from __future__ import annotations

import datetime as dt
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait

from . import lookup_ja
from . import records as R
from .prompts import clean_text

CACHE_SECONDS = 24 * 3600
WALL_SECONDS = 40  # 一回の照会に待つ長さ。遅い元は落とす
# (seed.sources の名前, data 行の key, 日本だけか)。周りの岩（rocks_jp）と地質図カタログ（sheet_jp）は
# 一回に何十も問い合わせるので使わない。Wikipedia の近くの記事も数が多いので使わない
USED = (
    ("address_jp", "place_name", True),
    ("parcel_jp", "parcel", True),
    ("elevation_jp", "elevation", True),
    ("elevation", "elevation", False),
    ("landform_jp", "landform", True),
    ("geology_jp", "geology", True),
    ("geology", "geology", False),
    ("faults_jp", "hazard", True),
    ("hazard_jp", "hazard", True),
    ("soil_jp", "soil", True),
    ("soil", "soil", False),
    ("historic", "history", False),
)
JP_BOX = (20.0, 46.0, 122.0, 154.0)  # 日本の照会元を使う範囲（緯度、経度のおおよその箱）

FN_LINE_RE = re.compile(r"^- `(?P<kind>data|reference)` (?P<text>.+?)\s+— (?P<src>.+)$")
URL_TAIL_RE = re.compile(r",?\s*https?://\S+$")

Raw = tuple[str, str, str]  # (data 行の key, 元の一行, 出典の名の代わり)
_cache: dict[tuple[float, float], tuple[float, str, list[Raw]]] = {}
_lock = threading.Lock()


def _load():
    """seed.sources から (Point, {名前: 関数}, {名前: 出典名}) を取る。部品（numpy、pillow）が無ければ None。"""
    try:
        from .sources import Point, world
    except ImportError:  # seed-farm[lookup] が入っていない。照会しないだけ
        return None
    return Point, dict(world.SOURCES), dict(world.NAMES)


def available() -> bool:
    return _load() is not None


def in_japan(lat: float, lon: float) -> bool:
    s, n, w, e = JP_BOX
    return s <= lat <= n and w <= lon <= e


def to_line(key: str, fn_line: str, fallback_source: str, day: str, language: str = "en") -> R.Line | None:
    """元の一行 → seed の data 行。出典の取れない行は捨てる。日本語なら英語の枠を置き換える。"""
    m = FN_LINE_RE.match(fn_line.strip())
    if not m:
        return None
    text = m["text"].strip().rstrip("。.").strip()
    src = URL_TAIL_RE.sub("", m["src"]).strip()
    src = re.sub(r"^出典[：:]\s*", "", src) or fallback_source
    if not text or not src:
        return None
    if lookup_ja.is_ja(language):
        text = lookup_ja.to_ja(text)
    return R.Line(key, f"{clean_text(text)}（出典: {clean_text(src)}、確認日 {day}）")


def _fetch(lat: float, lon: float) -> list[Raw]:
    """照会の元の行（言語に依らない）。"""
    loaded = _load()
    if loaded is None:
        return []
    point_cls, sources, names = loaded
    site = point_cls(lat=lat, lon=lon, country="JP" if in_japan(lat, lon) else "")
    jp = site.country == "JP"
    plan = [(name, key) for name, key, jp_only in USED if name in sources and (jp or not jp_only)]
    if jp:
        # 日本では国の照会があるので、世界の粗い地図（標高、地質、土壌）は使わない
        plan = [(n, k) for n, k in plan if n.endswith("_jp") or n == "historic"]
    pool = ThreadPoolExecutor(max_workers=max(1, len(plan)))
    futures = {pool.submit(sources[name], site): (name, key) for name, key in plan}
    done, _ = wait(futures, timeout=WALL_SECONDS)
    pool.shutdown(wait=False, cancel_futures=True)
    out: list[Raw] = []
    for name, key in plan:  # 並びは USED の順
        f = next(f for f, nk in futures.items() if nk == (name, key))
        if f not in done or f.exception() is not None:
            continue
        lines, _raw = f.result()
        out += [(key, s, names.get(name, name)) for s in lines]
    return out


def data_lines(lat: float, lon: float, language: str = "en") -> list[R.Line]:
    """座標 → 本人の言語の data 行。照会の部品が無ければ []。同じ 3 桁の座標は 24 時間使い回す。"""
    k = (round(float(lat), 3), round(float(lon), 3))
    now = time.monotonic()
    with _lock:
        hit = _cache.get(k)
        if hit and now - hit[0] < CACHE_SECONDS:
            _, day, raw = hit
        else:
            hit = None
            for old in [c for c, (t, _, _) in _cache.items() if now - t >= CACHE_SECONDS]:
                del _cache[old]
    if hit is None:
        day, raw = dt.date.today().isoformat(), _fetch(*k)
        with _lock:
            _cache[k] = (now, day, raw)
    out = [to_line(key, s, src, day, language) for key, s, src in raw]
    return [x for x in out if x]


def clear_cache() -> None:
    with _lock:
        _cache.clear()
