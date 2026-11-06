# SPDX-License-Identifier: AGPL-3.0-or-later
"""門: 相手ごとに出して取り消せる token の台帳と、誰が何をしたかの記録（設計書 §5.9）。

作者 2026-11-06「販売になると更に関係者が増えます。認証は大切です」「できるだけやりましょう。これが、サイバー攻撃対策ですね」。

- 台帳は JSON（`~/.config/aiseed/tokens.json` の形。研究室 §5b）。持つのは token のハッシュだけで、
  token そのものは出した時に一度だけ画面に出る。台帳が漏れても token は分からない。
- 一件に、呼び名、アプリ、範囲（scope）、作った日、期限、取り消した日。
- 範囲は三つ。`member`（招待した人。読み、公開、一言、Web 版）、`buyer`（買い手。公開の記録に一言を送るだけ）、
  `admin`（動かす人。管理の画面。member の事も全部できる）。
- 記録は kagi の形（追記だけ、連番とハッシュの連鎖と署名。`kagi log verify` で確かめられる）。
  書くのは呼び名、した事、結果。token も招待コードも書かない。
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from dataclasses import dataclass
from pathlib import Path

APP = "seed"
SCOPES = ("member", "buyer", "admin")  # admin は動かす人。member の事も全部できる
ENV_TOKENS = "SEED_TOKENS"
ENV_AUDIT = "SEED_AUDIT"
DEFAULT_TOKENS = "~/.config/aiseed/tokens.json"
MAX_DAYS = 3650

log = logging.getLogger("seed.server")


class GateError(Exception):
    """台帳を読めない、形が違う、足せない。メッセージに token は入れない。"""


@dataclass(frozen=True)
class Who:
    name: str
    scopes: frozenset[str]
    via: str  # invite（招待コードの一覧）| token（台帳）| open（開発中）


def code_hash(code: str) -> str:
    """token のハッシュ。token は長い乱数なので、素の SHA-256 でよい（人の作るパスワードではない）。"""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def tokens_path(path: str | Path | None = None, env: dict | None = None) -> Path:
    env = os.environ if env is None else env
    return Path(path or env.get(ENV_TOKENS) or DEFAULT_TOKENS).expanduser()


def _date(v) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(v))
    except ValueError:
        return None


def _parse(text: str) -> list[dict]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise GateError("台帳が JSON として読めない") from None
    tokens = data.get("tokens") if isinstance(data, dict) else None
    if not isinstance(tokens, list) or not all(isinstance(t, dict) for t in tokens):
        raise GateError('台帳は {"tokens": [...]} の形で書く')
    for t in tokens:
        if not isinstance(t.get("name"), str) or not isinstance(t.get("sha256"), str):
            raise GateError("台帳の一件に name か sha256 が無い")
        if not isinstance(t.get("scope"), list):
            raise GateError(f"台帳の {t['name']} の scope は並びで書く")
        if any(k in t for k in ("token", "code", "value")):
            raise GateError(f"台帳の {t['name']} に token そのものの欄がある。置くのはハッシュだけ")
    return tokens


def load(path: Path) -> list[dict]:
    """台帳の全部。無ければ空。"""
    try:
        text = Path(path).read_text("utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as e:
        raise GateError(f"台帳を読めない: {path} ({type(e).__name__})") from None
    return _parse(text)


def save(path: Path, tokens: list[dict]) -> None:
    """台帳を書く。新しく作る時は 600。在る物の許可は変えない（サーバーでは root:dev 640 に人が決める）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.stat() if path.exists() else None
    mode = old.st_mode & 0o777 if old else 0o600
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"tokens": tokens}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(tmp, mode)
    if old is not None:
        try:  # root が書き直しても、持ち主と組（サーバーが読める組）を保つ
            os.chown(tmp, old.st_uid, old.st_gid)
        except OSError:
            pass
    os.replace(tmp, path)


def state(entry: dict, today: dt.date | None = None) -> str:
    """live | expired | revoked。期限の無い物、読めない期限は expired の側に倒す。"""
    if entry.get("revoked"):
        return "revoked"
    exp = _date(entry.get("expires"))
    if exp is None or exp < (today or dt.date.today()):
        return "expired"
    return "live"


def add(
    path: Path,
    name: str,
    scopes: list[str],
    days: int,
    note: str = "",
    today: dt.date | None = None,
    app: str = APP,
) -> str:
    """一件足し、token を返す。token はここで一度だけ出て、台帳にはハッシュだけが残る。"""
    name = (name or "").strip()
    if not name or len(name) > 64 or any(ord(c) < 32 for c in name):
        raise GateError("呼び名が要る（64 字まで）")
    if not scopes or any(s not in SCOPES for s in scopes):
        raise GateError(f"範囲は {' | '.join(SCOPES)}")
    if not 1 <= days <= MAX_DAYS:
        raise GateError(f"期限は 1〜{MAX_DAYS} 日")
    today = today or dt.date.today()
    tokens = load(path)
    if any(t["name"] == name and t.get("app", APP) == app and state(t, today) == "live" for t in tokens):
        raise GateError(f"{name} の生きている token がもうある。先に取り消すか、別の呼び名で")
    code = secrets.token_urlsafe(18)
    tokens.append(
        {
            "name": name,
            "app": app,
            "scope": list(dict.fromkeys(scopes)),
            "sha256": code_hash(code),
            "created": today.isoformat(),
            "expires": (today + dt.timedelta(days=days)).isoformat(),
            "note": note.strip(),
        }
    )
    save(path, tokens)
    return code


