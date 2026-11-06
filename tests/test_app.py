# SPDX-License-Identifier: AGPL-3.0-or-later
"""画面の組み立ての確認。Flet の page は偽物で、view() が返す物の文を見る（押す操作は見ない）。"""

from __future__ import annotations

import flet as ft
import pytest

from seed import cli
from seed.app import entry, find, observe, plan, publish, records
from seed.app.main import SCREENS, App
from seed.records import Observation, Plan


class FakePage:
    route = "/"

    def __init__(self) -> None:
        self.views: list = []
        self.updated = 0

    def update(self) -> None:
        self.updated += 1

    async def push_route(self, route: str) -> None:
        self.route = route

    def show_dialog(self, d) -> None:
        pass

    def run_task(self, fn, *args) -> None:  # 索引の読み込みなど。テストでは走らせない
        self.tasks = [*getattr(self, "tasks", []), fn]


def texts(control) -> list[str]:
    """部品の木から、見える文を全部集める。"""
    out: list[str] = []
    stack = [control]
    while stack:
        c = stack.pop()
        if isinstance(c, ft.TextField) and c.value:
            out.append(str(c.value))
        if isinstance(c, ft.Text):
            if c.value:
                out.append(str(c.value))
            for sp in c.spans or []:
                if getattr(sp, "text", None):
                    out.append(str(sp.text))
        for name in ("label", "hint_text", "title", "subtitle", "text"):
            v = getattr(c, name, None)
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, ft.Text) and v.value:
                out.append(str(v.value))
        for name in ("controls", "segments", "destinations", "options", "actions"):
            kids = getattr(c, name, None)
            if kids:
                stack.extend(kids)
        for name in ("content", "appbar", "navigation_bar", "leading"):
            kid = getattr(c, name, None)
            if isinstance(kid, str):
                out.append(kid)  # 釦の文
            elif kid is not None:
                stack.append(kid)
    return out


@pytest.fixture
def app(seedfolder):
    a = App(FakePage(), str(seedfolder))
    a.lang = "ja"
    return a


def test_screens_build_without_records(app):
    for sc in SCREENS:
        v = sc.build(app)
        assert isinstance(v, ft.View) and v.route == sc.route
        words = texts(v)
        assert any("seed — " in w for w in words), sc.route
    assert "計画" in " ".join(texts(plan.view(app))) and "計画はまだありません。" in texts(plan.view(app))
    assert "畑を観察する" in texts(observe.view(app))
    assert any("知りたいこと" in w for w in texts(observe.view(app)))
    assert "テスター募集中（11-08 まで）。畑の写真を一枚読ませて、合う／違うを付けてみてください。" in texts(
        entry.view(app)
    )
    assert "観察はまだありません。" in texts(records.view(app)) or any(
        "観察" in w for w in texts(records.view(app))
    )


def test_observe_and_records_show_observation(app, seedfolder, photo):
    assert (
        cli.main(
            [
                "observe",
                "--folder",
                str(seedfolder),
                "--claude-code",
                "--ask",
                "grow",
                str(photo),
                "--say",
                "did: 見ただけ",
            ]
        )
        == 0
    )
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    obs = Observation.read(path)
    from seed.records import Line

    obs.reading = [Line("overall", "草が大半", 0.8)]
    obs.model = "claude-code"
    obs.write(path)
    app.state["obs"] = obs
    words = texts(observe.view(app))
    assert any("この土地で何が育つか" in w for w in words) and any("草が大半" in w for w in words)
    assert "合う" in words and "違う" in words and any("見ただけ" in w for w in words)
    words = texts(records.view(app))
    assert any("2026-11-05 14:21:07" in w for w in words)
    app.state["rec_open"] = "2026-11-05-142107"
    assert any("草が大半" in w for w in texts(records.view(app)))


def test_plan_screen_shows_plan_lines(app, seedfolder):
    from seed.records import Line

    p = Plan.new("ja", "2026-27 冬", "2026-11-03")
    p.reread([Line("sow", "北側に小麦", 0.7)], "claude-code")
    p.say("decided", "南側は草のまま")
    p.write(seedfolder / "plan.md")
    words = texts(plan.view(app))
    assert any("北側に小麦" in w for w in words) and any("南側は草のまま" in w for w in words)
    assert "2026-27 冬" in words and any("書き始め 2026-11-03" in w for w in words)
    assert "決めたこと" in words


def test_publish_and_find_build(app, seedfolder, photo):
    assert cli.main(["observe", "--folder", str(seedfolder), "--claude-code", str(photo)]) == 0
    assert any("公開" in w for w in texts(publish.view(app)))
    app.index = {"records": []}
    assert any("探す" in w or "繋が" in w for w in texts(find.view(app)))


# ---------------------------------------------------------------- Web 版（設計書 §6.2）


