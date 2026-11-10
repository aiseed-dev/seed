# SPDX-License-Identifier: AGPL-3.0-or-later
"""Meta の Model API（11-11 に fieldnotes から）。Claude に無い二つにだけ使う: SAM 3.1（sam.py）と Muse Voice Transcribe（voice.py）。

鍵は credentials.toml の meta_key（設定の秘密。seed.toml には書かない）。無ければ環境変数 MODEL_API_KEY、
それも無ければ fieldnotes の置き場 ~/.config/fieldnotes/model_api_key（前に fieldnotes を使っていた PC のため）。
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_URL = "https://api.meta.ai/v1"
ENV_KEY = "MODEL_API_KEY"


class MetaKeyMissing(RuntimeError):
    """Meta の鍵が無い。SAM と声の書き取りはできない（ほかは動く）。"""


def _old_place() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "fieldnotes" / "model_api_key"


def api_key(settings=None) -> str:
    key = getattr(settings, "meta_key", "") if settings is not None else ""
    if not key and settings is None:
        try:
            from . import settings as settings_mod

            key = str(settings_mod.read_credentials(settings_mod.credentials_path()).get("meta_key") or "")
        except Exception:  # noqa: BLE001 — 読めなければ次の置き場
            key = ""
    key = key or os.environ.get(ENV_KEY, "")
    if not key and _old_place().exists():
        key = _old_place().read_text(encoding="utf-8").strip()
    if not key:
        raise MetaKeyMissing("no Meta Model API key (credentials.toml meta_key)")
    return key


def available(settings=None) -> bool:
    try:
        api_key(settings)
    except MetaKeyMissing:
        return False
    return True
