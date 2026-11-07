# SPDX-License-Identifier: AGPL-3.0-or-later
"""Claude Code と同じやり方を、アプリの中に（設計書 §7.6）。

手元に Claude Code が無い端末（スマートフォン、入れていない PC）でも、言葉で頼む細かい作業と間違いの指摘ができるように、
Claude に道具（seed/prompts.py の TOOLS）を渡し、Claude が道具を呼び、この端末の中で道具を動かして結果を返す、を
答えが出るまで繰り返す（run）。道具は記録のフォルダーの中だけに効く（Desk）。公開を送る道具と、命令を走らせる道具は無い。

Claude を呼ぶ運び方は二つ。繰り返しと道具は同じ:
- KeyTransport: 本人の Anthropic の API の鍵で、この端末から Anthropic の API に直に（費用は本人）。
- ServerTransport: seed のサーバー（deb2）の /api/talk 経由（作者の鍵。招待コードか token が要る）。
  system と道具の形はサーバーが持つ物を使う。この端末は、やり取りだけを送る。

スマートフォンの包みに入るよう、anthropic の SDK は使わず httpx で書く（要求の形は Claude の API の資料の通り:
x-api-key、anthropic-version、tool_use と tool_result、stop_reason）。鍵の値は、Claude に渡す文、道具の結果、
例外の文、ログのどれにも入れない。送り先は API_URL だけ。
"""

from __future__ import annotations

import base64
import dataclasses
import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from . import prompts as P
from . import records as R
from .client import Client, ClientError
from .records import Folder, Line, Observation, Plan
from .settings import Settings

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
TIMEOUT = httpx.Timeout(300.0, connect=10.0)
MAX_ROUNDS = 12  # 一つの頼みで Claude を呼ぶ回数の上限（道具の一往復が一回）
TRANSPORT: httpx.BaseTransport | None = None  # テストが差し替える（本物の網に出ない）
OBS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}$")
PLAN_NAME = "plan"


class DirectError(ClientError):
    """自分の鍵で Claude を呼べなかった。word は strings の鍵。detail に鍵の値は入れない。"""


# ---------------------------------------------------------------- 運び方


@dataclass
class Reply:
    content: list[dict]
    stop_reason: str
    usage: dict = field(default_factory=dict)
    model: str = ""


def _api_error(r: httpx.Response) -> DirectError:
    try:
        err = r.json().get("error") or {}
        detail = str(err.get("message") or "")[:200] or None
    except (ValueError, AttributeError):
        detail = None
    s = r.status_code
    if s in (401, 403):
        return DirectError("key_bad", "the Claude key was not accepted", None, s)
    if s == 404:
        return DirectError("key_model", "the model was not found", detail, s)
    if s == 429:
        return DirectError("key_limit", "the Claude key's limit is reached", detail, s)
    if s >= 500:
        return DirectError("key_busy", "Claude is busy", detail, s)
    return DirectError("key_rejected", "the request was not accepted", detail, s)


def post(key: str, body: dict) -> dict:
    """Messages API に一回送る。答えの JSON を返す。失敗は DirectError（鍵の値は文に入らない）。"""
    headers = {"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"}
    if body.get("fallbacks"):
        headers["anthropic-beta"] = P.FALLBACK_BETA
    try:
        with httpx.Client(transport=TRANSPORT, timeout=TIMEOUT) as http:
            r = http.post(API_URL, headers=headers, json=body)
    except httpx.TimeoutException:
        raise DirectError("key_timeout", "no answer from Claude") from None
    except httpx.TransportError as e:
        raise DirectError("key_unreachable", f"cannot reach Claude ({type(e).__name__})") from None
    if r.status_code >= 400:
        raise _api_error(r)
    try:
        data = r.json()
    except ValueError:
        raise DirectError("key_bad_answer", "Claude's answer could not be read") from None
    if not isinstance(data, dict):
        raise DirectError("key_bad_answer", "Claude's answer could not be read")
    return data


def with_fallbacks(body: dict, model: str) -> dict:
    return {**body, "fallbacks": "default"} if P.uses_fallbacks(model) else body


