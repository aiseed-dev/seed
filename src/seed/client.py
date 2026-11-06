# SPDX-License-Identifier: AGPL-3.0-or-later
"""サーバー（seed.aiseed.dev）を呼ぶ側。契約は設計書 §7.1。

失敗はどれも ClientError にする。word は表示の語（app/strings.py）の鍵で、画面と CLI は
それを本人の言語の一文にして見せる。detail はサーバーが返した文（あれば）。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Self

import httpx

from .records import Line, Observation, render_lines

TIMEOUT = httpx.Timeout(180.0, connect=10.0)  # 読みは Claude を待つので長め


class ClientError(Exception):
    def __init__(self, word: str, message: str, detail: str | None = None, status: int | None = None):
        super().__init__(message + (f": {detail}" if detail else ""))
        self.word = word
        self.detail = detail
        self.status = status


@dataclass
class Reading:
    """/api/read の応答。lines は AI の行、data は出典付きの行。"""

    lines: list[Line]
    data: list[Line]
    model: str
    usage: dict = field(default_factory=dict)
    markdown: str = ""


def _lines(items, with_confidence: bool) -> list[Line]:
    """応答の行を Line に。形の合わない行は落とす（一行の誤りで読み全体を捨てない）。"""
    out = []
    for it in items or []:
        try:
            conf = it.get("confidence") if with_confidence else None
            out.append(
                Line(str(it["key"]), str(it["text"]).strip(), float(conf) if conf is not None else None)
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return out


def _as_text(v: str | list[Line] | None) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v or None
    return render_lines(v) if v else None


class Client:
    def __init__(
        self,
        server_url: str,
        token: str,
        language: str = "en",
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout | float = TIMEOUT,
        invite: str | None = None,
    ) -> None:
        self.base = server_url.rstrip("/")
        self.token = token
        self.language = language
        self.invite = (invite or "").strip() or None  # 招待コード（Discord で渡す）。API に要る
        self._http = httpx.Client(base_url=self.base, transport=transport, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- 送って受ける
    def _call(self, method: str, url: str, **kw) -> httpx.Response:
        try:
            r = self._http.request(method, url, **kw)
        except httpx.TimeoutException as e:
            raise ClientError("server_timeout", f"no answer from the server ({self.base})") from e
        except httpx.TransportError as e:
            raise ClientError("server_unreachable", f"cannot reach the server ({self.base})") from e
        if r.status_code >= 400:
            detail = _detail(r)
            if r.status_code == 429:
                raise ClientError("server_limit", "today's limit is reached", detail, 429)
            if r.status_code == 503:
                raise ClientError("server_busy", "the server is not reading now", detail, 503)
            if r.status_code in (401, 403):
                if "invite_required" in (r.text or ""):
                    raise ClientError("server_invite", "an invite code is needed", detail, r.status_code)
                raise ClientError(
                    "server_forbidden", "this token cannot change that record", detail, r.status_code
                )
            if r.status_code == 404:
                raise ClientError("server_not_found", "not found on the server", detail, 404)
            if r.status_code in (400, 413, 422):
                raise ClientError("server_rejected", "the server did not accept it", detail, r.status_code)
            raise ClientError("server_error", f"server error {r.status_code}", detail, r.status_code)
        return r

    def _inv(self) -> dict:
        return {"invite": self.invite} if self.invite else {}

    def _json(self, r: httpx.Response) -> dict:
        try:
            data = r.json()
        except ValueError as e:
            raise ClientError("server_bad_answer", "the server's answer could not be read") from e
        if not isinstance(data, dict):
            raise ClientError("server_bad_answer", "the server's answer could not be read")
        return data

    # --- API
    def read(
        self,
        photos: list[bytes],
        center: tuple[float, float] | list[float] | None = None,
        place_data: str | list[Line] | None = None,
        record: str | list[Line] | None = None,
        previous: str | None = None,
        ask: list[str] | None = None,
    ) -> Reading:
        """写真（縮小済みの JPEG）を送り、読みを受ける。previous は同じ場所の前の観察の Markdown。ask は ASKS の語。"""
        if not photos:
            raise ClientError("no_photos", "no photos to read")
        files = [("photos", (f"{i + 1}.jpg", b, "image/jpeg")) for i, b in enumerate(photos)]
        form = {"language": self.language, "token": self.token}
        if self.invite:
            form["invite"] = self.invite
        if center:
            form["center"] = f"{center[0]},{center[1]}"
        for k, v in (
            ("place_data", _as_text(place_data)),
            ("record", _as_text(record)),
            ("previous", previous),
            ("ask", ",".join(ask) if ask else None),
        ):
            if v:
                form[k] = v
        data = self._json(self._call("POST", "/api/read", files=files, data=form))
        if data.get("refused"):
            raise ClientError("server_refused", "Claude did not read these photos", data.get("category"))
        if "lines" not in data:
            raise ClientError("server_bad_answer", "the server's answer had no reading")
        return Reading(
            lines=_lines(data.get("lines"), True),
            data=_lines(data.get("data"), False),
            model=str(data.get("model") or "unknown"),
            usage=data.get("usage") or {},
            markdown=str(data.get("markdown") or ""),
        )

    def identify(self, photos: list[bytes]):
        """写真（縮小済みの JPEG、同じ株、5 枚まで）をサーバー経由で Pl@ntNet に。identify.Identification を返す。"""
        from . import identify as I

        if not photos:
            raise ClientError("identify_no_photos", "no photos")
        files = [("photos", (f"{i + 1}.jpg", b, "image/jpeg")) for i, b in enumerate(photos[: I.MAX_IMAGES])]
        form = {"language": self.language, "token": self.token, **self._inv()}
        data = self._json(self._call("POST", "/api/identify", files=files, data=form))
        return I.parse(data.get("plantnet") or {})

    def publish(self, markdown: str) -> dict:
        """公開ファイルを送る。{"id", "url"}。"""
        return self._json(
            self._call(
                "POST", "/api/publish", json={"token": self.token, "markdown": markdown, **self._inv()}
            )
        )

    def unpublish(self, public_id: str) -> None:
        self._call("DELETE", f"/api/publish/{public_id}", json={"token": self.token, **self._inv()})

    def connect(self, to: str, src: str, word: str) -> int:
        """一言を送る。相手の繋がりの数を返す。"""
        data = self._json(
            self._call(
                "POST",
                "/api/connect",
                json={"token": self.token, "to": to, "from": src, "word": word, **self._inv()},
            )
        )
        return int(data.get("count") or 0)

    def _me_headers(self) -> dict:
        """持ち帰りと消去の認証（設計書 §5.3）。GET に本文が無いので、URL でなくヘッダで送る。"""
        return {"X-Seed-Token": self.token, **({"X-Seed-Invite": self.invite} if self.invite else {})}

    def export(self) -> bytes:
        """Web 版: 自分の箱を zip で受け取る。"""
        return self._call("GET", "/api/export", headers=self._me_headers()).content

    def delete_me(self) -> dict:
        """Web 版: 自分の箱を消し、公開した物を全部取り下げる。{"deleted", "withdrawn"}。"""
        return self._json(self._call("DELETE", "/api/me", headers=self._me_headers()))

    # --- 管理の口（動かす人。範囲 admin の token を招待コードの所に入れて使う）
    def _admin_headers(self) -> dict:
        return {"X-Seed-Invite": self.invite} if self.invite else {}

    def whoami(self) -> dict:
        """入れてある token の呼び名と範囲。{"name", "scopes"}。"""
        return self._json(self._call("GET", "/api/whoami", headers=self._admin_headers()))

    def admin_overview(self) -> dict:
        return self._json(self._call("GET", "/api/admin/overview", headers=self._admin_headers()))

    def admin_tokens(self) -> list[dict]:
        return self._json(self._call("GET", "/api/admin/tokens", headers=self._admin_headers())).get(
            "tokens", []
        )

    def admin_token_add(self, name: str, scope: str, days: int, note: str = "") -> str:
        """一件出して、token を返す（出るのはこの一度だけ）。"""
        body = {"name": name, "scope": scope, "days": days, "note": note}
        r = self._call("POST", "/api/admin/tokens", json=body, headers=self._admin_headers())
        return str(self._json(r).get("token", ""))

    def admin_token_revoke(self, name: str) -> int:
        r = self._call("POST", "/api/admin/tokens/revoke", json={"name": name}, headers=self._admin_headers())
        return int(self._json(r).get("revoked", 0))

    def admin_audit(self, limit: int = 100) -> dict:
        r = self._call("GET", "/api/admin/audit", params={"limit": limit}, headers=self._admin_headers())
        return self._json(r)

    def admin_records(self) -> list[dict]:
        r = self._call("GET", "/api/admin/records", headers=self._admin_headers())
        return self._json(r).get("records", [])

    def admin_withdraw(self, public_id: str) -> None:
        self._call("DELETE", f"/api/admin/records/{public_id}", headers=self._admin_headers())

    def index(self) -> dict:
        """index.json（記録の形 §8）。"""
        data = self._json(self._call("GET", "/index.json"))
        data.setdefault("records", [])
        data.setdefault("total", {"records": len(data["records"]), "connections": 0})
        return data

    def public(self, public_id: str) -> str:
        """公開ファイルそのまま。"""
        return self._call("GET", f"/public/{public_id}.md").text


def _detail(r: httpx.Response) -> str | None:
    try:
        d = r.json().get("detail")
    except (ValueError, AttributeError):
        return r.text[:200] or None
    if isinstance(d, str):
        return d
    return str(d) if d else None


def apply_reading(obs: Observation, reading: Reading, today: str | None = None) -> None:
    """読みを観察に入れる。AI の行は置き換え（判定は残る）、data 行は無い物だけ足す。"""
    obs.reread(reading.lines, reading.model)
    if reading.data:
        have = {(l.key, l.text) for l in obs.data}
        obs.data += [l for l in reading.data if (l.key, l.text) not in have]
        obs.lookup = today or dt.date.today().isoformat()
