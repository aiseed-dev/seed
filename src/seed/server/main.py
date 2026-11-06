# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed.aiseed.dev の FastAPI（設計書 §7.1）。

API キーが無くても起きる（/api/read と /api/talk が 503）。CORS の許可は付けない（同一オリジンだけ）。
Web に出すのは入口（/）と公開された記録の閲覧（/p/<id>）と「一言を送る」だけ（設計書 §3、§6）。
観察・記録・公開の画面は出さない。データは本人の PC にある。HTML はテンプレート無しの文字列で、
本人の文はすべてエスケープする。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import anthropic
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from .. import __version__, index, lang
from .. import lookup as L
from .. import prompts as PR
from .. import records as R
from . import connect as C
from . import gate, pages
from . import publish as P
from . import read as RD
from . import talk as TK
from .limits import PHOTO_MAX, PHOTOS_MAX, PHOTOS_TOTAL_MAX, LimitReached, Limits
from .settings import Settings

log = logging.getLogger("seed.server")

FIELD_MAX = 16 * 1024  # center、record、place_data、previous、language、token のそれぞれ
BODY_MAX = PHOTOS_TOTAL_MAX + 6 * FIELD_MAX + 64 * 1024  # multipart の区切りの分の余り
# 話すの要求の全体（写真は base64 で 4/3 倍。文の上限と JSON の余り）
TALK_BODY_MAX = PR.TALK_IMAGES_MAX * PR.TALK_PHOTO_MAX * 4 // 3 + PR.TALK_TOTAL_TEXT_MAX * 2 + 64 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
# 外の物は何も読まない。一言のフォームの小さな script だけが同じオリジンの /api/connect を呼ぶ
CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; "
    "img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


class MemoryMultiPartParser(MultiPartParser):
    """写真をディスクに書かない（設計書 §9）。ふだんの 1 MB で溢れるのを、全体の上限まで上げる。"""

    spool_max_size = BODY_MAX


class TooLarge(Exception):
    pass


async def _counted(stream: AsyncIterator[bytes], limit: int) -> AsyncIterator[bytes]:
    n = 0
    async for chunk in stream:
        n += len(chunk)
        if n > limit:
            raise TooLarge
        yield chunk


def _error(status: int, error: str, **extra) -> JSONResponse:
    return JSONResponse({"error": error, **extra}, status_code=status)


def _client_ip(request: Request) -> str:
    # uvicorn は 127.0.0.1（Caddy）からの X-Forwarded-For を既定で信じる
    return request.client.host if request.client else "unknown"


def _parse_center(s: str | None) -> tuple[float, float] | None:
    if not s or not s.strip():
        return None
    lat, lon = (float(x) for x in s.split(","))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("center")
    return lat, lon


class PublishBody(BaseModel):
    token: str
    markdown: str
    invite: str | None = None


class WithdrawBody(BaseModel):
    token: str
    invite: str | None = None


class TokenBody(BaseModel):
    name: str
    scope: str = "member"
    days: int = 90
    note: str | None = None


class RevokeBody(BaseModel):
    name: str


class PauseBody(BaseModel):
    paused: bool


class ConnectBody(BaseModel):
    token: str | None = None  # あれば from は自分の公開の id。無ければ from は招待コードの呼び名
    to: str
    src: str = Field(alias="from", default="")
    word: str
    invite: str | None = None


