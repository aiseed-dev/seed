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


def test_publish_screen_is_guidance_and_list_on_every_version(app, seedfolder, monkeypatch):
    """公開は Claude を使って行う。どの版でも画面は在り、作る部分は無く、案内と公開した記録の一覧が在る。"""
    import flet as ft

    from seed.records import Line, Public

    pub = Public(
        id="my-field", place="徳島県", since="2026-11-05", name="見本", word="見本の一言", language="ja"
    )
    pub.days["2026-11-05"] = [Line("overall", "草が大半", 0.8)]
    (seedfolder / "public").mkdir(exist_ok=True)
    pub.write(seedfolder / "public" / "my-field.md")
    guide = app.t("publish_by_claude")
    assert guide.startswith("公開は、Claude を使って行います。PC で") and "できません" not in guide
    for web, platform in (
        (False, None),
        (True, None),
        (False, ft.PagePlatform.IOS),
        (False, ft.PagePlatform.ANDROID),
    ):
        app.page.web, app.page.platform = web, platform
        assert "/publish" in [sc.route for sc in app.screens()]
        app.route_change(path="/publish")
        view = app.page.views[-1]
        seen = texts(view)
        assert view.route == "/publish" and guide in seen
        assert "my-field · 2026-11-05" in seen

        # 作る部分（観察を選ぶ、行のチェック、粗さ、欄、送るボタン）は無い
        def walk(c):
            yield c
            for name in ("controls", "content", "title", "subtitle", "trailing"):
                v = getattr(c, name, None)
                for x in v if isinstance(v, list) else [v] if v is not None else []:
                    if isinstance(x, ft.Control):
                        yield from walk(x)

        everything = list(walk(view))
        assert any(isinstance(c, ft.TextButton) and c.content == "取り下げる" for c in everything)
        kinds = {type(c) for c in everything}
        assert not kinds & {ft.Checkbox, ft.TextField, ft.Dropdown, ft.Chip, ft.FilledButton}


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


# ---- 管理の画面（動かす人）


def _admin_app(tmp_path, monkeypatch, scopes=("admin",)):
    monkeypatch.setenv("SEED_CREDENTIALS", str(tmp_path / "cred.toml"))
    app = App(FakePage(), str(tmp_path / "seed"))
    app.scopes = set(scopes)
    return app


OVERVIEW = {
    "version": "0.0.1",
    "records": 2,
    "connections": 3,
    "boxes": 1,
    "tokens": {"live": 2, "expired": 1, "revoked": 0},
    "invites": 4,
    "read": False,
    "audit": "off",
    "remaining": {"reads": 0, "usd": 20.0},
}


def test_admin_tab_only_for_the_operator(tmp_path, monkeypatch):
    app = _admin_app(tmp_path, monkeypatch, scopes=("member",))
    assert "/admin" not in [sc.route for sc in app.screens()]
    app.route_change(path="/admin")  # 入れない人が道を打っても、入口に戻る
    assert "管理" not in texts(app.page.views[-1])
    app.scopes = {"admin"}
    assert [sc.route for sc in app.screens()][-1] == "/admin"


