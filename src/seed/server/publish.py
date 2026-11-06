# SPDX-License-Identifier: AGPL-3.0-or-later
"""公開の受け取りと取り下げ（設計書 §7.1、§10）。

受け取った Markdown は records.Public で読み、check() を通った物だけを public/<id>.md に書く。
書くのは読み直した形（決めた鍵と行だけ）で、受け取った文そのものではない。
id の持ち主は public/.owners.json（id → token のハッシュ）。上書きと取り下げは同じ token からだけ。
座標（設計書 §5.2）: 前書きの coord は小数 2 桁（約 1 km）に丸めて置く。前書きの他の欄と本文に
小数 3 桁以上の緯度経度らしい対があれば 400 で拒む（人の了解の無い細かい座標を静的ページに出さない）。
写真: 本文の `photo` の行が指す写真だけを受け、Pillow で開いて書き直し（RGB、長い辺 1280、EXIF 無し）、
public/photos/<id>/<名> に置く。端末が何を送っても、位置の情報はここに残らない。指されなくなった写真は消す。
"""

from __future__ import annotations

import base64
import binascii
import datetime as dt
import io
import json
import os
import re
import shutil
import threading
from pathlib import Path

import yaml

from .. import index
from .. import records as R
from .limits import token_hash
from .settings import Settings

MARKDOWN_MAX = 64 * 1024
TOKEN_MIN, TOKEN_MAX = 16, 200
JPEG_MAGIC = b"\xff\xd8\xff"
PHOTO_PIXELS_MAX = 60_000_000  # 開く前に見る画素の数の上限（小さなファイルで大きな絵を言う物を断る）
PHOTO_QUALITY = 85

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


def photos_dir(settings: Settings, record_id: str) -> Path:
    """その記録の写真の置き場 public/photos/<id>/。"""
    return settings.public_dir / "photos" / record_id


def decode_photos(raw: object) -> dict[str, bytes]:
    """要求の photos（名 → base64 の JPEG）を読む。名の形、JPEG の頭、一枚の大きさ、枚数を見る。"""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PublishError(400, ["photos は 名 → base64 の JPEG"])
    if len(raw) > R.PUBLIC_PHOTOS_MAX:
        raise PublishError(400, [f"写真は {R.PUBLIC_PHOTOS_MAX} 枚まで"])
    out: dict[str, bytes] = {}
    for name, b64 in raw.items():
        if not R.safe_photo_name(name):
            raise PublishError(400, [f"写真の名は英数字と ._-、終わりは .jpg: {str(name)[:60]!r}"])
        if not isinstance(b64, str):
            raise PublishError(400, [f"写真は base64 の文字: {name}"])
        if len(b64) > (R.PUBLIC_PHOTO_BYTES + 2) * 4 // 3 + 4:
            raise PublishError(413, [f"写真は一枚 {R.PUBLIC_PHOTO_BYTES // 1024} KB まで: {name}"])
        try:
            data = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError):
            raise PublishError(400, [f"写真の base64 を読めない: {name}"]) from None
        if len(data) > R.PUBLIC_PHOTO_BYTES:
            raise PublishError(413, [f"写真は一枚 {R.PUBLIC_PHOTO_BYTES // 1024} KB まで: {name}"])
        if not data.startswith(JPEG_MAGIC):
            raise PublishError(400, [f"写真は JPEG だけ: {name}"])
        out[name] = data
    return out


def clean_photo(name: str, data: bytes) -> bytes:
    """Pillow で開いて書き直す（向きを画素に焼き、RGB、長い辺 PUBLIC_PHOTO_SIDE まで、EXIF 無し）。開けなければ 400。"""
    from PIL import Image, ImageOps, UnidentifiedImageError

    side = R.PUBLIC_PHOTO_SIDE
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format != "JPEG":
                raise PublishError(400, [f"写真は JPEG だけ: {name}"])
            if img.width * img.height > PHOTO_PIXELS_MAX:
                raise PublishError(400, [f"写真が大きすぎる: {name}"])
            img.draft("RGB", (side, side))  # 縮めて読む（速く、少ない記憶で）
            out = ImageOps.exif_transpose(img).convert("RGB")
        out.thumbnail((side, side), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=PHOTO_QUALITY, optimize=True)  # exif を渡さない
        return buf.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise PublishError(400, [f"写真を開けない: {name}"]) from None


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def remove_photos(settings: Settings, record_id: str) -> None:
    shutil.rmtree(photos_dir(settings, record_id), ignore_errors=True)


def rebuild(settings: Settings) -> dict:
    """索引を作り直し、静的サイト（site/）も書き出す（設計書 §7.5）。"""
    from . import pages  # 循環を避ける

    idx = index.write_index(settings.public_dir, settings.connections_dir, settings.index_path)
    try:
        pages.write_site(settings)
    except OSError:
        pass  # 静的サイトが書けなくても API は動く
    return idx


