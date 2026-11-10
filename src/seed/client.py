# SPDX-License-Identifier: AGPL-3.0-or-later
"""サーバー（seed.aiseed.dev）を呼ぶ側。契約は設計書 §7.1。

失敗はどれも ClientError にする。word は表示の語（app/strings.py）の鍵で、画面と CLI は
それを本人の言語の一文にして見せる。detail はサーバーが返した文（あれば）。
"""

from __future__ import annotations

import base64
import datetime as dt
from dataclasses import dataclass, field
from typing import Self

import httpx

from .records import Line, Observation, render_lines

TIMEOUT = httpx.Timeout(180.0, connect=10.0)  # 読みは Claude を待つので長め
HEALTH_TIMEOUT = httpx.Timeout(5.0, connect=3.0)
VIDEO_TIMEOUT = httpx.Timeout(300.0, connect=10.0)  # 動画は大きい。一つの塊を書く・答えを待つ間
VIDEO_CHUNK = 1024 * 1024
_HOME: dict[str, bool] = {}  # サーバーの URL → 家のサーバーか（/health の home。設計書 §5.13）。一度だけ聞く


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
                if _error_word(r) == "too_many_tries":  # 招待コードを何度も間違えた番地を、しばらく止めている
                    raise ClientError(
                        "server_tries", "too many wrong invite codes; wait a while", detail, 429
                    )
                raise ClientError("server_limit", "today's limit is reached", detail, 429)
            if r.status_code == 503:
                word = _error_word(r)
                if word == "paused":  # 動かす人が受け付けを止めている（設計書 §5.10）
                    raise ClientError("server_paused", "the server is not accepting requests now", None, 503)
                if word in _NOT_READY:  # サーバーに鍵が無い口。準備中（設計書 §5.1）
                    raise ClientError(_NOT_READY[word], "not ready yet on the server", None, 503)
                if word == "talk_closed":  # 話す口を閉じている（設計書 §7.6）
                    raise ClientError("server_no_talk", "the server does not talk now", None, 503)
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
        names: list[str] | None = None,
        field: str | None = None,
        date: str | None = None,
        time: str | None = None,
        kind: str | None = None,
        context: str | None = None,
    ) -> Reading:
        """写真（縮小済みの JPEG）を送り、読みを受ける。previous は同じ場所の前の観察の Markdown。ask は ASKS の語。

        names は写真の名（ファイルの名の幹）。送るファイルの名にし、読みの行はこの名で写真を指す。
        field は家のサーバー（設計書 §5.13）で、写真と観察を置く畑の名。
        date・time・kind は観察の前書き（時期と、候補地の読み方のため）。観察が持っている時だけ送る。座標は今まで通り
        center だけ（サーバーが資料の照会に使い、Claude には渡さない）。context は写真の位置の語、覆い％、草の読み（fieldctx.py）。
        """
        if not photos:
            raise ClientError("no_photos", "no photos to read")
        names = list(names or [])
        files = [
            ("photos", (f"{names[i] if i < len(names) else i + 1}.jpg", b, "image/jpeg"))
            for i, b in enumerate(photos)
        ]
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
            ("field", field),
            ("date", date),
            ("time", time),
            ("kind", kind),
            ("context", context),
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

    def lookup(self, lat: float, lon: float) -> list[Line]:
        """座標から土地の資料の行（出典付きの data 行）を引く（GET /api/lookup。AI は使わない）。"""
        params = {"lat": lat, "lon": lon, "language": self.language}
        if self.invite:
            params["invite"] = self.invite
        data = self._json(self._call("GET", "/api/lookup", params=params))
        return [
            Line(str(x["key"]), str(x["text"]))
            for x in data.get("data") or []
            if x.get("key") and x.get("text")
        ]

    def identify(self, photos: list[bytes]):
        """写真（縮小済みの JPEG、同じ株、5 枚まで）をサーバー経由で Pl@ntNet に。identify.Identification を返す。"""
        from . import identify as I

        if not photos:
            raise ClientError("identify_no_photos", "no photos")
        files = [("photos", (f"{i + 1}.jpg", b, "image/jpeg")) for i, b in enumerate(photos[: I.MAX_IMAGES])]
        form = {"language": self.language, "token": self.token, **self._inv()}
        data = self._json(self._call("POST", "/api/identify", files=files, data=form))
        return I.parse(data.get("plantnet") or {})

    def publish(self, markdown: str, photos: dict[str, bytes] | None = None) -> dict:
        """公開ファイルを送る。photos は photo の行が指す写真（公開の名 → 縮めた JPEG）。{"id", "url", "state"}。

        state はサーバーが預かった時 "pending"（動かす人が読んでから載る）、すぐ載せた時 "public"。古いサーバーは返さない。
        """
        body = {"token": self.token, "markdown": markdown, **self._inv()}
        if photos:
            body["photos"] = {n: base64.b64encode(b).decode("ascii") for n, b in photos.items()}
        return self._json(self._call("POST", "/api/publish", json=body))

    def publish_state(self, public_id: str) -> dict:
        """その公開の今（GET /api/publish/<id>/state）。{"state": pending|returned|public|none, "reason"?}。

        公開の token と招待コードは頭の行で送る（URL に秘密を載せない）。
        """
        headers = {"x-seed-token": self.token}
        if self.invite:
            headers["x-seed-invite"] = self.invite
        return self._json(self._call("GET", f"/api/publish/{public_id}/state", headers=headers))

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

    def talk(self, messages: list[dict], field: str | None = None) -> dict:
        """話す（POST /api/talk）。やり取り（Messages API の形）を送り、{content, stop_reason, usage, model} を受ける。

        system と道具の形はサーバーが持つ物を使う（ここからは送らない）。field は家のサーバーで話す畑の名。
        """
        body = {"messages": messages, "language": self.language, **self._inv()}
        if field:
            body["field"] = field
        return self._json(self._call("POST", "/api/talk", json=body))

    def video(self, path, where: dict | None = None, field: str | None = None) -> str:
        """動画を家のサーバーへ送る（POST /api/video）。ファイルから少しずつ流す。PC の上の置き場（畑からの道）を返す。

        招待コードと時と所は頭の行で送る（URL に秘密を載せない）。field は送る畑の名。
        """
        import json
        from pathlib import Path

        path = Path(path)
        size = path.stat().st_size

        def chunks():
            with path.open("rb") as f:
                while b := f.read(VIDEO_CHUNK):
                    yield b

        headers = {
            "content-type": "video/mp4",
            "content-length": str(size),
            "x-seed-where": json.dumps(where or {}, ensure_ascii=True),
        }
        if self.invite:
            headers["x-seed-invite"] = self.invite
        r = self._call(
            "POST",
            "/api/video",
            params={"field": field} if field else None,
            content=chunks(),
            headers=headers,
            timeout=VIDEO_TIMEOUT,
        )
        return str(self._json(r).get("path") or "")

    def health(self) -> dict:
        """/health。"""
        return self._json(self._call("GET", "/health", timeout=HEALTH_TIMEOUT))

    def index(self) -> dict:
        """index.json（記録の形 §8）。"""
        data = self._json(self._call("GET", "/index.json"))
        data.setdefault("records", [])
        data.setdefault("total", {"records": len(data["records"]), "connections": 0})
        return data

    def public(self, public_id: str) -> str:
        """公開ファイルそのまま。"""
        return self._call("GET", f"/public/{public_id}.md").text


