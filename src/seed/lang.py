# SPDX-License-Identifier: AGPL-3.0-or-later
"""言語。ファイルの中の決まった語は英語のまま、表示だけを本人の言語にする（docs/記録の形.md §2）。

既定の言語は OS の物。設定（seed.toml の language）があればそれが勝つ。
"""

from __future__ import annotations

import locale
import os
import re

from . import records as R

FALLBACK = "en"
LANG_TAG_RE = re.compile(r"^[A-Za-z]{2,3}")


def normalize(tag: str | None) -> str | None:
    """'ja_JP.UTF-8' や 'en-US' → 'ja', 'en'。読めなければ None。"""
    if not tag:
        return None
    m = LANG_TAG_RE.match(tag.strip())
    if not m or tag.strip().upper().startswith("C") and len(tag.strip()) <= 2:
        return None
    short = m.group(0).lower()
    return None if short in ("c", "posix") else short


def os_language() -> str | None:
    """OS の言語。環境変数（LANGUAGE, LC_ALL, LC_MESSAGES, LANG）→ locale → Windows の UI 言語。"""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = normalize((os.environ.get(var) or "").split(":")[0])
        if v:
            return v
    try:
        v = normalize(locale.getlocale()[0])
        if v:
            return v
    except ValueError:
        pass
    if os.name == "nt":
        try:
            import ctypes

            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
            return normalize(locale.windows_locale.get(lang_id))
        except Exception:  # noqa: BLE001 — 取れなければ無いだけ
            return None
    return None


def default_language(configured: str | None = None) -> str:
    """設定 → OS → en。"""
    return normalize(configured) or os_language() or FALLBACK


# 表示の語。ファイルには書かない
STRINGS: dict[str, dict[str, str]] = {
    "en": {
        R.H_READING: "Reading",
        R.H_EARLIER: "Earlier reading",
        R.H_PLAN: "Plan",
        R.H_PLAN_EARLIER: "Earlier plan",
        R.H_DATA: "Data",
        R.H_RECORD: "Record",
        "right": "right",
        "wrong": "wrong",
        "unjudged": "not yet judged",
        R.EMPTY: "(none)",
        "Sell": "Sell",
        "Process": "Process",
        "Host or teach": "Host or teach",
        "Paperwork": "Paperwork",
        "prefecture": "region",
        "city": "municipality",
        "oaza": "locality",
    },
    "ja": {
        R.H_READING: "読み",
        R.H_EARLIER: "前の読み",
        R.H_PLAN: "計画",
        R.H_PLAN_EARLIER: "前の計画",
        R.H_DATA: "資料",
        R.H_RECORD: "本人",
        "right": "合う",
        "wrong": "違う",
        "unjudged": "まだ見ていない",
        R.EMPTY: "（なし）",
        "Sell": "売る",
        "Process": "加工",
        "Host or teach": "宿や教室",
        "Paperwork": "手続き",
        "prefecture": "都道府県",
        "city": "市町村",
        "oaza": "大字",
    },
}


def t(word: str, language: str) -> str:
    """表示の語。無い言語は en、en にも無ければそのまま。"""
    return STRINGS.get(language, {}).get(word) or STRINGS[FALLBACK].get(word) or word