def revoke(path: Path, name: str, today: dt.date | None = None, app: str = APP) -> int:
    """その呼び名の生きている token を取り消す。行は消さず、取り消した日を書く（後から辿れるように）。"""
    today = today or dt.date.today()
    tokens = load(path)
    n = 0
    for t in tokens:
        if t["name"] == name.strip() and t.get("app", APP) == app and state(t, today) == "live":
            t["revoked"] = today.isoformat()
            n += 1
    if not n:
        raise GateError(f"{name} の生きている token が無い")
    save(path, tokens)
    return n


def rows(path: Path, today: dt.date | None = None, app: str = APP) -> list[dict]:
    """一覧に出す物。ハッシュは出さない。"""
    out = []
    for t in load(path):
        if t.get("app", APP) != app:
            continue
        out.append(
            {
                "name": t["name"],
                "scope": list(t["scope"]),
                "created": str(t.get("created", "")),
                "expires": str(t.get("expires", "")),
                "state": state(t, today),
                "revoked": str(t.get("revoked", "")),
                "note": str(t.get("note", "")),
            }
        )
    return out


class TokenBook:
    """台帳を読む側（サーバー）。ファイルが変わっていれば次に聞かれた時に読み直すので、取り消しは次の要求から効く。

    読めない時は前の物を保ってログに一行。無くなれば空（門を閉じる側に倒す）。
    """

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._tokens: list[dict] = []
        self._stamp: tuple[int, int, int] | None = None
        self._lock = threading.Lock()

    def entries(self) -> list[dict]:
        if self.path is None:
            return []
        try:
            st = self.path.stat()
            stamp: tuple[int, int, int] | None = (st.st_mtime_ns, st.st_size, st.st_ino)
        except OSError:
            stamp = None
        with self._lock:
            if stamp is None:
                self._tokens, self._stamp = [], None
            elif stamp != self._stamp:
                try:
                    self._tokens = load(self.path)
                except GateError as e:
                    log.warning(
                        "token の台帳を読めない（%s）。前の物（%d 件）を保つ: %s",
                        self.path,
                        len(self._tokens),
                        e,
                    )
                self._stamp = stamp
            return self._tokens

    def find(self, code: str, today: dt.date | None = None) -> tuple[dict | None, str]:
        """（生きている一件、""）か、（None、理由）。理由は unknown | expired | revoked。"""
        h = code_hash(code)
        for t in self.entries():
            if t.get("app", APP) == APP and hmac.compare_digest(str(t["sha256"]), h):
                st = state(t, today)
                return (t, "") if st == "live" else (None, st)
        return None, "unknown"


class Journal:
    """誰が何をしたかの記録。kagi の記録の形で追記する。署名の鍵が無ければ書かない（/health に off と出る）。"""

    def __init__(self, path: Path | None, env: dict | None = None) -> None:
        self.path = path
        self._env = env
        self.state = "off"
        self._key = None
        if path is None:
            return
        try:
            from kagi import audit

            self._key = audit.find_key(env)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.state = "on"
        except Exception as e:  # noqa: BLE001  記録の用意で落ちても、サーバーは立ち上げる
            log.warning("記録を始められない（%s）: %s", path, type(e).__name__)

    def record(self, actor: str, action: str, detail: str) -> None:
        if self._key is None or self.path is None:
            return
        try:
            from kagi import audit

            clean = [" ".join(str(x).replace("|", "/").split())[:200] for x in (actor or "?", action, detail)]
            audit.add(self.path, self._key, *clean)
        except Exception as e:  # noqa: BLE001  記録に書けなくても要求は通す。書けなかった事は /health に出す
            self.state = "error"
            log.error("記録に書けない（%s）: %s", self.path, type(e).__name__)

    def tail(self, limit: int = 100) -> list[dict]:
        """記録の終わりの limit 行（新しい物が先）。管理の画面が読む。署名とハッシュは返さない。"""
        if self.path is None:
            return []
        try:
            lines = [ln for ln in self.path.read_text("utf-8").splitlines() if ln.strip()]
        except OSError:
            return []
        out = []
        for ln in reversed(lines[-max(1, limit) :]):
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            out.append({k: r.get(k) for k in ("seq", "ts", "actor", "action", "detail")})
        return out

    def verified(self) -> bool | None:
        """記録が書き換えられていないか（kagi log verify と同じ確かめ）。確かめられなければ None。"""
        if self._key is None or self.path is None or not self.path.exists():
            return None
        try:
            from kagi import audit

            _n, fails = audit.verify(self.path, self._key)
        except Exception:  # noqa: BLE001
            return None
        return not fails