class KeyTransport:
    """本人の鍵で、この端末から直に。system と道具の形は seed/prompts.py の物。"""

    via = "key"

    def __init__(self, key: str, model: str, skill_dir: Path | None, language: str) -> None:
        self._key = key
        self.model = model
        self.system = P.talk_system(P.skill_text(skill_dir), language)

    def __repr__(self) -> str:  # 鍵の値を出さない
        return f"KeyTransport(model={self.model!r})"

    def send(self, messages: list[dict]) -> Reply:
        body = {
            "model": self.model,
            "max_tokens": P.MAX_TOKENS,
            "system": self.system,
            "tools": P.TOOLS,
            "messages": messages,
            "output_config": {"effort": P.EFFORT},
        }
        data = post(self._key, with_fallbacks(body, self.model))
        return Reply(
            [b for b in data.get("content") or [] if isinstance(b, dict)],
            str(data.get("stop_reason") or ""),
            data.get("usage") or {},
            str(data.get("model") or self.model),
        )


class ServerTransport:
    """seed のサーバーの /api/talk 経由。送るのはやり取りと言語だけ（system と道具はサーバーの物）。"""

    via = "server"

    def __init__(
        self, settings: Settings, http: httpx.BaseTransport | None = None, field: str | None = None
    ) -> None:
        self.settings = settings
        self.http = http
        self.field = field  # 家のサーバー（設計書 §5.13）で話す畑の名
        self.model = "server"

    def send(self, messages: list[dict]) -> Reply:
        st = self.settings
        with Client(st.server, st.token, st.language, invite=st.invite, transport=self.http) as c:
            data = c.talk(messages, field=self.field)
        self.model = str(data.get("model") or self.model)
        return Reply(
            [b for b in data.get("content") or [] if isinstance(b, dict)],
            str(data.get("stop_reason") or ""),
            data.get("usage") or {},
            self.model,
        )


# ---------------------------------------------------------------- 道具（記録のフォルダーの中だけ）


class ToolError(Exception):
    """道具を使えなかった。文は Claude に is_error の結果として返す。"""


@dataclass
class Desk:
    """道具が触れてよい物。記録のフォルダーと設定（草の名と公開の下書きに使う）。"""

    folder: Folder
    settings: Settings
    model: str = "claude"
    drafts: list[str] = field(default_factory=list)  # 作った公開の下書き（public/<id>.md）
    images: int = 0  # このやり取りで渡した写真の数

    @property
    def language(self) -> str:
        return self.settings.language

    def obs_path(self, name: object) -> Path:
        name = str(name or "").strip().removesuffix(".md")
        if not OBS_RE.fullmatch(name):
            raise ToolError(f"観察の名は日-時刻（例 2026-11-05-142107）: {name[:40]!r}")
        path = self.folder.observations / f"{name}.md"
        if not path.is_file():
            raise ToolError(f"その観察は無い: {name}")
        return path

    def doc(self, name: object) -> tuple[Path, Observation | Plan]:
        if str(name).strip() == PLAN_NAME:
            if not self.folder.plan.exists():
                raise ToolError("栽培計画（plan.md）はまだ無い")
            return self.folder.plan, Plan.read(self.folder.plan)
        path = self.obs_path(name)
        return path, Observation.read(path)

    def photo(self, ref: object) -> Path:
        """写真の相対の道を、記録の写真のファイルに。フォルダーの外、観察に無い写真は断る。"""
        ref = str(ref or "").strip()
        if not ref or ref.startswith(("/", "\\")) or "://" in ref or ":" in ref[:3]:
            raise ToolError("写真は記録のフォルダーからの相対の道（photos/…）で")
        root = self.folder.root.resolve()
        try:
            target = (root / ref).resolve()
            rel = target.relative_to(root).as_posix()
        except (OSError, ValueError):
            raise ToolError("記録のフォルダーの外は見ない") from None
        if not rel.startswith("photos/"):
            raise ToolError("見られるのは photos/ の下の写真だけ")
        known = {r for p in self.folder.list_observations() for r in _photos_of(p)}
        if rel not in known or not target.is_file():
            raise ToolError(f"その写真は観察に無い: {rel}")
        return target


def _photos_of(path: Path) -> list[str]:
    try:
        return list(Observation.read(path).photos)
    except (ValueError, TypeError, OSError):
        return []


def _lines(items: object, keys: tuple[str, ...]) -> list[Line]:
    if not isinstance(items, list) or not items:
        raise ToolError("lines は {key, text, confidence} の並び")
    out = []
    for it in items:
        if not isinstance(it, dict) or it.get("key") not in keys:
            raise ToolError(f"key は {', '.join(keys)}")
        text = P.clean_text(str(it.get("text") or ""))
        if not text:
            continue
        try:
            conf = round(min(1.0, max(0.0, float(it.get("confidence")))), 2)
        except (TypeError, ValueError):
            conf = 0.5
        out.append(Line(it["key"], text, conf))
    if not out:
        raise ToolError("書く行が無い")
    return out


