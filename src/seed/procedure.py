# SPDX-License-Identifier: AGPL-3.0-or-later
"""手続きの下書き procedures/<slug>/（docs/記録の形.md §18）。今は nochi-3jo（農地法 3 条）だけ。

AI（このコード）が書く物は全部下書きで、判定（許可が要る・要らない）は書かない。窓口（農業委員会）で決めてもらう。
作り直すと下書きの行は置き換わり、本人の [x]、本人が書き換えた欄、本人が足した行は残る。
条文の本文は長く引かない。条番号と url と確認日だけ（skill/sources-law.md の A5〜A7）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .records import EMPTY, HEADING_RE, Folder, Plan

SLUG = "nochi-3jo"
HEAD = "これは AI の下書きで、判定ではない。出す前に農業委員会で確かめる。"
SELF = "（本人が書く）"
DRAFT_MARK_RE = re.compile(r"（下書き: [^（）]*）$")
H_CHECKLIST = "Checklist"
H_DRAFT = "Draft"
H_DATA = "Data"
H_RECORD = "Record"

# skill/sources-law.md の A5〜A7（e-Gov 法令検索。確認日 2026-11-05）
CHECKED = "2026-11-05"
LAW = "https://laws.e-gov.go.jp/law/327AC0000000229"  # A5 農地法
REI = "https://laws.e-gov.go.jp/law/327CO0000000445"  # A6 農地法施行令
KISOKU = "https://laws.e-gov.go.jp/law/327M50010000079"  # A7 農地法施行規則
GUIDE = "手引き 13 章「四 手続き（農地法 3 条、地目）」"
GUIDE_2 = "手引き 13 章「二 筆と所有者」"


def src(*names: str) -> str:
    """出典の書き添え。（出典: 名と url、…、確認日 …）"""
    return f"（出典: {'、'.join(names)}、確認日 {CHECKED}）"


def law(where: str) -> str:
    return f"農地法 {where} {LAW} "


def rei(where: str) -> str:
    return f"農地法施行令 {where} {REI} "


def kisoku(where: str) -> str:
    return f"農地法施行規則 {where} {KISOKU} "


# 必要な物の一覧。key は作り直しで本人の [x] を引き継ぐ鍵
CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "window",
        "申請書の出し先は、畑のある市町村の農業委員会。様式と添える書類を窓口で聞く"
        + src(law("第三条第一項"), rei("第一条"), GUIDE),
    ),
    (
        "application",
        "申請書。書く事項は施行規則 第十一条に並ぶ（draft.md の欄）" + src(rei("第一条"), kisoku("第十一条")),
    ),
    (
        "signatures",
        "当事者（権利を渡す人と受ける人）の連署。第十条第一項のただし書の場合は別"
        + src(kisoku("第十条第一項")),
    ),
    (
        "registry",
        "土地の登記事項証明書（全部事項証明書）。法務局で取る" + src(kisoku("第十条第二項第一号"), GUIDE_2),
    ),
    ("kozu", "地番を法務局の地図（公図）で確かめる。筆ポリゴンは地番を示さない" + src(GUIDE_2)),
    (
        "chimoku",
        "地目。登記簿の地目と現況の地目を並べる（違う時は両方を書く事項）"
        + src(kisoku("第十一条第一項第二号"), GUIDE),
    ),
    (
        "parties",
        "当事者の氏名と住所。土地の所在、地番、地目、面積、所有者の氏名"
        + src(kisoku("第十一条第一項第一号、第二号")),
    ),
    (
        "other_rights",
        "所有権以外の使用収益の権利が付いていれば、その種類と内容" + src(kisoku("第十一条第一項第三号")),
    ),
    (
        "contract",
        "権利を設定・移転する契約の内容（所有権、賃借権、使用貸借など）"
        + src(kisoku("第十一条第一項第四号")),
    ),
    (
        "current_use",
        "権利を取得する人と世帯員等が今持つ・借りる農地の利用の状況" + src(kisoku("第十一条第一項第五号イ")),
    ),
    (
        "machines",
        "耕作に使う機械の所有、農作業に従事する人の数と配置、農業に関する法令の遵守の状況"
        + src(kisoku("第十一条第一項第五号ロ"), law("第三条第二項第一号")),
    ),
    (
        "work_days",
        "個人の場合、権利を取得する人と世帯員等の農作業への従事状況"
        + src(kisoku("第十一条第一項第十号"), law("第三条第二項第四号")),
    ),
    (
        "neighbors",
        "取得後の耕作が、周辺の農地の農業上の利用に及ぼす影響"
        + src(kisoku("第十一条第一項第十二号"), law("第三条第二項第六号")),
    ),
    ("nationality", "所有権を取得する場合は、国籍等" + src(kisoku("第十一条第一項第六号"))),
    (
        "corporation",
        "法人が権利を取得する場合は、定款か寄附行為の写しなど"
        + src(kisoku("第十条第二項第二号、第三号"), law("第三条第二項第二号")),
    ),
    (
        "conditional_lease",
        "第三条第三項（貸借の解除の条件を書面の契約に付ける形）を使う場合は、その契約書の写しと、地域の農業者との役割分担の計画"
        + src(law("第三条第三項"), kisoku("第十条第二項第七号、第十一条第一項第十三号")),
    ),
    ("other_docs", "その他参考となる書類。何を添えるかは窓口で聞く" + src(kisoku("第十条第二項第十一号"))),
    (
        "ask_window",
        "第三条第二項の各号を読み、分からない所を書き出して窓口で聞く。窓口で言われたことは next.md の Paperwork か Record の said に"
        + src(law("第三条第二項"), GUIDE),
    ),
)
CHECK_RE = re.compile(r"^- \[(?P<mark>[ xX])\] (?P<key>[a-z][a-z0-9_]*): ")

# 申請書の下書きの欄（施行規則 第十一条の事項。個人が取得する場合の並び）
FIELDS: tuple[tuple[str, str], ...] = (
    ("applicant", "権利を取得する人の氏名と住所（施行規則 第十一条第一項第一号）"),
    ("counterparty", "権利を設定・移転する人の氏名と住所（同 第一号）"),
    ("location", "土地の所在（同 第二号）"),
    ("chiban", "地番（同 第二号）"),
    ("chimoku_registry", "地目・登記簿（同 第二号）"),
    ("chimoku_current", "現況（同 第二号）"),
    ("area", "面積（同 第二号）"),
    ("owner", "所有者の氏名（同 第二号）"),
    ("other_rights", "所有権以外の権利（同 第三号）"),
    ("contract", "契約の内容（同 第四号）"),
    ("current_use", "今の農地の利用の状況（同 第五号イ）"),
    ("machines", "機械、農作業に従事する人の数と配置、法令の遵守の状況（同 第五号ロ）"),
    ("work_days", "農作業への従事状況（同 第十号）"),
    ("neighbors", "周辺の農地の農業上の利用への影響（同 第十二号）"),
    ("farming_plan", "耕作の計画（同 第十五号 その他参考の事項）"),
)
FIELD_RE = re.compile(r"^- (?P<key>[a-z][a-z0-9_]*): (?P<label>.*?) = (?P<value>.*)$")

SOURCES: tuple[tuple[str, str], ...] = (
    ("nochi_ho", f"農地法（昭和二十七年法律第二百二十九号）第三条{src('e-Gov 法令検索 ' + LAW + ' ')}"),
    (
        "nochi_ho_rei",
        f"農地法施行令（昭和二十七年政令第四百四十五号）第一条{src('e-Gov 法令検索 ' + REI + ' ')}",
    ),
    (
        "nochi_ho_kisoku",
        (
            f"農地法施行規則（昭和二十七年農林省令第七十九号）第十条、第十一条。2027-04-01 施行の改正が e-Gov に載っている"
            f"{src('e-Gov 法令検索 ' + KISOKU + ' ')}"
        ),
    ),
    ("guide", f"{GUIDE}、{GUIDE_2}（skill/13-手続きと農地.md）"),
)
SOURCE_RE = re.compile(r"^- (?P<key>[a-z][a-z0-9_]*): ")

# place.md の照会の行（server/lookup_ja.py の日本語と、英語のまま）
ADDRESS_RES = (
    re.compile(r"住所: (?P<a>.+?)（市区町村コード"),
    re.compile(r"Address: (?P<a>.+?) \(市区町村コード"),
)
PARCEL_RES = (
    re.compile(r"(?P<m2>[\d,.]+) m² の筆の中にある。(?P<year>\d{4}) 年に (?P<use>\S+) と読まれた"),
    re.compile(r"parcel of (?P<m2>[\d,.]+) m², read as (?P<use>\S+) in (?P<year>\d{4})"),
)


@dataclass
class Result:
    out: Path
    filled: list[str]  # 埋めた欄の key
    kept_checks: int  # 引き継いだ [x] の数
    kept_lines: int  # 残した本人の行の数


# ---------------------------------------------------------------- 読む


def _sections(text: str) -> list[tuple[str, list[str]]]:
    """見出しごとの行。見出しの前（頭の一行など）は ('', 行)。"""
    out: list[tuple[str, list[str]]] = [("", [])]
    for raw in text.splitlines():
        m = HEADING_RE.match(raw)
        if m:
            out.append((m["title"], []))
        else:
            out[-1][1].append(raw)
    return out


def _own_lines(text: str, is_draft) -> list[str]:
    """本人が足した行: 見出しの下の、下書きの行でも (none) でも空でもない行。頭の文は下書きなので入れない。"""
    own = []
    for title, lines in _sections(text):
        if not title:
            continue
        for raw in lines:
            if raw.strip() and raw.strip() != EMPTY and not is_draft(raw):
                own.append(raw)
    return own


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ---------------------------------------------------------------- 記録から埋める


def _place_lines(folder: Folder) -> list[str]:
    """place.md の data 行の文。無ければ観察の Data（新しい順）。"""
    texts = [l.text for l in folder.place_data() if l.key in ("place_name", "parcel")]
    if texts:
        return texts
    from .records import Observation

    for path in reversed(folder.list_observations()):
        try:
            obs = Observation.read(path)
        except (ValueError, OSError):
            continue
        got = [l.text for l in obs.data if l.key in ("place_name", "parcel")]
        if got:
            return got
    return []


def fill(folder: Folder) -> dict[str, str]:
    """records から埋められる欄。値は「（下書き: どこから）」で終わる（作り直しで置き換える印）。"""
    out: dict[str, str] = {}
    for text in _place_lines(folder):
        for r in ADDRESS_RES:
            m = r.search(text)
            if m and "location" not in out:
                out["location"] = (
                    f"{m['a'].strip()}。地番は公図で確かめる（下書き: place.md の住所の行。国土地理院の逆ジオコーダ）"
                )
        for r in PARCEL_RES:
            m = r.search(text)
            if m and "area" not in out:
                out["area"] = (
                    f"概算 {m['m2']} m²。筆ポリゴンから計算した数で、測量や登記の数ではない（下書き: place.md の筆ポリゴンの行）"
                )
                out["chimoku_current"] = (
                    f"筆ポリゴンでは {m['year']} 年に {m['use']} と読まれた。筆ポリゴンは位置と形の参考で、地目ではない"
                    "（下書き: place.md の筆ポリゴンの行）"
                )
    if folder.plan.is_file():
        try:
            plan = Plan.read(folder.plan)
        except (ValueError, OSError):
            plan = None
        decided = [l.text for l in (plan.record if plan else []) if l.key == "decided"]
        if decided:
            out["farming_plan"] = "；".join(decided) + "（下書き: plan.md の decided）"
    return out


# ---------------------------------------------------------------- 書く


def _tail(own: list[str]) -> list[str]:
    return ["", f"## {H_RECORD}", "", *(own or [EMPTY]), ""]


def render_checklist(old: str) -> tuple[str, int, int]:
    keys = {k for k, _ in CHECKLIST}
    checked = set()
    for raw in old.splitlines():
        m = CHECK_RE.match(raw)
        if m and m["key"] in keys and m["mark"] in "xX":
            checked.add(m["key"])
    own = _own_lines(old, lambda raw: bool((m := CHECK_RE.match(raw)) and m["key"] in keys))
    lines = [
        HEAD,
        "できた物に [x] を付ける。自分の行は ## Record に書く（作り直しても残る）。",
        "",
        f"## {H_CHECKLIST}",
        "",
    ]
    for key, text in CHECKLIST:
        lines.append(f"- [{'x' if key in checked else ' '}] {key}: {text}")
    return "\n".join(lines + _tail(own)), len(checked), len(own)


def render_draft(old: str, filled: dict[str, str]) -> tuple[str, int]:
    keys = {k for k, _ in FIELDS}
    kept: dict[str, str] = {}
    for raw in old.splitlines():
        m = FIELD_RE.match(raw)
        if m and m["key"] in keys:
            v = m["value"].strip()
            if v and v != SELF and not DRAFT_MARK_RE.search(v):
                kept[m["key"]] = v  # 本人が書き換えた欄
    own = _own_lines(old, lambda raw: bool((m := FIELD_RE.match(raw)) and m["key"] in keys))
    lines = [
        HEAD,
        (
            "申請書の事項（農地法施行規則 第十一条）に沿った欄。様式は農業委員会の物を使う。"
            "「（下書き: …）」で終わる欄と「（本人が書く）」の欄は作り直すと置き換わり、書き換えた欄は残る。"
        ),
        "",
        f"## {H_DRAFT}",
        "",
    ]
    for key, label in FIELDS:
        lines.append(f"- {key}: {label} = {kept.get(key) or filled.get(key) or SELF}")
    return "\n".join(lines + _tail(own)), len(own)


def render_sources(old: str) -> tuple[str, int]:
    keys = {k for k, _ in SOURCES}
    own = _own_lines(old, lambda raw: bool((m := SOURCE_RE.match(raw)) and m["key"] in keys))
    lines = [
        HEAD,
        "引いた条文の url と確認日。条文は e-Gov 法令検索で読む。",
        "",
        f"## {H_DATA}",
        "",
        *(f"- {key}: {text}" for key, text in SOURCES),
    ]
    return "\n".join(lines + _tail(own)), len(own)


def nochi_3jo(folder: Folder) -> Result:
    """procedures/nochi-3jo/ の三つを書く（作り直す）。"""
    out = folder.root / "procedures" / SLUG
    out.mkdir(parents=True, exist_ok=True)
    filled = fill(folder)
    check, n_checked, own1 = render_checklist(_read(out / "checklist.md"))
    draft, own2 = render_draft(_read(out / "draft.md"), filled)
    sources, own3 = render_sources(_read(out / "sources.md"))
    (out / "checklist.md").write_text(check, encoding="utf-8")
    (out / "draft.md").write_text(draft, encoding="utf-8")
    (out / "sources.md").write_text(sources, encoding="utf-8")
    return Result(out, sorted(filled), n_checked, own1 + own2 + own3)


PROCEDURES = {SLUG: nochi_3jo}
