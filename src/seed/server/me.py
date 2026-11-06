# SPDX-License-Identifier: AGPL-3.0-or-later
"""Web 版の人の持ち帰りと消去（設計書 §5.3）。

Web 版の記録は SEED_USERS_DIR/<招待コードのハッシュ>/ に本人の形のまま置かれる（700）。
ここでは、招待コードと、その箱の token が揃った時だけ、その箱を zip で返す・消す。
箱は招待コードから決まり、token はその箱の credentials.toml（古い箱は seed.toml）の物と比べる。
他人の箱には届かない（別の招待コードの箱は別の名、token が合わなければ 403）。
"""

from __future__ import annotations

import datetime as dt
import hmac
import io
import os
import shutil
import tomllib
import zipfile
from pathlib import Path

from .. import settings as seed_settings
from .limits import token_hash
from .publish import PublishError, check_token, load_owners, rebuild, save_owners, write_lock
from .settings import Settings, user_slug

SKIP_NAMES = {seed_settings.CREDENTIALS_FILENAME}  # 秘密は zip に入れない


def box_for(settings: Settings, invite: str | None, token: str | None) -> Path:
    """招待コードと token から本人の箱。無ければ 404、token が合わなければ 403。"""
    if settings.users_dir is None:
        raise PublishError(404, ["このサーバーには Web 版の箱が無い"])
    code = (invite or "").strip()
    if not settings.known_invite(code):
        raise PublishError(403, ["招待コードが要る（Discord で渡す）"])
    check_token(token)
    box = settings.users_dir / user_slug(code)
    if not box.is_dir():
        raise PublishError(404, ["箱が無い"])
    stored = stored_token(box)
    if not stored or not hmac.compare_digest(stored.encode("utf-8"), str(token).encode("utf-8")):
        raise PublishError(403, ["この箱の token ではない"])
    return box


def stored_token(box: Path) -> str:
    """箱の token。credentials.toml、無ければ古い形の seed.toml。"""
    for name in (seed_settings.CREDENTIALS_FILENAME, seed_settings.FILENAME):
        try:
            got = tomllib.loads((box / name).read_text(encoding="utf-8")).get("token")
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            continue
        if isinstance(got, str) and got:
            return got
    return ""


def files_of(box: Path) -> list[Path]:
    """zip に入れる物（箱の中の道）。秘密と一時の物と symlink は入れない。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(box, followlinks=False):
        d = Path(dirpath)
        dirnames[:] = sorted(n for n in dirnames if not (d / n).is_symlink())
        for n in sorted(filenames):
            p = d / n
            if n in SKIP_NAMES or n.endswith(".tmp") or p.is_symlink() or not p.is_file():
                continue
            out.append(p.relative_to(box))
    return out


def export_zip(box: Path) -> bytes:
    """箱を丸ごと zip に（photos、observations、plan.md、public、seed.toml、他の本人の物）。

    seed.toml は秘密を落とした形で入れる（古い箱で token が残っていても出さない）。
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files_of(box):
            path = box / rel
            if rel.as_posix() == seed_settings.FILENAME:
                try:
                    st = seed_settings.Settings.parse(path.read_text(encoding="utf-8"))
                    z.writestr(rel.as_posix(), st.render())
                    continue
                except (UnicodeDecodeError, tomllib.TOMLDecodeError):
                    continue  # 読めない設定は入れない（秘密が混じっているかもしれない）
            z.write(path, rel.as_posix())
    return buf.getvalue()


def export_name() -> str:
    return f"seed-{dt.date.today().isoformat()}.zip"


def delete_box(settings: Settings, box: Path, token: str) -> list[str]:
    """本人が公開した物を全部取り下げ、箱を消し、site を書き直す。取り下げた id を返す。"""
    h = token_hash(token)
    with write_lock:
        owners = load_owners(settings.owners_path)
        mine = sorted(rid for rid, owner in owners.items() if owner == h)
        for rid in mine:
            (settings.public_dir / f"{rid}.md").unlink(missing_ok=True)
            del owners[rid]
        if mine:
            save_owners(settings.owners_path, owners)
        shutil.rmtree(box)
        rebuild(settings)
    return mine
