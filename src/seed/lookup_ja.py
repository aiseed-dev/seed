# SPDX-License-Identifier: AGPL-3.0-or-later
"""照会の data 行を本人の言語（日本語）にする（設計書 §7.2）。

照会の元（seed.sources）は、決まった英語の枠（"Elevation 6.9 m (DEM: …)"、"the field is outside; …" など）に
日本の資料の語をはめて返す。本人の言語が日本語のときは、その枠だけを日本語に置き換える。資料の語
（地形分類の名、土壌の名と説明、筆ポリゴンの注意の中の語）と出典はそのまま。枠に合わない行は英語の
まま通す（捨てない）。枠を変えたら、ここの規則とテスト（tests/test_lookup_ja.py）も変える。
"""

from __future__ import annotations

import re
from collections.abc import Callable

DIRECTIONS = {
    "N": "北",
    "NE": "北東",
    "E": "東",
    "SE": "南東",
    "S": "南",
    "SW": "南西",
    "W": "西",
    "NW": "北西",
}
# OpenStreetMap の historic の値（よく出る物だけ。無ければ英語のまま）
KINDS = {
    "memorial": "記念碑",
    "monument": "記念碑",
    "wayside_shrine": "路傍の祠",
    "wayside_cross": "路傍の十字架",
    "shrine": "神社",
    "temple": "寺",
    "castle": "城",
    "ruins": "遺構",
    "archaeological_site": "遺跡",
    "tomb": "墓",
    "boundary_stone": "境界石",
    "milestone": "里程標",
    "building": "歴史的建物",
    "manor": "屋敷",
    "mine": "鉱山",
    "battlefield": "古戦場",
    "church": "教会",
    "fort": "砦",
    "monastery": "修道院",
    "yes": "史跡（種類の記載なし）",
    "feature": "地物",
}
EXTRA = {"hazard:name": "災害の名", "start_date": "年代", "wikipedia": "Wikipedia"}
FUDE_CAVEAT_JA = (
    "筆ポリゴンは農地の位置と形の参考で、面積調査のために空中写真の上に手で描き、田/畑は目で読んだ物。"
    "筆界も権利も示さない"
)

_DIST = r"[\d.,]+ (?:km|m)"
_DIR = r"N|NE|E|SE|S|SW|W|NW"


def _d(m: re.Match, name: str) -> str:
    """距離と方角の組（"3.0 km SW"）→ "3.0 km 南西"。"""
    return f"{m[name]} {DIRECTIONS[m[name + '_dir']]}"


def _around(s: str) -> str:
    m = re.fullmatch(r"within (\d+) m, (\d+) (other )?parcels(?: \(([^)]*)\))?", s)
    if not m:
        return s
    split = re.sub(r"(\d+) (田|畑|\?)", r"\2 \1", m[4] or "").replace(", ", "、")
    return f"{m[1]} m 以内に{'他に' if m[3] else ''} {m[2]} 筆" + (f"（{split}）" if split else "")


def _parcel_said(s: str) -> str:
    m = re.fullmatch(
        r"the field point lies in a parcel of ([\d,.]+) m², read as (\S+) in (\S+) \(id ([^)]+)\); (.+)", s
    )
    if m:
        return f"畑の地点は {m[1]} m² の筆の中にある。{m[3]} 年に {m[2]} と読まれた（id {m[4]}）。{_around(m[5])}"
    m = re.fullmatch(
        r"the field point lies in no parcel \(land outside the 面積調査, such as a garden\); (.+)", s
    )
    if m:
        return f"畑の地点はどの筆にも入らない（庭など、面積調査の外の土地）。{_around(m[1])}"
    return s


def _extra(s: str) -> str:
    parts = []
    for p in s.split("; "):
        k, _, v = p.partition(": ")
        parts.append(f"{EXTRA.get(k, k)}: {v}" if v else p)
    return "。".join(parts)