def _html(text: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(text, status_code=status, headers={"Content-Security-Policy": CSP})


DENIED = {
    "missing": "招待コードが要る（Discord で渡す）",
    "unknown": "招待コードが要る（Discord で渡す）",
    "expired": "この招待コードは期限が切れた。渡した人に新しい物を頼む",
    "revoked": "この招待コードは取り消された",
    "scope": "この招待コードでは、ここは使えない",
}
PAUSED = "今、受け付けを止めている（サーバーを動かす人が再開するまで）"
NO_LEDGER = "このサーバーには token の台帳が無い（SEED_TOKENS）"


def _paused(settings: Settings) -> JSONResponse | None:
    """受け付けを止めている間は 503（設計書 §5.10）。公開、一言、写真の読み取り、話す、草の名の口だけが見る。"""
    if settings.paused():
        return _error(503, "paused", reason="paused", detail=[PAUSED])
    return None


def _invite(
    settings: Settings,
    code: str | None,
    action: str = "",
    need: tuple[str, ...] = ("member",),
    detail: str = "",
    note: bool = True,
) -> str | JSONResponse:
    """門。招待コードか token の呼び名。入れなければ 403 の答え（設計書 §7.5、§5.9）。

    need は入ってよい範囲（どれか一つを持っていれば通る）。通した事も断った事も記録に一行（token は書かない）。
    note が False なら通した行は書かない（結果の数を後で書く口のため。断った行は書く）。
    """
    who, why = settings.who(code)
    if who is not None and "admin" not in who.scopes and not (who.scopes & set(need)):
        who, why = None, "scope"  # admin は member の事も全部できる
    if who is None:
        settings.journal.record("?", action, f"断った: {why}" + (f" {detail}" if detail else ""))
        return _error(403, "invite_required", reason=why, detail=[DENIED[why]])
    if note:
        settings.journal.record(_actor(who), action, detail or "通した")
    return who.name


def _actor(who: gate.Who) -> str:
    return who.name or f"（{who.via}）"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    limits = Limits(
        settings.daily_reads,
        settings.per_token_reads,
        settings.per_ip_reads,
        settings.daily_usd,
        settings.daily_talks,
        settings.per_token_talks,
    )
    client = anthropic.AsyncAnthropic(api_key=settings.api_key, timeout=180.0) if settings.api_key else None

    app = FastAPI(title="seed", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.limits = limits
    app.state.client = client

    try:
        settings.public_dir.mkdir(parents=True, exist_ok=True)
        P.rebuild(settings)
    except OSError as e:
        log.warning("公開のフォルダーを用意できない（%s）: %s", settings.public_dir, e)

    @app.get("/health")
    async def health():
        return {
            "version": __version__,
            "read": app.state.client is not None,
            "talk": app.state.client is not None
            and settings.daily_talks > 0,  # 話す口（/api/talk）が使えるか
            "lookup": L.available(),
            "model": settings.model,
            "remaining": limits.remaining(),
            "audit": settings.journal.state,  # on | off | error（誰が何をしたかの記録。設計書 §5.9）
            "paused": settings.paused(),  # 受け付けを止めているか（設計書 §5.10）
        }

    async def _multipart(request: Request):
        """写真付きの form をメモリ上で読む（設計書 §9）。(form, None) か (None, 誤りの答え)。"""
        if int(request.headers.get("content-length") or 0) > BODY_MAX:
            return None, _error(413, "too_large", detail="写真は合計 8 MB まで")
        if not request.headers.get("content-type", "").startswith("multipart/form-data"):
            return None, _error(400, "multipart_required")
        parser = MemoryMultiPartParser(
            request.headers,
            _counted(request.stream(), BODY_MAX),
            max_files=PHOTOS_MAX + 1,
            max_fields=10,
            max_part_size=FIELD_MAX,
        )
        try:
            return await parser.parse(), None
        except TooLarge:
            return None, _error(413, "too_large", detail="写真は合計 8 MB まで")
        except MultiPartException as e:
            return None, _error(400, "bad_form", detail=e.message)

    @app.post("/api/read")
    async def api_read(request: Request):
        if (closed := _paused(settings)) is not None:
            return closed
        if app.state.client is None:
            return _error(503, "read_unavailable", detail="このサーバーには API キーが無い")
        form, err = await _multipart(request)
        if err is not None:
            return err
        try:
            return await _read(request, form)
        finally:
            await form.close()

    async def _read(request: Request, form) -> JSONResponse | dict:
        token = form.get("token")
        if not isinstance(token, str):
            return _error(400, "token_required")
        try:
            P.check_token(token)
        except P.PublishError as e:
            return _error(400, "bad_token", detail=e.reasons)
        inv = form.get("invite")
        who = _invite(settings, inv if isinstance(inv, str) else None, "read")
        if not isinstance(who, str):
            return who
        uploads = [f for f in form.getlist("photos") if isinstance(f, UploadFile)]
        if not 1 <= len(uploads) <= PHOTOS_MAX:
            return _error(400, "photos", detail=f"写真は 1〜{PHOTOS_MAX} 枚")
        photos = [await f.read() for f in uploads]
        if any(len(p) > PHOTO_MAX for p in photos):
            return _error(413, "photo_too_large", detail="写真は 1 枚 2 MB まで（縮小してから送る）")
        if sum(map(len, photos)) > PHOTOS_TOTAL_MAX:
            return _error(413, "too_large", detail="写真は合計 8 MB まで")
        if not all(p.startswith(JPEG_MAGIC) for p in photos):
            return _error(415, "jpeg_only")
        try:
            center = _parse_center(form.get("center"))
        except ValueError:
            return _error(400, "bad_center", detail='center は "lat,lon"')
        place_data = R.parse_lines(str(form.get("place_data") or ""))
        record = str(form.get("record") or "") or None
        previous = str(form.get("previous") or "") or None
        language = lang.normalize(str(form.get("language") or "")) or lang.FALLBACK
        try:
            ask = R.parse_asks(str(form.get("ask") or ""))
        except ValueError:
            return _error(400, "bad_ask", detail=f"ask は {', '.join(R.ASKS)} をコンマで")

        try:
            limits.take(token, _client_ip(request))
        except LimitReached as e:
            return _error(429, "limit", kind=e.kind, detail="今日はここまで")

        data = await run_in_threadpool(L.data_lines, *center, language) if center else []
        try:
            reading = await RD.read(
                app.state.client,
                model=settings.model,
                skill_dir=settings.skill_dir,
                photos=photos,
                data=data,
                place_data=place_data,
                previous=previous,
                record=record,
                language=language,
                ask=ask,
                names=[Path(f.filename or "").stem for f in uploads],
            )
        except RD.ReadError as e:
            limits.spend(e.usage)
            headers = {"Retry-After": e.retry_after} if e.retry_after else None
            resp = _error(e.status, "read_failed", kind=e.kind)
            if headers:
                resp.headers.update(headers)
            return resp
        cost = limits.spend(reading.usage)
        log.info("read model=%s photos=%d usd=%.4f", reading.model, len(photos), cost)
        out = {
            "lines": [{"key": x.key, "text": x.text, "confidence": x.confidence} for x in reading.lines],
            "data": [{"key": x.key, "text": x.text} for x in data],
            "model": reading.model,
            "usage": reading.usage,
            "markdown": "" if reading.refused else RD.markdown(reading.model, reading.lines, data),
        }
        if reading.refused:
            out.update(refused=True, category=reading.category)
        return out

    @app.post("/api/talk")
    async def api_talk(request: Request):
        """話す（設計書 §7.6）。やり取りを受け、サーバーの system と道具の形とサーバーの鍵で Claude を一回呼ぶ。

        道具を動かすのは端末。中身は盤にもログにも書かない。記録には、誰が、talk、通した・断った、の一行だけ。
        """
        if (closed := _paused(settings)) is not None:
            return closed
        if app.state.client is None:
            return _error(503, "talk_unavailable", detail=["このサーバーには Claude の鍵が無い"])
        if settings.daily_talks <= 0:
            return _error(503, "talk_closed", detail=["このサーバーは今、話す口を閉じている"])
        if int(request.headers.get("content-length") or 0) > TALK_BODY_MAX:
            return _error(413, "too_large", detail=["やり取りが大きすぎる"])
        raw = bytearray()
        try:
            async for chunk in _counted(request.stream(), TALK_BODY_MAX):
                raw += chunk
        except TooLarge:
            return _error(413, "too_large", detail=["やり取りが大きすぎる"])
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return _error(400, "bad_talk", detail=["JSON でない"])
        if not isinstance(body, dict):
            return _error(400, "bad_talk", detail=["JSON の表でない"])
        inv = body.get("invite")
        code = inv if isinstance(inv, str) else None
        who = _invite(settings, code, "talk", note=False)
        if not isinstance(who, str):
            return who
        actor = who or "?"
        try:
            messages = PR.clean_messages(body.get("messages"))
        except PR.TalkTooLarge as e:
            settings.journal.record(actor, "talk", "断った: too_large")
            return _error(413, "too_large", detail=[str(e)])
        except ValueError as e:
            settings.journal.record(actor, "talk", "断った: bad_talk")
            return _error(400, "bad_talk", detail=[str(e)])
        language = lang.normalize(str(body.get("language") or "")) or lang.FALLBACK
        try:
            limits.take_talk((code or "").strip() or f"ip:{_client_ip(request)}")
        except LimitReached as e:
            settings.journal.record(actor, "talk", f"断った: limit {e.kind}")
            return _error(429, "limit", kind=e.kind, detail=["今日はここまで"])
        settings.journal.record(actor, "talk", "通した")
        try:
            out = await TK.talk(
                app.state.client,
                model=settings.model,
                skill_dir=settings.skill_dir,
                language=language,
                messages=messages,
            )
        except RD.ReadError as e:
            limits.spend(e.usage)
            resp = _error(e.status, "talk_failed", kind=e.kind)
            if e.retry_after:
                resp.headers["Retry-After"] = e.retry_after
            return resp
        cost = limits.spend(out["usage"])
        log.info("talk model=%s usd=%.4f", out["model"], cost)
        return out

    def _plantnet() -> str | None:
        """Pl@ntNet の鍵。systemd が渡した物（settings）か、環境変数。"""
        from .. import identify as I

        return settings.plantnet_key or I.key_from_env()

    @app.post("/api/identify")
    async def api_identify(request: Request):
        """草の名を Pl@ntNet で（設計書 §17）。サーバーの鍵 PLANTNET_API_KEY。写真は 1〜5 枚、JPEG。"""

        if (closed := _paused(settings)) is not None:
            return closed
        if not _plantnet():
            return _error(503, "identify_unavailable", detail=["このサーバーには Pl@ntNet の鍵が無い"])
        form, err = await _multipart(request)
        if err is not None:
            return err
        try:
            return await _identify(request, form)
        finally:
            await form.close()

    async def _identify(request: Request, form) -> JSONResponse | dict:
        from .. import identify as I

        token = form.get("token")
        if not isinstance(token, str):
            return _error(400, "token_required")
        try:
            P.check_token(token)
        except P.PublishError as e:
            return _error(400, "bad_token", detail=e.reasons)
        inv = form.get("invite")
        who = _invite(settings, inv if isinstance(inv, str) else None, "identify")
        if not isinstance(who, str):
            return who
        uploads = [f for f in form.getlist("photos") if isinstance(f, UploadFile)]
        if not 1 <= len(uploads) <= I.MAX_IMAGES:
            return _error(400, "photos", detail=f"写真は 1〜{I.MAX_IMAGES} 枚")
        photos = [await f.read() for f in uploads]
        if any(len(p) > PHOTO_MAX for p in photos) or not all(p.startswith(JPEG_MAGIC) for p in photos):
            return _error(415, "jpeg_only")
        language = lang.normalize(str(form.get("language") or "")) or lang.FALLBACK
        try:
            limits.take_lookup(_client_ip(request))  # 外のサービスに出るので照会と同じ枠
        except LimitReached as e:
            return _error(429, "limit", kind=e.kind)
        try:
            result = await run_in_threadpool(I.identify, photos, _plantnet(), language)
        except I.IdentifyError as e:
            status = {"identify_limit": 429, "identify_unreachable": 503}.get(e.word, 502)
            return _error(status, e.word, detail=[e.detail] if e.detail else None)
        return {
            "plantnet": result.raw,
            "candidates": [
                {"scientific": c.scientific, "score": c.score, "common": c.common, "gbif": c.gbif}
                for c in result.candidates
            ],
            "remaining": result.remaining,
        }

    @app.get("/api/lookup")
    async def api_lookup(
        request: Request, lat: float, lon: float, invite: str | None = None, language: str | None = None
    ):
        who = _invite(settings, invite, "lookup")
        if not isinstance(who, str):
            return who
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return _error(400, "bad_center")
        if not L.available():
            return {"data": [], "note": "このサーバーには照会（fieldnotes-farm）が無い"}
        try:
            limits.take_lookup(_client_ip(request))
        except LimitReached as e:
            return _error(429, "limit", kind=e.kind)
        lg = lang.normalize(language) or lang.FALLBACK
        lines = await run_in_threadpool(L.data_lines, lat, lon, lg)
        return {"data": [{"key": x.key, "text": x.text} for x in lines]}

    @app.post("/api/publish")
    async def api_publish(body: PublishBody, request: Request):
        if (closed := _paused(settings)) is not None:
            return closed
        who = _invite(settings, body.invite, "publish")
        if not isinstance(who, str):
            return who
        try:
            pub = await run_in_threadpool(P.publish, settings, body.token, body.markdown)
        except P.PublishError as e:
            return _error(e.status, "publish_rejected", detail=e.reasons)
        await run_in_threadpool(P.note_publisher, settings, pub.id, who)  # 管理の画面の「公開した人」
        # 外向きの url。SEED_PUBLIC_URL があればそれを基底にする（127.0.0.1 で叩かれても外の url を返す。11-05）
        base = (settings.public_url or str(request.base_url)).rstrip("/")
        return {"id": pub.id, "url": f"{base}/public/{pub.id}.md"}

    @app.delete("/api/publish/{record_id}")
    async def api_withdraw(record_id: str, body: WithdrawBody):
        who = _invite(settings, body.invite, "withdraw", detail=record_id[:80])
        if not isinstance(who, str):
            return who
        try:
            await run_in_threadpool(P.withdraw, settings, body.token, record_id)
        except P.PublishError as e:
            return _error(e.status, "withdraw_rejected", detail=e.reasons)
        return {"id": record_id, "withdrawn": True}

    # ---- 管理の口（動かす人だけ。範囲 admin。招待コードと同じ所に入れた token をヘッダで受ける）
    def _admin(request: Request, action: str, detail: str = "") -> str | JSONResponse:
        return _invite(settings, request.headers.get("x-seed-invite"), action, need=("admin",), detail=detail)

    @app.get("/api/whoami")
    async def api_whoami(request: Request):
        """入れてある token の呼び名と範囲。アプリが、管理の画面を出すかを決めるのに使う。"""
        who, why = settings.who(request.headers.get("x-seed-invite"))
        if who is None:
            return _error(403, "invite_required", reason=why, detail=[DENIED[why]])
        return {"name": who.name, "scopes": sorted(who.scopes)}

    @app.get("/api/admin/overview")
    async def admin_overview(request: Request):
        who = _admin(request, "admin.overview")
        if not isinstance(who, str):
            return who
        idx = await run_in_threadpool(pages.load_index, settings)
        rows = await run_in_threadpool(_token_rows)
        tokens = {st: sum(1 for r in rows if r["state"] == st) for st in ("live", "expired", "revoked")}
        tokens["expiring"] = sum(1 for r in rows if gate.expiring(r))
        return {
            "version": __version__,
            "records": idx.get("total", {}).get("records", 0),
            "connections": idx.get("total", {}).get("connections", 0),
            "tokens": tokens,
            "invites": len(settings._book.codes()),
            "read": app.state.client is not None,
            "audit": settings.journal.state,
            "remaining": limits.remaining(),
            "paused": settings.paused(),
            # 外の鍵は在るか無いかだけ。値は出さない
            "keys": {"claude": bool(settings.api_key), "plantnet": bool(_plantnet())},
            "denied_today": await run_in_threadpool(settings.journal.denied_today),
        }

    def _token_rows() -> list[dict]:
        if settings.tokens_path is None:
            return []
        try:
            return gate.rows(settings.tokens_path)
        except gate.GateError:
            return []

    @app.get("/api/admin/tokens")
    async def admin_tokens(request: Request):
        who = _admin(request, "admin.tokens")
        if not isinstance(who, str):
            return who
        return {"tokens": await run_in_threadpool(_token_rows), "ledger": settings.tokens_path is not None}

    @app.post("/api/admin/tokens")
    async def admin_token_add(body: TokenBody, request: Request):
        who = _admin(request, "admin.token.add", f"{body.name[:60]} {body.scope}")
        if not isinstance(who, str):
            return who
        if settings.tokens_path is None:
            return _error(503, "no_ledger", detail=[NO_LEDGER])
        try:
            code = await run_in_threadpool(
                gate.add, settings.tokens_path, body.name, [body.scope], body.days, body.note or ""
            )
        except gate.GateError as e:
            return _error(400, "token_rejected", detail=[str(e)])
        except OSError as e:
            return _error(503, "ledger_unwritable", detail=[f"台帳に書けない ({type(e).__name__})"])
        return {"token": code, "name": body.name.strip(), "scope": body.scope, "days": body.days}

    @app.post("/api/admin/tokens/revoke")
    async def admin_token_revoke(body: RevokeBody, request: Request):
        who = _admin(request, "admin.token.revoke", body.name[:60])
        if not isinstance(who, str):
            return who
        if settings.tokens_path is None:
            return _error(503, "no_ledger", detail=[NO_LEDGER])
        try:
            n = await run_in_threadpool(gate.revoke, settings.tokens_path, body.name)
        except gate.GateError as e:
            return _error(400, "token_rejected", detail=[str(e)])
        except OSError as e:
            return _error(503, "ledger_unwritable", detail=[f"台帳に書けない ({type(e).__name__})"])
        return {"revoked": n}

    @app.post("/api/admin/tokens/revoke_all")
    async def admin_token_revoke_all(request: Request):
        """押した本人の token を残して、生きている token を全部取り消す。記録には取り消した数を一行。"""
        action = "admin.token_revoke_all"
        who = _invite(settings, request.headers.get("x-seed-invite"), action, need=("admin",), note=False)
        if not isinstance(who, str):
            return who
        if settings.tokens_path is None:
            return _error(503, "no_ledger", detail=[NO_LEDGER])
        try:
            n = await run_in_threadpool(gate.revoke_all, settings.tokens_path, who)
        except gate.GateError as e:
            return _error(400, "token_rejected", detail=[str(e)])
        except OSError as e:
            return _error(503, "ledger_unwritable", detail=[f"台帳に書けない ({type(e).__name__})"])
        settings.journal.record(who or "?", action, f"{n} 件")
        return {"revoked": n}

    @app.post("/api/admin/pause")
    async def admin_pause(body: PauseBody, request: Request):
        """受け付けを止める・再開する。印は台帳の隣のファイルで、再起動しても残る。"""
        action = "admin.pause" if body.paused else "admin.resume"
        who = _invite(settings, request.headers.get("x-seed-invite"), action, need=("admin",), note=False)
        if not isinstance(who, str):
            return who
        flag = settings.pause_path
        if flag is None:
            return _error(503, "no_ledger", detail=[NO_LEDGER + "。止める印を置く所が無い"])
        try:
            await run_in_threadpool(gate.set_paused, flag, body.paused)
        except OSError as e:
            return _error(503, "pause_unwritable", detail=[f"止める印を書けない ({type(e).__name__})"])
        settings.journal.record(who or "?", action, "通した")  # 印を置けてから一行
        return {"paused": settings.paused()}

    @app.get("/api/admin/audit")
    async def admin_audit(request: Request, limit: int = 100):
        who = _admin(request, "admin.audit")
        if not isinstance(who, str):
            return who
        j = settings.journal
        return {
            "state": j.state,
            "verified": await run_in_threadpool(j.verified),
            "lines": await run_in_threadpool(j.tail, max(1, min(limit, 500))),
        }

    @app.get("/api/admin/records")
    async def admin_records(request: Request):
        who = _admin(request, "admin.records")
        if not isinstance(who, str):
            return who
        idx = await run_in_threadpool(pages.load_index, settings)
        base = (settings.public_url or str(request.base_url)).rstrip("/")

        def more(rec: dict) -> dict:
            rid = str(rec.get("id", ""))
            return {
                **rec,
                "owner": P.publisher_of(settings, rid),  # 名前だけ。ハッシュは返さない
                "published": P.published_on(settings, rid),
                "connections": index.count_connections(settings.connections_dir, rid) if rid else 0,
                "url": f"{base}/p/{rid}",
            }

        return {"records": await run_in_threadpool(lambda: [more(r) for r in idx.get("records", [])])}

    @app.get("/api/admin/records/{record_id}/connections")
    async def admin_connections(record_id: str, request: Request):
        who = _admin(request, "admin.connections", record_id[:80])
        if not isinstance(who, str):
            return who
        try:
            return {"connections": await run_in_threadpool(P.connections, settings, record_id)}
        except P.PublishError as e:
            return _error(e.status, "connections_rejected", detail=e.reasons)

    @app.delete("/api/admin/records/{record_id}/connections/{name}")
    async def admin_connection_remove(record_id: str, name: str, request: Request):
        """寄せられた一言を一件消す。記録には公開の id と日だけ（言葉そのものは書かない）。"""
        action = "admin.connection_remove"
        who = _invite(
            settings,
            request.headers.get("x-seed-invite"),
            action,
            need=("admin",),
            detail=record_id[:80],
            note=False,
        )
        if not isinstance(who, str):
            return who
        try:
            day = await run_in_threadpool(P.remove_connection, settings, record_id, name)
        except P.PublishError as e:
            return _error(e.status, "connection_rejected", detail=e.reasons)
        settings.journal.record(who or "?", action, f"{record_id} {day}")
        return {"id": record_id, "name": name, "removed": True}

    @app.delete("/api/admin/records/{record_id}")
    async def admin_withdraw(record_id: str, request: Request):
        who = _admin(request, "admin.withdraw", record_id[:80])
        if not isinstance(who, str):
            return who
        try:
            await run_in_threadpool(P.withdraw_as_admin, settings, record_id)
        except P.PublishError as e:
            return _error(e.status, "withdraw_rejected", detail=e.reasons)
        return {"id": record_id, "withdrawn": True}

    @app.post("/api/connect")
    async def api_connect(body: ConnectBody, request: Request):
        if (closed := _paused(settings)) is not None:
            return closed
        # 一言は買い手も送れる（買い手の token でできるのはここだけ。設計書 §5.9）
        who = _invite(settings, body.invite, "connect", need=("member", "buyer"), detail=str(body.to)[:80])
        if not isinstance(who, str):
            return who
        ip = _client_ip(request)
        src = body.src if body.token is not None else (who or body.src)  # 招待コードの呼び名が送り主
        charge = None if body.token is not None else (lambda: limits.take_connect(ip))
        try:
            n = await run_in_threadpool(C.connect, settings, body.token, body.to, src, body.word, charge)
        except P.PublishError as e:
            return _error(e.status, "connect_rejected", detail=e.reasons)
        except LimitReached as e:
            return _error(429, "limit", kind=e.kind, detail=["今日はここまで"])
        await run_in_threadpool(P.rebuild, settings)  # 繋がりの数が静的な頁に出る
        return {"count": n}

    @app.get("/index.json")
    async def index_json():
        if settings.index_path.is_file():
            return FileResponse(settings.index_path, media_type="application/json")
        return index.build_index(settings.public_dir, settings.connections_dir)

    @app.get("/public/{name}")
    async def public_file(name: str):
        record_id = name.removesuffix(".md")
        path = settings.public_dir / f"{record_id}.md"
        if not name.endswith(".md") or not R.ID_RE.match(record_id) or not path.is_file():
            return _error(404, "not_found")
        return FileResponse(path, media_type="text/markdown; charset=utf-8")

    @app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
    async def entry():
        return _html(await run_in_threadpool(lambda: pages.entry_html(pages.load_index(settings))))

    @app.get("/robots.txt")
    async def robots():
        return HTMLResponse("User-agent: *\nAllow: /\n", media_type="text/plain")

    @app.api_route("/p/{record_id}", methods=["GET", "HEAD"], response_class=HTMLResponse)
    async def record(record_id: str):
        path = settings.public_dir / f"{record_id}.md"
        if not R.ID_RE.match(record_id) or not path.is_file():
            return _html(pages.not_found_html(), 404)
        try:
            pub = R.Public.read(path)
        except (ValueError, TypeError, KeyError):
            return _html(pages.not_found_html(), 404)
        if not pages.showable(pub):
            return _html(pages.not_found_html(), 404)
        n = index.count_connections(settings.connections_dir, pub.id)
        return _html(await run_in_threadpool(pages.record_html, pub, n))

    return app


app = create_app()
