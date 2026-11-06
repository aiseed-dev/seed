# SPDX-License-Identifier: AGPL-3.0-or-later
"""公開の受け取りと取り下げ（設計書 §7.1、§10）。

受け取った Markdown は records.Public で読み、check() を通った物だけを public/<id>.md に書く。
書くのは読み直した形（決めた鍵と行だけ）で、受け取った文そのものではない。
id の持ち主は public/.owners.json（id → token のハッシュ）。上書きと取り下げは同じ token からだけ。
座標（設計書 §5.2）: 前書きの coord は小数 2 桁（約 1 km）に丸めて置く。前書きの他の欄と本文に
小数 3 桁以上の緯度経度らしい対があれば 400 で拒む（人の了解の無い細かい座標を静的ページに出さない）。
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import yaml

from .. import index
from .. import records as R
from .limits import token_hash
from .settings import Settings

MARKDOWN_MAX = 64 * 1024
TOKEN_MIN, TOKEN_MAX = 16, 200

# 公開と繋がりの書き込みは一つずつ（索引と持ち主の表を壊さないため）
write_lock = threading.Lock()


class PublishError(Exception):
    def __init__(self, status: int, reasons: list[str]):
        super().__init__("; ".join(reasons))
        self.status = status
        self.reasons = reasons


def check_token(token: str | None) -> str:
    if not token or not TOKEN_MIN <= len(token) <= TOKEN_MAX:
        raise PublishError(400, [f"token は {TOKEN_MIN}〜{TOKEN_MAX} 字"])
    return token


def coarsen(pub: R.Public) -> None:
    """前書きの coord を小数 2 桁に丸める（送る側の coarse_coord と同じ。§5.2）。"""
    if pub.coord is not None and len(pub.coord) == 2:
        pub.coord = R.coarse_coord(pub.coord)


def load_owners(path: Path) -> dict[str, str]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_owners(path: Path, owners: dict[str, str]) -> None:
    tmp = Path(path).with_suffix(".tmp")
    tmp.write_text(json.dumps(owners, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def owned_by(settings: Settings, record_id: str, token: str) -> bool:
    return load_owners(settings.owners_path).get(record_id) == token_hash(token)


def public_path(settings: Settings, record_id: str) -> Path:
    if not R.ID_RE.match(record_id):
        raise PublishError(400, ["id は [a-z0-9-]+"])
    return settings.public_dir / f"{record_id}.md"


def rebuild(settings: Settings) -> dict:
    """索引を作り直し、静的サイト（site/）も書き出す（設計書 §7.5）。"""
    from . import pages  # 循環を避ける

    idx = index.write_index(settings.public_dir, settings.connections_dir, settings.index_path)
    try:
        pages.write_site(settings)
    except OSError:
        pass  # 静的サイトが書けなくても API は動く
    return idx


def publish(settings: Settings, token: str, markdown: str) -> R.Public:
    """公開ファイルを受け取って書く。合わなければ PublishError（400 は形、403 は持ち主）。"""
    check_token(token)
    if len(markdown.encode("utf-8")) > MARKDOWN_MAX:
        raise PublishError(413, [f"公開ファイルは {MARKDOWN_MAX // 1024} KB まで"])
    try:
        pub = R.Public.parse(markdown.replace("\r\n", "\n"))
    except (ValueError, TypeError, KeyError) as e:
        raise PublishError(400, [str(e)]) from e
    except yaml.YAMLError as e:
        raise PublishError(400, [f"前書きを読めない: {type(e).__name__}"]) from e
    coarsen(pub)
    if R.fine_coords(pub.render()):
        raise PublishError(
            400, ["小数 3 桁以上の座標らしい数がある（座標は前書きの coord に、小数 2 桁まで）"]
        )
    bad = pub.check()
    if bad:
        raise PublishError(400, bad)
    path = public_path(settings, pub.id)
    h = token_hash(token)
    with write_lock:
        settings.public_dir.mkdir(parents=True, exist_ok=True)
        owners = load_owners(settings.owners_path)
        owner = owners.get(pub.id)
        if (owner and owner != h) or (path.exists() and not owner):
            raise PublishError(403, ["この id は別の人が公開している"])
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(pub.render(), encoding="utf-8")
        os.replace(tmp, path)
        owners[pub.id] = h
        save_owners(settings.owners_path, owners)
        rebuild(settings)
    return pub


def withdraw_as_admin(settings: Settings, record_id: str) -> None:
    """動かす人の取り下げ（管理の画面）。持ち主の token を問わない。繋がりの記録は残す。"""
    path = public_path(settings, record_id)
    with write_lock:
        if not path.exists():
            raise PublishError(404, ["その id の公開は無い"])
        owners = load_owners(settings.owners_path)
        path.unlink()
        owners.pop(record_id, None)
        save_owners(settings.owners_path, owners)
        rebuild(settings)


def withdraw(settings: Settings, token: str, record_id: str) -> None:
    """取り下げ。公開ファイルを消して索引から外す。繋がりの記録（connections/<id>/）は残す。"""
    check_token(token)
    path = public_path(settings, record_id)
    with write_lock:
        owners = load_owners(settings.owners_path)
        if not path.exists():
            raise PublishError(404, ["その id の公開は無い"])
        if owners.get(record_id) != token_hash(token):
            raise PublishError(403, ["公開した token からだけ取り下げられる"])
        path.unlink()
        del owners[record_id]
        save_owners(settings.owners_path, owners)
        rebuild(settings)