def test_web_user_folder_and_login_view(tmp_path, monkeypatch, seedfolder):
    from seed.app import main as M

    inv = tmp_path / "invites.toml"
    inv.write_text('[codes]\n"inv-web-1" = "てすと"\n', encoding="utf-8")
    monkeypatch.setenv(M.ENV_INVITES, str(inv))
    monkeypatch.setenv(M.ENV_USERS_DIR, str(tmp_path / "users"))
    monkeypatch.setenv(M.ENV_UPLOAD_DIR, str(tmp_path / "uploads"))
    assert M.web_user_for("nope") is None and M.web_user_for("") is None
    user = M.web_user_for("inv-web-1")
    assert user is not None and user.name == "てすと" and len(user.slug) == 16 and "inv" not in user.slug
    folder = M.user_folder(user)
    assert folder.parent == tmp_path / "users"

    page = FakePage()
    page.web = True
    app = M.App(page, str(folder), web_user=user)
    assert app.web and app.settings.invite == "inv-web-1" and app.settings.name == "てすと"
    # 招待コードは箱の中の credentials.toml（600）に。seed.toml には書かない（設計書 §5.1）
    assert "inv-web-1" not in (folder / "seed.toml").read_text(encoding="utf-8")
    cred = folder / "credentials.toml"
    assert 'invite = "inv-web-1"' in cred.read_text(encoding="utf-8")
    assert cred.stat().st_mode & 0o777 == 0o600
    words = texts(entry.view(app))
    assert any("ログイン中: てすと" in w for w in words) and "このブラウザから出る" in words
    # 持ち帰りと消去の釦（設計書 §5.3）。入口の文は「準備中」と言わない
    assert "持ち帰る（zip）" in words and "全部消す" in words
    assert not any("準備中" in w for w in words)
    assert not any("招待コードを入れる" in w for w in words)
    words = texts(observe.view(app))
    assert "手元の Claude で読む" not in words and "自分の Claude で読む" not in words  # Web 版はサーバーだけ

    async def noop(code):
        return None

    v = M.login_view(page, "ja", noop)
    assert v.route == "/login" and "招待コード" in texts(v) and "入る" in texts(v)
    assert "その招待コードは一覧にありません。" in texts(M.login_view(page, "ja", noop, bad=True))


def test_pc_entry_shows_invite_field(app):
    words = texts(entry.view(app))
    assert "招待コード" in words and "入れる" in words
    assert not app.web
    assert "持ち帰る（zip）" not in words and "全部消す" not in words  # PC 版の記録は手元にある


def _walk(control):
    stack = [control]
    while stack:
        c = stack.pop()
        yield c
        for name in ("controls", "actions"):
            stack.extend(getattr(c, name, None) or [])
        for name in ("content",):
            kid = getattr(c, name, None)
            if kid is not None and not isinstance(kid, str):
                stack.append(kid)


def test_web_delete_asks_once_before_deleting(tmp_path, monkeypatch, seedfolder):
    import asyncio

    from seed.app import main as M

    inv = tmp_path / "invites.toml"
    inv.write_text('[codes]\n"inv-web-2" = "てすと"\n', encoding="utf-8")
    monkeypatch.setenv(M.ENV_INVITES, str(inv))
    monkeypatch.setenv(M.ENV_USERS_DIR, str(tmp_path / "users"))
    user = M.web_user_for("inv-web-2")
    page = FakePage()
    page.web = True
    shown, popped, calls = [], [], []
    page.show_dialog = shown.append
    page.pop_dialog = lambda: popped.append(1)
    app = M.App(page, str(M.user_folder(user)), web_user=user)

    async def call(method, *args):
        calls.append(method)
        return {"deleted": True, "withdrawn": []}

    async def launch_url(url):
        calls.append(("launch", url))

    class Prefs:
        async def remove(self, key):
            calls.append(("forget", key))

    app.call = call
    page.launch_url = launch_url
    page.shared_preferences = Prefs()
    v = entry.view(app)
    delete = next(c for c in _walk(v) if isinstance(c, ft.TextButton) and c.content == "全部消す")
    delete.on_click(None)
    assert calls == [] and len(shown) == 1  # まず確かめるだけ
    dialog = shown[0]
    assert isinstance(dialog, ft.AlertDialog) and "元には戻せません" in dialog.content.value
    cancel, yes = dialog.actions
    cancel.on_click(None)
    assert calls == [] and popped == [1]
    asyncio.run(yes.on_click(None))
    assert calls[0] == "delete_me" and ("launch", "/") in calls


def test_field_picker_only_with_two_fields(app, seedfolder, tmp_path):
    from seed import fields as fields_mod

    assert app.field_picker() is None  # 一覧が無い
    fl = fields_mod.Fields()
    fl.add("自分の畑", str(seedfolder))
    fields_mod.save_fields(fl)
    assert app.field_picker() is None  # 一つだけ
    fl.add("知人の田", str(tmp_path / "other"))
    fields_mod.save_fields(fl)
    picker = app.field_picker()
    assert picker is not None and picker.value == "自分の畑"
    assert [o.key for o in picker.options] == ["自分の畑", "知人の田"]
    assert len(records.view(app).appbar.actions) == 1