RULES: list[tuple[re.Pattern, Callable[[re.Match], str]]] = [
    # 住所（国土地理院 逆ジオコーダ）
    (
        re.compile(r"Address: none at this point \(sea or outside Japan\)"),
        lambda m: "住所: この地点には無い（海か日本の外）",
    ),
    (
        re.compile(r"Address: (.+?) \(市区町村コード (\d+)\)"),
        lambda m: f"住所: {m[1]}（市区町村コード {m[2]}）",
    ),
    # 筆ポリゴン（農林水産省）と 全国農地ナビ
    (
        re.compile(
            r"Parcel \(筆ポリゴン\): (.+?)\. 筆ポリゴン are reference for .+? neither 筆界 nor rights"
        ),
        lambda m: f"筆ポリゴン: {_parcel_said(m[1])}。{FUDE_CAVEAT_JA}",
    ),
    (
        re.compile(
            r"全国農地ナビ \(eMAFF農地ナビ\): the 農業委員会's farmland map, .+? search the address above"
        ),
        lambda m: (
            "全国農地ナビ（eMAFF農地ナビ）: 農業委員会の農地の地図。農振の区分と、遊休かどうかが分かる。"
            "リンクに座標は付けられないので、上の住所で探す"
        ),
    ),
    # 標高（国土地理院 標高API）
    (re.compile(r"Elevation ([\d.\-]+) m \(DEM: (.*)\)"), lambda m: f"標高 {m[1]} m（DEM: {m[2]}）"),
    (
        re.compile(r"Elevation: no value here in the GSI DEM"),
        lambda m: "標高: 国土地理院の DEM にこの地点の値が無い",
    ),
    # 地形分類（国土地理院 ベクトルタイル）
    (
        re.compile(r"(Landform|Made ground): (.+?) \((.+?); code (\w+)\)"),
        lambda m: (
            f"{'地形分類' if m[1] == 'Landform' else '人工地形'}: "
            f"{'不明な区分' if m[2] == 'unknown class' else m[2]}（{m[3]}、コード {m[4]}）"
        ),
    ),
    (re.compile(r"Landform: not mapped at this point"), lambda m: "地形分類: この地点は未整備"),
    # 活断層（国土地理院 活断層図）
    (
        re.compile(
            r"Active faults: no 活断層図 sheet covers this area \(it maps the faults near cities only\)"
        ),
        lambda m: "活断層: この範囲を覆う活断層図の図葉が無い（都市圏の断層だけが対象）",
    ),
    (
        re.compile(rf"Active faults: no fault line on the 活断層図 within ({_DIST})"),
        lambda m: f"活断層: {m[1]} 以内に活断層図の断層線は無い",
    ),
    (
        re.compile(
            rf"Active faults: nearest fault line (?P<d1>{_DIST}) (?P<d1_dir>{_DIR})"
            rf"(?:; on the other side (?P<d2>{_DIST}) (?P<d2_dir>{_DIR}))?"
            rf" \(an estimate: red lines read by colour from the map image, searched (?P<reach>{_DIST}) round;"
            r" the tiles carry no fault names\)"
        ),
        lambda m: (
            f"活断層: 最も近い断層線は {_d(m, 'd1')}"
            + (f"。反対側に {_d(m, 'd2')}" if m["d2"] else "")
            + f"（推定: 地図の画像の赤い線を色で読んだ物。{m['reach']} の範囲を探した。タイルに断層の名は無い）"
        ),
    ),
    # 土砂災害警戒区域・洪水浸水想定区域（ハザードマップポータルサイト）
    (
        re.compile(r"(\S+): the field is INSIDE one \(([^)]*)\)"),
        lambda m: f"{m[1]}: 畑はその中にある（{m[2]}）",
    ),
    (
        re.compile(rf"(\S+): the field is outside; nearest (?P<d>{_DIST}) (?P<d_dir>{_DIR}) \(([^)]*)\)"),
        lambda m: f"{m[1]}: 畑は外。最も近い物は {_d(m, 'd')}（{m[4]}）",
    ),
    (
        re.compile(rf"(\S+): the field is outside; none within ({_DIST})"),
        lambda m: f"{m[1]}: 畑は外。{m[2]} 以内に無い",
    ),
    # 土壌（農研機構 日本土壌インベントリー）
    (
        re.compile(
            r"Soil type: (.+?) \(([^)]+)\)\.(?: (.*?))? ?The soil map contains errors \(誤差を含む\), "
            r"read from the map colour at the point"
        ),
        lambda m: (
            f"土壌: {m[1]}（{m[2]}）。"
            + (f"{m[3].strip()} " if m[3] else "")
            + "土壌図には誤差が含まれる。地点の地図の色から読んだ"
        ),
    ),
    (
        re.compile(r"Soil type: the soil map has no tile here \(outside its coverage\)"),
        lambda m: "土壌: 土壌図のタイルがこの地点に無い（範囲の外）",
    ),
    (
        re.compile(r"Soil type: not mapped at this point \(no colour on the soil map\)"),
        lambda m: "土壌: この地点は未整備（土壌図に色が無い）",
    ),
    (
        re.compile(
            r"Soil type: the map's colour here, RGB (\(.*?\)|\S+), is not in its legend; not guessed\. Look at the map: (\S+)"
        ),
        lambda m: f"土壌: この地点の地図の色 RGB {m[1]} は凡例に無い。推測しない。地図を見る: {m[2]}",
    ),
    # 史跡（OpenStreetMap の historic）
    (
        re.compile(rf"(.+?) \(([\w:]+), (?P<d>{_DIST}) (?P<d_dir>{_DIR})(?:; (.+))?\)"),
        lambda m: (
            f"{m[1]}（{KINDS.get(m[2], m[2])}、{_d(m, 'd')}" + (f"。{_extra(m[5])}" if m[5] else "") + "）"
        ),
    ),
]


def to_ja(text: str) -> str:
    """英語の枠の一行 → 日本語。枠に合わなければそのまま。"""
    for rx, make in RULES:
        m = rx.fullmatch(text)
        if m:
            return make(m)
    return text


def is_ja(language: str | None) -> bool:
    return bool(language) and language.split("-")[0].split("_")[0].lower() == "ja"
