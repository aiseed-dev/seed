# SPDX-License-Identifier: AGPL-3.0-or-later
"""準備の画面（/setup）と直し方のボタン（設計書 §5.19）。

命令は走らせない: subprocess を差し替えて、呼ばれた命令が定数の物だけである事を見る。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import flet as ft
import pytest
from test_app import FakePage, texts, walk

from seed import local, ready
from seed import settings as settings_mod
from seed.app import setup, talk
from seed.app.main import App
from seed.client import ClientError
from seed.photos import PhotoError


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


class Done:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def fake_run(calls, answers):
    """subprocess.run の代わり。呼ばれた命令を覚え、先頭の語で答えを選ぶ。"""

    def run_(cmd, **kw):
        calls.append((list(cmd), kw.get("cwd")))
        for key, out in answers.items():
            if key in cmd:
                return out
        return Done()

    return run_


# ---------------------------------------------------------------- 足りない物だけを並べる


def test_needs_only_what_is_missing(monkeypatch):
    calls: list = []
    monkeypatch.setattr(ready.subprocess, "run", fake_run(calls, {}))
    assert ready.needs(pc=True, has_read=False) == ["install"]  # claude が無い: ログインは見ない
    assert calls == []
    monkeypatch.setattr(local, "available", lambda: "/opt/claude")
    out = {"status": Done(0, json.dumps({"loggedIn": False}))}
    monkeypatch.setattr(ready.subprocess, "run", fake_run(calls, out))
    assert ready.needs(pc=True, has_read=False) == ["login"]
    assert calls[-1][0] == ["/opt/claude", "auth", "status", "--json"]
    out["status"] = Done(0, json.dumps({"loggedIn": True}))
    assert ready.needs(pc=True, has_read=False) == []
    out["status"] = Done(1, "not json")  # 形が分からない時は戻りの値で
    assert ready.needs(pc=True, has_read=False) == ["login"]
    # スマートフォン: 読む所（招待コードか鍵）だけ
    assert ready.needs(pc=False, has_read=False) == ["phone_read"]
    assert ready.needs(pc=False, has_read=True) == []


def test_unknown_login_is_not_shown(monkeypatch):
    monkeypatch.setattr(local, "available", lambda: "/opt/claude")

    def boom(*a, **k):
        raise OSError("no")

    monkeypatch.setattr(ready.subprocess, "run", boom)
    assert ready.logged_in("/opt/claude") is None
    assert ready.needs(pc=True, has_read=True) == []


def test_claude_found_where_the_installer_puts_it(tmp_path, monkeypatch):
    """入れた直後は PATH に無い事がある: 入れた先を見つけ、PATH の頭に足す。"""
    bin_ = tmp_path / ".local" / "bin"
    bin_.mkdir(parents=True)
    exe = bin_ / "claude"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", "/nowhere")
    monkeypatch.setattr(ready, "installed_places", lambda: [exe])
    assert ready.claude_path() == str(exe)
    assert os.environ["PATH"].split(os.pathsep)[0] == str(bin_)


def test_preview_lists_rows_without_running(monkeypatch):
    calls: list = []
    monkeypatch.setattr(ready.subprocess, "run", fake_run(calls, {}))
    monkeypatch.setenv(ready.ENV_PREVIEW, "install, login,nonsense,phone_read")
    assert ready.needs(pc=True, has_read=True) == ["install", "login", "phone_read"]
    assert calls == []


# ---------------------------------------------------------------- 定数の命令だけを呼ぶ


@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
def test_install_runs_only_the_official_command(monkeypatch, platform):
    calls: list = []
    monkeypatch.setattr(ready.sys, "platform", platform)
    monkeypatch.setattr(ready.subprocess, "run", fake_run(calls, {}))
    monkeypatch.setattr(ready, "claude_path", lambda: "/home/x/.local/bin/claude")
    ok, _ = ready.run_install()
    assert ok
    ((cmd, _cwd),) = calls
    if platform == "win32":
        assert cmd == ["powershell", "-NoProfile", "-Command", "irm https://claude.ai/install.ps1 | iex"]
        assert ready.install_line() == ready.INSTALL_WINDOWS
    else:
        assert cmd == ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"]
        assert ready.install_line() == ready.INSTALL_POSIX


def test_install_failure_keeps_the_tail(monkeypatch):
    monkeypatch.setattr(ready.subprocess, "run", lambda *a, **k: Done(1, "a\nb\n", "boom"))
    ok, tail = ready.run_install()
    assert not ok and tail[-1] == "boom"


class FakeProc:
    def __init__(self, cmd, **kw):
        self.cmd = list(cmd)
        self.stdin = None
        self.stdout = None
        self.code = None

    def poll(self):
        return self.code

    def wait(self, timeout=None):
        return self.code

    def send_signal(self, sig):
        self.code = 0

    def kill(self):
        self.code = -9


def test_login_starts_only_claude_auth_login(monkeypatch):
    seen: list = []

    def popen(cmd, **kw):
        p = FakeProc(cmd, **kw)
        seen.append(p)
        return p

    monkeypatch.setattr(ready.subprocess, "Popen", popen)
    child = ready.start_login("/opt/claude")
    assert seen[0].cmd == ["/opt/claude", "auth", "login"]
    child.stop()


def test_setup_screen_login_waits_and_rechecks(app, monkeypatch):
    """「ログインする」: 子を立て、終わったら見直す。走らせたのは auth login と auth status だけ。"""
    monkeypatch.setattr(local, "available", lambda: "/opt/claude")
    state = {"in": False}
    calls: list = []

    def run_(cmd, **kw):
        calls.append(list(cmd))
        return Done(0, json.dumps({"loggedIn": state["in"]}))

    def popen(cmd, **kw):
        calls.append(list(cmd))
        p = FakeProc(cmd)
        p.code = 0
        state["in"] = True
        return p

    monkeypatch.setattr(ready.subprocess, "run", run_)
    monkeypatch.setattr(ready.subprocess, "Popen", popen)
    assert run(setup.first(app)) and app.ready["needs"] == ["login"]
    ok = run(setup.login(app))
    assert ok and app.ready["needs"] == [] and app.ready["busy"] is None
    assert {tuple(c[1:]) for c in calls} == {("auth", "status", "--json"), ("auth", "login")}
    assert app.ready["note"] == app.t("setup_login_done")


def test_parts_runs_pip_in_the_repo_with_this_python(monkeypatch):
    calls: list = []
    monkeypatch.setattr(ready.subprocess, "run", fake_run(calls, {}))
    root = ready.repo_root()
    assert root is not None and (root / "pyproject.toml").is_file()  # テストは editable の repo で走る
    ok, _ = ready.run_parts("heic")
    assert ok
    assert calls == [([sys.executable, "-m", "pip", "install", "-e", ".[heic]"], root)]
    with pytest.raises(ValueError):
        ready.parts_command("server]; rm -rf ~ #")


# ---------------------------------------------------------------- 開いた時、閉じたら出ない


def test_setup_shows_only_missing_rows(app):
    """claude が無い PC: 「入れる」の行だけ（ログインとスマートフォンの行は無い）。走らせる命令を一行で見せる。"""
    assert run(setup.first(app))
    app.route_change(path=setup.ROUTE)
    view = app.page.views[-1]
    words = texts(view)
    assert app.t("setup_install") in words and ready.install_line() in words
    assert app.t("setup_login") not in words and app.t("setup_phone_read") not in words
    assert app.t("setup_later") in words


def test_phone_setup_row_opens_the_settings_form(app):
    app.page.platform = ft.PagePlatform.ANDROID
    assert run(setup.first(app)) and app.ready["needs"] == ["phone_read"]
    app.route_change(path=setup.ROUTE)
    btn = next(
        c
        for c in walk(app.page.views[-1])
        if isinstance(c, ft.FilledButton) and c.content == app.t("setup_phone_open")
    )
    btn.on_click(None)
    assert isinstance(app.page.dialogs[-1], ft.AlertDialog)


def test_ready_pc_does_not_show_setup(app, monkeypatch):
    monkeypatch.setattr(local, "available", lambda: "/opt/claude")
    monkeypatch.setattr(ready.subprocess, "run", lambda *a, **k: Done(0, json.dumps({"loggedIn": True})))
    assert not run(setup.first(app))


def test_not_now_is_kept_and_setup_does_not_open_itself(app, seedfolder):
    assert run(setup.first(app))
    run(setup.later(app))
    assert app.settings.setup == setup.LATER
    assert settings_mod.load(str(seedfolder)).setup == "later"  # seed.toml に残る
    assert not run(setup.first(app))  # 次からは自分では出ない
    run(setup.open_setup(app))  # 歯車からは開ける
    assert app.page.route == setup.ROUTE and app.ready["needs"] == ["install"]


def test_setup_is_not_written_until_not_now(seedfolder):
    st = settings_mod.load(str(seedfolder))
    assert "\nsetup = " not in st.render()
    st.setup = "later"
    assert 'setup = "later"' in st.render()


def test_gear_form_opens_setup(app):
    app.show_settings()
    btn = next(
        c
        for c in walk(app.page.dialogs[-1])
        if isinstance(c, ft.TextButton) and c.content == app.t("form_setup")
    )
    run(btn.on_click(None))
    assert app.page.route == setup.ROUTE


def test_preview_buttons_do_not_run(app, monkeypatch):
    calls: list = []
    monkeypatch.setattr(ready.subprocess, "run", fake_run(calls, {}))
    monkeypatch.setattr(ready.subprocess, "Popen", lambda *a, **k: calls.append(a))
    monkeypatch.setenv(ready.ENV_PREVIEW, "install,login")
    app.settings.setup = "later"
    assert run(setup.first(app))  # 見本は「今はしない」の後でも出る
    run(setup.install(app))
    run(setup.login(app))
    assert calls == [] and app.ready["note"] == app.t("setup_preview")


# ---------------------------------------------------------------- 直し方のボタン


def fix_buttons(app, item) -> list[str]:
    side = talk.item_controls(app, item)
    return [
        c.content for c in walk(side[0]) if isinstance(c, ft.FilledTonalButton) and isinstance(c.content, str)
    ]


def test_fix_for_words():
    assert ready.fix_for("local_auth") == "login"
    assert ready.fix_for("heic") == "parts:heic"
    assert ready.fix_for("home_need_server") == "parts:server"
    assert ready.fix_for("local_failed") is None and ready.fix_for(None) is None


def test_fix_parts_hidden_when_not_editable(monkeypatch):
    monkeypatch.setattr(ready, "repo_root", lambda: None)
    assert ready.fix_for("heic") is None
    assert ready.fix_for("local_auth") == "login"


def test_login_error_gets_a_button_and_keeps_the_command(app):
    talk.say_error(app, ClientError("local_auth", "auth"))
    item = talk.talk_state(app)[-1]
    assert item["fix"] == "login"
    assert "claude" in item["text"]  # 文の中の命令は残す
    assert fix_buttons(app, item) == [app.t("fix_login")]


def test_heic_error_gets_parts_button(app, tmp_path):
    talk.say_error(app, PhotoError("heic", tmp_path / "a.heic", "x"))
    item = talk.talk_state(app)[-1]
    assert item["fix"] == "parts:heic" and "pip install" in item["text"]
    assert fix_buttons(app, item) == [app.t("fix_parts")]


def test_other_errors_and_phones_get_no_button(app):
    talk.say_error(app, ClientError("local_failed", "x"))
    assert "fix" not in talk.talk_state(app)[-1]
    app.page.platform = ft.PagePlatform.IOS
    talk.say_error(app, ClientError("local_auth", "auth"))
    assert "fix" not in talk.talk_state(app)[-1]
    assert fix_buttons(app, talk.talk_state(app)[-1]) == []


def test_parts_button_runs_pip_and_says_so(app, monkeypatch, tmp_path):
    calls: list = []
    monkeypatch.setattr(ready.subprocess, "run", fake_run(calls, {}))
    talk.say_error(app, PhotoError("heic", tmp_path / "a.heic", "x"))
    side = talk.item_controls(app, talk.talk_state(app)[-1])
    btn = next(c for c in walk(side[0]) if isinstance(c, ft.FilledTonalButton))
    run(btn.on_click(None))
    assert [c[0][1:5] for c in calls] == [["-m", "pip", "install", "-e"]]
    assert talk.talk_state(app)[-1]["text"] == app.t("fix_parts_done")


def test_setup_and_send_words_show_login_button(app, monkeypatch):
    """手元の Claude Code のログインが切れた: 話すの返事にボタン。"""
    monkeypatch.setattr(local, "available", lambda: "/opt/claude")

    def talk_(*a, **k):
        raise local.LocalError("local_auth", "not logged in")

    monkeypatch.setattr(local, "talk", talk_)
    run(talk.send_words(app, "こんにちは"))
    assert talk.talk_state(app)[-1].get("fix") == "login"


def test_no_shell_strings_in_commands():
    """走らせる命令は並びで渡し、shell=True を使わない（公式の入れ方も bash -c に一つの定数を渡すだけ）。"""
    import inspect

    src = inspect.getsource(ready)
    assert "shell=True" not in src
