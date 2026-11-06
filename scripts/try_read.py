# SPDX-License-Identifier: AGPL-3.0-or-later
"""本物の Claude で一度だけ読ませて確かめる。テストの外（費用がかかる。一回 約 $0.06）。

    .venv/bin/python scripts/try_read.py 畑.jpg [畑2.jpg ...] [--center 34.05,134.25] [--language ja]

ANTHROPIC_API_KEY が無ければ理由を言って終わる。写真はサーバーと同じに縮小（長辺 1568 px、JPEG 85）してから送る。
写真も座標もどこにも書き残さない。
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

import anthropic
from PIL import Image, ImageOps

from seed.server import limits, lookup
from seed.server import read as RD
from seed.server.settings import Settings

LONG_SIDE = 1568


def shrink(path: Path) -> bytes:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((LONG_SIDE, LONG_SIDE))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("photos", nargs="+", type=Path)
    ap.add_argument("--center", help="lat,lon（照会に使う。fieldnotes-farm が無ければ使わない）")
    ap.add_argument("--record", help="本人の言葉")
    ap.add_argument("--previous", type=Path, help="同じ場所の前の観察（observations/*.md）")
    ap.add_argument("--language", default="ja")
    args = ap.parse_args()

    settings = Settings.from_env()
    if not settings.api_key:
        print("ANTHROPIC_API_KEY が無いので、本物の読みは試さない。", file=sys.stderr)
        return 1
    if not 1 <= len(args.photos) <= 6:
        print("写真は 1〜6 枚。", file=sys.stderr)
        return 1
    photos = [shrink(p) for p in args.photos]
    if any(len(p) > limits.PHOTO_MAX for p in photos):
        print("縮小しても 2 MB を超える写真がある。", file=sys.stderr)
        return 1
    data = []
    if args.center:
        lat, lon = (float(x) for x in args.center.split(","))
        data = lookup.data_lines(lat, lon)

    client = anthropic.AsyncAnthropic(api_key=settings.api_key)
    try:
        reading = await RD.read(
            client,
            model=settings.model,
            skill_dir=settings.skill_dir,
            photos=photos,
            data=data,
            previous=args.previous.read_text(encoding="utf-8") if args.previous else None,
            record=args.record,
            language=args.language,
        )
    except RD.ReadError as e:
        print(f"読めなかった: {e.kind}（HTTP {e.status} として返す物）", file=sys.stderr)
        return 1
    if reading.refused:
        print(f"断られた: {reading.category}", file=sys.stderr)
    else:
        print(RD.markdown(reading.model, reading.lines, data))
    print(json.dumps(reading.usage), f"約 ${limits.cost_usd(reading.usage):.4f}", file=sys.stderr)
    if not reading.usage.get("cache_read_input_tokens") and not reading.usage.get(
        "cache_creation_input_tokens"
    ):
        print("キャッシュは書かれていない（手引きが短いと最小の長さに届かない）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
