# SPDX-License-Identifier: AGPL-3.0-or-later
"""家の網の中で、seed home の PC を探す（スマートフォンの側）。

UDP で `seed?` を網の全体に呼びかけ、PC（server/home.py の answer_discovery）の
`seed-home <URL>` の返事を待つ。外へは出ない（同じ Wi-Fi の中だけ）。
"""

from __future__ import annotations

import socket

PORT = 8801
ASK = b"seed?"
ANSWER = b"seed-home "


def find_home(timeout: float = 2.5, port: int = PORT, sock: socket.socket | None = None) -> str | None:
    """PC の URL。返事が無ければ None。sock はテスト用（差し替えられる）。"""
    own = sock is None
    s = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        for host in ("255.255.255.255", "<broadcast>"):
            try:
                s.sendto(ASK, (host, port))
            except OSError:
                pass
        try:
            while True:
                data, _ = s.recvfrom(1024)
                if data.startswith(ANSWER):
                    url = data[len(ANSWER) :].decode("utf-8", "replace").strip()
                    if url.startswith(("http://", "https://")):
                        return url
        except OSError:  # 時間切れ（socket.timeout）など
            return None
    finally:
        if own:
            s.close()
