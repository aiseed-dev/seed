# SPDX-License-Identifier: AGPL-3.0-or-later
"""アプリの歯車の「新しくする」（設計書 §5.19）。今の版を見せ、GitHub に新しい版が在るかを見て、入れ替える。Flet を使わない。

走らせる命令は下の定数だけ（`git fetch`、`git status`、`git rev-list`、`git pull --ff-only`、
このアプリの Python の `pip install -e ".[app,server]"`）。画面に入れた文字や Claude の返事を混ぜない。
手で直した所が在る時（`git status --porcelain` が空でない）と、手元にだけ在るコミットが在って
進めない時は、入れ替えない（本人の直しを消さないため）。`.git` の無い写し（ZIP で取った物）は GitHub の頁を開くまで。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

GITHUB = "https://github.com/aiseed-dev/seed"
GIT_FETCH = ("git", "fetch", "--quiet")
GIT_STATUS = (
    "git",
    "status",
    "--porcelain",
    "--untracked-files=no",
)  # 本人が足したファイルは見ない（pull は消さない）
GIT_COUNT = ("git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}")
GIT_HEAD = ("git", "rev-list", "--max-count=1", "--abbrev-commit", "HEAD")
GIT_PULL = ("git", "pull", "--ff-only", "--quiet")
PIP_EXTRAS = ".[app,server]"
GIT_TIMEOUT_S = 120
PIP_TIMEOUT_S = 900


def pip_command() -> list[str]:
    """このアプリが動いている Python の pip で、repo の根を入れ直す命令。"""
    return [sys.executable, "-m", "pip", "install", "-e", PIP_EXTRAS]


@dataclass
class Check:
    """見た事。state: zip（.git が無い）、nogit（git が無い・upstream が無い）、failed（fetch できない）、
    same（新しい版は無い）、behind（新しい版が在る）、dirty（在るが、手で直した所が在る）、diverged（進めない）。"""

    state: str
    behind: int = 0
    ahead: int = 0
    tail: list[str] = field(default_factory=list)


def _run(cmd, root: Path, timeout: int = GIT_TIMEOUT_S) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}  # 合言葉を聞いて止まらない
    return subprocess.run(
        list(cmd),
        cwd=root,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
        env=env,
    )


def _tail(r) -> list[str]:
    return [x for x in ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines() if x.strip()][-3:]


def is_git(root: Path) -> bool:
    return (root / ".git").exists()


def version(root: Path | None) -> str:
    """pyproject.toml の版（読めなければ seed.__version__）。"""
    if root is not None:
        try:
            got = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
            if isinstance(got, str):
                return got
        except (OSError, KeyError, tomllib.TOMLDecodeError):
            pass
    from seed import __version__

    return __version__


def head(root: Path) -> str | None:
    """今のコミットの短いハッシュ。git の写しでなければ None。"""
    if not is_git(root):
        return None
    try:
        r = _run(GIT_HEAD, root)
    except (OSError, subprocess.TimeoutExpired):
        return None
    got = r.stdout.strip()
    return got if r.returncode == 0 and got else None


def dirty(root: Path) -> bool | None:
    """手で直した所が在るか。分からなければ None。"""
    try:
        r = _run(GIT_STATUS, root)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return bool(r.stdout.strip()) if r.returncode == 0 else None


def check(root: Path) -> Check:
    """`git fetch` して、新しい版が幾つ在るか、手元にだけ在るコミットが在るか、手で直した所が在るかを見る。"""
    if not is_git(root):
        return Check("zip")
    try:
        r = _run(GIT_FETCH, root)
    except FileNotFoundError:
        return Check("nogit")
    except (OSError, subprocess.TimeoutExpired) as e:
        return Check("failed", tail=[type(e).__name__])
    if r.returncode != 0:
        return Check("failed", tail=_tail(r))
    try:
        r = _run(GIT_COUNT, root)
    except (OSError, subprocess.TimeoutExpired) as e:
        return Check("failed", tail=[type(e).__name__])
    try:
        ahead, behind = (int(x) for x in r.stdout.split())
    except ValueError:
        return Check("nogit", tail=_tail(r))  # upstream が無い（手で作った枝など）
    if behind == 0:
        return Check("same", behind, ahead)
    if ahead > 0:
        return Check("diverged", behind, ahead)
    if dirty(root) is not False:
        return Check("dirty", behind, ahead)
    return Check("behind", behind, ahead)


def run_update(root: Path) -> tuple[str, list[str]]:
    """入れ替える。("done" | "dirty" | "diverged" | "pull_failed" | "pip_failed" | 見直しの state, 出力の終わり)。

    走らせる前に見直す（見せた後に直した所が出来ていれば、入れ替えない）。"""
    got = check(root)
    if got.state != "behind":
        return got.state, got.tail
    try:
        r = _run(GIT_PULL, root)
    except (OSError, subprocess.TimeoutExpired) as e:
        return "pull_failed", [type(e).__name__]
    if r.returncode != 0:
        return "pull_failed", _tail(r)
    try:
        r = _run(pip_command(), root, PIP_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        return "pip_failed", [type(e).__name__]
    if r.returncode != 0:
        return "pip_failed", _tail(r)
    return "done", []