def test_admin_says_what_to_do(tmp_path, monkeypatch):
    from seed.app import admin

    app = _admin_app(tmp_path, monkeypatch)
    warns = admin.attention(app, OVERVIEW, {"verified": False})
    assert len(warns) == 5
    said = dict(warns)
    # 何が起きているか → サーバーで打つコマンド（文とコマンドは分かれている。コマンドは一行に一つ）
    assert said["写真を読み取れません。Claude の鍵が入っていません。サーバーで次を打ちます。"] == [
        "sudoedit /etc/seed/env   # ANTHROPIC_API_KEY= の後に鍵を入れる",
        "sudo systemctl restart seed",
    ]
    (audit_off,) = [w for w in warns if w[0].startswith("操作の記録を書いていません。")]
    assert "鍵がもう在る時は作り直しません" in audit_off[0]
    assert audit_off[1] == [
        "sudo test -e /etc/seed/log-key || sudo sh -c 'umask 077; head -c 32 /dev/urandom > /etc/seed/log-key'",
        "sudo systemctl restart seed",
    ]
    (tampered,) = [w for w in warns if w[0].startswith("操作の記録が書き換えられています。")]
    assert "『受け付けを止める』" in tampered[0]
    assert tampered[1] == ["last -n 20", "sudo journalctl -u ssh --since -2d"]
    assert any("出し直します" in w and not cmds for w, cmds in warns)
    err = admin.attention(app, {**OVERVIEW, "audit": "error"})
    assert ["df -h /var/lib/seed", "ls -ld /var/lib/seed/audit"] in [c for _, c in err]
    good = {**OVERVIEW, "read": True, "audit": "on", "tokens": {"live": 2, "expired": 0, "revoked": 0}}
    good["remaining"] = {"reads": 180}
    good["denied_today"] = admin.DENIED_MANY - 1
    good["keys"] = {"claude": True, "plantnet": False}
    assert admin.attention(app, good, {"verified": True}) == []
    rows = dict(admin.state_rows(app, good))
    assert (
        rows["写真の読み取り（Claude）"] == "できます"
        and rows["操作の記録"] == "書いています"
        and rows["今日の残り"] == "読み取り 180 回"
        and rows["受け付け"] == "受け付けています"
        and rows["外の鍵"] == "Claude 在る、Pl@ntNet 無い"
        and rows["公開"] == "記録 2 件、寄せられた一言 3 件"
        and rows["入れる人"] == "token 2 人、招待コード 4 人、Web 版で記録を置いている人 1 人"
    )
    # 止めている、断った要求が多い、もうすぐ切れる token
    busy = {**good, "paused": True, "denied_today": admin.DENIED_MANY}
    busy["tokens"] = {**good["tokens"], "expiring": 3}
    warns = admin.attention(app, busy, {"verified": True})
    assert [w for w, _ in warns] == [
        "受け付けを止めています。戻すには下の『受け付けを再開する』を押します。",
        (
            f"今日、断った要求が {admin.DENIED_MANY} 回あります。誰かが試しているかもしれません。"
            "下の『誰が何をしたか』で相手を見ます。続くなら『受け付けを止める』を押します。"
        ),
        "あと 14 日以内に切れる token が 3 件あります。要る人には、切れる前に出し直します。",
    ]
    assert all(cmds == [] for _, cmds in warns)
    assert dict(admin.state_rows(app, busy))["受け付け"] == "止めています"
    # en も同じ形
    app.lang = "en"
    assert dict(admin.state_rows(app, busy))["Requests"] == "Paused"
    assert len(admin.attention(app, OVERVIEW, {"verified": False})) == 5
    app.lang = "ja"
    tokens = [
        {
            "name": "b",
            "scope": ["buyer"],
            "state": "revoked",
            "created": "2026-11-01",
            "expires": "2026-12-01",
        },
        {
            "name": "a",
            "scope": ["admin"],
            "state": "live",
            "created": "2026-11-06",
            "expires": "2027-02-04",
            "note": "n",
        },
    ]
    tr = admin.token_rows(app, tokens)
    assert [(r["name"], r["live"]) for r in tr] == [("a", True), ("b", False)]
    assert tr[0]["scope"] == "動かす人（この画面）" and tr[1]["state"] == "取り消し済み"
    lines = [
        {"ts": "2026-11-06T16:55:01+09:00", "actor": "?", "action": "publish", "detail": "断った: scope"},
        {
            "ts": "2026-11-06T16:54:00+09:00",
            "actor": "にじ",
            "action": "admin.token.add",
            "detail": "買い手 buyer",
        },
    ]
    assert admin.audit_rows(app, lines) == [
        ["2026-11-06 16:55", "知らない人", "公開した", "断った: scope"],
        ["2026-11-06 16:54", "にじ", "管理: token を出した", "買い手 buyer"],
    ]
    more = [
        {"ts": "2026-11-06T17:00:00+09:00", "actor": "にじ", "action": a, "detail": d}
        for a, d in (
            ("admin.pause", "通した"),
            ("admin.resume", "通した"),
            ("admin.token_revoke_all", "3 件"),
        )
    ]
    assert [r[2] for r in admin.audit_rows(app, more)] == [
        "管理: 受け付けを止めた",
        "管理: 受け付けを再開した",
        "管理: token を全部取り消した",
    ]


