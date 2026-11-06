# SPDX-License-Identifier: AGPL-3.0-or-later
"""アプリの入口。`flet run src/seed/app/main.py` か `seed app` で開く。

PC 版（設計書 §6）は本人のフォルダー（既定 ~/seed）を読む。
Web 版（§6.2。`seed app --web --serve`、deb2 で動かす）は、招待コードでログインし、人ごとのフォルダー
SEED_USERS_DIR/<コードのハッシュ>/ を本人のフォルダーにする。写真はブラウザから上げる（upload_dir）。
画面は六つで、道（route）で切り替える。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import flet as ft

from seed import fields as fields_mod
from seed import lang
from seed import settings as settings_mod
from seed.app import entry, find, observe, plan, publish, records, theme
from seed.app.strings import s
from seed.cli import prepare
from seed.client import Client

log = logging.getLogger("seed.app")

MAX_PHOTOS = 6
ENV_USERS_DIR = "SEED_USERS_DIR"  # Web 版: 人ごとのフォルダーの親
ENV_UPLOAD_DIR = "SEED_UPLOAD_DIR"  # Web 版: ブラウザから上げた写真の一時置き場
ENV_INVITES = "SEED_INVITES"  # 招待コードの一覧（サーバーと同じファイル）
PREF_INVITE = "seed.invite"  # ブラウザに覚えさせる鍵
UPLOAD_WAIT_S = 180
PHOTO_EXTENSIONS = [
    "jpg",
    "jpeg",
    "png",
    "heic",
    "heif",
    "JPG",
    "JPEG",
    "PNG",
    "HEIC",
    "HEIF",
]  # HEIC は拒む理由を言うため


@dataclass
class Screen:
    route: str
    word: str
    icon: ft.IconData
    build: Callable[[App], ft.View]


SCREENS = [
    Screen("/", "nav_entry", ft.Icons.HOME_OUTLINED, entry.view),
    Screen("/observe", "nav_observe", ft.Icons.PHOTO_CAMERA_OUTLINED, observe.view),
    Screen("/records", "nav_records", ft.Icons.LIST_ALT, records.view),
    Screen("/plan", "nav_plan", ft.Icons.YARD_OUTLINED, plan.view),
    Screen("/publish", "nav_publish", ft.Icons.PUBLIC, publish.view),
    Screen("/find", "nav_find", ft.Icons.SEARCH, find.view),
]


class App:
    """一つの窓の状態。"""

    def __init__(self, page: ft.Page, folder: str | None = None, web_user: WebUser | None = None) -> None:
        self.page = page
        self.web_user = web_user  # Web 版でログインした人。None なら PC 版
        if web_user is None:
            folder = fields_mod.chosen(None, folder)  # PC 版は畑の一覧の current も見る（記録の形 §19）
        self.index: dict | None = None
        self.picker = ft.FilePicker()  # 参照を持っておく（無いと外される）
        self._uploads: list[Path] = []  # Web 版で上げた写真の一時フォルダー（取り込んだら消す）
        self.open_folder(folder)

    def open_folder(self, folder: str | None) -> None:
        """記録のフォルダーを開く（設定を読み、手引きを写す）。畑を切り替えた時も呼ぶ。"""
        web_user = self.web_user
        # Web 版の秘密（token、招待コード）は人ごとの箱の中の credentials.toml（設計書 §5.1）
        creds = (
            Path(folder) / settings_mod.CREDENTIALS_FILENAME if (web_user is not None and folder) else None
        )
        self.settings = settings_mod.load(folder, credentials=creds)
        if web_user is not None and (
            self.settings.invite != web_user.code or self.settings.name != web_user.name
        ):
            self.settings.invite, self.settings.name = web_user.code, web_user.name
            self.settings.save()
        self.folder = self.settings.records
        prepare(self.folder)  # 手引きの写しも（もうあれば触らない）
        self.lang = self.settings.language
        self.state: dict = {}  # 画面をまたいで残す物（今の観察、開いている記録など）。畑が替われば空に

    # --- 畑（記録の形 §19。PC 版だけ）
    def field_picker(self) -> ft.Control | None:
        """見出しの右の畑の選択。Web 版か、一覧が一つ以下なら出さない。"""
        if self.web:
            return None
        fl = fields_mod.load_fields()
        if len(fl.fields) < 2:
            return None
        return ft.Dropdown(
            options=[ft.DropdownOption(key=n, text=n) for n in fl.names],
            value=fields_mod.selected_name(fl, self.folder.root),
            label=self.t("field_choose"),
            dense=True,
            width=200,
            on_select=self._field_selected,
        )

    async def _field_selected(self, e) -> None:
        name = e.control.value
        if name:
            await self.switch_field(name)

    async def switch_field(self, name: str) -> None:
        """畑を切り替える: current を書き、設定とフォルダーを読み直して、今の画面を描き直す。"""
        folder = fields_mod.switch_field(name)
        self.open_folder(str(folder))
        await self.go(urlparse(self.page.route or "/").path or "/")

    @property
    def web(self) -> bool:
        """Web 版（ブラウザ）か。読みはサーバーだけ、写真はブラウザから上げる。"""
        return self.web_user is not None

    # --- 文と道
    def t(self, word: str, **kw) -> str:
        return s(word, self.lang, **kw)

    @property
    def folder_label(self) -> str:
        home = Path.home()
        root = self.folder.root
        return f"~/{root.relative_to(home).as_posix()}" if root.is_relative_to(home) else str(root)

    def view(self, route: str, controls: list[ft.Control]) -> ft.View:
        idx = next(i for i, sc in enumerate(SCREENS) if sc.route == route)
        return ft.View(
            route=route,
            appbar=ft.AppBar(
                title=ft.Text(f"seed — {self.t(SCREENS[idx].word)}"),
                actions=[c for c in [self.field_picker()] if c is not None],
            ),
            controls=[self._column(controls)],
            navigation_bar=ft.NavigationBar(
                destinations=[
                    ft.NavigationBarDestination(icon=sc.icon, label=self.t(sc.word)) for sc in SCREENS
                ],
                selected_index=idx,
                on_change=self._nav,
            ),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            padding=0,
        )

    def _column(self, controls: list[ft.Control]) -> ft.Container:
        """本文の列。窓の幅が変わったら、画面を作り直さずに幅だけを直す（撮っている間も部品を外さない）。"""
        self._body = theme.page_column(controls, getattr(self.page, "width", None))
        self.page.on_resize = self._fit
        return self._body

    def _fit(self, e=None) -> None:
        body = getattr(self, "_body", None)
        if body is not None:
            body.width = theme.fit_width(getattr(self.page, "width", None))
            self.page.update()

    def route_change(self, e=None, path: str | None = None) -> None:
        path = path or urlparse(self.page.route or "/").path or "/"
        sc = next((sc for sc in SCREENS if sc.route == path), SCREENS[0])
        try:
            view = sc.build(self)
        except Exception:
            log.exception("画面を作れない: %s", path)
            raise
        self.page.views.clear()
        self.page.views.append(view)
        self.page.update()
        log.debug("route: %s → %s", path, sc.route)

    def refresh(self) -> None:
        self.route_change()

    async def go(self, route: str) -> None:
        if urlparse(self.page.route or "/").path != route:
            await self.page.push_route(route)
        # ブラウザ（Web 版）では push_route の後の on_route_change が来ないことがあるので、ここでも作る
        self.route_change(path=route)

    async def _nav(self, e) -> None:
        await self.go(SCREENS[e.control.selected_index].route)

    def toast(self, text: str) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(text)))

    # --- サーバー
    def client(self) -> Client:
        return Client(self.settings.server, self.settings.token, self.lang, invite=self.settings.invite)

    async def call(self, method: str, *args):
        """Client のメソッドを別の糸で呼ぶ（画面を止めない）。"""

        def work():
            with self.client() as c:
                return getattr(c, method)(*args)

        return await asyncio.to_thread(work)

    async def load_index(self, force: bool = False) -> dict:
        if self.index is None or force:
            self.index = await self.call("index")
        return self.index

    # --- 写真を選ぶ
    async def pick_photos(self) -> list[Path]:
        """写真を選び、その道を返す。道が無い（ブラウザで開いた）物は使えない。"""
        files = await self.picker.pick_files(
            dialog_title=self.t("choose_photos"),
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=PHOTO_EXTENSIONS,
        )
        if not files:
            return []
        if len(files) > MAX_PHOTOS:
            files = files[:MAX_PHOTOS]
            self.toast(self.t("too_many_photos"))
        if self.web:
            return await self._upload(files)
        paths = [Path(f.path) for f in files if f.path]
        if not paths:
            self.toast(self.t("pc_only"))
        return paths

    async def _upload(self, files) -> list[Path]:
        """Web 版: 選んだ写真をブラウザから上げ、一時フォルダーの道を返す（設計書 §6.2）。"""
        upload_dir = upload_root()
        if upload_dir is None or self.web_user is None:
            self.toast(self.t("upload_unavailable"))
            return []
        batch = f"{self.web_user.slug}/{uuid.uuid4().hex}"
        done: dict[str, str | None] = {}
        event = asyncio.Event()

        def on_upload(e: ft.FilePickerUploadEvent) -> None:
            if e.error:
                done[e.file_name] = e.error
            elif (e.progress or 0) >= 1.0:
                done[e.file_name] = None
            if len(done) >= len(files):
                event.set()

        self.picker.on_upload = on_upload
        await self.picker.upload(
            [
                ft.FilePickerUploadFile(
                    upload_url=self.page.get_upload_url(f"{batch}/{f.name}", 600), id=f.id, name=f.name
                )
                for f in files
            ]
        )
        try:
            await asyncio.wait_for(event.wait(), UPLOAD_WAIT_S)
        except TimeoutError:
            self.toast(self.t("upload_failed", detail="timeout"))
            return []
        errors = [f"{k}: {v}" for k, v in done.items() if v]
        if errors:
            self.toast(self.t("upload_failed", detail="; ".join(errors)[:200]))
        folder = upload_dir / batch
        self._uploads.append(folder)
        return [folder / f.name for f in files if (folder / f.name).is_file()]

    def cleanup_uploads(self) -> None:
        """取り込みが終わった一時フォルダーを消す（写真の本体は本人のフォルダーに写っている）。"""
        for d in self._uploads:
            shutil.rmtree(d, ignore_errors=True)
        self._uploads = []


@dataclass(frozen=True)
class WebUser:
    """Web 版でログインした人。code は招待コード、name はその呼び名、slug はフォルダー名（コードから作る）。"""

    code: str
    name: str

    @property
    def slug(self) -> str:
        from seed.server.settings import user_slug

        return user_slug(self.code)


def users_root() -> Path | None:
    v = os.environ.get(ENV_USERS_DIR, "").strip()
    return Path(v).expanduser() if v else None


def upload_root() -> Path | None:
    v = os.environ.get(ENV_UPLOAD_DIR, "").strip()
    return Path(v).expanduser() if v else None


def invites() -> dict[str, str]:
    """招待コードの一覧（サーバーと同じファイル。SEED_INVITES）。"""
    from seed.server.settings import load_invites

    return load_invites(os.environ.get(ENV_INVITES))


def web_user_for(code: str | None) -> WebUser | None:
    code = (code or "").strip()
    name = invites().get(code) if code else None
    if not name and code:
        # 相手ごとの token の台帳（SEED_TOKENS）。Web 版に入れるのは member だけ（買い手の token では入れない）
        from seed.server import gate

        path = os.environ.get(gate.ENV_TOKENS, "").strip()
        if path:
            entry, _ = gate.TokenBook(Path(path).expanduser()).find(code)
            if entry is not None and "member" in entry["scope"]:
                name = str(entry["name"])
    return WebUser(code, name) if name else None


def user_folder(user: WebUser) -> Path:
    root = users_root()
    assert root is not None
    return root / user.slug


def login_view(page: ft.Page, language: str, on_login, bad: bool = False) -> ft.View:
    """Web 版のログイン。招待コードを入れる（設計書 §6.2、§7.5）。"""
    t = lambda w, **kw: s(w, language, **kw)
    # password にしない: ブラウザが「フォームの送信」と取って頁を読み直すことがある（11-03 に確認）
    code = ft.TextField(label=t("invite"), autofocus=True, autocorrect=False)

    async def submit(e=None) -> None:
        await on_login(code.value or "")

    code.on_submit = submit
    controls: list[ft.Control] = [
        theme.heading(t("login_title")),
        theme.body(t("tagline")),
        theme.muted(t("login_hint")),
        code,
        ft.FilledButton(t("login_button"), icon=ft.Icons.LOGIN, on_click=submit),
    ]
    if bad:
        controls.insert(3, theme.error(t("login_bad")))
    controls.append(theme.muted(t("web_records_note")))
    return ft.View(route="/login", controls=[theme.page_column(controls)], padding=0)


def make_main(folder: str | None = None, web_users: bool | None = None) -> Callable[[ft.Page], object]:
    """web_users が True（既定: SEED_USERS_DIR があれば）なら、ブラウザの客は招待コードでログインする。"""
    multi = users_root() is not None if web_users is None else web_users

    async def main(page: ft.Page) -> None:
        page.title = "seed"
        theme.apply(page)
        log.info("session: web=%s route=%s multi=%s", page.web, page.route, multi)
        if not (multi and page.web):
            app = App(page, folder)
            page.on_route_change = app.route_change
            app.route_change()
            return
        language = lang.default_language(None)

        async def start(user: WebUser) -> None:
            try:
                app = App(page, str(user_folder(user)), web_user=user)
                page.on_route_change = app.route_change
                # ログインの画面（/login）から入口へ。道を変えると on_route_change が画面を作る
                await page.push_route("/")
                app.route_change(path="/")
                log.info("web: %s が入った（%s）", user.name, page.route)
            except Exception:
                log.exception("web: 入った後の画面を作れない")
                raise

        async def on_login(code: str) -> None:
            user = web_user_for(code)
            log.info("web: ログインの試み（コードの長さ %d、%s）", len(code or ""), "可" if user else "不可")
            if user is None:
                page.views.clear()
                page.views.append(login_view(page, language, on_login, bad=True))
                page.update()
                return
            with contextlib.suppress(Exception):  # 覚えられなくてもログインはできる
                await page.shared_preferences.set(PREF_INVITE, user.code)
            await start(user)

        remembered = None
        try:
            remembered = await page.shared_preferences.get(PREF_INVITE)
        except Exception:  # noqa: BLE001
            remembered = None
        user = web_user_for(remembered if isinstance(remembered, str) else None)
        if user is not None:
            await start(user)
        else:
            page.views.clear()
            page.views.append(login_view(page, language, on_login))
            page.update()
            log.info("session: ログインの画面を出した")

    return main


main = make_main()


def asgi_app(folder: str | None = None):
    """Web 版を ASGI のアプリとして（uvicorn で動かす。設計書 §6.2）。写真の受け取りは SEED_UPLOAD_DIR。"""
    up = upload_root()
    return ft.run(make_main(folder, web_users=True), export_asgi_app=True, upload_dir=str(up) if up else None)


def run(web: bool = False, folder: str | None = None, port: int = 0, serve: bool = False) -> None:
    """PC 版は窓で開く。web はブラウザで開く（開発中の確認用）。serve は Web 版をサーバーとして動かす（§6.2）。"""
    if serve:
        import uvicorn

        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("flet").setLevel(logging.INFO)
        uvicorn.run(
            asgi_app(folder),
            host=os.environ.get("SEED_APP_HOST", "127.0.0.1"),
            port=port or 8550,
            log_level="info",
        )
        return
    up = upload_root()
    ft.run(
        make_main(folder),
        view=ft.AppView.WEB_BROWSER if web else ft.AppView.FLET_APP,
        port=port,
        upload_dir=str(up) if (web and up) else None,
    )


if __name__ == "__main__":
    ft.run(main)
