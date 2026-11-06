# SPDX-License-Identifier: AGPL-3.0-or-later
"""サーバーの設定。環境変数と、systemd が渡す鍵のファイルから読む。

.env は読まない。deb2 では、秘密でない設定を systemd の EnvironmentFile（/etc/seed/env）が入れ、
Claude と Pl@ntNet の鍵は root だけが読めるファイル（/etc/seed/keys/*）を LoadCredential= が
このサービスにだけ渡す（$CREDENTIALS_DIRECTORY/anthropic、…/plantnet）。在ればそれを、無ければ環境変数を読む
（手元で動かす時とテスト）。鍵はここにだけ入り、ログにも応答にも出さない。
"""

from __future__ import annotations

import logging
import os
import threading
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import gate

REPO_SKILL_DIR = Path(__file__).resolve().parents[3] / "skill"

log = logging.getLogger("seed.server")


def _int(name: str, default: int) -> int:
    v = os.environ.get(name, "").strip()
    return int(v) if v else default


ENV_CREDENTIALS_DIR = "CREDENTIALS_DIRECTORY"  # systemd が LoadCredential= の物を置く所
CRED_ANTHROPIC = "anthropic"  # LoadCredential=anthropic:/etc/seed/keys/anthropic
CRED_PLANTNET = "plantnet"


def credential(name: str, env: str) -> str | None:
    """鍵を一つ。$CREDENTIALS_DIRECTORY/<name> が在ればその中身（前後の空白を除く）、無ければ環境変数 env。

    読めない時は値を出さずにログに一行（どの鍵かと理由の種類だけ）。
    """
    d = os.environ.get(ENV_CREDENTIALS_DIR, "").strip()
    if d:
        path = Path(d) / name
        try:
            value = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            value = ""
        except (OSError, UnicodeDecodeError) as e:
            log.warning("鍵 %s を読めない（%s）", name, type(e).__name__)
            value = ""
        if value:
            return value
    return os.environ.get(env, "").strip() or None


def _float(name: str, default: float) -> float:
    v = os.environ.get(name, "").strip()
    return float(v) if v else default


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(repr=False)  # Claude の鍵。値を repr（例外の文、ログ）に出さない
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
    # SEED_TOKENS。相手ごとの token の台帳（ハッシュ、範囲、期限、取り消し。設計書 §5.9）。無ければ招待コードの一覧だけ
    tokens_path: Path | None = None
    # SEED_AUDIT。誰が何をしたかの記録（kagi の形）。署名の鍵（KAGI_LOG_KEY_FILE か credential）が無ければ書かない
    audit_path: Path | None = None
    # SEED_DAILY_TALKS、SEED_PER_TOKEN_TALKS。話す（/api/talk）の 1 日の回数。0 で閉じる（設計書 §7.6）
    daily_talks: int = 300
    per_token_talks: int = 60
    plantnet_key: str | None = field(
        default=None, repr=False
    )  # Pl@ntNet の鍵（無ければ環境変数 PLANTNET_API_KEY）
    _book: InviteBook = field(init=False, repr=False, compare=False)
    _tokens: gate.TokenBook = field(init=False, repr=False, compare=False)
    journal: gate.Journal = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_book", InviteBook(self.invites_path, self.invites))
        object.__setattr__(self, "_tokens", gate.TokenBook(self.tokens_path))
        object.__setattr__(self, "journal", gate.Journal(self.audit_path))

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
            api_key=credential(CRED_ANTHROPIC, "ANTHROPIC_API_KEY"),
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
            tokens_path=Path(t).expanduser() if (t := os.environ.get(gate.ENV_TOKENS, "").strip()) else None,
            audit_path=Path(a).expanduser() if (a := os.environ.get(gate.ENV_AUDIT, "").strip()) else None,
            daily_talks=_int("SEED_DAILY_TALKS", 300),
            per_token_talks=_int("SEED_PER_TOKEN_TALKS", 60),
            plantnet_key=credential(CRED_PLANTNET, "PLANTNET_API_KEY"),
        )

    @property
    def pause_path(self) -> Path | None:
        """受け付けを止めている印（台帳の隣）。台帳の置き場が無ければ None で、止められない。"""
        return gate.pause_path(self.tokens_path)

    def paused(self) -> bool:
        """受け付けを止めているか。要求ごとに見る（ファイルなので、再起動しても残る）。"""
        p = self.pause_path
        return p is not None and p.exists()

    @property
    def site_dir(self) -> Path:
        """静的サイト（index.html、p/<id>.html、index.json、public/<id>.md）。Caddy はここだけを配る。"""
        return self.public_dir / "site"

    def who(self, code: str | None) -> tuple[gate.Who | None, str]:
        """（誰か、""）か（None、理由）。招待コードの一覧 → token の台帳 → open の順に見る。

        理由は missing | unknown | expired | revoked。招待コードの一覧の人は member（今まで通り）。
        """
        code = (code or "").strip()
        why = "missing"
        if code:
            codes = self._book.codes()
            if code in codes:
                return gate.Who(codes[code], frozenset({"member"}), "invite"), ""
            entry, why = self._tokens.find(code)
            if entry is not None:
                return gate.Who(str(entry["name"]), frozenset(entry["scope"]), "token"), ""
        if self.open:
            return gate.Who("", frozenset({"member"}), "open"), ""
        return None, why

    def invite_name(self, code: str | None) -> str | None:
        """招待コードか token の呼び名。無ければ None。open なら無しでも "" を返す（通す）。"""
        w, _ = self.who(code)
        return w.name if w is not None else None


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