def t_list_observations(desk: Desk, inp: dict) -> str:
    rows = []
    for p in desk.folder.list_observations():
        try:
            o = Observation.read(p)
        except (ValueError, TypeError, OSError):
            continue
        kind = "候補地" if o.kind == "candidate" else "自分の畑"
        rows.append(
            f"- {p.stem}: {o.date} {o.time}、写真 {len(o.photos)} 枚、読み {o.model or 'まだ'}、{kind}"
        )
    return "\n".join(rows) or "観察はまだ無い"


def t_read_observation(desk: Desk, inp: dict) -> str:
    obs = Observation.read(desk.obs_path(inp.get("name")))
    return dataclasses.replace(obs, location=None).render()  # 細かい座標は渡さない


def t_view_photo(desk: Desk, inp: dict) -> list[dict]:
    from . import photos

    path = desk.photo(inp.get("path"))
    if desk.images >= P.TALK_IMAGES_MAX:
        raise ToolError(f"このやり取りでは、もう写真を見せられない（{P.TALK_IMAGES_MAX} 枚まで）")
    data = photos.shrink(path, max_side=P.TALK_VIEW_SIDE)
    desk.images += 1
    return [
        {"type": "text", "text": f"写真 {path.stem}"},
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(data).decode()},
        },
    ]


def t_photos_by_place(desk: Desk, inp: dict) -> str:
    from . import album

    return album.render_places(album.by_place(desk.folder), desk.language) or "写真はまだ無い"


def t_mark_line(desk: Desk, inp: dict) -> str:
    path, doc = desk.doc(inp.get("observation"))
    verdict = inp.get("verdict")
    if verdict not in R.VERDICTS:
        raise ToolError("verdict は right か wrong")
    try:
        line = doc.mark(str(inp.get("key")), verdict, inp.get("reason") or None, inp.get("text") or None)
    except KeyError as e:
        raise ToolError(str(e.args[0])) from None
    doc.write(path)
    return f"印を付けた: {line.render()}"


def t_add_words(desk: Desk, inp: dict) -> str:
    path, doc = desk.doc(inp.get("observation"))
    text = str(inp.get("text") or "").replace("\n", " ").strip()
    if not text:
        raise ToolError("text が空")
    try:
        line = doc.say(str(inp.get("key")), text)
    except ValueError as e:
        raise ToolError(str(e)) from None
    doc.write(path)
    return f"足した: {line.render()}"


def t_write_reading(desk: Desk, inp: dict) -> str:
    from .cli import keep_model_lines

    path = desk.obs_path(inp.get("observation"))
    obs = Observation.read(path)
    lines = _lines(inp.get("lines"), R.READING_KEYS)
    before = list(obs.reading)
    obs.reread(lines, desk.model)
    keep_model_lines(obs, before)
    obs.write(path)
    return "書き直した:\n" + R.render_lines(obs.reading)


def t_read_plan(desk: Desk, inp: dict) -> str:
    if not desk.folder.plan.exists():
        return "栽培計画（plan.md）はまだ無い。write_plan で作れる"
    return Plan.read(desk.folder.plan).render()


def t_write_plan(desk: Desk, inp: dict) -> str:
    from .cli import load_plan

    plan = load_plan(desk.settings, desk.folder)
    plan.reread(_lines(inp.get("lines"), R.PLAN_KEYS), desk.model)
    if inp.get("season"):
        plan.season = str(inp["season"]).strip()[:80]
    plan.write(desk.folder.plan)
    return "書いた:\n" + R.render_lines(plan.reading)


def t_read_land(desk: Desk, inp: dict) -> str:
    from .land import scrub

    data = [scrub(l.render()) for l in desk.folder.place_data()]
    rec = [scrub(l.render()) for l in desk.folder.place_record()]
    out = ["## Data（出典付き）", *(data or ["(none)"])]
    if rec:
        out += ["", "## 本人が確かめた事", *rec]
    return "\n".join(out)


def t_identify_plant(desk: Desk, inp: dict) -> str:
    from . import identify
    from .cli import identify_photos

    path = desk.obs_path(inp.get("observation"))
    obs = Observation.read(path)
    stem = str(inp.get("photo") or "").strip()
    via = "local" if identify.available() else "server"
    if via == "server" and not desk.settings.invite:
        raise ToolError("Pl@ntNet の鍵も招待コードも無いので、草の名は確かめられない")
    try:
        added = identify_photos(desk.settings, desk.folder, obs, [stem], via)
    except ClientError as e:
        raise ToolError(f"確かめられなかった（{e.word}）") from None
    obs.write(path)
    return "\n".join(l.render() for l in added) or "名は分からなかった"


