# SPDX-License-Identifier: AGPL-3.0-or-later
"""繋がり（設計書 §5.7、§7.1、§10）。一言を connections/<to>/<YYYY-MM-DD>-<鍵>.md に一行で置く。

seed は伝言を持たない（会話は Discord）。ここにあるのは「誰から誰へ、いつ、一言」と数だけ。
送り手は二通り:
- アプリから（token あり）: from は、その token が公開している id か、公開していない人なら
  token のハッシュの先頭 8 桁（設計書 §13.4 の案）。ほかの人の id を名乗っては送れない。
- Web の閲覧ページから（token 無し）: from は呼び名の文字列。公開されている id と同じ名は使えない。
  回数は呼ぶ側（main）が IP ごとに数える。
同じ from → to は 1 日 1 回。
"""

from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Callable

from .. import index
from .. import records as R
from . import clean_text
from .limits import token_hash
from .publish import PublishError, check_token, load_owners, public_path, rebuild, write_lock
from .settings import Settings

NAME_MAX = 40


def anonymous_id(token: str) -> str:
    return token_hash(token)[:8]


def _word(word: str) -> str:
    word = clean_text(word or "")
    if not word:
        raise PublishError(400, ["word が無い"])
    if len(word) > R.WORD_MAX:
        raise PublishError(400, [f"word は {R.WORD_MAX} 字まで"])
    if R.HTML_RE.search(word):
        raise PublishError(400, ["HTML は書かない"])
    if R.PERSONAL_RE.search(word):
        raise PublishError(400, ["電話、メール、郵便番号の形の文がある"])
    return word


def _name(name: str, owners: dict[str, str]) -> str:
    """呼び名 → 行の from。空白は _ に（行の文法で from は空白を含まない）。"""
    name = clean_text(name or "").replace(" ", "_")
    if not name:
        raise PublishError(400, ["from（呼び名）が無い"])
    if len(name) > NAME_MAX:
        raise PublishError(400, [f"呼び名は {NAME_MAX} 字まで"])
    if R.HTML_RE.search(name) or "→" in name or name.endswith(":"):
        raise PublishError(400, ["呼び名に使えない文字がある"])
    if R.PERSONAL_RE.search(name):
        raise PublishError(400, ["電話、メール、郵便番号の形の文がある"])
    if name in owners:
        raise PublishError(403, ["公開されている id と同じ呼び名は使えない"])
    return name


def connect(
    settings: Settings,
    token: str | None,
    to: str,
    src: str,
    word: str,
    charge: Callable[[], None] | None = None,
) -> int:
    """一言を置いて、to の繋がりの数を返す。charge は検査が通ってから書く前に呼ぶ（回数の上限）。"""
    word = _word(word)
    if not public_path(settings, to).exists():
        raise PublishError(404, ["その id の公開は無い"])
    owners = load_owners(settings.owners_path)
    if token is not None:
        check_token(token)
        if not R.ID_RE.match(src or ""):
            raise PublishError(400, ["from は [a-z0-9-]+"])
        if owners.get(src) != token_hash(token) and src != anonymous_id(token):
            raise PublishError(403, ["from は自分の公開の id か、token から作った名前だけ"])
        key = src
    else:
        src = _name(src, owners)
        # ファイルの名に呼び名をそのまま使わない（道の文字を避ける）
        key = "n-" + hashlib.sha256(src.encode("utf-8")).hexdigest()[:8]
    if src == to:
        raise PublishError(400, ["自分には送れない"])

    day = dt.date.today().isoformat()
    folder = settings.connections_dir / to
    path = folder / f"{day}-{key}.md"
    with write_lock:
        if path.exists():
            raise PublishError(429, ["同じ相手には 1 日 1 回"])
        if charge:
            charge()
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(R.Connection(day, src, to, word).render() + "\n", encoding="utf-8")
        rebuild(settings)
    return index.count_connections(settings.connections_dir, to)
