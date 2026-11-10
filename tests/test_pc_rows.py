# SPDX-License-Identifier: AGPL-3.0-or-later
"""歯車の PC の行（設計書 §5.19）: スマートフォンから写真を受ける（seed home を子として）と、新しくする。

本物の `seed home` は口 8800・8801 で立てない（この PC で作者が動かしている事がある）。子は差し替えるか、
空いている別の口で、決まった文を出すだけの小さな Python を立てる。「新しくする」は一時のフォルダーに作った
git の repo（手元の bare を origin にする）で見て、pip は差し替える。この repo には fetch も pull もしない。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import flet as ft
import pytest
from test_app import FakePage, texts, walk

from seed import cli, homerun, ready, update
from seed import settings as settings_mod
from seed.app import pc_rows, talk
from seed.app.main import App


def run(coro):
    return asyncio.run(coro)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def safe_port(monkeypatch):
    """作者の seed home の口（8800）を見に行かない・取りに行かない。"""
    monkeypatch.setattr(homerun, "PORT", free_port())


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


class FakeChild:
    """立てた子の代わり。state を手で動かす。"""

    def __init__(self, project, port, state="running", url="http://192.0.2.1:8800"):
        self.project, self.port = project, port
        self.state, self.url = state, url
        self.lines = ["  サーバーの URL: " + url]
        self.stopped = False

    def stop(self):
        self.stopped = True
        self.state = "stopped"


@pytest.fixture
def started(monkeypatch):
    """HomeChild.start を差し替える。呼ばれた (project, port) を覚える。"""
    calls: list = []

    def start(project, port=homerun.PORT, host=None):
        calls.append((Path(project), port))
        return FakeChild(project, port)

    monkeypatch.setattr(homerun.HomeChild, "start", staticmethod(start))
    monkeypatch.setattr(homerun, "already", lambda port: None)
    monkeypatch.setattr(homerun, "has_server", lambda: True)
    return calls


def form_controls(app) -> list:
    """開いている歯車のフォームの部品（開いていなければ開く）。押すと、開いたまま中が作り直される。"""
    if not app.page.dialogs:
        app.show_settings()
    return list(walk(app.page.dialogs[-1]))


def form_texts(app) -> list[str]:
    """歯車のフォームを開き直して、見える文。"""
    app.show_settings()
    return texts(app.page.dialogs[-1])


def now_texts(app) -> list[str]:
    """開いているフォームの今の文（開き直さない）。"""
    return texts(app.page.dialogs[-1])


def button(app, word: str):
    return next(
        c
        for c in form_controls(app)
        if isinstance(c, (ft.TextButton, ft.FilledTonalButton)) and c.content == app.t(word)
    )


def press(app, word: str) -> None:
    got = button(app, word).on_click(None)
    if asyncio.iscoroutine(got):
        run(got)


# ---------------------------------------------------------------- seed home の命令


def test_home_command_is_fixed(tmp_path):
    cmd = homerun.command(tmp_path, 8800)
    assert cmd == [
        sys.executable,
        "-m",
        "seed.cli",
        "home",
        "--folder",
        str(tmp_path),
        "--port",
        "8800",
        "--no-code",
    ]
    assert "shell=True" not in inspect.getsource(homerun)


def test_seed_home_no_code_keeps_the_code_out_of_the_output(seedfolder, monkeypatch, capsys):
    """`seed home --no-code` は招待コードを出さない。引数が無ければ今のまま出す。"""
    import uvicorn

    from seed.server import main as server_main

    monkeypatch.setattr(os, "environ", os.environ.copy())  # cmd_home が足す環境変数を、ほかのテストに残さない
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: None)
    monkeypatch.setattr(server_main, "create_app", lambda: None)
    args = ["home", "--folder", str(seedfolder), "--host", "127.0.0.1", "--port", str(homerun.PORT)]
    assert cli.main([*args, "--no-code"]) == 0
    code = cli.home_invite(seedfolder)[1]
    out = capsys.readouterr()
    assert code not in out.out + out.err
    assert f"http://127.0.0.1:{homerun.PORT}" in out.out
    assert cli.main(args) == 0
    assert code in capsys.readouterr().out


SCRIPT = """
import sys, time
print("  サーバーの URL: http://127.0.0.1:{port}", flush=True)
print("  招待コード: 123456", flush=True)
time.sleep(30)
"""


def test_child_reads_url_hides_digits_and_stops(tmp_path):
    """子の出力: URL を拾い、6 桁の数は覚える前に伏せる。口が開けば running。止めれば stopped。"""
    port = homerun.PORT
    proc = subprocess.Popen(
        [sys.executable, "-c", SCRIPT.format(port=port)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    child = homerun.HomeChild(proc, port)
    try:
        for _ in range(100):
            if len(child.lines) >= 2:
                break
            time.sleep(0.05)
        assert child.url == f"http://127.0.0.1:{port}"
        assert not any("123456" in x for x in child.lines + child._lines)
        assert any(homerun.HIDDEN in x for x in child.lines)
        assert child.state == "starting"  # 口がまだ開いていない
        with socket.socket() as srv:
            srv.bind(("127.0.0.1", port))
            srv.listen()
            assert child.state == "running"
    finally:
        child.stop()
    assert child.state == "stopped"


def test_real_seed_home_child_on_a_spare_port(seedfolder):
    """本物の seed home を、一時のフォルダーで、127.0.0.1 の空いた口に立てる（探す口 8801 は 0.0.0.0 の時だけ）。"""
    pytest.importorskip("uvicorn")
    settings_mod.load(seedfolder)
    child = homerun.HomeChild.start(seedfolder, homerun.PORT, host="127.0.0.1")
    try:
        for _ in range(200):
            if child.state != "starting":
                break
            time.sleep(0.05)
        assert child.state == "running"
        assert child.url == f"http://127.0.0.1:{homerun.PORT}"
        code = homerun.invite_code(seedfolder)
        assert not any(code in x for x in child.lines)
    finally:
        child.stop()
    assert child.state == "stopped"


def test_already_tells_home_from_other(monkeypatch):
    from seed import client

    port = homerun.PORT
    assert homerun.already(port) is None
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", port))
        srv.listen()
        assert homerun.already(port) == "other"
        monkeypatch.setattr(client, "is_home", lambda url: url == f"http://127.0.0.1:{port}")
        assert homerun.already(port) == "home"


# ---------------------------------------------------------------- 歯車の行: 立てる、止める


def test_start_and_stop_from_the_gear(app, started):
    assert app.t("pc_home") in form_texts(app)
    assert app.t("pc_home_none") in form_texts(app)
    press(app, "pc_home_start")
    assert started == [(app.project, homerun.PORT)]  # プロジェクトの根で、決まった口で
    child = app.pc["home"]
    got = form_texts(app)
    assert app.t("pc_home_running") in got and child.url in got
    assert app.t("pc_home_how") in got
    press(app, "pc_home_stop")
    assert child.stopped and app.pc["home"] is None
    assert app.t("pc_home_none") in form_texts(app)


def test_child_survives_a_field_switch(app, started, seedfolder):
    run(pc_rows.home_start(app))
    child = app.pc["home"]
    app.open_folder(str(seedfolder))  # 畑を開き直しても
    assert app.pc["home"] is child and not child.stopped


def test_no_second_server_when_one_is_running(app, started, monkeypatch):
    monkeypatch.setattr(homerun, "already", lambda port: "home")
    press(app, "pc_home_start")
    assert started == [] and app.pc["home"] is None
    got = form_texts(app)
    assert app.t("pc_home_already") in got
    assert app.t("pc_home_start") not in got  # 二つ目を立てるボタンは出さない


def test_port_used_by_something_else(app, started, monkeypatch):
    monkeypatch.setattr(homerun, "already", lambda port: "other")
    run(pc_rows.home_start(app))
    assert started == []
    assert app.t("pc_home_port_used", port=homerun.PORT) in form_texts(app)


def test_form_looks_for_a_terminal_server_once(app, started, monkeypatch):
    monkeypatch.setattr(homerun, "already", lambda port: "home")
    app.show_settings()
    (task,) = [t for t in app.page.tasks if t is pc_rows.probe]
    assert task is pc_rows.probe
    run(pc_rows.probe(app, lambda: None))
    assert app.pc["already"] == "home"


def test_invite_code_only_when_shown(app, started, seedfolder, caplog):
    """コードは「見せる」の間だけ部品に。app.pc、app.state、話すのやり取り、ログ、子の行には入らない。"""
    caplog.set_level(logging.DEBUG)
    run(pc_rows.home_start(app))
    code = cli.home_invite(app.project)[1]
    assert not any(code in x for x in form_texts(app))
    press(app, "pc_home_show")
    assert app.t("pc_home_code", code=code) in now_texts(app)
    assert app.pc["show"] is True and code not in repr(app.pc) and code not in repr(app.state)
    press(app, "pc_home_hide")
    assert not any(code in x for x in now_texts(app))
    press(app, "pc_home_show")
    assert any(code in x for x in now_texts(app))
    assert not any(code in x for x in form_texts(app))  # 開き直すと隠した形から
    assert code not in caplog.text
    assert not any(code in str(i.get("text", "")) for i in talk.talk_state(app))
    assert not any(code in x for x in app.pc["home"].lines)


def test_need_server_shows_the_parts_button(app, started, monkeypatch):
    monkeypatch.setattr(homerun, "has_server", lambda: False)
    monkeypatch.setattr(ready, "fix_for", lambda w: "parts:server" if w == "home_need_server" else None)
    got = form_texts(app)
    assert app.t("home_need_server") in got and app.t("fix_parts") in got
    assert app.t("pc_home_start") not in got


def test_start_when_the_app_opens_is_kept_in_seed_toml(app, started, seedfolder):
    box = next(c for c in form_controls(app) if isinstance(c, ft.Checkbox))
    assert box.label == app.t("pc_home_auto") and box.value is False
    box.value = True
    box.on_change(None)
    assert 'home_start = "auto"' in (seedfolder / "seed.toml").read_text(encoding="utf-8")
    assert settings_mod.load(seedfolder).home_start == "auto"
    app.settings = settings_mod.load(seedfolder)
    run(pc_rows.auto_start(app))
    assert started == [(app.project, homerun.PORT)]
    box = next(c for c in form_controls(app) if isinstance(c, ft.Checkbox))
    box.value = False
    box.on_change(None)
    assert "home_start" not in (seedfolder / "seed.toml").read_text(encoding="utf-8")


def test_auto_start_needs_the_pc_app(app, started):
    app.settings.home_start = "auto"
    app.page.web = True
    run(pc_rows.auto_start(app))
    assert started == []


def test_rows_only_on_the_pc_app_and_preview_runs_nothing(app, started, monkeypatch):
    app.page.web = True
    assert app.t("pc_home") not in form_texts(app)
    monkeypatch.setenv(ready.ENV_PC_PREVIEW, "home=running,update=behind,nonsense=1")
    assert ready.pc_preview() == {"home": "running", "update": "behind"}
    got = form_texts(app)
    assert pc_rows.PREVIEW_URL in got and app.t("pc_update_behind", n=1) in got
    press(app, "pc_home_stop")
    press(app, "pc_update_run")
    assert started == [] and app.pc["home"] is None
    assert app.pc["home_note"] == app.t("setup_preview") == app.pc["update_note"]


# ---------------------------------------------------------------- 新しくする（一時の git の repo で）


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return r.stdout.strip()


@pytest.fixture
def repos(tmp_path, monkeypatch):
    """origin（bare）、本人の写し mine、GitHub の側で直す up。"""
    cfg = tmp_path / "gitconfig"
    cfg.write_text("", encoding="utf-8")
    for k, v in {
        "GIT_CONFIG_GLOBAL": str(cfg),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }.items():
        monkeypatch.setenv(k, v)
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    up = tmp_path / "up"
    git(tmp_path, "clone", "-q", str(origin), str(up))
    (up / "pyproject.toml").write_text('[project]\nname = "seed-farm"\nversion = "0.0.9"\n', encoding="utf-8")
    (up / "a.txt").write_text("1\n", encoding="utf-8")
    git(up, "add", ".")
    git(up, "commit", "-q", "-m", "one")
    git(up, "push", "-q", "origin", "main")
    mine = tmp_path / "mine"
    git(tmp_path, "clone", "-q", str(origin), str(mine))
    pips: list = []

    def pip_command():
        pips.append(1)
        return [sys.executable, "-c", "pass"]

    monkeypatch.setattr(update, "pip_command", pip_command)
    return {"origin": origin, "up": up, "mine": mine, "pips": pips}


def push_new(up: Path) -> None:
    (up / "a.txt").write_text("2\n", encoding="utf-8")
    git(up, "commit", "-q", "-am", "two")
    git(up, "push", "-q", "origin", "main")


def test_version_and_head(repos):
    mine = repos["mine"]
    assert update.version(mine) == "0.0.9"
    assert update.head(mine) == git(mine, "rev-parse", "--short", "HEAD")
    assert update.version(None)  # seed.__version__


def test_same_then_behind_then_update(repos):
    mine = repos["mine"]
    assert update.check(mine).state == "same"
    push_new(repos["up"])
    got = update.check(mine)
    assert (got.state, got.behind, got.ahead) == ("behind", 1, 0)
    assert update.run_update(mine) == ("done", [])
    assert (mine / "a.txt").read_text(encoding="utf-8") == "2\n" and repos["pips"] == [1]
    assert update.check(mine).state == "same"


def test_local_edits_are_not_replaced(repos):
    mine = repos["mine"]
    push_new(repos["up"])
    (mine / "a.txt").write_text("my edit\n", encoding="utf-8")
    assert update.check(mine).state == "dirty"
    assert update.run_update(mine)[0] == "dirty"
    assert (mine / "a.txt").read_text(encoding="utf-8") == "my edit\n" and repos["pips"] == []
    (mine / "mine-only.txt").write_text("x\n", encoding="utf-8")  # 本人が足しただけのファイルは止めない
    git(mine, "checkout", "--", "a.txt")
    assert update.check(mine).state == "behind"


def test_local_commits_that_cannot_fast_forward(repos):
    mine = repos["mine"]
    (mine / "b.txt").write_text("mine\n", encoding="utf-8")
    git(mine, "add", "b.txt")
    git(mine, "commit", "-q", "-m", "local")
    assert update.check(mine).state == "same"  # 手元にだけ在っても、新しい版が無ければそのまま
    push_new(repos["up"])
    got = update.check(mine)
    assert (got.state, got.ahead, got.behind) == ("diverged", 1, 1)
    before = git(mine, "rev-parse", "HEAD")
    assert update.run_update(mine)[0] == "diverged"
    assert git(mine, "rev-parse", "HEAD") == before and repos["pips"] == []


def test_zip_copy_and_unreachable_origin(repos, tmp_path):
    zipped = tmp_path / "seed-main"
    zipped.mkdir()
    assert update.check(zipped).state == "zip"
    assert update.head(zipped) is None
    git(repos["mine"], "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    assert update.check(repos["mine"]).state == "failed"


def test_update_runs_only_the_fixed_commands(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    calls: list = []

    class Done:
        returncode, stderr = 0, ""

        def __init__(self, out=""):
            self.stdout = out

    def run_(cmd, **kw):
        calls.append(tuple(cmd))
        assert kw["cwd"] == tmp_path and "shell" not in kw
        return Done("0\t2\n" if "--count" in cmd else "")

    monkeypatch.setattr(update.subprocess, "run", run_)
    assert update.run_update(tmp_path)[0] == "done"
    pip = (sys.executable, "-m", "pip", "install", "-e", ".[app,server]")
    assert set(calls) <= {update.GIT_FETCH, update.GIT_COUNT, update.GIT_STATUS, update.GIT_PULL, pip}
    assert calls[-2:] == [update.GIT_PULL, pip]
    assert "shell=True" not in inspect.getsource(update)


def test_update_rows_in_the_gear(app, repos, monkeypatch):
    mine = repos["mine"]
    monkeypatch.setattr(ready, "repo_root", lambda: mine)
    got = form_texts(app)
    assert app.t("pc_update") in got
    assert any(x.startswith(app.t("pc_update_version", version="0.0.9 (")) for x in got)
    press(app, "pc_update_check")
    assert app.t("pc_update_same") in form_texts(app)
    push_new(repos["up"])
    press(app, "pc_update_check")
    assert app.t("pc_update_behind", n=1) in form_texts(app)
    press(app, "pc_update_run")
    assert app.t("pc_update_done") in form_texts(app)
    assert (mine / "a.txt").read_text(encoding="utf-8") == "2\n"


def test_update_rows_keep_edits_and_point_zip_to_github(app, repos, monkeypatch, tmp_path):
    mine = repos["mine"]
    monkeypatch.setattr(ready, "repo_root", lambda: mine)
    push_new(repos["up"])
    (mine / "a.txt").write_text("my edit\n", encoding="utf-8")
    press(app, "pc_update_check")
    got = form_texts(app)
    assert app.t("pc_update_dirty") in got and app.t("pc_update_run") not in got
    zipped = tmp_path / "seed-main"
    zipped.mkdir()
    monkeypatch.setattr(ready, "repo_root", lambda: zipped)
    app.pc["version"] = None
    assert app.t("pc_update_zip") in form_texts(app)
    assert button(app, "pc_update_github").url == update.GITHUB