def t_draft_public(desk: Desk, inp: dict) -> str:
    from .cli import make_public, resolve_photos

    names = inp.get("observations")
    if not isinstance(names, list) or not names:
        raise ToolError("observations は観察の名の並び")
    observations = [Observation.read(desk.obs_path(n)) for n in names]
    pid = str(inp.get("id") or "").strip()
    if not R.ID_RE.match(pid):
        raise ToolError("id は英小文字・数字・ハイフン")

    def tags(v: object) -> list[str]:
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []

    chosen = None  # 無ければ日ごとに今日の一枚
    if "photos" in inp:
        if not isinstance(inp["photos"], list):
            raise ToolError("photos は写真の名の並び")
        try:
            chosen = resolve_photos(observations, [str(x) for x in inp["photos"]])
        except ValueError as e:
            raise ToolError(f"その写真は、選んだ観察に無い: {e.args[0]}") from None

    pub = make_public(
        desk.settings,
        observations,
        public_id=pid,
        place=str(inp.get("place") or ""),
        word=str(inp.get("word") or ""),
        what=tags(inp.get("what")),
        next_=tags(inp.get("next")),
        with_coord=bool(inp.get("coord")),
        contact=str(inp.get("contact") or "") or None,
        name=str(inp.get("name") or "") or None,
        photos=chosen,
        folder=desk.folder,
    )
    bad = pub.check()
    if not pub.days:
        bad.append("入れる行が無い（判定の付いた読み、Data、Record）")
    if bad:
        raise ToolError("直す所: " + "; ".join(bad))
    desk.folder.public.mkdir(parents=True, exist_ok=True)
    pub.write(desk.folder.public / f"{pid}.md")
    rel = f"public/{pid}.md"
    if rel not in desk.drafts:
        desk.drafts.append(rel)
    note = (
        "（候補地の観察が入っている。持ち主の許しの無い所は公開しない）\n"
        if any(o.kind == "candidate" for o in observations)
        else ""
    )
    return f"{note}下書きを {rel} に作った。送っていない。アプリが本人に全文を見せ、本人が「出す」を押すと送られる:\n\n{pub.render()}"


TOOL_RUN = {
    "list_observations": t_list_observations,
    "read_observation": t_read_observation,
    "view_photo": t_view_photo,
    "photos_by_place": t_photos_by_place,
    "mark_line": t_mark_line,
    "add_words": t_add_words,
    "write_reading": t_write_reading,
    "read_plan": t_read_plan,
    "write_plan": t_write_plan,
    "read_land": t_read_land,
    "identify_plant": t_identify_plant,
    "draft_public": t_draft_public,
}
assert set(TOOL_RUN) == P.TOOL_NAMES


def run_tool(desk: Desk, name: str, inp: object) -> tuple[str | list[dict], bool]:
    """道具を一つ動かす。(結果, 誤りか)。知らない道具、形の違う入力、記録の外を指す道は誤りとして返す。"""
    fn = TOOL_RUN.get(name)
    if fn is None:
        return f"その道具は無い: {name}", True
    if not isinstance(inp, dict):
        return "入力の形が違う", True
    try:
        return fn(desk, inp), False
    except ToolError as e:
        return str(e), True
    except (OSError, ValueError, TypeError) as e:
        return f"できなかった（{type(e).__name__}）", True


# ---------------------------------------------------------------- 繰り返し


@dataclass
class Outcome:
    text: str
    stopped: str | None = None  # None（答えが出た）| max_rounds | stopped | max_tokens | refusal
    drafts: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


def fresh_if_needed(messages: list[dict]) -> bool:
    """やり取りが上限に近ければ、新しく始める（前の物を消す。途中を書き換えない）。新しくしたら True。"""
    n, images, size = P.talk_size(messages)
    if (
        n + 2 * MAX_ROUNDS + 1 > P.TALK_MESSAGES_MAX
        or images >= P.TALK_IMAGES_MAX
        or size > P.TALK_TOTAL_TEXT_MAX // 2
        or (messages and messages[-1].get("role") == "assistant" and _uses(messages[-1]))
    ):
        messages.clear()
        return True
    return False


