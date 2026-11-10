# SPDX-License-Identifier: AGPL-3.0-or-later
"""アプリを使い始める準備を見る所と、直すために走らせる命令（設計書 §5.19）。Flet を使わない。

見る物: この PC に Claude Code が在るか、ログインしているか（`claude auth status`）、スマートフォンに読む所が在るか。
走らせる物は、下の定数の命令だけ: Anthropic の公式の入れ方、`claude auth login`、この repo の `.venv` の
`pip install -e ".[…]"`。画面に入れた文字や Claude の返事を命令に混ぜない（shell で文字を組まない）。
公式の入れ方はパイプを使うので、決まった一つの文字列だけを bash か PowerShell に渡す。
"""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import sys
from pathlib import Path

from . import local

# Anthropic の公式の入れ方（https://code.claude.com/docs/en/setup の Native Install。2026-11-10 に見た）
INSTALL_SOURCE = "https://code.claude.com/docs/en/setup"
INSTALL_POSIX = "curl -fsSL https://claude.ai/install.sh | bash"  # macOS、Linux
INSTALL_WINDOWS = "irm https://claude.ai/install.ps1 | iex"  # Windows の PowerShell
INSTALL_TIMEOUT_S = 900
STATUS_ARGS = ("auth", "status", "--json")
STATUS_TIMEOUT_S = 20
LOGIN_ARGS = ("auth", "login")
# 「部品を入れる」で入れてよい extra の名（pyproject.toml の optional-dependencies）
PARTS = ("heic", "server")
PARTS_TIMEOUT_S = 900
ENV_PREVIEW = "SEED_SETUP_PREVIEW"  # 画面の見本: 「install,login,phone_read」の形。押しても何も走らせない

NEEDS = ("install", "login", "phone_read")
WORD_FIX = {"local_auth": "login", "heic": "parts:heic", "home_need_server": "parts:server"}


def windows() -> bool:
    return sys.platform.startswith("win")


# ---------------------------------------------------------------- Claude Code が在るか


def install_line() -> str:
    """走らせる前に見せる一行（この OS の公式の入れ方）。"""
    return INSTALL_WINDOWS if windows() else INSTALL_POSIX


def install_command() -> list[str]:
    """公式の入れ方を走らせる命令。決まった文字列を一つ渡すだけ。"""
    if windows():
        return ["powershell", "-NoProfile", "-Command", INSTALL_WINDOWS]
    return ["bash", "-c", INSTALL_POSIX]


def installed_places() -> list[Path]:
    """公式の入れ方が claude を置く所。入れた直後は PATH に無い事があるので、ここも探す。"""
    home = Path.home()
    return [home / ".local" / "bin" / ("claude.exe" if windows() else "claude")]


def claude_path() -> str | None:
    """claude の道。PATH に無ければ入れた先を探し、在ればその場所を PATH の頭に足す（子の命令も見つけるように）。"""
    got = local.available()
    if got is not None:
        return got
    for p in installed_places():
        if p.is_file() and os.access(p, os.X_OK):
            os.environ["PATH"] = str(p.parent) + os.pathsep + os.environ.get("PATH", "")
            return local.available() or str(p)
    return None


