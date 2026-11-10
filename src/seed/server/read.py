# SPDX-License-Identifier: AGPL-3.0-or-later
"""読み（設計書 §7.2）。写真 + data 行 + 本人の言葉 + 手引き → Claude → 読みの行。

手引き（skill/SKILL.md と章）は毎回同じ文なので system の頭に置いて cache_control を付ける。
毎回違う物（data 行、本人の record）は後ろの user の中に、指示ではない資料として置く。
出力は structured outputs の JSON で受け、行の文法に直すのはここ。写真と座標は書き残さない。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from .. import records as R
from ..prompts import (  # noqa: F401 — 指示は端末と同じ物（seed/prompts.py）。テストと前の import のためにここからも引ける
    ASK_RULE,
    BUILTIN_RULES,
    CORRECTION_RULE,
    FALLBACK_BETA,
    MAX_TOKENS,
    NAME_RE,
    SCHEMA,
    TASK,
    markdown,
    photo_names,
    previous_text,
    read_request,
    skill_text,
    system_blocks,
    to_lines,
    user_content,
    uses_fallbacks,
)


class ReadError(Exception):
    """Claude を呼べなかった。status は返す HTTP の番号、kind は理由の種類。"""

    def __init__(self, status: int, kind: str, retry_after: str | None = None, usage: dict | None = None):
        super().__init__(kind)
        self.status = status
        self.kind = kind
        self.retry_after = retry_after
        self.usage = usage or {}  # 応答はあったが使えなかったとき。日の予算には足す


@dataclass
class Reading:
    lines: list[R.Line]
    model: str
    usage: dict = field(default_factory=dict)
    refused: bool = False
    category: str | None = None


async def call(client: anthropic.AsyncAnthropic, **kwargs):
    """Claude を一回呼ぶ。テストはここを差し替える。"""
    return await client.beta.messages.create(**kwargs)


def usage_dict(usage) -> dict:
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    return {k: getattr(usage, k, None) or 0 for k in keys} if usage is not None else {}


def fallback_args(model: str) -> dict:
    """断られた時に別のモデルで読み直す（Haiku には無い）。"""
    return {"betas": [FALLBACK_BETA], "fallbacks": "default"} if uses_fallbacks(model) else {}


async def call_mapped(client: anthropic.AsyncAnthropic, **kwargs):
    """call を呼び、失敗を ReadError（返す番号と理由の種類）にする。読みと話すで同じ。"""
    try:
        return await call(client, **kwargs)
    except anthropic.BadRequestError as e:
        raise ReadError(502, "bad_request") from e
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
        raise ReadError(503, "credentials") from e
    except anthropic.NotFoundError as e:
        raise ReadError(503, "model") from e
    except anthropic.RateLimitError as e:
        raise ReadError(503, "busy", e.response.headers.get("retry-after")) from e
    except anthropic.InternalServerError as e:
        raise ReadError(503, "upstream") from e
    except anthropic.APIStatusError as e:
        raise ReadError(503 if e.status_code >= 500 else 502, "upstream") from e
    except anthropic.APITimeoutError as e:
        raise ReadError(504, "timeout") from e
    except anthropic.APIConnectionError as e:
        raise ReadError(503, "network") from e


async def read(
    client: anthropic.AsyncAnthropic,
    *,
    model: str,
    skill_dir: Path,
    photos: list[bytes],
    data: list[R.Line] = (),
    place_data: list[R.Line] = (),
    previous: str | None = None,
    record: str | None = None,
    language: str = "en",
    ask: list[str] = (),
    names: list[str] | None = None,
    date: str | None = None,
    time: str | None = None,
    kind: str | None = None,
    context: str | None = None,
) -> Reading:
    body = read_request(
        model,
        skill_dir,
        photos,
        data,
        place_data,
        previous,
        record,
        language,
        ask,
        names,
        date,
        time,
        kind,
        context,
    )
    msg = await call_mapped(client, **body, **fallback_args(model))
    usage = usage_dict(getattr(msg, "usage", None))
    used_model = getattr(msg, "model", None) or model
    if msg.stop_reason == "refusal":
        details = getattr(msg, "stop_details", None)
        return Reading([], used_model, usage, refused=True, category=getattr(details, "category", None))
    if msg.stop_reason == "max_tokens":
        raise ReadError(502, "truncated", usage=usage)
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise ReadError(502, "unparsable", usage=usage) from e
    return Reading(to_lines(payload, language), used_model, usage)
