# SPDX-License-Identifier: AGPL-3.0-or-later
"""観察 /observe。写真を選び、座標と時刻を出し、サーバーか自分の Claude で読み、合う／違うを付ける。

観察は observations/<日>-<時刻>.md に、操作のたびに書く（利用マニュアル §5）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from seed import identify, local, photos
from seed.app import capture, theme
from seed.app.strings import error_text
from seed.cli import claude_steps, identify_photos, read_local, read_on_server
from seed.client import ClientError
from seed.records import ASKS, KINDS, RECORD_KEYS, Line, Observation, ask_word

if TYPE_CHECKING:
    from seed.app.main import App

THUMB = 160


def reading_rows(app: App, obs, path: Path) -> list[ft.Control]:
    """読みの行に「合う」「違う」を付ける表。記録と計画の画面でも使う（reading と write を持つ物なら何でも）。"""
    t = app.t
    rows: list[ft.Control] = []
    for i, line in enumerate(obs.reading):
        text = theme.line_text(line, app.lang)
        reason = ft.TextField(
            label=t("reason"), value=line.reason or "", visible=line.verdict == "wrong", dense=True
        )
        seg = ft.SegmentedButton(
            segments=[
                ft.Segment(value="right", label=ft.Text(t("right"))),
                ft.Segment(value="wrong", label=ft.Text(t("wrong"))),
            ],
            selected=[line.verdict] if line.verdict else [],
            allow_empty_selection=True,
            show_selected_icon=False,
        )

        def save(i=i, seg=seg, reason=reason, text=text) -> None:
            old = obs.reading[i]
            verdict = seg.selected[0] if seg.selected else None
            why = ((reason.value or "").strip() or None) if verdict == "wrong" else None
            obs.reading[i] = Line(old.key, old.text, old.confidence, verdict, why)
            obs.write(path)
            reason.visible = verdict == "wrong"
            text.spans = theme.line_text(obs.reading[i], app.lang).spans
            app.page.update()

        seg.on_change = lambda e, save=save: save()
        reason.on_submit = lambda e, save=save: save()
        reason.on_blur = lambda e, save=save: save()
        rows.append(ft.Column([text, ft.Row([seg], wrap=True), reason], spacing=4))
        rows.append(ft.Divider(height=1))
    return rows


def record_adder(
    app: App, obs, path: Path, keys: tuple[str, ...] = RECORD_KEYS, hint: str = "record_hint"
) -> list[ft.Control]:
    """本人の言葉を足す欄（観察は did, saw, said, note, ask。栽培計画は decided, did）。"""
    t = app.t
    key = ft.Dropdown(
        value=keys[0], options=[ft.DropdownOption(key=k, text=t(k)) for k in keys], width=160, dense=True
    )
    text = ft.TextField(hint_text=t(hint), expand=True, dense=True)

    def add(e=None) -> None:
        if not (text.value or "").strip():
            return
        obs.say(key.value or keys[0], text.value.strip().replace("\n", " "))
        obs.write(path)
        app.refresh()

    text.on_submit = add
    return [
        theme.subheading(t("record_add")),
        ft.Row([key, text, ft.Button(t("add"), on_click=add)], wrap=True),
    ]


def lines_block(app: App, heading: str, lines: list[Line]) -> list[ft.Control]:
    if not lines:
        return []
    return [theme.subheading(app.t(heading)), *[theme.line_text(l, app.lang) for l in lines]]


def summary(app: App, obs: Observation) -> list[ft.Control]:
    t = app.t
    out: list[ft.Control] = [theme.body(f"{t(obs.kind)} · {t('photos_n', n=len(obs.photos))}")]
    if obs.ask:
        out.append(theme.muted(f"{t('ask')}: " + "、".join(ask_word(a, app.lang) for a in obs.ask)))
    thumbs = []
    for rel in obs.photos:
        try:
            thumbs.append(
                ft.Image(
                    src=photos.shrink(app.folder.root / rel, max_side=THUMB), width=THUMB, border_radius=6
                )
            )
        except (photos.PhotoError, OSError):
            continue
    if thumbs:
        out.append(ft.Row(thumbs, wrap=True, spacing=8, run_spacing=8))
    out.append(theme.body(t("taken", date=obs.date, time=obs.time)))
    loc = obs.location
    if loc:
        out.append(
            theme.body(
                t(
                    "coord",
                    lat=loc["center"][0],
                    lon=loc["center"][1],
                    points=loc["points"],
                    extent=loc["extent_m"],
                )
            )
        )
    else:
        out.append(theme.error(t("no_coord")))
    return out


def view(app: App) -> ft.View:
    t, st = app.t, app.state
    obs: Observation | None = st.get("obs")
    busy = ft.Row([ft.ProgressRing(width=20, height=20), theme.body(t("reading_now"))], visible=False)
    kind = st.setdefault("kind", obs.kind if obs else "own")
    controls: list[ft.Control] = [theme.heading(t("observe_title"))]

    def kind_changed(e) -> None:
        st["kind"] = e.control.selected[0] if e.control.selected else "own"
        if obs:  # 今の観察にも付ける（読みはそのまま）
            obs.kind = st["kind"]
            obs.write(app.folder.observation_path(obs))
        app.refresh()

    controls += [
        theme.muted(t("kind")),
        ft.SegmentedButton(
            segments=[ft.Segment(value=k, label=ft.Text(t(k))) for k in KINDS],
            selected=[kind],
            show_selected_icon=False,
            on_change=kind_changed,
        ),
    ]
    if kind == "candidate":
        controls.append(theme.note(t("candidate_hint")))

    asks: list[str] = st.setdefault("ask", list(obs.ask) if obs else [])

    def ask_changed(e, key: str) -> None:
        if e.control.value and key not in asks:
            asks.append(key)
        elif not e.control.value and key in asks:
            asks.remove(key)
        st["ask"] = [a for a in ASKS if a in asks]
        if obs:  # 今の観察にも付ける（読みはそのまま。次に読むときに効く）
            obs.ask = list(st["ask"])
            obs.write(app.folder.observation_path(obs))

    controls += [
        theme.muted(t("ask")),
        ft.Row(
            [
                ft.Checkbox(
                    label=ask_word(a, app.lang),
                    value=a in asks,
                    on_change=lambda e, a=a: ask_changed(e, a),
                )
                for a in ASKS
            ],
            wrap=True,
        ),
        theme.note(t("ask_hint")),
    ]

    async def choose(e) -> None:
        try:
            paths = await app.pick_photos()
        except (OSError, TimeoutError) as ex:
            st.update(err=str(ex), msg=None)
            app.refresh()
            return
        if paths:
            await take_in(paths)

    async def take_in(paths: list) -> None:
        """写真（選んだ物、撮った物）を記録のフォルダーに取り込み、観察にする。"""
        try:
            rel = await asyncio.to_thread(photos.import_photos, app.folder, paths, app.settings.keep)
            new = await asyncio.to_thread(photos.observation_for, app.folder, rel, app.lang)
            app.cleanup_uploads()
        except photos.PhotoError as ex:
            st.update(err=error_text(ex, app.lang), msg=None)
            app.refresh()
            return
        except (OSError, TimeoutError) as ex:
            st.update(err=str(ex), msg=None)
            app.refresh()
            return
        new.kind = st["kind"]
        new.ask = list(st.get("ask") or [])
        path = app.folder.observation_path(new)
        new.write(path)
        st.update(obs=new, msg=t("saved_to", path=path), err=None, steps=None)
        app.refresh()

    async def read_server(e) -> None:
        busy.visible = True
        for b in buttons.controls:
            b.disabled = True
        app.page.update()
        try:
            await asyncio.to_thread(read_on_server, app.settings, app.folder, obs)
            path = app.folder.observation_path(obs)
            obs.write(path)
            st.update(err=None, msg=t("saved_to", path=path))
        except (ClientError, photos.PhotoError) as ex:
            st.update(err=error_text(ex, app.lang, server=app.settings.server), msg=None)
        app.refresh()

    async def read_here(e) -> None:
        busy.visible = True
        for b in buttons.controls:
            b.disabled = True
        st.update(err=None, msg=t("local_reading"))
        app.page.update()
        try:
            await asyncio.to_thread(read_local, app.settings, app.folder, obs)
            path = app.folder.observation_path(obs)
            obs.write(path)
            st.update(err=None, msg=t("saved_to", path=path))
        except (ClientError, photos.PhotoError) as ex:
            st.update(err=error_text(ex, app.lang), msg=None)
        app.refresh()

    def read_claude(e) -> None:
        st["steps"] = claude_steps(app.lang, app.folder, obs, app.folder_label)
        app.refresh()

    async def identify_now(e) -> None:
        busy.visible = True
        for b in buttons.controls:
            b.disabled = True
        st.update(err=None, msg=t("identifying"))
        app.page.update()
        try:
            via = "server" if app.web or not identify.available() else "local"
            added = await asyncio.to_thread(identify_photos, app.settings, app.folder, obs, None, via)
            obs.write(app.folder.observation_path(obs))
            st.update(err=None, msg=t("identify_done", n=len(added)) if added else t("identify_none"))
        except (ClientError, photos.PhotoError) as ex:
            st.update(err=error_text(ex, app.lang, server=app.settings.server), msg=None)
        app.refresh()

    async def start_capture(e) -> None:
        st["capture"] = capture.Session()
        app.refresh()

    async def end_capture(paths: list | None = None) -> None:
        sess = st.pop("capture", None)
        st.pop("capture_parts", None)
        if paths:
            await take_in(paths)  # 取り込みが済んでから、一時の場所を消す
        else:
            app.refresh()
        if sess is not None:
            sess.close()

    if st.get("capture") is not None:  # 撮っている間は、撮る画面だけを出す
        return app.view("/observe", capture.view(app, end_capture, end_capture))

    can_capture = capture.available(app.page)
    controls += [
        theme.muted(t("photos_hint")),
        ft.Row(
            [
                *(
                    [
                        ft.FilledButton(
                            t("capture_button"), icon=ft.Icons.PHOTO_CAMERA_OUTLINED, on_click=start_capture
                        )
                    ]
                    if can_capture
                    else []
                ),
                (ft.OutlinedButton if can_capture else ft.FilledButton)(
                    t("choose_photos"), icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, on_click=choose
                ),
            ],
            wrap=True,
        ),
    ]
    has_local = local.available() is not None and not app.web  # Web 版はサーバーだけ
    buttons = ft.Row(
        [
            (
                ft.FilledButton(t("read_local"), icon=ft.Icons.COMPUTER_OUTLINED, on_click=read_here)
                if has_local
                else ft.FilledButton(t("read_server"), icon=ft.Icons.CLOUD_OUTLINED, on_click=read_server)
            ),
            (
                ft.OutlinedButton(t("read_server"), icon=ft.Icons.CLOUD_OUTLINED, on_click=read_server)
                if has_local
                else ft.OutlinedButton(t("read_local"), icon=ft.Icons.COMPUTER_OUTLINED, on_click=read_here)
            ),
            *(
                []
                if app.web
                else [ft.OutlinedButton(t("read_claude"), icon=ft.Icons.TERMINAL, on_click=read_claude)]
            ),
        ],
        wrap=True,
    )
    if app.web:  # Web 版: 手元の釦は出さず、サーバーの釦だけ
        buttons.controls = [b for b in buttons.controls if getattr(b, "content", None) != t("read_local")]
    can_identify = identify.available() or bool(app.settings.invite)
    if obs and can_identify:
        buttons.controls.append(
            ft.OutlinedButton(t("identify_button"), icon=ft.Icons.GRASS_OUTLINED, on_click=identify_now)
        )
    if obs:
        path = app.folder.observation_path(obs)
        controls += summary(app, obs)
        controls += [buttons, theme.muted(t("web_read_hint") if app.web else t("read_local_hint")), busy]
        if can_identify:
            controls.append(theme.muted(t("identify_hint")))
    if st.get("err"):
        controls.append(theme.error(st["err"]))
    if st.get("msg"):
        controls.append(theme.muted(st["msg"]))
    if obs and st.get("steps"):
        controls.append(theme.mono(st["steps"]))
    if obs and obs.reading:
        controls += [theme.subheading(f"{t('Reading')} ({obs.model})"), theme.muted(t("ai_hint"))]
        controls += reading_rows(app, obs, path)
    if obs:
        controls += lines_block(app, "Data", obs.data)
        controls += lines_block(app, "Record", obs.record)
        controls += record_adder(app, obs, path)
    return app.view("/observe", controls)