def run_install() -> tuple[bool, list[str]]:
    """公式の入れ方を走らせる。(済んだか, 出力の終わりの数行)。"""
    try:
        r = subprocess.run(
            install_command(),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=INSTALL_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, [type(e).__name__]
    tail = [x for x in (r.stdout + "\n" + r.stderr).splitlines() if x.strip()][-3:]
    return r.returncode == 0 and claude_path() is not None, tail


# ---------------------------------------------------------------- ログイン


def logged_in(path: str) -> bool | None:
    """`claude auth status --json` の loggedIn。分からなければ None（出力の値は読まず、この一つだけを見る）。"""
    try:
        r = subprocess.run(
            [path, *STATUS_ARGS],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=STATUS_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    try:
        got = json.loads(r.stdout).get("loggedIn")
    except (ValueError, AttributeError):
        got = None
    if isinstance(got, bool):
        return got
    return r.returncode == 0


def start_login(path: str):
    """`claude auth login` を子として立てる（ブラウザが開く）。出力は remote.Remote と同じく別の線で読む。"""
    from .remote import Remote

    proc = subprocess.Popen(
        [path, *LOGIN_ARGS],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        errors="replace",
    )
    r = Remote(proc)
    atexit.register(r.stop)  # アプリが終わる時に子を残さない
    return r


# ---------------------------------------------------------------- 足りない物


def preview() -> list[str] | None:
    """画面の見本（環境変数）。無ければ None。"""
    raw = os.environ.get(ENV_PREVIEW)
    if raw is None:
        return None
    return [x for x in (y.strip() for y in raw.split(",")) if x in NEEDS]


def needs(pc: bool, has_read: bool) -> list[str]:
    """足りない物（NEEDS の名）を並べる。PC は Claude Code が在るか、在ればログインしているか。
    スマートフォンは読む所（招待コードか自分の鍵）が在るか。ログインが分からない時は出さない。"""
    shown = preview()
    if shown is not None:
        return shown
    if not pc:
        return [] if has_read else ["phone_read"]
    path = claude_path()
    if path is None:
        return ["install"]
    return ["login"] if logged_in(path) is False else []


# ---------------------------------------------------------------- 部品を入れる


def repo_root() -> Path | None:
    """seed を `pip install -e` で入れた repo の根。editable でなければ（包みが site-packages に在れば）None。"""
    import seed

    root = Path(seed.__file__).resolve().parent.parent.parent
    pyproject = root / "pyproject.toml"
    if not (pyproject.is_file() and (root / "src" / "seed").is_dir()):
        return None
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    return root if 'name = "seed-farm"' in text else None


def parts_command(extra: str) -> list[str]:
    """アプリが動いている Python の pip で、repo の根の extra を入れる命令。"""
    if extra not in PARTS:
        raise ValueError(extra)
    return [sys.executable, "-m", "pip", "install", "-e", f".[{extra}]"]


def run_parts(extra: str) -> tuple[bool, list[str]]:
    """部品を入れる。(済んだか, 出力の終わりの数行)。"""
    root = repo_root()
    if root is None:
        return False, []
    try:
        r = subprocess.run(
            parts_command(extra),
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=PARTS_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, [type(e).__name__]
    tail = [x for x in (r.stdout + "\n" + r.stderr).splitlines() if x.strip()][-3:]
    return r.returncode == 0, tail


# ---------------------------------------------------------------- 歯車の PC の行の見本


ENV_PC_PREVIEW = (
    "SEED_PC_PREVIEW"  # 歯車の PC の行の見本: 「home=running,update=behind」の形。押しても何も走らせない
)
PC_PREVIEW = {
    "home": ("none", "starting", "running", "stopped", "already", "port_used", "need_server"),
    "update": ("unknown", "same", "behind", "dirty", "diverged", "zip"),
}


def pc_preview() -> dict[str, str] | None:
    """歯車の PC の行の見本（環境変数）。無ければ None。Web でも PC の行を出す。知らない値は捨てる。"""
    raw = os.environ.get(ENV_PC_PREVIEW)
    if raw is None:
        return None
    out: dict[str, str] = {}
    for part in raw.split(","):
        k, _, v = part.partition("=")
        k, v = k.strip(), v.strip()
        if v in PC_PREVIEW.get(k, ()):
            out[k] = v
    return out


def fix_for(word: str | None) -> str | None:
    """文の鍵（strings）に付ける直し方: "login"、"parts:heic"、"parts:server"。付けられなければ None。"""
    fix = WORD_FIX.get(word or "")
    if fix is None:
        return None
    if fix.startswith("parts:") and repo_root() is None:
        return None  # editable で入っていない（どこへ入れるか分からない）
    return fix
