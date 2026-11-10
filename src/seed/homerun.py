# SPDX-License-Identifier: AGPL-3.0-or-later
"""アプリの歯車から `seed home`（設計書 §5.13）を子として立てる、止める、状態を見る（設計書 §5.19）。Flet を使わない。

走らせるのは、このアプリの Python の `-m seed.cli home --folder <プロジェクト> --port <口> --no-code` だけ。
画面に入れた文字や Claude の返事を命令に混ぜない。子は招待コードを出さない（`--no-code`）。画面に出すコードは
`cli.home_invite` と同じ道（プロジェクトの home.toml）で、「見せる」を押した時だけ読む。覚える出力の行からは、
念のため 6 桁の数も伏せる。持ち方は remote.Remote と同じ（出力を別の線で読み、アプリが終わる時に止める）。
"""

from __future__ import annotations

import atexit
import importlib
import importlib.util
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

from .remote import KEEP_LINES, STOP_WAIT_S, Remote, strip_ansi

PORT = 8800  # cli.HOME_PORT と同じ（cli を読まずに済むよう、ここにも置く）
SERVER_MODULES = ("uvicorn", "fastapi")  # [server] の部品
URL = re.compile(r"http://[^\s<>\"'\x1b]+")
DIGITS6 = re.compile(r"(?<!\d)\d{6}(?!\d)")
HIDDEN = "••••••"
PROBE_TIMEOUT_S = 0.5


def command(project: Path, port: int = PORT, host: str | None = None) -> list[str]:
    """子の命令。決まった語と、プロジェクトの道と、口の数だけ。host はテストで 127.0.0.1 にする時だけ。"""
    cmd = [sys.executable, "-m", "seed.cli", "home", "--folder", str(project), "--port", str(int(port))]
    if host is not None:
        cmd += ["--host", host]
    return [*cmd, "--no-code"]


def has_server() -> bool:
    """サーバーの部品（[server]）が入っているか。「部品を入れる」の後にも見直せるよう、毎回探し直す。"""
    importlib.invalidate_caches()
    return all(importlib.util.find_spec(m) is not None for m in SERVER_MODULES)


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    """この PC のその口で、もう何かが待っているか。"""
    try:
        with socket.create_connection((host, port), timeout=PROBE_TIMEOUT_S):
            return True
    except OSError:
        return False


def already(port: int = PORT) -> str | None:
    """その口がもう使われていれば "home"（seed home。端末で始めた物など）か "other"。空いていれば None。"""
    if not port_open(port):
        return None
    from . import client

    return "home" if client.is_home(f"http://127.0.0.1:{port}") else "other"


def invite_code(project: Path) -> str:
    """スマートフォンに打つ 6 桁（cli.home_invite と同じ道。無ければ作る）。画面の「見せる」の時だけ呼ぶ。"""
    from .cli import home_invite

    return home_invite(project)[1]


def hide_digits(text: str) -> str:
    return DIGITS6.sub(HIDDEN, text)


class HomeChild(Remote):
    """立てた `seed home` の一つ。状態は starting、running、stopped。"""

    def __init__(self, proc: subprocess.Popen, port: int = PORT) -> None:
        self.port = port
        self._up = False
        super().__init__(proc)

    @classmethod
    def start(cls, project: Path, port: int = PORT, host: str | None = None) -> HomeChild:  # type: ignore[override]
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        proc = subprocess.Popen(
            command(project, port, host),
            cwd=project,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            errors="replace",
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # Windows で黒い窓を出さない
        )
        r = cls(proc, port)
        atexit.register(r.stop)  # アプリが終わる時、子を残さない
        return r

    def _feed(self, chunk: str) -> None:
        """行に分けて覚える。6 桁の数は覚える前に伏せる（招待コードを持たない）。"""
        text = strip_ansi(chunk).replace("\r\n", "\n").replace("\r", "\n")
        with self._lock:
            parts = (self._partial + text).split("\n")
            self._partial = parts.pop()
            self._lines += [hide_digits(p.rstrip()) for p in parts if p.strip()]
            del self._lines[:-KEEP_LINES]

    @property
    def lines(self) -> list[str]:
        with self._lock:
            tail = hide_digits(self._partial.strip())
            return list(self._lines) + ([tail] if tail else [])

    @property
    def url(self) -> str | None:
        for line in self.lines:
            m = URL.search(line)
            if m:
                return m.group(0).rstrip(".,;:)")
        return None

    @property
    def state(self) -> str:
        if self.proc.poll() is not None:
            return "stopped"
        if not self._up and self.url is not None:
            self._up = port_open(self.port)  # URL を出した後、口が開けば立った
        return "running" if self._up else "starting"

    def stop(self) -> None:
        """止める。POSIX は SIGINT（uvicorn が静かに閉じる）、Windows は terminate。3 秒で止まらなければ kill。"""
        if self.proc.poll() is None:
            try:
                if sys.platform.startswith("win"):
                    self.proc.terminate()
                else:
                    import signal

                    self.proc.send_signal(signal.SIGINT)
                self.proc.wait(timeout=STOP_WAIT_S)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            except (OSError, ValueError):
                pass
        for f in (self.proc.stdin, self.proc.stdout):
            try:
                if f:
                    f.close()
            except (OSError, ValueError):
                pass
