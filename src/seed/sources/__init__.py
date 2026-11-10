# SPDX-License-Identifier: AGPL-3.0-or-later
"""座標から引く公開の資料（設計書 §2.2、§7.2）。元は fieldnotes の lookup.py と lookup_jp.py（11-11 に seed に一本化）。

- `world.py`: 世界のどこでも引ける物（標高、地質、土壌、Wikipedia、OpenStreetMap）と、日本のシームレス地質図。
- `jp.py`: 日本の一次資料（国土地理院、ハザードマップポータルサイト、産総研の地質図カタログ、筆ポリゴン、日本土壌インベントリー）。

どの元も (行のリスト, 生の答え) を返す。行は `- \\`data\\` <英語の枠の文> — <出典>, <URL>` の形で、日本語にするのは
`seed/lookup.py` と `seed/lookup_ja.py`。網に出るのは `world.get_json` と `jp.get_bytes` の二つだけ（テストはそこを差し替える）。
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import __version__

USER_AGENT = f"seed/{__version__} (+https://github.com/aiseed-dev/seed)"
# タイルの置き場（照会の jp.py と、動画の origin.py が使う。ここは numpy も PIL も読まない）
GSI = "https://cyberjapandata.gsi.go.jp/xyz"
PORTAL = "https://disaportaldata.gsi.go.jp/raster"


@dataclass(frozen=True)
class Point:
    """照会する地点。country は ISO の二文字（日本なら "JP"、分からなければ ""）。"""

    lat: float
    lon: float
    country: str = ""
