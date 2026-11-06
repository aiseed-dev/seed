# SPDX-License-Identifier: AGPL-3.0-or-later
"""アプリの始まり。`flet run src/seed/app/main.py` か `seed app` で開く。

アプリは PC 版とスマートフォン（iOS、Android）。本人のフォルダー（既定 ~/seed）を読む（設計書 §6）。
`seed app --web` は、この PC の中だけで、ブラウザで画面を確かめるための一人用。人ごとに分ける Web 版はやめた
（作者 2026-11-06「Web 版は、マニュアル的なものだけにする」）。

画面は二つ（話す /、写真 /photos）。道（route）で切り替える。サーバーの管理は kagi の机の画面「人の出入り」から。
古い道（/observe、/records など）に来たら「話す」へ。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import flet as ft

from seed import fields as fields_mod
from seed import lang
from seed import settings as settings_mod
from seed.app import gallery, plugins, talk, theme
from seed.app.strings import s
from seed.cli import prepare
from seed.client import Client

log = logging.getLogger("seed.app")

MAX_PHOTOS = 6
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
    title: dict[str, str] | None = None  # プラグインの画面は、言葉の鍵ではなくこの名を使う


SCREENS = [
    Screen("/", "nav_talk", ft.Icons.CHAT_BUBBLE_OUTLINE, talk.view),
    Screen("/photos", "nav_photos", ft.Icons.PHOTO_LIBRARY_OUTLINED, gallery.view),
]


class App:
    """一つの窓の状態。"""

    def __init__(self, page: ft.Page, folder: str | None = None) -> None:
        self.page = page
        folder = fields_mod.chosen(None, folder)  # 畑の一覧の current も見る（記録の形 §19）
        self.index: dict | None = None
        self.picker = ft.FilePicker()  # 参照を持っておく（無いと外される）
        self.open_folder(folder)

    def open_folder(self, folder: str | None) -> None:
        """記録のフォルダーを開く（設定を読み、手引きを写す）。畑を切り替えた時も呼ぶ。"""
        old = getattr(self, "state", {}).get("remote")
        if old is not None:  # 前の畑のリモートコントロールは止める
            old.stop()
        self.settings = settings_mod.load(folder)
        self.folder = self.settings.records
        prepare(self.folder, self.settings.language)  # 手引きの写しと CLAUDE.md も（もうあれば触らない）
        self.lang = self.settings.language
        self.plugins = plugins.load(self.folder)
        self._plugins_stamp = plugins.stamp(self.folder)
        self.state: dict = {}  # この窓の間だけ残す物（やり取りに足した物、撮っている間の物）。畑が替われば空に

    # --- 畑（記録の形 §19。切り替えは「話す」の設定の札から）
    async def switch_field(self, name: str) -> None:
        """畑を切り替える: current を書き、設定とフォルダーを読み直して、今の画面を描き直す。"""
        folder = fields_mod.switch_field(name)
        self.open_folder(str(folder))
        await self.go(urlparse(self.page.route or "/").path or "/")

    async def open_other_folder(self, folder: str) -> None:
        """別のフォルダーを開く: 一覧に覚えて current にし、設定を読み直して、今の画面を描き直す。"""
        fields_mod.remember_folder(folder)
        self.open_folder(folder)
        await self.go(urlparse(self.page.route or "/").path or "/")

    async def pick_folder(self) -> None:
        """フォルダーを選ぶ窓を出し、選ばれたら開く（PC のアプリ）。"""
        got = await self.picker.get_directory_path()
        if got:
            await self.open_other_folder(got)

    # --- スマートフォンから使う（Claude Code の Remote Control。remote.py）
    async def remote_start(self) -> None:
        """この畑のフォルダーで立てる。立つまで 1 秒ごとに札を描き直す（最大 60 秒）。"""
        from seed import remote

        old = self.state.pop("remote", None)
        if old is not None:
            old.stop()
        name = fields_mod.selected_name(fields_mod.load_fields(), self.folder.root) or self.folder.root.name
        self.state["remote_name"] = name
        self.state["remote"] = await asyncio.to_thread(remote.Remote.start, self.folder.root, name)
        self.refresh()
        self.remote_poll = asyncio.create_task(self._remote_poll(self.state["remote"]))

    async def _remote_poll(self, r) -> None:
        for _ in range(60):
            await asyncio.sleep(1)
            if self.state.get("remote") is not r:
                return
            self.refresh()
            if r.state != "starting":  # asking は人の「はい」を待つ。押されたらまた回す
                return

    async def remote_yes(self) -> None:
        r = self.state.get("remote")
        if r is not None:
            r.answer_yes()
            self.refresh()
            self.remote_poll = asyncio.create_task(self._remote_poll(r))

    async def remote_stop(self) -> None:
        r = self.state.pop("remote", None)
        if r is not None:
            await asyncio.to_thread(r.stop)
        self.refresh()

    # --- 文と道
    def t(self, word: str, **kw) -> str:
        return s(word, self.lang, **kw)

    @property
    def folder_label(self) -> str:
        home = Path.home()
        root = self.folder.root
        return f"~/{root.relative_to(home).as_posix()}" if root.is_relative_to(home) else str(root)

    @property
    def project_name(self) -> str:
        """プロジェクトフォルダーの名: 一覧にある畑の名、無ければフォルダーの名。"""
        name = fields_mod.selected_name(fields_mod.load_fields(), self.folder.root)
        return name or self.folder.root.name

    def show_projects(self, e=None) -> None:
        from seed.app import cards  # cards は main を読むので、使う時に取る

        self.page.show_dialog(cards.project_sheet(self))

    def screens(self) -> list[Screen]:
        """切り替えの並び。話す、写真、同梱のプラグイン、本人のプラグイン。"""
        return SCREENS + [
            Screen(p.route, p.name, p.icon, self._plugin_builder(p), p.title) for p in self.plugins
        ]

    def screen_name(self, sc: Screen) -> str:
        if sc.title is not None:
            return sc.title.get(self.lang) or sc.title.get("en") or next(iter(sc.title.values()))
        return self.t(sc.word)

    def _plugin_builder(self, p: plugins.Plugin) -> Callable[[App], ft.View]:
        def build(app: App) -> ft.View:
            try:
                controls = p.build(app)
            except Exception as ex:
                log.exception("プラグインが動かない: %s", p.name)
                controls = [theme.muted(app.t("plugin_failed", name=p.name, detail=type(ex).__name__))]
            return app.view(p.route, controls)

        return build

    def view(self, route: str, controls: list[ft.Control]) -> ft.View:
        """縦に流れる画面（写真、撮る）。"""
        return self.frame(route, None, controls)

    def frame(self, route: str, body: ft.Control | None, controls: list[ft.Control] | None = None) -> ft.View:
        """画面の枠。上の端に、名と、画面を切り替える小さな印。body は本文（「話す」のやり取りと入力）。"""
        screens = self.screens()
        idx = next((i for i, sc in enumerate(screens) if sc.route == route), 0)
        if body is None:
            self._body = theme.page_column(controls or [], getattr(self.page, "width", None))
        else:
            self._body = ft.Container(
                content=body,
                width=theme.fit_width(getattr(self.page, "width", None)),
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                expand=True,
            )
        self.page.on_resize = self._fit
        return ft.View(
            route=route,
            appbar=ft.AppBar(
                title=ft.Text(f"{self.project_name} — {self.screen_name(screens[idx])}"),
                actions=[
                    ft.IconButton(
                        ft.Icons.FOLDER_OPEN_OUTLINED,
                        tooltip=self.t("project_switch"),
                        on_click=self.show_projects,
                    )
                ]
                + [
                    ft.IconButton(
                        sc.icon,
                        tooltip=self.screen_name(sc),
                        selected=i == idx,
                        icon_color=ft.Colors.PRIMARY if i == idx else None,
                        on_click=self._nav_to(sc.route),
                    )
                    for i, sc in enumerate(screens)
                ],
            ),
            controls=[self._body],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            padding=0,
        )

    def _fit(self, e=None) -> None:
        """窓の幅が変わったら、画面を作り直さずに幅だけを直す（撮っている間も部品を外さない）。"""
        body = getattr(self, "_body", None)
        if body is not None:
            body.width = theme.fit_width(getattr(self.page, "width", None))
            self.page.update()

    def reload_plugins(self) -> None:
        """話す間に Claude Code が <フォルダー>/plugins/ に書いた物を、開き直さずに拾う。"""
        now = plugins.stamp(self.folder)
        if now != self._plugins_stamp:
            self._plugins_stamp = now
            self.plugins = plugins.load(self.folder)

    def route_change(self, e=None, path: str | None = None) -> None:
        self.reload_plugins()
        path = path or urlparse(self.page.route or "/").path or "/"
        sc = next((sc for sc in self.screens() if sc.route == path), SCREENS[0])  # 知らない道は「話す」へ
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
        # ブラウザでは push_route の後の on_route_change が来ないことがあるので、ここでも作る
        self.route_change(path=route)

    def _nav_to(self, route: str):
        async def h(e) -> None:
            await self.go(route)

        return h

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
        paths = [Path(f.path) for f in files if f.path]
        if not paths:
            self.toast(self.t("pc_only"))
        return paths


def make_main(folder: str | None = None) -> Callable[[ft.Page], object]:
    async def main(page: ft.Page) -> None:
        page.title = "seed"
        theme.apply(page)
        log.info("session: web=%s route=%s", page.web, page.route)
        app = App(page, folder)
        page.on_route_change = app.route_change
        app.route_change()

    return main


main = make_main()


def run(web: bool = False, folder: str | None = None, port: int = 0, serve: bool = False) -> None:
    """PC 版は窓で開く。web はこの PC のブラウザで開く（画面の確かめ用、一人用）。serve（Web 版）はやめた。"""
    if serve:
        print(s("web_serve_gone", lang.default_language(None)))
        return
    ft.run(make_main(folder), view=ft.AppView.WEB_BROWSER if web else ft.AppView.FLET_APP, port=port)


if __name__ == "__main__":
    ft.run(main)