def test_admin_view_builds_from_loaded_state(tmp_path, monkeypatch):
    app = _admin_app(tmp_path, monkeypatch)
    app.state["admin"] = {
        "loaded": True,
        "overview": OVERVIEW,
        "tokens": [
            {
                "name": "買い手 A",
                "scope": ["buyer"],
                "state": "live",
                "created": "2026-11-06",
                "expires": "2026-12-06",
            }
        ],
        "audit": {"state": "off", "verified": None, "lines": []},
        "records": [{"id": "2026-11-06-x-1", "name": "にじ", "place": "徳島県", "since": "2026-11-06"}],
        "new_token": {"name": "買い手 A", "code": "not-a-real-token-000"},
    }
    app.route_change(path="/admin")
    seen = " ".join(texts(app.page.views[-1]))
    for word in (
        "今の状態",
        "気を付ける事",
        "人に渡す、入る鍵（token）",
        "渡す相手の名前",
        "受け付けを止める",
        "token を全部取り消す",
        "sudo systemctl restart seed",
        "公開された記録",
        "誰が何をしたか",
        "買い手 A",
        "取り消す",
        "取り下げる",
        "出るのはこの一度だけ",
        "not-a-real-token-000",
    ):
        assert word in seen, word
    # 止めている間は、同じ所のボタンが「再開する」になる。全部取り消すは二度押し
    app.state["admin"].update(overview={**OVERVIEW, "paused": True}, confirm=("revoke_all", ""))
    app.route_change(path="/admin")
    seen = " ".join(texts(app.page.views[-1]))
    assert "受け付けを再開する" in seen and "受け付けを止める" not in seen
    assert "本当に全部取り消す（自分の分は残す）" in seen
    # まだ読んでいなければ、尋ねている事だけを出す
    app.state["admin"] = {}
    app.route_change(path="/admin")
    assert "サーバーに尋ねています…" in texts(app.page.views[-1])


def test_admin_record_rows(tmp_path, monkeypatch):
    from seed.app import admin

    app = _admin_app(tmp_path, monkeypatch)
    recs = [
        {
            "id": "2026-11-06-x-1",
            "name": "にじ",
            "place": "徳島県",
            "since": "2026-11-06",
            "owner": "仲間",
            "published": "2026-11-06",
            "connections": 2,
            "url": "https://seed.example/p/2026-11-06-x-1",
        },
        {
            "id": "2026-11-05-y-1",
            "name": "y",
            "owner": "",
            "published": "2026-11-05",
            "connections": 0,
            "url": "",
        },
    ]
    rows = admin.record_rows(app, recs)
    assert rows[0] == {
        "id": "2026-11-06-x-1",
        "head": "にじ · 徳島県 · 2026-11-06",
        "meta": "公開した人 仲間　公開した日 2026-11-06　寄せられた一言 2 件",
        "url": "https://seed.example/p/2026-11-06-x-1",
    }
    assert rows[1]["meta"].startswith("公開した人 分からない人")
    conns = [
        {"name": "2026-11-06-n-0123abcd", "date": "2026-11-06", "from": "買い手", "word": "分けてほしい"}
    ]
    assert admin.connection_rows(conns) == [
        {"name": "2026-11-06-n-0123abcd", "head": "2026-11-06　買い手", "word": "分けてほしい"}
    ]
    # 画面: 開いた記録の下に一言と「消す」。二度押しで「本当に消す」
    app.state["admin"] = {
        "loaded": True,
        "overview": OVERVIEW,
        "tokens": [],
        "audit": {"lines": []},
        "records": recs,
        "conns": {"2026-11-06-x-1": conns},
        "confirm": ("connection", "2026-11-06-x-1/2026-11-06-n-0123abcd"),
    }
    app.route_change(path="/admin")
    seen = " ".join(texts(app.page.views[-1]))
    for word in (
        "公開の頁を開く",
        "寄せられた一言を閉じる",
        "寄せられた一言を見る",
        "分けてほしい",
        "本当に消す",
        "公開した人 仲間",
    ):
        assert word in seen, word