def publish(settings: Settings, token: str, markdown: str, photos: object = None) -> R.Public:
    """公開ファイルと、その photo の行が指す写真を受け取って書く。合わなければ PublishError（400 は形、403 は持ち主）。

    photos は 名 → base64 の JPEG（無くてもよい。前に置いた写真はそのまま使える）。
    """
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
    names = pub.photo_names()
    incoming = decode_photos(photos)
    stray = [n for n in incoming if n not in names]
    if stray:
        raise PublishError(400, [f"photo の行が指していない写真: {', '.join(stray)}"])
    cleaned = {n: clean_photo(n, b) for n, b in incoming.items()}
    path = public_path(settings, pub.id)
    h = token_hash(token)
    with write_lock:
        settings.public_dir.mkdir(parents=True, exist_ok=True)
        owners = load_owners(settings.owners_path)
        owner = owners.get(pub.id)
        if (owner and owner != h) or (path.exists() and not owner):
            raise PublishError(403, ["この id は別の人が公開している"])
        folder = photos_dir(settings, pub.id)
        missing = [n for n in names if n not in cleaned and not (folder / n).is_file()]
        if missing:
            raise PublishError(400, [f"photo の行が指す写真が無い: {', '.join(missing)}"])
        if cleaned:
            folder.mkdir(parents=True, exist_ok=True)
        for n, data in cleaned.items():
            _write_atomic(folder / n, data)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(pub.render(), encoding="utf-8")
        os.replace(tmp, path)
        if folder.is_dir():  # もう指されていない写真を消す
            for old in folder.iterdir():
                if old.name not in names:
                    old.unlink(missing_ok=True)
        owners[pub.id] = h
        save_owners(settings.owners_path, owners)
        rebuild(settings)
    return pub


def withdraw_as_admin(settings: Settings, record_id: str) -> None:
    """動かす人の取り下げ（管理の画面）。持ち主の token を問わない。写真は消し、繋がりの記録は残す。"""
    path = public_path(settings, record_id)
    with write_lock:
        if not path.exists():
            raise PublishError(404, ["その id の公開は無い"])
        owners = load_owners(settings.owners_path)
        path.unlink()
        remove_photos(settings, record_id)
        owners.pop(record_id, None)
        save_owners(settings.owners_path, owners)
        rebuild(settings)


def withdraw(settings: Settings, token: str, record_id: str) -> None:
    """取り下げ。公開ファイルと写真を消して索引から外す。繋がりの記録（connections/<id>/）は残す。"""
    check_token(token)
    path = public_path(settings, record_id)
    with write_lock:
        owners = load_owners(settings.owners_path)
        if not path.exists():
            raise PublishError(404, ["その id の公開は無い"])
        if owners.get(record_id) != token_hash(token):
            raise PublishError(403, ["公開した token からだけ取り下げられる"])
        path.unlink()
        remove_photos(settings, record_id)
        del owners[record_id]
        save_owners(settings.owners_path, owners)
        rebuild(settings)


# ---- 管理の画面のため（設計書 §5.10）。公開した人の名前と、寄せられた一言を見る・消す

PUBLISHERS = ".publishers.json"  # id → 門で通した名前（.owners.json のハッシュは持ち主の token の物で、門の名前は引けない）
CONNECTION_NAME_RE = re.compile(r"^[0-9a-z-]+$")


def publishers_path(settings: Settings) -> Path:
    return settings.public_dir / PUBLISHERS


def note_publisher(settings: Settings, record_id: str, name: str) -> None:
    """公開した人の名前を残す（公開が通った後に呼ぶ）。名前の無い時（開発中の open）は書かない。"""
    if not name or not R.ID_RE.match(record_id):
        return
    path = publishers_path(settings)
    with write_lock:
        names = load_owners(path)
        names[record_id] = name
        save_owners(path, names)


def publisher_of(settings: Settings, record_id: str) -> str:
    """公開した人の名前。残っていなければ ""（この仕組みより前の公開など）。"""
    return str(load_owners(publishers_path(settings)).get(record_id, ""))


def published_on(settings: Settings, record_id: str) -> str:
    """公開した日（公開ファイルの更新日。上書きすれば新しい日になる）。"""
    try:
        mtime = public_path(settings, record_id).stat().st_mtime
    except (OSError, PublishError):
        return ""
    return dt.datetime.fromtimestamp(mtime).date().isoformat()


def connections(settings: Settings, record_id: str) -> list[dict]:
    """その公開に寄せられた一言（新しい物が先）。name はファイルの名の幹で、消す時に使う。"""
    if not R.ID_RE.match(record_id):
        raise PublishError(400, ["id は [a-z0-9-]+"])
    folder = settings.connections_dir / record_id
    out = []
    for f in sorted(folder.glob("*.md"), reverse=True) if folder.is_dir() else []:
        for line in f.read_text(encoding="utf-8").splitlines():
            c = R.Connection.parse(line)
            if c is not None:
                out.append({"name": f.stem, "date": c.date, "from": c.src, "word": c.word})
    return out


def remove_connection(settings: Settings, record_id: str, name: str) -> str:
    """寄せられた一言を一件消し、索引と頁を作り直す。消した物の日を返す（記録に書くため）。"""
    if not R.ID_RE.match(record_id) or not CONNECTION_NAME_RE.match(name):
        raise PublishError(400, ["id と name は [0-9a-z-]+"])
    path = settings.connections_dir / record_id / f"{name}.md"
    with write_lock:
        if not path.is_file():
            raise PublishError(404, ["その一言は無い"])
        path.unlink()
        rebuild(settings)
    return name[:10]