def _uses(message: dict) -> list[dict]:
    c = message.get("content")
    return (
        [b for b in c if isinstance(b, dict) and b.get("type") == "tool_use"] if isinstance(c, list) else []
    )


def _close_open_uses(messages: list[dict], why: str) -> None:
    """答えの無い道具の呼び出しが残っていれば、動かさなかった事を結果として返しておく（次の頼みが通るように）。"""
    if messages and messages[-1].get("role") == "assistant":
        uses = _uses(messages[-1])
        if uses:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": u["id"], "content": why, "is_error": True}
                        for u in uses
                    ],
                }
            )


def _add_usage(total: dict, usage: dict) -> None:
    for k, v in (usage or {}).items():
        if isinstance(v, (int, float)):
            total[k] = total.get(k, 0) + v


def run(
    transport,
    desk: Desk,
    messages: list[dict],
    text: str,
    stop: threading.Event | None = None,
    max_rounds: int = MAX_ROUNDS,
) -> Outcome:
    """本人の言葉を足し、Claude が道具を呼ぶ間は端末で動かして返す、を答えが出るまで（上限 max_rounds 回）。

    messages は Messages API の形のやり取りで、ここで足していく（次の頼みでも続ける）。
    失敗（ClientError）はそのまま上げる。その時 messages は空にする（半端なやり取りを残さない）。
    """
    fresh_if_needed(messages)
    messages.append({"role": "user", "content": [{"type": "text", "text": text}]})
    desk.images = P.talk_size(messages)[1]
    desk.model = getattr(transport, "model", desk.model)
    usage: dict = {}
    last_text = ""
    try:
        for round_ in range(max_rounds):
            if stop is not None and stop.is_set():
                return Outcome(last_text, "stopped", list(desk.drafts), usage)
            reply = transport.send(messages)
            _add_usage(usage, reply.usage)
            desk.model = reply.model or desk.model
            if reply.stop_reason == "refusal":
                messages.clear()  # 断られたやり取りを持ち越さない
                return Outcome(last_text, "refusal", list(desk.drafts), usage)
            content = [b for b in reply.content if b.get("type") != "fallback"]
            said = "\n".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
            last_text = said or last_text
            if not content:
                return Outcome(last_text, None, list(desk.drafts), usage)
            messages.append({"role": "assistant", "content": content})
            uses = _uses(messages[-1])
            if reply.stop_reason == "pause_turn":
                continue
            if reply.stop_reason != "tool_use" or not uses:
                _close_open_uses(messages, "動かさなかった（答えが切れた）")
                stopped = "max_tokens" if reply.stop_reason == "max_tokens" else None
                return Outcome(last_text, stopped, list(desk.drafts), usage)
            results = []
            for u in uses:
                out, err = run_tool(desk, str(u.get("name")), u.get("input"))
                block = {"type": "tool_result", "tool_use_id": u["id"], "content": out}
                if err:
                    block["is_error"] = True
                results.append(block)
            messages.append({"role": "user", "content": results})
        return Outcome(last_text, "max_rounds", list(desk.drafts), usage)
    except ClientError:
        messages.clear()
        raise


# ---------------------------------------------------------------- 写真の読み取り（自分の鍵で）


def read_with_key(st: Settings, folder: Folder, obs: Observation, skill_dir: Path | None):
    """観察を本人の鍵で読み、client.Reading を返す。指示はサーバーの /api/read と同じ（prompts.read_request）。"""
    from . import photos
    from .client import Reading

    if not st.anthropic_key:
        raise DirectError("key_missing", "no Claude key")
    prev = folder.previous_observation(obs)
    record = R.render_lines([*folder.place_record(), *obs.record]) or None
    body = P.read_request(
        st.model,
        skill_dir,
        photos.shrunk(folder, obs),
        list(obs.data),
        folder.place_data(),
        prev.render() if prev else None,
        record,
        obs.language or st.language,
        list(obs.ask),
        [Path(r).stem for r in obs.photos],
    )
    data = post(st.anthropic_key, with_fallbacks(body, st.model))
    stop = data.get("stop_reason")
    if stop == "refusal":
        raise DirectError("server_refused", "Claude did not read these photos")
    if stop == "max_tokens":
        raise DirectError("key_bad_answer", "the answer was cut off")
    text = "".join(b.get("text", "") for b in data.get("content") or [] if b.get("type") == "text")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise DirectError("key_bad_answer", "the answer was not JSON") from None
    model = str(data.get("model") or st.model)
    return Reading(P.to_lines(payload, obs.language or st.language), [], model, data.get("usage") or {})