def is_home(server_url: str, transport: httpx.BaseTransport | None = None) -> bool:
    """家のサーバー（seed home。/health が home: true）か。URL ごとに一度だけ聞く。届かなければ False（覚えない）。"""
    base = server_url.rstrip("/")
    if base in _HOME:
        return _HOME[base]
    try:
        with Client(base, "", "en", transport=transport) as c:
            home = bool(c.health().get("home"))
    except ClientError:
        return False
    _HOME[base] = home
    return home


def forget_home(server_url: str) -> None:
    """覚えを消す（サーバーの URL を変えた時。次に聞き直す）。"""
    _HOME.pop(server_url.rstrip("/"), None)


def known_home(server_url: str) -> bool:
    """もう聞いてあって家のサーバーだったか（画面から。網には出ない）。"""
    return _HOME.get(server_url.rstrip("/"), False)


# サーバーに鍵が無い口の error の語 → 本人に出す札（strings.py）
_NOT_READY = {
    "read_unavailable": "server_read_not_ready",
    "talk_unavailable": "server_talk_not_ready",
    "identify_unavailable": "server_identify_not_ready",
}


def _detail(r: httpx.Response) -> str | None:
    try:
        d = r.json().get("detail")
    except (ValueError, AttributeError):
        return r.text[:200] or None
    if isinstance(d, str):
        return d
    return str(d) if d else None


def _error_word(r: httpx.Response) -> str | None:
    try:
        e = r.json().get("error")
    except (ValueError, AttributeError):
        return None
    return e if isinstance(e, str) else None


def apply_reading(obs: Observation, reading: Reading, today: str | None = None) -> None:
    """読みを観察に入れる。AI の行は置き換え（判定は残る）、data 行は無い物だけ足す。"""
    obs.reread(reading.lines, reading.model)
    if reading.data:
        have = {(l.key, l.text) for l in obs.data}
        obs.data += [l for l in reading.data if (l.key, l.text) not in have]
        obs.lookup = today or dt.date.today().isoformat()
