# SPDX-License-Identifier: AGPL-3.0-or-later
"""家の網の中で、seed home の PC を探す（スマートフォンの側）。

UDP で `seed?` を網の全体に呼びかけ、PC（server/home.py の answer_discovery）の
`seed-home <URL>` の返事を待つ。外へは出ない（同じ Wi-Fi の中だけ）。
"""

from __future__ import annotations

import socket
import time

PORT = 8801
ASK = b"seed?"
ANSWER = b"seed-home "


def _own_ip() -> str | None:
    """この端末の網の番地（UDP の口を向けるだけ。何も送らない）。"""
    s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s2.connect(("10.255.255.255", 1))
        ip = s2.getsockname()[0]
    except OSError:
        return None
    finally:
        s2.close()
    return None if not ip or ip.startswith(("127.", "0.")) else ip


def _wait(s: socket.socket, until: float) -> str | None:
    """until（monotonic）まで返事を待つ。seed-home の返事の URL か None。"""
    while True:
        left = until - time.monotonic()
        if left <= 0:
            return None
        s.settimeout(left)
        try:
            data, _ = s.recvfrom(1024)
        except OSError:  # 時間切れ（TimeoutError）など
            return None
        if data.startswith(ANSWER):
            url = data[len(ANSWER) :].decode("utf-8", "replace").strip()
            if url.startswith(("http://", "https://")):
                return url


def find_home(
    timeout: float = 3.5,
    port: int = PORT,
    sock: socket.socket | None = None,
    own_ip: str | None = None,
    first: float = 1.2,
) -> str | None:
    """PC の URL。返事が無ければ None。

    まず放送（全体、自分の /24）。first 秒で返事が無ければ、同じ /24 の全部の番地へ一つずつ送る
    （放送を通さない網のため）。sock と own_ip はテスト用（sock を渡して own_ip が無ければ 192.168.1.10）。
    """
    own = sock is None
    s = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if own_ip is None:
        own_ip = _own_ip() if own else "192.168.1.10"
    parts = own_ip.split(".") if own_ip else []
    prefix = ".".join(parts[:3]) if len(parts) == 4 else None

    def send(host: str) -> None:
        try:
            s.sendto(ASK, (host, port))
        except OSError:
            pass

    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        start = time.monotonic()
        for host in ("255.255.255.255", "<broadcast>", *([f"{prefix}.255"] if prefix else [])):
            send(host)
        got = _wait(s, start + first)
        if got or not prefix:
            return got or _wait(s, start + timeout)
        for n in range(1, 255):
            if f"{prefix}.{n}" != own_ip:
                send(f"{prefix}.{n}")
        return _wait(s, start + timeout)
    finally:
        if own:
            s.close()
