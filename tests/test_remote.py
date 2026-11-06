# SPDX-License-Identifier: AGPL-3.0-or-later
"""Claude Code の Remote Control を立てる包み（remote.py）。本物の claude は呼ばず、偽の claude で確かめる。"""

from __future__ import annotations

import time

from seed import remote

ASKING = """#!/bin/sh
[ "$1" = remote-control ] || exit 2
printf '\\033[1mRemote Control\\033[0m\\n'
printf 'The session keeps running on this machine. Use your other devices as a remote control. Press Ctrl+C to stop.\\n'
printf 'Enable Remote Control? (y/n) '
read ans
echo "Session: https://claude.ai/code/abc123."
echo "Press Ctrl+C to stop."
trap 'exit 0' INT
while true; do sleep 0.1; done
"""

UNTRUSTED = """#!/bin/sh
echo 'Error: Workspace not trusted. Please run `claude` in /x first.' >&2
exit 1
"""


def fake(tmp_path, monkeypatch, body):
    p = tmp_path / "claude"
    p.write_text(body)
    p.chmod(0o755)
    monkeypatch.setenv("SEED_CLAUDE", str(p))


def wait_for(cond, seconds=10):
    end = time.time() + seconds
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


def test_strip_ansi():
    assert remote.strip_ansi("\x1b[1mA\x1b[0m\x1b[2K b") == "A b"


def test_asking_then_running(tmp_path, monkeypatch):
    fake(tmp_path, monkeypatch, ASKING)
    r = remote.Remote.start(tmp_path, "畑")
    try:
        assert wait_for(lambda: r.state == "asking")
        assert r.url is None
        r.answer_yes()
        assert wait_for(lambda: r.state == "running")
        assert r.url == "https://claude.ai/code/abc123"
        assert any("Press Ctrl+C" in x for x in r.lines)
    finally:
        r.stop()
    assert r.returncode is not None
    assert r.state == "stopped"


def test_untrusted(tmp_path, monkeypatch):
    fake(tmp_path, monkeypatch, UNTRUSTED)
    r = remote.Remote.start(tmp_path, "畑")
    assert wait_for(lambda: r.state == "untrusted")
    assert wait_for(lambda: r.returncode == 1)
    r.stop()


def test_qr_png():
    png = remote.qr_png("https://claude.ai/code/abc123")
    assert png is not None and png.startswith(b"\x89PNG")


def test_stop_twice_and_atexit(tmp_path, monkeypatch):
    import atexit

    fake(tmp_path, monkeypatch, ASKING)
    got = []
    monkeypatch.setattr(atexit, "register", lambda f, *a: got.append(f))
    r = remote.Remote.start(tmp_path, "畑")
    assert got == [r.stop]
    r.stop()
    r.stop()
    assert r.returncode is not None
