# SPDX-License-Identifier: AGPL-3.0-or-later
"""話す（設計書 §7.6）。端末から来たやり取りを、サーバーの鍵で Claude に一回渡し、返事をそのまま返す。

道具を動かすのは端末。サーバーは状態を持たず、やり取りの中身を盤にもログにも書かない。
system と道具の形はサーバーが持つ物（seed/prompts.py）だけを使い、端末から送られた物は使わない。
"""

from __future__ import annotations

from pathlib import Path

import anthropic

from .. import prompts as P
from . import read as RD


def block_dict(b) -> dict:
    """SDK の塊を JSON にできる dict に（無い欄は落とす）。"""
    if hasattr(b, "model_dump"):
        return b.model_dump(mode="json", exclude_none=True)
    if isinstance(b, dict):
        return dict(b)
    return {k: v for k, v in vars(b).items() if v is not None}


async def talk(
    client: anthropic.AsyncAnthropic, *, model: str, skill_dir: Path, language: str, messages: list[dict]
) -> dict:
    """Claude を一回呼ぶ。{content, stop_reason, usage, model}。失敗は read.ReadError。"""
    msg = await RD.call_mapped(
        client,
        model=model,
        max_tokens=P.MAX_TOKENS,
        system=P.talk_system(P.skill_text(skill_dir), language),
        tools=P.TOOLS,
        messages=messages,
        output_config={"effort": P.EFFORT},
        **RD.fallback_args(model),
    )
    return {
        "content": [block_dict(b) for b in msg.content or []],
        "stop_reason": msg.stop_reason,
        "usage": RD.usage_dict(getattr(msg, "usage", None)),
        "model": getattr(msg, "model", None) or model,
    }
