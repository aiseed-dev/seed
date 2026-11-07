# SPDX-License-Identifier: AGPL-3.0-or-later
"""撮る画面（iPhone 版、Android 版、Web 版）。アプリのカメラで撮り、撮った時の位置を写真に書く。

作者 2026-11-06「flet アプリで専用のカメラを持った方がいいかも」「iphone 版をつくればいい」
「撮った写真の整理もできるようにしましょうね」。人から届いた写真に座標が入っていなかった事から。

- 座標はこの作業に必須（設計書 §9）。位置が取れるまで、シャッターは切れない。
- 撮った写真には、その場で座標・時刻・向き・誤差を EXIF で書く（photos.stamp）。後はスマートフォンのカメラの写真と同じ道。
- 撮った物は並べて見て、要らない物を外してから観察にする。
- 部品は flet-camera と flet-geolocator。PC の窓ではカメラの部品が動かないので、この画面は出さない。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from seed import photos

from . import theme

if TYPE_CHECKING:
    from .main import App

MOBILE = (ft.PagePlatform.IOS, ft.PagePlatform.ANDROID)
MAX_SHOTS = 6  # 一度の観察の写真の数（選ぶ時と同じ）
POSITION_WAIT_S = 10
THUMB = 96


def available(page: ft.Page) -> bool:
    """この端末で撮れるか。スマートフォンのアプリか Web 版で、カメラと位置の部品が入っている時だけ。"""
    try:
        import flet_camera  # noqa: F401
        import flet_geolocator  # noqa: F401
    except ImportError:
        return False
    return bool(getattr(page, "web", False)) or getattr(page, "platform", None) in MOBILE


def is_pc(app) -> bool:
    """PC のアプリか（Web 版でも、スマートフォンでもない）。カメラが無く、写真は選んで足す。"""
    page = app.page
    return not getattr(page, "web", False) and getattr(page, "platform", None) not in MOBILE


def position_fields(pos) -> dict | None:
    """位置の部品の答え → stamp に渡す物。緯度と経度が無ければ None。"""
    lat, lon = getattr(pos, "latitude", None), getattr(pos, "longitude", None)
    if lat is None or lon is None:
        return None

    def num(name: str) -> float | None:
        v = getattr(pos, name, None)
        return float(v) if isinstance(v, (int, float)) else None

    heading = num("heading")
    return {
        "lat": float(lat),
        "lon": float(lon),
        "altitude": num("altitude"),
        # 向きは、止まっていると 0 か負で来る端末がある。確かでない物は書かない
        "heading": heading if heading is not None and 0 < heading < 360 else None,
        "accuracy": num("accuracy"),
    }


@dataclass
class Shot:
    path: Path
    accuracy: float | None
    kept: Path | None = None  # スマートフォンの Pictures に残した写真。外しても消さない


@dataclass
class Session:
    """撮っている間の物。写真は一時の場所に置き、観察にした時に記録のフォルダーへ写す。"""

    dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="seed-shot-")))
    shots: list[Shot] = field(default_factory=list)
    position: dict | None = None  # 最後に取れた位置
    ready: bool = False

    def add(self, jpeg: bytes, position: dict | None = None, now: dt.datetime | None = None) -> Shot:
        """一枚足す。位置は今取れた物、無ければ最後に取れた物。どちらも無ければ足さない。"""
        pos = position or self.position
        if pos is None:
            raise photos.PhotoError("capture_no_position", "shot.jpg", "no position yet")
        if len(self.shots) >= MAX_SHOTS:
            raise photos.PhotoError("too_many_photos", "shot.jpg", "too many shots")
        now = now or dt.datetime.now()
        data = photos.stamp(
            jpeg, pos["lat"], pos["lon"], now, pos.get("altitude"), pos.get("heading"), pos.get("accuracy")
        )
        path = self.dir / f"{now.strftime('%Y%m%d-%H%M%S')}-{len(self.shots) + 1}.jpg"
        path.write_bytes(data)
        kept = photos.keep_on_device(data, path.name, now.strftime("%Y-%m-%d"))
        self.position = pos
        shot = Shot(path, pos.get("accuracy"), kept)
        self.shots.append(shot)
        return shot

    def remove(self, shot: Shot) -> None:
        if shot in self.shots:
            self.shots.remove(shot)
            shot.path.unlink(missing_ok=True)

    def paths(self) -> list[Path]:
        return [s.path for s in self.shots]

    def close(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


def keep_video(root: Path, data: bytes, position: dict | None, now: dt.datetime | None = None) -> Path:
    """動画を記録の videos/<日>/<HHMMSS>.mp4 に置き、撮った所と時を同じ名の .json に書く（動画の中には書けないので）。

    スマートフォンの共有の Pictures/seed にも残す（写真と同じ。消すのは本人）。
    """
    now = now or dt.datetime.now()
    day = now.strftime("%Y-%m-%d")
    path = Path(root) / "videos" / day / f"{now.strftime('%H%M%S')}.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    where = {"taken": now.isoformat(timespec="seconds")}
    if position:
        where.update(
            {k: position[k] for k in ("lat", "lon", "accuracy", "heading") if position.get(k) is not None}
        )
    path.with_suffix(".json").write_text(json.dumps(where, ensure_ascii=False, indent=1), encoding="utf-8")
    photos.keep_on_device(data, path.name, day)
    return path


def accuracy_text(app: App, pos: dict | None) -> str:
    if pos is None:
        return app.t("capture_waiting")
    acc = pos.get("accuracy")
    return app.t("capture_position_ok", m=round(acc)) if acc is not None else app.t("capture_position_plain")


def view(app: App, on_done, on_cancel) -> list[ft.Control]:
    """撮る画面の中身。画面を作り直さずに、部品だけを更新する（カメラの部品を外さないため）。

    on_done(paths) は撮った写真の道を受けて観察にする。on_cancel() は何もせず戻る。
    """
    import flet_camera as fc
    import flet_geolocator as fg

    t = app.t
    sess: Session = app.state["capture"]
    camera = fc.Camera(expand=True)
    geo = fg.Geolocator(configuration=fg.GeolocatorConfiguration(accuracy=fg.GeolocatorPositionAccuracy.BEST))
    app.state["capture_parts"] = (camera, geo)  # 参照を持っておく（無いと外される）

    status = theme.body("")
    problem = theme.error("")
    problem.visible = False
    thumbs = ft.Row(wrap=True, spacing=8)
    shutter = ft.FilledButton(t("capture_shoot"), icon=ft.Icons.CAMERA, disabled=True)
    done = ft.FilledButton(t("capture_done", n=0), icon=ft.Icons.CHECK, disabled=True)
    opener = ft.FilledButton(t("capture_open"), icon=ft.Icons.PHOTO_CAMERA_OUTLINED)
    kept_note = theme.muted("")
    kept_note.visible = False
    # 倍率（カメラを開いてから、その機種の最小〜最大で）
    zoom = ft.Slider(min=1, max=1, value=1, divisions=None, label="{value}×", visible=False, expand=True)
    zoom_text = theme.muted("")
    zoom_text.visible = False
    # 写真と動画を切り替える
    mode = {"video": False, "recording": False}
    to_photo = ft.TextButton(t("capture_mode_photo"), icon=ft.Icons.PHOTO_CAMERA_OUTLINED, visible=False)
    to_video = ft.TextButton(t("capture_mode_video"), icon=ft.Icons.VIDEOCAM_OUTLINED, visible=False)
    record = ft.FilledButton(
        t("capture_record"), icon=ft.Icons.FIBER_MANUAL_RECORD, visible=False, disabled=True
    )

    def say(text: str | None) -> None:
        problem.value, problem.visible = text or "", bool(text)

    def redraw() -> None:
        n = len(sess.shots)
        thumbs.controls = [
            ft.Stack(
                [
                    ft.Image(src=photos.shrink(s.path, max_side=THUMB), width=THUMB, border_radius=6),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_size=16,
                        tooltip=t("capture_remove"),
                        on_click=lambda e, s=s: drop(s),
                        right=0,
                        top=0,
                    ),
                ],
                width=THUMB,
            )
            for s in sess.shots
        ]
        if sess.shots and sess.shots[-1].kept:
            kept_note.value, kept_note.visible = t("capture_kept"), True
        elif sess.shots and getattr(app.page, "platform", None) in MOBILE and photos.device_pictures_dir():
            kept_note.value, kept_note.visible = t("capture_not_kept"), True
        else:
            kept_note.visible = False
        done.content, done.disabled = t("capture_done", n=n), n == 0
        shutter.disabled = not sess.ready or sess.position is None or n >= MAX_SHOTS
        shutter.visible = not mode["video"]
        record.visible = sess.ready and mode["video"]
        record.disabled = not sess.ready
        record.content = t("capture_stop") if mode["recording"] else t("capture_record")
        record.icon = ft.Icons.STOP if mode["recording"] else ft.Icons.FIBER_MANUAL_RECORD
        to_photo.visible = sess.ready and mode["video"] and not mode["recording"]
        to_video.visible = sess.ready and not mode["video"]
        zoom.visible = zoom_text.visible = sess.ready and zoom.max > zoom.min
        status.value = accuracy_text(app, sess.position) if sess.ready else ""
        app.page.update()

    def drop(shot: Shot) -> None:
        sess.remove(shot)
        redraw()

    async def locate() -> dict | None:
        try:
            pos = await asyncio.wait_for(geo.get_current_position(), POSITION_WAIT_S)
        except Exception:  # noqa: BLE001  位置の部品は端末ごとに違う例外を投げる。取れなかった、で扱う
            return None
        return position_fields(pos)

    async def open_camera(e) -> None:
        say(None)
        opener.disabled = True
        status.value = t("capture_waiting")
        app.page.update()
        try:
            granted = await geo.request_permission()
            if granted in (
                fg.GeolocatorPermissionStatus.DENIED,
                fg.GeolocatorPermissionStatus.DENIED_FOREVER,
            ):
                raise RuntimeError(t("capture_location_denied"))
            sess.position = await locate() or sess.position
            cams = await camera.get_available_cameras()
            if not cams:
                raise RuntimeError(t("capture_no_camera"))
            back = next((c for c in cams if c.lens_direction == fc.CameraLensDirection.BACK), cams[0])
            await camera.initialize(
                description=back,
                resolution_preset=fc.ResolutionPreset.MAX,
                enable_audio=False,
                image_format_group=fc.ImageFormatGroup.JPEG,
            )
            sess.ready = True
            opener.visible = False
            try:
                lo, hi = await camera.get_min_zoom_level(), await camera.get_max_zoom_level()
                zoom.min, zoom.max, zoom.value = float(lo), float(min(hi, 10.0)), float(lo)
                zoom_text.value = t("capture_zoom", z=f"{zoom.value:.1f}")
            except Exception:  # noqa: BLE001  倍率を持たない機種は、つまみを出さない
                zoom.min = zoom.max = 1.0
            if sess.position is None:
                say(t("capture_no_position"))
        except Exception as ex:  # noqa: BLE001  許しが無い、カメラが無い、を本人に見せる
            opener.disabled = False
            say(str(ex) or t("capture_no_camera"))
        redraw()

    async def shoot(e) -> None:
        say(None)
        shutter.disabled = True
        app.page.update()
        try:
            data = await camera.take_picture()
            sess.add(data, await locate())
        except photos.PhotoError as ex:
            say(t(ex.word) if ex.word.startswith("capture_") or ex.word == "too_many_photos" else str(ex))
        except Exception as ex:  # noqa: BLE001
            say(str(ex) or t("capture_no_camera"))
        redraw()

    async def retry_position(e) -> None:
        sess.position = await locate() or sess.position
        say(None if sess.position else t("capture_no_position"))
        redraw()

    async def finish(e) -> None:
        await on_done(sess.paths())

    async def cancel(e) -> None:
        await on_cancel()

    async def set_zoom(e) -> None:
        try:
            await camera.set_zoom_level(float(zoom.value))
        except Exception:  # noqa: BLE001
            return
        zoom_text.value = t("capture_zoom", z=f"{float(zoom.value):.1f}")
        app.page.update()

    def switch(video: bool):
        def h(e) -> None:
            mode["video"] = video
            say(None)
            redraw()

        return h

    async def toggle_record(e) -> None:
        say(None)
        record.disabled = True
        app.page.update()
        try:
            if not mode["recording"]:
                try:
                    await camera.prepare_for_video_recording()
                except Exception:  # noqa: BLE001, S110  要らない端末もある
                    pass
                await camera.start_video_recording()
                mode["recording"] = True
                sess.position = await locate() or sess.position
            else:
                data = await camera.stop_video_recording()
                mode["recording"] = False
                path = await asyncio.to_thread(keep_video, app.folder.root, data, sess.position)
                kept_note.value, kept_note.visible = (
                    t("capture_video_kept", path=path.relative_to(app.folder.root).as_posix()),
                    True,
                )
        except Exception as ex:  # noqa: BLE001  録れない機種、許しが無い、を本人に見せる
            mode["recording"] = False
            say(str(ex) or t("capture_no_camera"))
        redraw()

    zoom.on_change_end = set_zoom
    to_photo.on_click, to_video.on_click, record.on_click = switch(False), switch(True), toggle_record
    opener.on_click, shutter.on_click, done.on_click = open_camera, shoot, finish
    return [
        theme.heading(t("capture_title")),
        theme.muted(t("capture_hint")),
        ft.Container(
            camera,
            height=420,
            border_radius=8,
            bgcolor=ft.Colors.BLACK,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        ),
        ft.Row(
            [ft.Icon(ft.Icons.ZOOM_IN, size=18), zoom, zoom_text],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ft.Row([opener, shutter, record, to_video, to_photo], wrap=True),
        status,
        ft.Row(
            [
                ft.TextButton(
                    t("capture_retry_position"), icon=ft.Icons.MY_LOCATION, on_click=retry_position
                ),
                ft.TextButton(t("capture_cancel"), icon=ft.Icons.CLOSE, on_click=cancel),
            ],
            wrap=True,
        ),
        problem,
        thumbs,
        kept_note,
        done,
    ]
