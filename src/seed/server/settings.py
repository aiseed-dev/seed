# SPDX-License-Identifier: AGPL-3.0-or-later
"""サーバーの設定。環境変数だけから読む。

.env は読まない。deb2 では systemd の EnvironmentFile（/etc/seed/env）が入れる。
API キーはここにだけ入り、ログにも応答にも出さない。
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_SKILL_DIR = Path(__file__).resolve().parents[3] / "skill"

log = logging.getLogger("seed.server")


def _int(name: str, default: int) -> int:
    v = os.environ.get(name, "").strip()
    return int(v) if v else default


def _float(name: str, default: float) -> float:
    v = os.environ.get(name, "").strip()
    return float(v) if v else default


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    public_dir: Path
    daily_usd: float
    daily_reads: int
    per_token_reads: int
    per_ip_reads: int
    model: str
    skill_dir: Path
    invites: dict[str, str] = field(default_factory=dict)  # 招待コード → 呼び名（設計書 §7.5）
    open: bool = False  # True なら招待コード無しでも API を受ける（開発中だけ。SEED_OPEN=1）
    invites_path: Path | None = None  # SEED_INVITES。あれば要求ごとに stat し、変わっていれば読み直す
    # SEED_PUBLIC_URL。公開の url の外から見た基底（https://seed.aiseed.dev）。空なら要求の base_url から作る
    public_url: str = ""
    # SEED_USERS_DIR。Web 版の人ごとの箱の親（設計書 §5.3）。無ければ持ち帰りと消去の口は 404
    users_dir: Path | None = None
    _book: InviteBook = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_book", InviteBook(self.invites_path, self.invites))

    @property
    def connections_dir(self) -> Path:
        return self.public_dir / "connections"

    @property
    def index_path(self) -> Path:
        return self.public_dir / "index.json"

    @property
    def owners_path(self) -> Path:
        return self.public_dir / ".owners.json"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
            public_dir=Path(os.environ.get("SEED_PUBLIC_DIR") or "/var/lib/seed/public"),
            daily_usd=_float("SEED_DAILY_USD", 20.0),
            daily_reads=_int("SEED_DAILY_READS", 200),
            per_token_reads=_int("SEED_PER_TOKEN_READS", 10),
            per_ip_reads=_int("SEED_PER_IP_READS", 20),
            model=os.environ.get("SEED_MODEL") or "claude-opus-5-5",
            skill_dir=Path(os.environ.get("SEED_SKILL_DIR") or REPO_SKILL_DIR),
            invites_path=Path(p) if (p := os.environ.get("SEED_INVITES")) else None,
            open=os.environ.get("SEED_OPEN", "").strip() in ("1", "true", "yes"),
            public_url=os.environ.get("SEED_PUBLIC_URL", "").strip(),
            users_dir=Path(u).expanduser() if (u := os.environ.get("SEED_USERS_DIR", "").strip()) else None,
        )

    @property
    def site_dir(self) -> Path:
        """静的サイト（index.html、p/<id>.html、index.json、public/<id>.md）。Caddy はここだけを配る。"""
        return self.public_dir / "site"

    def known_invite(self, code: str | None) -> bool:
        """一覧にある招待コードか（open でも一覧で決める。Web 版の箱を開くのに使う）。"""
        code = (code or "").strip()
        return bool(code) and code in self._book.codes()

    def invite_name(self, code: str | None) -> str | None:
        """招待コードの呼び名。無ければ None。open なら無しでも "" を返す（通す）。"""
        code = (code or "").strip()
        codes = self._book.codes()
        if code and code in codes:
            return codes[code]
        return "" if self.open else None


def user_slug(code: str) -> str:
    """Web 版の人ごとの箱の名（招待コードのハッシュの頭 16 桁）。app と server で同じ物を使う。"""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()[:16]


def _parse_invites(text: str) -> dict[str, str]:
    codes = tomllib.loads(text).get("codes") or {}
    if not isinstance(codes, dict):
        raise TypeError("[codes] が表でない")
    return {str(k).strip(): str(v).strip() for k, v in codes.items() if str(k).strip() and str(v).strip()}


def load_invites(path: str | Path | None) -> dict[str, str]:
    """招待コードの一覧（TOML。[codes] の下に "コード" = "呼び名"）。無いか読めなければ空。"""
    if not path:
        return {}
    try:
        return _parse_invites(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, TypeError):
        return {}


class InviteBook:
    """招待コードの一覧。ファイルの mtime・大きさ・inode が変わっていれば、次に聞かれたときに読み直す。

    失効は invites.toml から行を消すだけで、次の要求から効く（設計書 §7.5）。壊れた TOML や
    読めないときは前の一覧を保ち、ログに一行。ファイルが無くなれば空（門を閉じる側に倒す）。
    path が無ければ、渡された一覧をそのまま使う（テストと SEED_INVITES 無し）。
    """

    def __init__(self, path: Path | None, codes: dict[str, str] | None = None) -> None:
        self.path = path
        self._codes: dict[str, str] = dict(codes or {})
        self._stamp: tuple[int, int, int] | None = None
        self._lock = threading.Lock()
        if path is not None:
            self.codes()

    def codes(self) -> dict[str, str]:
        if self.path is None:
            return self._codes
        try:
            st = self.path.stat()
            stamp: tuple[int, int, int] | None = (st.st_mtime_ns, st.st_size, st.st_ino)
        except OSError:
            stamp = None
        with self._lock:
            if stamp is not None and stamp == self._stamp:
                return self._codes
            if stamp is None:
                if self._stamp is not None or self._codes:
                    log.warning("招待コードの一覧が無い（%s）。空にする", self.path)
                self._codes, self._stamp = {}, None
                return self._codes
            try:
                codes = _parse_invites(self.path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, TypeError) as e:
                log.warning(
                    "招待コードの一覧を読めない（%s）。前の一覧（%d 件）を保つ: %s",
                    self.path,
                    len(self._codes),
                    e,
                )
                self._stamp = stamp  # 同じ壊れた物を毎回読まない。直して保存すれば stamp が変わる
                return self._codes
            self._codes, self._stamp = codes, stamp
            return self._codes
