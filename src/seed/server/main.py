# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed.aiseed.dev の FastAPI（設計書 §7.1）。

鍵が無くても起きる（/api/read と /api/talk、/api/identify が 503 で「準備中です」。入口に一行）。CORS の許可は付けない（同一オリジンだけ）。
Web に出すのは入口（/）と公開された記録の閲覧（/p/<id>）と「一言を送る」だけ（設計書 §3、§6）。
観察・記録・公開の画面は出さない。データは本人の PC にある。HTML はテンプレート無しの文字列で、
本人の文はすべてエスケープする。
"""

from __future__ import annotations

import json
import logging
import math
import secrets
from collections.abc import AsyncIterator
from pathlib import Path

import anthropic
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from .. import __version__, index, lang, local
from .. import lookup as L
from .. import prompts as PR
from .. import records as R
from . import connect as C
from . import gate, pages
from . import home as H
from . import publish as P
from . import read as RD
from . import talk as TK
from .limits import PHOTO_MAX, PHOTOS_MAX, PHOTOS_TOTAL_MAX, LimitReached, Limits
from .settings import Settings

# 鍵が無い口の 503 の文（来た人がアプリやブラウザーで見る）。error の語（read_unavailable など）は変えない
READ_NOT_READY = "Claude の読み取りは準備中です"
TALK_NOT_READY = "Claude と話すのは準備中です"
IDENTIFY_NOT_READY = "草の名の照会は準備中です"

log = logging.getLogger("seed.server")

FIELD_MAX = 16 * 1024  # center、record、place_data、previous、language、token のそれぞれ
BODY_MAX = PHOTOS_TOTAL_MAX + 6 * FIELD_MAX + 64 * 1024  # multipart の区切りの分の余り
HOME_BODY_MAX = H.PHOTOS_TOTAL_MAX + 7 * FIELD_MAX + 64 * 1024  # 家のサーバー（元のままの写真）
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
    photos: dict[str, str] | None = None  # 公開の名 → base64 の JPEG（無い古い形もそのまま通る）


# 公開の要求の全体: 公開ファイル（JSON で文字が膨らむ分の余り）と、写真（base64 で 4/3 倍）
PUBLISH_BODY_MAX = (
    P.MARKDOWN_MAX * 6 + R.PUBLIC_PHOTOS_MAX * (R.PUBLIC_PHOTO_BYTES * 4 // 3 + 256) + 64 * 1024
)


class WithdrawBody(BaseModel):
    token: str
    invite: str | None = None


class ReturnBody(BaseModel):
    reason: str = ""


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


# 間違えた回数に数える理由。missing（コード無し）と scope（正しいコードで範囲の外）は、コードを当てる試しではないので数えない
MISSES = ("unknown", "expired", "revoked")


def _minutes(seconds: float) -> int:
    return max(1, math.ceil(seconds / 60))


def _gate_closed(settings: Settings, ip: str) -> JSONResponse | None:
    """間違いを重ねた番地は、止めている間は正しいコードでも 429（limits.Tries）。止めていなければ None。"""
    left = settings.tries.blocked(ip)
    if left <= 0:
        return None
    r = _error(
        429,
        "too_many_tries",
        detail=f"招待コードを何度も間違えたので、あと {_minutes(left)} 分ほど受け付けない",
    )
    r.headers["Retry-After"] = str(math.ceil(left))
    return r


def _missed(settings: Settings, ip: str, why: str, action: str) -> None:
    """間違えた一回を数える。止め始めたら、記録と端末（seed home の出力）に一行。コードと token は書かない。"""
    if why not in MISSES or not settings.tries.fail(ip):
        return
    t = settings.tries
    line = f"止めた: {ip} が {_minutes(t.window)} 分に {t.tries} 回間違えたので {_minutes(t.block)} 分断る"
    settings.journal.record("?", action, line)
    log.warning("門: %s", line)  # seed home は記録（SEED_AUDIT）を渡さないので、端末にも出す


def _invite(
    settings: Settings,
    request: Request,
    code: str | None,
    action: str = "",
    need: tuple[str, ...] = ("member",),
    detail: str = "",
    note: bool = True,
) -> str | JSONResponse:
    """門。招待コードか token の呼び名。入れなければ 403 の答え（設計書 §7.5、§5.9）。

    need は入ってよい範囲（どれか一つを持っていれば通る）。通した事も断った事も記録に一行（token は書かない）。
    note が False なら通した行は書かない（結果の数を後で書く口のため。断った行は書く）。
    間違えた回数はここで数え、重ねた番地は止める（429）。6 桁の家のコードだけでなく token の門の全部に効かせる:
    門はこの一か所なので分ける方が複雑で、token は長い乱数なので正しい人が 10 分に 10 回間違える事はまず無い。
    """
    ip = _client_ip(request)
    if (closed := _gate_closed(settings, ip)) is not None:
        return closed
    who, why = settings.who(code)
    if who is not None and "admin" not in who.scopes and not (who.scopes & set(need)):
        who, why = None, "scope"  # admin は member の事も全部できる
    if who is None:
        settings.journal.record("?", action, f"断った: {why}" + (f" {detail}" if detail else ""))
        _missed(settings, ip, why, action)
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
    app.state.home_sessions = {}  # 家のサーバーの話す: (呼び名, 畑の道) → Claude Code の会話の id（メモリだけ）
    home = settings.home
    body_max = HOME_BODY_MAX if home else BODY_MAX
    photo_max = H.PHOTO_MAX if home else PHOTO_MAX
    total_max = H.PHOTOS_TOTAL_MAX if home else PHOTOS_TOTAL_MAX
    too_large = f"写真は合計 {total_max // (1024 * 1024)} MB まで"

    def can_read() -> bool:
        return app.state.client is not None or (home is not None and local.available() is not None)

    try:
        settings.public_dir.mkdir(parents=True, exist_ok=True)
        P.rebuild(settings)
    except OSError as e:
        log.warning("公開のフォルダーを用意できない（%s）: %s", settings.public_dir, e)

    @app.get("/health")
    async def health():
        out = {
            "version": __version__,
            "read": can_read(),
            "talk": can_read() and settings.daily_talks > 0,  # 話す口（/api/talk）が使えるか
            "identify": bool(_plantnet()),  # 草の名（/api/identify）。Pl@ntNet の鍵が在るか
            "lookup": L.available(),
            "model": settings.model,
            "remaining": limits.remaining(),
            "audit": settings.journal.state,  # on | off | error（誰が何をしたかの記録。設計書 §5.9）
            "paused": settings.paused(),  # 受け付けを止めているか（設計書 §5.10）
        }
        if home is not None:
            out["home"] = True  # 家のサーバー（設計書 §5.13）。アプリは写真を縮めずに送る
        return out

    async def _multipart(request: Request):
        """写真付きの form をメモリ上で読む（設計書 §9）。(form, None) か (None, 誤りの答え)。"""
        if int(request.headers.get("content-length") or 0) > body_max:
            return None, _error(413, "too_large", detail=too_large)
        if not request.headers.get("content-type", "").startswith("multipart/form-data"):
            return None, _error(400, "multipart_required")
        parser = MemoryMultiPartParser(
            request.headers,
            _counted(request.stream(), body_max),
            max_files=PHOTOS_MAX + 1,
            max_fields=10,
            max_part_size=FIELD_MAX,
        )
        parser.spool_max_size = body_max
        try:
            return await parser.parse(), None
        except TooLarge:
            return None, _error(413, "too_large", detail=too_large)
        except MultiPartException as e:
            return None, _error(400, "bad_form", detail=e.message)

    @app.post("/api/read")
    async def api_read(request: Request):
        if (closed := _paused(settings)) is not None:
            return closed
        if not can_read():
            return _error(503, "read_unavailable", detail=READ_NOT_READY)
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
        who = _invite(settings, request, inv if isinstance(inv, str) else None, "read")
        if not isinstance(who, str):
            return who
        uploads = [f for f in form.getlist("photos") if isinstance(f, UploadFile)]
        if not 1 <= len(uploads) <= PHOTOS_MAX:
            return _error(400, "photos", detail=f"写真は 1〜{PHOTOS_MAX} 枚")
        photos = [await f.read() for f in uploads]
        if any(len(p) > photo_max for p in photos):
            mb = photo_max // (1024 * 1024)
            return _error(413, "photo_too_large", detail=f"写真は 1 枚 {mb} MB まで（縮小してから送る）")
        if sum(map(len, photos)) > total_max:
            return _error(413, "too_large", detail=too_large)
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
        # 観察の前書きの date・time・kind（時期と、候補地の読み方のため）。古いアプリは送らないので無くてよい。
        # 座標は Claude に渡さない（center は資料の照会にだけ使う）
        front = {k: str(form.get(k) or "") or None for k in ("date", "time", "kind")}
        for k, ok in (
            ("date", R.DATE_RE.fullmatch),
            ("time", R.TIME_RE.fullmatch),
            ("kind", R.KINDS.__contains__),
        ):
            if front[k] is not None and not ok(front[k]):
                return _error(400, "bad_front", detail=f"{k} の形が違う")

        try:
            limits.take(token, _client_ip(request))
        except LimitReached as e:
            return _error(429, "limit", kind=e.kind, detail="今日はここまで")

        if home is not None:
            field = str(form.get("field") or "")
            return await _read_home(photos, center, record, ask, language, field)
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
                **front,
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

    async def _read_home(photos, center, record, ask, language, field) -> JSONResponse | dict:
        """家のサーバーの読み（設計書 §5.13）。写真と観察を畑に置き、PC の Claude Code（無ければ鍵）で読む。"""
        from .. import cli
        from .. import client as CL
        from .. import photos as PH

        st = await run_in_threadpool(H.project, home)
        folder = H.folder_for(st, field)
        try:
            obs = await run_in_threadpool(H.store, st, folder, photos, R.parse_lines(record or ""), ask)
        except PH.PhotoError:
            return _error(415, "jpeg_only")
        path = folder.observation_path(obs)
        if obs.location:
            center = tuple(obs.location["center"])
        data = await run_in_threadpool(L.data_lines, *center, language) if center else []
        before = list(obs.reading)
        if local.available() is not None:
            try:
                got = await run_in_threadpool(cli.read_local, st, folder, obs)
            except CL.ClientError as e:
                log.warning("家のサーバーの読み: Claude Code が読めなかった（%s）", e.word)
                return _error(502, "read_failed", kind=e.word)
            model, usage = got.model, got.usage
        else:
            prev = folder.previous_observation(obs)
            try:
                reading = await RD.read(
                    app.state.client,
                    model=settings.model,
                    skill_dir=settings.skill_dir,
                    photos=await run_in_threadpool(PH.shrunk, folder, obs),
                    data=data,
                    place_data=folder.place_data(),
                    previous=prev.render() if prev else None,
                    record=R.render_lines([*folder.place_record(), *obs.record]) or None,
                    language=language,
                    ask=list(obs.ask),
                    names=[Path(r).stem for r in obs.photos],
                    date=obs.date,
                    time=obs.time,
                    kind=obs.kind,
                )
            except RD.ReadError as e:
                limits.spend(e.usage)
                return _error(e.status, "read_failed", kind=e.kind)
            limits.spend(reading.usage)
            if reading.refused:
                return {"lines": [], "data": [], "model": reading.model, "usage": reading.usage,
                        "markdown": "", "refused": True, "category": reading.category}  # fmt: skip
            CL.apply_reading(obs, CL.Reading(reading.lines, [], reading.model, reading.usage))
            cli.keep_model_lines(obs, before)
            model, usage = reading.model, reading.usage
        H.add_data(folder, obs, data)
        await run_in_threadpool(obs.write, path)
        log.info("read home photos=%d model=%s", len(photos), model)
        lines = list(obs.reading)
        return {
            "lines": [{"key": x.key, "text": x.text, "confidence": x.confidence} for x in lines],
            "data": [{"key": x.key, "text": x.text} for x in data],
            "model": model,
            "usage": usage or {},
            "markdown": RD.markdown(model, lines, data),
        }

    @app.post("/api/video")
    async def api_video(request: Request, field: str | None = None):
        """動画を受ける（家のサーバーだけ。設計書 §5.13）。本体はそのままの MP4、招待コードと時と所は頭の行。

        大きいのでメモリに貯めず、畑の中の一時のファイルに書いてから videos/<日>/ に移す。
        """
        if home is None:
            return _error(404, "not_found")
        if (closed := _paused(settings)) is not None:
            return closed
        who = _invite(settings, request, request.headers.get("x-seed-invite"), "video")
        if not isinstance(who, str):
            return who
        if int(request.headers.get("content-length") or 0) > H.VIDEO_MAX:
            return _error(413, "too_large", detail="動画は 2 GB まで")
        st = await run_in_threadpool(H.project, home)
        folder = H.folder_for(st, field)
        folder.root.mkdir(parents=True, exist_ok=True)
        from .. import bundle as B

        await run_in_threadpool(B.clean_leftovers, folder.root, ".video-*.part", 86400)  # 落ちた時の残り
        tmp = folder.root / f".video-{secrets.token_hex(6)}.part"
        try:
            head = b""
            with tmp.open("wb") as f:
                async for chunk in _counted(request.stream(), H.VIDEO_MAX):
                    if len(head) < 12:
                        head += chunk[: 12 - len(head)]
                    await run_in_threadpool(f.write, chunk)
            if not H.is_mp4(head):
                return _error(415, "mp4_only")
            where = H.where_of(request.headers.get("x-seed-where"))
            path = await run_in_threadpool(H.keep_video, folder, tmp, where)
        except TooLarge:
            return _error(413, "too_large", detail="動画は 2 GB まで")
        finally:
            tmp.unlink(missing_ok=True)
        log.info("video home bytes=%d", path.stat().st_size)
        return {"path": path.relative_to(folder.root).as_posix()}

    async def _talk_home(body: dict, who: str, code: str | None) -> JSONResponse | dict:
        """家のサーバーの話す。最後の本人の言葉を、その畑のフォルダーで PC の Claude Code に渡す。"""
        from .. import client as CL

        actor = who or "?"
        text = H.last_user_text(body.get("messages"))
        if text is None:
            settings.journal.record(actor, "talk", "断った: bad_talk")
            return _error(400, "bad_talk", detail=["本人の言葉が無い"])
        if len(text) > PR.TALK_TOTAL_TEXT_MAX:
            settings.journal.record(actor, "talk", "断った: too_large")
            return _error(413, "too_large", detail=["言葉が長すぎる"])
        language = lang.normalize(str(body.get("language") or "")) or lang.FALLBACK
        st = await run_in_threadpool(H.project, home)
        folder = H.folder_for(st, str(body.get("field") or ""))
        try:
            limits.take_talk((code or "").strip() or "home")
        except LimitReached as e:
            settings.journal.record(actor, "talk", f"断った: limit {e.kind}")
            return _error(429, "limit", kind=e.kind, detail=["今日はここまで"])
        settings.journal.record(actor, "talk", "通した")
        key = (who, str(folder.root))
        sessions = app.state.home_sessions
        try:
            said, session = await run_in_threadpool(
                local.talk, folder, text, language, sessions.get(key), home=True
            )
        except CL.ClientError as e:
            return _error(502, "talk_failed", kind=e.word)
        if session:
            sessions[key] = session
        return H.reply(said)

    @app.post("/api/talk")
    async def api_talk(request: Request):
        """話す（設計書 §7.6）。やり取りを受け、サーバーの system と道具の形とサーバーの鍵で Claude を一回呼ぶ。

        道具を動かすのは端末。中身は盤にもログにも書かない。記録には、誰が、talk、通した・断った、の一行だけ。
        """
        if (closed := _paused(settings)) is not None:
            return closed
        talk_home = home is not None and local.available() is not None
        if app.state.client is None and not talk_home:
            return _error(503, "talk_unavailable", detail=[TALK_NOT_READY])
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
        who = _invite(settings, request, code, "talk", note=False)
        if not isinstance(who, str):
            return who
        if talk_home:
            return await _talk_home(body, who, code)
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
            return _error(503, "identify_unavailable", detail=[IDENTIFY_NOT_READY])
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
        who = _invite(settings, request, inv if isinstance(inv, str) else None, "identify")
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
        who = _invite(settings, request, invite, "lookup")
        if not isinstance(who, str):
            return who
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return _error(400, "bad_center")
        if not L.available():
            return {"data": [], "note": "このサーバーには照会の部品（seed-farm[lookup]）が無い"}
        try:
            limits.take_lookup(_client_ip(request))
        except LimitReached as e:
            return _error(429, "limit", kind=e.kind)
        lg = lang.normalize(language) or lang.FALLBACK
        lines = await run_in_threadpool(L.data_lines, lat, lon, lg)
        return {"data": [{"key": x.key, "text": x.text} for x in lines]}

    @app.post("/api/publish")
    async def api_publish(request: Request):
        if (closed := _paused(settings)) is not None:
            return closed
        if int(request.headers.get("content-length") or 0) > PUBLISH_BODY_MAX:
            return _error(413, "too_large", detail=["公開の要求が大きすぎる"])
        raw = bytearray()
        try:
            async for chunk in _counted(request.stream(), PUBLISH_BODY_MAX):
                raw += chunk
        except TooLarge:
            return _error(413, "too_large", detail=["公開の要求が大きすぎる"])
        try:
            body = PublishBody.model_validate_json(bytes(raw))
        except ValidationError as e:
            return JSONResponse({"detail": e.errors(include_url=False, include_input=False)}, status_code=422)
        who = _invite(settings, request, body.invite, "publish", note=False)
        if not isinstance(who, str):
            return who
        actor = who or "?"
        try:
            pub = await run_in_threadpool(P.publish, settings, body.token, body.markdown, body.photos)
        except P.PublishError as e:
            settings.journal.record(actor, "publish", f"断った: {e.status}")
            return _error(e.status, "publish_rejected", detail=e.reasons)
        shots = len(pub.photo_names())
        state = "pending" if settings.publish_review else "public"
        held = "。預かった（動かす人が読んでから載る）" if settings.publish_review else ""
        settings.journal.record(
            actor, "publish", (f"通した（写真 {shots} 枚）" if shots else "通した") + held
        )
        await run_in_threadpool(P.note_publisher, settings, pub.id, who)  # 管理の画面の「公開した人」
        # 外向きの url。SEED_PUBLIC_URL があればそれを基底にする（127.0.0.1 で叩かれても外の url を返す。11-05）
        # 預かりの間は、この url はまだ前の版か 404（載せた後に出る）
        base = (settings.public_url or str(request.base_url)).rstrip("/")
        return {"id": pub.id, "url": f"{base}/public/{pub.id}.md", "state": state}

    @app.get("/api/publish/{record_id}/state")
    async def api_publish_state(record_id: str, request: Request):
        """公開した人が、その id の今を見る（pending | returned | public | none）。

        招待コードは頭の x-seed-invite、公開の token は頭の x-seed-token（GET なので本文を持たない。URL に出さない）。
        """
        who = _invite(
            settings, request, request.headers.get("x-seed-invite"), "publish.state", detail=record_id[:80]
        )
        if not isinstance(who, str):
            return who
        try:
            return await run_in_threadpool(
                P.state, settings, request.headers.get("x-seed-token") or "", record_id
            )
        except P.PublishError as e:
            return _error(e.status, "state_rejected", detail=e.reasons)

    @app.delete("/api/publish/{record_id}")
    async def api_withdraw(record_id: str, body: WithdrawBody, request: Request):
        who = _invite(settings, request, body.invite, "withdraw", detail=record_id[:80])
        if not isinstance(who, str):
            return who
        try:
            await run_in_threadpool(P.withdraw, settings, body.token, record_id)
        except P.PublishError as e:
            return _error(e.status, "withdraw_rejected", detail=e.reasons)
        return {"id": record_id, "withdrawn": True}

    # ---- 管理の口（動かす人だけ。範囲 admin。招待コードと同じ所に入れた token をヘッダで受ける）
    def _admin(request: Request, action: str, detail: str = "") -> str | JSONResponse:
        return _invite(
            settings, request, request.headers.get("x-seed-invite"), action, need=("admin",), detail=detail
        )

    @app.get("/api/whoami")
    async def api_whoami(request: Request):
        """入れてある token の呼び名と範囲。アプリが、管理の画面を出すかを決めるのに使う。"""
        ip = _client_ip(request)
        if (closed := _gate_closed(settings, ip)) is not None:  # 尋ねる口でも試せないように、門と同じく数える
            return closed
        who, why = settings.who(request.headers.get("x-seed-invite"))
        if who is None:
            _missed(settings, ip, why, "whoami")
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
        who = _invite(
            settings, request, request.headers.get("x-seed-invite"), action, need=("admin",), note=False
        )
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
        who = _invite(
            settings, request, request.headers.get("x-seed-invite"), action, need=("admin",), note=False
        )
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
            request,
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

    @app.get("/api/admin/pending")
    async def admin_pending(request: Request):
        """預かっている公開（読んでから載せる）。全文と写真の名を返す。"""
        who = _admin(request, "admin.pending")
        if not isinstance(who, str):
            return who
        return {"pending": await run_in_threadpool(P.pending, settings), "review": settings.publish_review}

    @app.get("/api/admin/pending/{record_id}/photos/{name}")
    async def admin_pending_photo(record_id: str, name: str, request: Request):
        """預かった写真（載せる前に見る）。"""
        who = _admin(request, "admin.pending_photo", record_id[:80])
        if not isinstance(who, str):
            return who
        if not R.ID_RE.match(record_id) or not R.safe_photo_name(name):
            return _error(404, "not_found")
        path = P.pending_photos_dir(settings, record_id) / name
        if not path.is_file():
            return _error(404, "not_found")
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/admin/pending/{record_id}/approve")
    async def admin_approve(record_id: str, request: Request):
        """預かった版を載せる（public/ に移し、索引と頁を作り直す）。記録には id を一行。"""
        action = "admin.approve"
        who = _invite(
            settings,
            request,
            request.headers.get("x-seed-invite"),
            action,
            need=("admin",),
            detail=record_id[:80],
            note=False,
        )
        if not isinstance(who, str):
            return who
        try:
            await run_in_threadpool(P.approve, settings, record_id)
        except P.PublishError as e:
            settings.journal.record(who or "?", action, f"{record_id[:80]} 断った: {e.status}")
            return _error(e.status, "approve_rejected", detail=e.reasons)
        settings.journal.record(who or "?", action, record_id)
        base = (settings.public_url or str(request.base_url)).rstrip("/")
        return {"id": record_id, "state": "public", "url": f"{base}/p/{record_id}"}

    @app.post("/api/admin/pending/{record_id}/return")
    async def admin_return(record_id: str, body: ReturnBody, request: Request):
        """預かった版を戻す（消す）。理由は公開した人が state で読む。記録には id だけ（理由は書かない）。"""
        action = "admin.return"
        who = _invite(
            settings,
            request,
            request.headers.get("x-seed-invite"),
            action,
            need=("admin",),
            detail=record_id[:80],
            note=False,
        )
        if not isinstance(who, str):
            return who
        try:
            await run_in_threadpool(P.return_pending, settings, record_id, body.reason)
        except P.PublishError as e:
            settings.journal.record(who or "?", action, f"{record_id[:80]} 断った: {e.status}")
            return _error(e.status, "return_rejected", detail=e.reasons)
        settings.journal.record(who or "?", action, record_id)
        return {"id": record_id, "state": "returned"}

    @app.post("/api/connect")
    async def api_connect(body: ConnectBody, request: Request):
        if (closed := _paused(settings)) is not None:
            return closed
        # 一言は買い手も送れる（買い手の token でできるのはここだけ。設計書 §5.9）
        who = _invite(
            settings, request, body.invite, "connect", need=("member", "buyer"), detail=str(body.to)[:80]
        )
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

    @app.get("/photos/{record_id}/{name}")
    async def public_photo(record_id: str, name: str):
        """公開された写真（開発中の確認用。本番は Caddy が site/photos/ を配る）。"""
        if not R.ID_RE.match(record_id) or not R.safe_photo_name(name):
            return _error(404, "not_found")
        path = P.photos_dir(settings, record_id) / name
        if not path.is_file():
            return _error(404, "not_found")
        return FileResponse(path, media_type="image/jpeg")

    @app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
    async def entry():
        idx = await run_in_threadpool(pages.load_index, settings)
        return _html(pages.entry_html(idx, claude=can_read(), plantnet=bool(_plantnet())))

    @app.api_route("/manual", methods=["GET", "HEAD"], response_class=HTMLResponse)
    async def manual():
        """使い方（開発中の確認用。本番は Caddy が site/manual.html を配る）。"""
        page = await run_in_threadpool(pages.manual_html)
        return _html(page) if page else _html(pages.not_found_html(), 404)

    @app.get("/static/{name}")
    async def static_file(name: str):
        """入口の写真（開発中の確認用。本番は Caddy が site/static/ を配る）。"""
        path = pages.STATIC / name
        if "/" in name or name.startswith(".") or not path.is_file():
            return _error(404, "not_found")
        return FileResponse(path)

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
