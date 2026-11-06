# SPDX-License-Identifier: AGPL-3.0-or-later
"""Claude Code の Remote Control（`claude remote-control --name 畑の名`）を、畑のフォルダーで立てる。

スマートフォンの Claude アプリの Code から、この PC の Claude Code（seed の手引きと `seed` 命令つき）と話すため。
やる事は端末で打つ `cd 畑のフォルダー && claude remote-control --name 畑の名` と同じで、出力を読んで状態を見せるだけ。
Flet も asyncio も使わない（読み取りは別の線）。出力の言い回しには頼らず、使う目印は次の三つだけ:
`Workspace not trusted`（フォルダーを一度 claude で開いていない）、`(y/n)`（Claude Code の問い）、
`Press Ctrl+C to stop`（立ち上がった）。URL は出力の中の最初の `https://` をそのまま拾う。
"""

from __future__ import annotations

import atexit
import io
import re
import signal
import subprocess
import threading
from pathlib import Path

from . import local

KEEP_LINES = 200  # 覚えておく行の数（古い方から捨てる）
STOP_WAIT_S = 3  # SIGINT の後、止まるのを待つ秒数。過ぎたら kill
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")
URL = re.compile(r"https://[^\s<>\"'\x1b]+")
TRAILING = ".,;:!?)]}>、。」』"


def strip_ansi(text: str) -> str:
    """色や位置を決める制御の列を取り除く。"""
    return ANSI.sub("", text)


class Remote:
    """立てた `claude remote-control` の一つ。"""

    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
        self._lines: list[str] = []
        self._partial = ""  # 改行の来ていない最後の行（問いは改行なしで出る）
        self._lock = threading.Lock()
        self._answered = False
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    @classmethod
    def start(cls, folder: Path, name: str) -> Remote:
        proc = subprocess.Popen(
            [local.command(), "remote-control", "--name", name],
            cwd=folder,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            errors="replace",
        )
        r = cls(proc)
        atexit.register(r.stop)  # アプリが終わる時、子の claude を残さない（止まっていれば何もしない）
        return r

    # --- 出力を読む
    def _read(self) -> None:
        out = self.proc.stdout
        try:
            while out is not None:
                chunk = out.read1(4096) if hasattr(out, "read1") else out.read(1)
                if not chunk:
                    break
                self._feed(chunk)
        except (ValueError, OSError):
            pass
        finally:
            self.proc.wait()

    def _feed(self, chunk: str) -> None:
        text = strip_ansi(chunk).replace("\r\n", "\n").replace("\r", "\n")
        with self._lock:
            parts = (self._partial + text).split("\n")
            self._partial = parts.pop()
            for p in parts:
                if p.strip():
                    self._lines.append(p.rstrip())
            if self._partial.rstrip().endswith("(y/n)"):  # 問いは改行なしで止まる
                self._lines.append(self._partial.rstrip())
                self._partial = ""
            del self._lines[:-KEEP_LINES]

    # --- 見せる物
    @property
    def lines(self) -> list[str]:
        with self._lock:
            return list(self._lines) + ([self._partial.strip()] if self._partial.strip() else [])

    @property
    def url(self) -> str | None:
        for line in self.lines:
            m = URL.search(line)
            if m:
                return m.group(0).rstrip(TRAILING)
        return None

    @property
    def returncode(self) -> int | None:
        return self.proc.poll()

    @property
    def state(self) -> str:
        """starting（何も決まらない）、asking（Claude Code の問いに答え待ち）、untrusted（フォルダーが未信頼）、
        running（立った）、stopped（プロセスが終わった）。"""
        lines = self.lines
        if any("Workspace not trusted" in x for x in lines):
            return "untrusted"
        if self.proc.poll() is not None:
            return "stopped"
        # 問い（(y/n)）より後に Press Ctrl+C が出たら立った。問いが無い（二度目以降）なら、出ていれば立った
        ask = max((i for i, x in enumerate(lines) if "(y/n)" in x), default=-1)
        if self.url or any("Press Ctrl+C to stop" in x for x in lines[ask + 1 :]):
            return "running"
        if ask >= 0 and not self._answered:
            return "asking"
        return "starting"

    # --- 操作
    def answer_yes(self) -> None:
        """人が「はい」を押した。Claude Code の問いに y を返す。"""
        self._answered = True
        try:
            if self.proc.stdin:
                self.proc.stdin.write("y\n")
                self.proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError):
            pass

    def stop(self) -> None:
        """SIGINT で止める（SIGTERM では止まらない）。3 秒で止まらなければ kill。二度呼んでもよい。"""
        if self.proc.poll() is None:
            try:
                self.proc.send_signal(signal.SIGINT)
                self.proc.wait(timeout=STOP_WAIT_S)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            except OSError:
                pass
        for f in (self.proc.stdin, self.proc.stdout):
            try:
                if f:
                    f.close()
            except (OSError, ValueError):
                pass


def qr_png(url: str) -> bytes | None:
    """URL の QR コードを PNG にする。qrcode が無ければ None。"""
    try:
        import qrcode
    except ImportError:
        return None
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return buf.getvalue()
