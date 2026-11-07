# SPDX-License-Identifier: AGPL-3.0-or-later
"""撮る画面（iPhone 版、Android 版、Web 版）。アプリのカメラで撮り、撮った時の位置を写真に書く。

作者 2026-11-06「flet アプリで専用のカメラを持った方がいいかも」「iphone 版をつくればいい」
「撮った写真の整理もできるようにしましょうね」。人から届いた写真に座標が入っていなかった事から。
作者 2026-11-07「カメラアプリは使いづらいので設計をやり直して。タイトルや先頭部分の文字は邪魔、特に横にしたとき。
横にしたときは、拡大・縮小がしずらい。元に戻ることがわかりにくい。失敗した写真や動画を簡単に消せない」
「できるだけ標準のカメラアプリに近いものにして」。

- 画面いっぱいがカメラ。上の端に「← 戻る」と位置の印だけ。下（横の時は右の端）に倍率、写真と動画、シャッター。
- 倍率は二本の指でつまむか、0.5× 1× 2× 5× の印を押す。
- 左下の丸は最後に撮った物。押すと見返しになり、「消す」で消せる（すぐ下に「元に戻す」）。
- 座標はこの作業に必須（設計書 §9）。位置が取れるまで、シャッターは切れない。
- 撮った写真には、その場で座標・時刻・向き・誤差を EXIF で書く（photos.stamp）。
- 動画は撮った時に記録の videos/ に置き、カメラを出た時に PC（家のサーバー）へ送る。消す物は送る前に消せる。
- 部品は flet-camera と flet-geolocator。PC の窓ではカメラの部品が動かないので、この画面は出さない。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from seed import photos

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
    kept: Path | None = None  # スマートフォンの Pictures/seed に残した写し
    kind: str = "photo"  # photo | video
    trashed: list[tuple[Path, Path]] = field(default_factory=list)  # 消した時の (元の所, 一時のごみ箱)

    @property
    def files(self) -> list[Path]:
        """この一つに属するファイル（動画は撮った時と所の .json も）。"""
        out = [self.path]
        if self.kind == "video":
            out.append(self.path.with_suffix(".json"))
        if self.kept is not None:
            out.append(self.kept)
        return out


@dataclass
class Session:
    """撮っている間の物。写真は一時の場所に置き、観察にした時に記録のフォルダーへ写す。

    消した物はこの間だけ一時のごみ箱に置き（「元に戻す」のため）、カメラを出る時に本当に消す。
    """

    dir: Path = field(default_factory=lambda: Path(tempfile.mkdtemp(prefix="seed-shot-")))
    shots: list[Shot] = field(default_factory=list)
    position: dict | None = None  # 最後に取れた位置
    ready: bool = False

    def photos(self) -> list[Shot]:
        return [s for s in self.shots if s.kind == "photo"]

    def add(self, jpeg: bytes, position: dict | None = None, now: dt.datetime | None = None) -> Shot:
        """一枚足す。位置は今取れた物、無ければ最後に取れた物。どちらも無ければ足さない。"""
        pos = position or self.position
        if pos is None:
            raise photos.PhotoError("capture_no_position", "shot.jpg", "no position yet")
        if len(self.photos()) >= MAX_SHOTS:
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

    def add_video(self, path: Path) -> Shot:
        """記録に置いた動画（keep_video の後）を、この間に撮った物として並べる。"""
        base = photos.device_pictures_dir()
        kept = base / path.parent.name / path.name if base is not None else None
        shot = Shot(
            path, (self.position or {}).get("accuracy"), kept if kept and kept.exists() else None, "video"
        )
        self.shots.append(shot)
        return shot

    def remove(self, shot: Shot) -> None:
        """消す（一時のごみ箱へ。元に戻せる）。Pictures/seed の写しも、動画は記録の物も。"""
        if shot not in self.shots:
            return
        bin_ = self.dir / "trash" / str(id(shot))
        bin_.mkdir(parents=True, exist_ok=True)
        shot.trashed = []
        for i, f in enumerate(shot.files):
            if f.exists():
                dst = bin_ / f"{i}-{f.name}"
                shutil.move(str(f), dst)
                shot.trashed.append((f, dst))
        self.shots.remove(shot)

    def undo(self, shot: Shot) -> None:
        """消した物を元の所へ戻し、並びの元の位置（撮った順）に戻す。"""
        for src, dst in shot.trashed:
            if dst.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), src)
        shot.trashed = []
        if shot not in self.shots:
            self.shots.append(shot)
            self.shots.sort(key=lambda s: s.path.stat().st_mtime if s.path.exists() else 0)

    def paths(self) -> list[Path]:
        """観察にする写真（動画は入らない）。"""
        return [s.path for s in self.photos()]

    def close(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


ZOOM_STEPS = (0.5, 1.0, 2.0, 5.0, 10.0)


def zoom_steps(lo: float, hi: float) -> list[float]:
    """押す倍率の印（標準のカメラと同じ 0.5× 1× 2× 5×）。その機種の範囲にある物だけ。最小が 1 より小さければ最小も。"""
    out = [z for z in ZOOM_STEPS if lo - 1e-6 <= z <= hi + 1e-6]
    if lo < 1.0 and all(abs(z - lo) > 0.05 for z in out):
        out.insert(0, round(lo, 1))
    return out if len(out) > 1 else []


def clamp(z: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, z))


def is_landscape(width: float | None, height: float | None) -> bool:
    return bool(width and height and width > height)


def zoom_label(z: float) -> str:
    return f"{z:.1f}".rstrip("0").rstrip(".") + "×"


def clock(seconds: float) -> str:
    m, sec = divmod(int(seconds), 60)
    return f"{m}:{sec:02d}"


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


def _side(path: Path) -> dict:
    side = path.with_suffix(".json")
    try:
        got = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
    except (OSError, ValueError):
        return {}
    return got if isinstance(got, dict) else {}


def unsent_videos(root: Path) -> list[Path]:
    """記録の videos/ の中で、まだ PC へ送っていない動画（.json に sent が無い物）。古い順。"""
    base = Path(root) / "videos"
    if not base.is_dir():
        return []
    return sorted(p for p in base.glob("*/*.mp4") if not _side(p).get("sent"))


def send_video_home(app: App, path: Path) -> str:
    """動画と、同じ名の .json（撮った時と所）を家のサーバーへ。送れたら .json に sent（PC の上の置き場）を書く。"""
    where = _side(path)
    with app.client() as c:
        got = c.video(path, {k: v for k, v in where.items() if k != "sent"}, field=app.field_name or None)
    where["sent"] = got or True
    path.with_suffix(".json").write_text(json.dumps(where, ensure_ascii=False, indent=1), encoding="utf-8")
    return got


def accuracy_text(app: App, pos: dict | None) -> str:
    """上の端の位置の印。"""
    if pos is None:
        return app.t("capture_waiting")
    acc = pos.get("accuracy")
    return app.t("capture_position_ok", m=round(acc)) if acc is not None else app.t("capture_position_plain")


async def send_pending_videos(app: App) -> None:
    """家のサーバー（seed home）に繋いでいれば、まだ送っていない動画を古い順に PC へ送り、結果を一行で見せる。

    カメラを出た時に呼ぶ。畑で網が無くて送れなかった物も、次に繋がった時にここで送る。
    """
    from seed.app.talk import home_server

    if app.state.get("videos_sending"):
        return
    pending = await asyncio.to_thread(unsent_videos, app.folder.root)
    if not pending or not await home_server(app):
        return
    app.state["videos_sending"] = True
    sent: list[str] = []
    try:
        for path in pending:
            sent.append(await asyncio.to_thread(send_video_home, app, path))
        app.toast(app.t("capture_video_sent", n=len(sent), path=sent[-1]))
    except Exception as ex:  # noqa: BLE001  届かない、断られた、を本人に見せる（動画はスマートフォンに残る）
        why = str(ex).split(": ", 1)[0] or type(ex).__name__
        app.toast(app.t("capture_video_not_sent", n=len(pending) - len(sent), why=why))
    finally:
        app.state.pop("videos_sending", None)


WHITE = ft.Colors.WHITE
SHADE = ft.Colors.with_opacity(0.45, ft.Colors.BLACK)
PICK = ft.Colors.AMBER_300  # 選んでいる物（標準のカメラの黄色）


def view(app: App, on_done, on_cancel) -> ft.View:
    """撮る画面。画面いっぱいのカメラに、ボタンを重ねる。カメラの部品は作り直さず、重ねる物だけを描き直す。

    on_done(paths) は撮った写真の道を受けて観察にする。on_cancel() は何もせず戻る。
    """
    import flet_camera as fc
    import flet_geolocator as fg

    t = app.t
    page = app.page
    sess: Session = app.state["capture"]
    camera = fc.Camera(expand=True)
    geo = fg.Geolocator(configuration=fg.GeolocatorConfiguration(accuracy=fg.GeolocatorPositionAccuracy.BEST))
    app.state["capture_parts"] = (camera, geo)  # 参照を持っておく（無いと外される）
    st: dict = {
        "video": False,
        "recording": False,
        "rec_start": 0.0,
        "busy": False,
        "zoom": 1.0,
        "lo": 1.0,
        "hi": 1.0,
        "pinch_from": 1.0,
        "zoom_sent": 1.0,
        "zooming": False,
        "note": "",
        "error": False,
        "left": False,
    }

    # ---- 描く
    def chip(text: str, on_click=None, color=WHITE, bg=SHADE, size=13, pad=(10, 6)) -> ft.Container:
        return ft.Container(
            ft.Text(text, color=color, size=size, weight=ft.FontWeight.W_600),
            bgcolor=bg,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=pad[0], vertical=pad[1]),
            on_click=on_click,
            ink=on_click is not None,
        )

    def top_bar() -> ft.Control:
        back = ft.Container(
            ft.Row(
                [
                    ft.Icon(ft.Icons.ARROW_BACK, color=WHITE, size=22),
                    ft.Text(t("capture_back"), color=WHITE, size=15),
                ],
                spacing=6,
                tight=True,
            ),
            bgcolor=SHADE,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            on_click=go_back,
            ink=True,
        )
        right: list[ft.Control] = []
        if st["recording"]:
            right.append(
                chip("● " + clock(time.monotonic() - st["rec_start"]), color=WHITE, bg=ft.Colors.RED_700)
            )
        pos_ok = sess.position is not None
        right.append(
            ft.Container(
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.LOCATION_ON if pos_ok else ft.Icons.LOCATION_SEARCHING,
                            color=WHITE if pos_ok else PICK,
                            size=16,
                        ),
                        ft.Text(
                            t("capture_pos_m", m=round(sess.position["accuracy"]))
                            if pos_ok and sess.position.get("accuracy") is not None
                            else (t("capture_pos_ok_short") if pos_ok else t("capture_waiting")),
                            color=WHITE if pos_ok else PICK,
                            size=13,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                bgcolor=SHADE,
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                on_click=retry_position,
                tooltip=t("capture_retry_position"),
                ink=True,
            )
        )
        return ft.Row(
            [back, ft.Row(right, spacing=8, tight=True)],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def zoom_chips(vertical: bool) -> ft.Control | None:
        steps = zoom_steps(st["lo"], st["hi"])
        if not sess.ready or not steps:
            return None
        z = st["zoom"]
        near = min(steps, key=lambda s: abs(s - z))
        items = []
        for s_ in steps:
            on = s_ == near
            items.append(
                ft.Container(
                    ft.Text(
                        zoom_label(z) if on else zoom_label(s_),
                        color=PICK if on else WHITE,
                        size=13 if on else 12,
                        weight=ft.FontWeight.BOLD if on else ft.FontWeight.W_500,
                    ),
                    width=46 if on else 38,
                    height=46 if on else 38,
                    border_radius=23,
                    bgcolor=SHADE,
                    alignment=ft.Alignment.CENTER,
                    on_click=lambda e, s_=s_: page.run_task(zoom_to, s_),
                    ink=True,
                )
            )
        kw = {"spacing": 10, "alignment": ft.MainAxisAlignment.CENTER}
        return (
            ft.Column(items, horizontal_alignment=ft.CrossAxisAlignment.CENTER, **kw)
            if vertical
            else ft.Row(items, vertical_alignment=ft.CrossAxisAlignment.CENTER, **kw)
        )

    def mode_switch(vertical: bool) -> ft.Control:
        def item(label: str, video: bool) -> ft.Control:
            on = st["video"] == video
            return ft.Container(
                ft.Text(label, color=ft.Colors.BLACK if on else WHITE, size=14, weight=ft.FontWeight.W_600),
                bgcolor=PICK if on else None,
                border_radius=16,
                padding=ft.Padding.symmetric(horizontal=14, vertical=6),
                on_click=None if st["recording"] else (lambda e, v=video: switch(v)),
                ink=not st["recording"],
            )

        items = [item(t("capture_photo"), False), item(t("capture_video"), True)]
        return (
            ft.Column(items, spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            if vertical
            else ft.Row(items, spacing=8, alignment=ft.MainAxisAlignment.CENTER)
        )

    def shutter_button() -> ft.Control:
        if st["video"]:
            inner = ft.Container(
                width=26 if st["recording"] else 58,
                height=26 if st["recording"] else 58,
                border_radius=6 if st["recording"] else 29,
                bgcolor=ft.Colors.RED_600,
            )
            ok = sess.ready and not st["busy"]
            tip = t("capture_stop") if st["recording"] else t("capture_record")
        else:
            inner = ft.Container(width=60, height=60, border_radius=30, bgcolor=WHITE)
            ok = (
                sess.ready and sess.position is not None and not st["busy"] and len(sess.photos()) < MAX_SHOTS
            )
            tip = t("capture_shoot")
        return ft.Container(
            inner,
            width=78,
            height=78,
            border_radius=39,
            border=ft.Border.all(4, WHITE),
            alignment=ft.Alignment.CENTER,
            opacity=1.0 if ok else 0.4,
            on_click=(toggle_record if st["video"] else shoot) if ok else None,
            tooltip=tip,
        )

    def last_thumb() -> ft.Control:
        size = 54
        if not sess.shots:
            return ft.Container(width=size, height=size)
        last = sess.shots[-1]
        inner: ft.Control = (
            ft.Image(src=photos.shrink(last.path, max_side=160), fit=ft.BoxFit.COVER, width=size, height=size)
            if last.kind == "photo"
            else ft.Icon(ft.Icons.VIDEOCAM, color=WHITE, size=26)
        )
        return ft.Container(
            inner,
            width=size,
            height=size,
            border_radius=size // 2,
            border=ft.Border.all(2, WHITE),
            bgcolor=ft.Colors.GREY_800,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: review(len(sess.shots) - 1),
            tooltip=t("capture_review"),
        )

    def done_button() -> ft.Control:
        n = len(sess.photos())
        if st["recording"]:
            return ft.Container(width=54, height=54)
        return ft.Container(
            ft.Column(
                [ft.Icon(ft.Icons.CHECK, color=ft.Colors.BLACK if n else WHITE, size=22)]
                + ([ft.Text(str(n), color=ft.Colors.BLACK, size=11, weight=ft.FontWeight.BOLD)] if n else []),
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=54,
            height=54,
            border_radius=27,
            bgcolor=PICK if n else SHADE,
            opacity=1.0 if n else 0.5,
            alignment=ft.Alignment.CENTER,
            on_click=finish if n else None,
            tooltip=t("capture_done", n=n),
        )

    def note_line() -> ft.Control | None:
        if not st["note"]:
            return None
        return ft.Container(
            ft.Text(
                st["note"], color=PICK if st["error"] else WHITE, size=13, text_align=ft.TextAlign.CENTER
            ),
            bgcolor=SHADE,
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        )

    def opener() -> ft.Control | None:
        if sess.ready or st["busy"]:
            return None
        return ft.FilledButton(t("capture_open"), icon=ft.Icons.PHOTO_CAMERA_OUTLINED, on_click=open_camera)

    def overlays() -> list[ft.Control]:
        land = is_landscape(getattr(page, "width", None), getattr(page, "height", None))
        out: list[ft.Control] = [ft.Container(top_bar(), left=12, right=12, top=8)]
        zc = zoom_chips(vertical=land)
        note, open_ = note_line(), opener()
        if land:
            side = ft.Container(
                ft.Column(
                    [done_button(), shutter_button(), last_thumb()],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                right=0,
                top=0,
                bottom=0,
                width=110,
                bgcolor=SHADE,
                padding=ft.Padding.symmetric(vertical=12),
            )
            out += [
                side,
                ft.Container(
                    mode_switch(vertical=True), right=118, top=0, bottom=0, alignment=ft.Alignment.CENTER
                ),
            ]
            if zc is not None:
                out.append(ft.Container(zc, right=200, top=0, bottom=0, alignment=ft.Alignment.CENTER))
            extra = [c for c in (note, open_) if c is not None]
            if extra:
                out.append(
                    ft.Container(
                        ft.Column(
                            extra, spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        left=12,
                        right=260,
                        bottom=12,
                        alignment=ft.Alignment.BOTTOM_CENTER,
                    )
                )
        else:
            rows: list[ft.Control] = [c for c in (open_, note, zc) if c is not None]
            rows += [
                mode_switch(vertical=False),
                ft.Row(
                    [last_thumb(), shutter_button(), done_button()],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ]
            out.append(
                ft.Container(
                    ft.Column(
                        rows, spacing=14, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    left=0,
                    right=0,
                    bottom=0,
                    bgcolor=SHADE,
                    padding=ft.Padding.only(top=12, bottom=20),
                )
            )
        return out

    preview = ft.GestureDetector(content=camera, expand=True)
    stack = ft.Stack(
        [
            ft.Container(
                preview,
                left=0,
                top=0,
                right=0,
                bottom=0,
                bgcolor=ft.Colors.BLACK,
                alignment=ft.Alignment.CENTER,
            )
        ],
        expand=True,
    )

    def redraw() -> None:
        if st["left"]:
            return
        stack.controls[1:] = overlays()
        page.update()

    def say(text: str | None, error: bool = False) -> None:
        st["note"], st["error"] = text or "", error

    # ---- 位置
    async def locate() -> dict | None:
        try:
            pos = await asyncio.wait_for(geo.get_current_position(), POSITION_WAIT_S)
        except Exception:  # noqa: BLE001  位置の部品は端末ごとに違う例外を投げる。取れなかった、で扱う
            return None
        return position_fields(pos)

    async def retry_position(e=None) -> None:
        sess.position = await locate() or sess.position
        say(None if sess.position else t("capture_no_position"), error=sess.position is None)
        redraw()

    # ---- カメラ
    async def open_camera(e=None) -> None:
        say(None)
        st["busy"] = True
        redraw()
        try:
            granted = await geo.request_permission()
            if granted in (
                fg.GeolocatorPermissionStatus.DENIED,
                fg.GeolocatorPermissionStatus.DENIED_FOREVER,
            ):
                raise RuntimeError(t("capture_location_denied"))
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
            try:
                lo, hi = await camera.get_min_zoom_level(), await camera.get_max_zoom_level()
                st["lo"], st["hi"] = float(lo), float(min(hi, 10.0))
                start = clamp(1.0, st["lo"], st["hi"])  # 標準のカメラと同じく 1× から
                await camera.set_zoom_level(start)
                st["zoom"] = st["zoom_sent"] = start
            except Exception:  # noqa: BLE001  倍率を持たない機種は、印を出さない
                st["lo"] = st["hi"] = 1.0
        except Exception as ex:  # noqa: BLE001  許しが無い、カメラが無い、を本人に見せる
            say(str(ex) or t("capture_no_camera"), error=True)
        st["busy"] = False
        redraw()
        if sess.ready and sess.position is None:
            await retry_position()

    async def apply_zoom(z: float) -> None:
        if st["zooming"]:
            return
        st["zooming"] = True
        try:
            await camera.set_zoom_level(z)
            st["zoom_sent"] = z
        except Exception:  # noqa: BLE001, S110  倍率を変えられない時はそのまま
            pass
        finally:
            st["zooming"] = False

    async def zoom_to(z: float) -> None:
        st["zoom"] = clamp(z, st["lo"], st["hi"])
        await apply_zoom(st["zoom"])
        redraw()

    def pinch_start(e) -> None:
        st["pinch_from"] = st["zoom"]

    def pinch(e) -> None:
        if not sess.ready or st["hi"] <= st["lo"] or e.pointer_count < 2:
            return
        z = clamp(st["pinch_from"] * float(e.scale), st["lo"], st["hi"])
        st["zoom"] = z
        if abs(z - st["zoom_sent"]) >= 0.05:
            page.run_task(apply_zoom, z)
            redraw()

    def pinch_end(e) -> None:
        if abs(st["zoom"] - st["zoom_sent"]) > 1e-3:
            page.run_task(zoom_to, st["zoom"])

    preview.on_scale_start, preview.on_scale_update, preview.on_scale_end = pinch_start, pinch, pinch_end

    # ---- 撮る
    async def shoot(e=None) -> None:
        say(None)
        st["busy"] = True
        redraw()
        try:
            data = await camera.take_picture()
            sess.add(data, await locate())
        except photos.PhotoError as ex:
            say(
                t(ex.word) if ex.word.startswith("capture_") or ex.word == "too_many_photos" else str(ex),
                True,
            )
        except Exception as ex:  # noqa: BLE001
            say(str(ex) or t("capture_no_camera"), error=True)
        st["busy"] = False
        redraw()

    def switch(video: bool) -> None:
        st["video"] = video
        say(None)
        redraw()

    async def tick() -> None:
        while st["recording"] and not st["left"]:
            redraw()
            await asyncio.sleep(1)

    async def toggle_record(e=None) -> None:
        say(None)
        st["busy"] = True
        redraw()
        try:
            if not st["recording"]:
                try:
                    await camera.prepare_for_video_recording()
                except Exception:  # noqa: BLE001, S110  要らない端末もある
                    pass
                await camera.start_video_recording()
                st["recording"], st["rec_start"] = True, time.monotonic()
                page.run_task(tick)
                page.run_task(retry_position)
            else:
                data = await camera.stop_video_recording()
                st["recording"] = False
                path = await asyncio.to_thread(keep_video, app.folder.root, data, sess.position)
                sess.add_video(path)
        except Exception as ex:  # noqa: BLE001  録れない機種、許しが無い、を本人に見せる
            st["recording"] = False
            say(str(ex) or t("capture_no_camera"), error=True)
        st["busy"] = False
        redraw()

    # ---- 見返す、消す
    def review(i: int) -> None:
        if not sess.shots:
            return
        i = max(0, min(i, len(sess.shots) - 1))
        shot = sess.shots[i]
        w = (getattr(page, "width", None) or 400) - 40
        h = (getattr(page, "height", None) or 700) * 0.6
        body: ft.Control = (
            ft.Image(src=photos.shrink(shot.path, max_side=1600), fit=ft.BoxFit.CONTAIN, width=w, height=h)
            if shot.kind == "photo"
            else ft.Container(
                ft.Column(
                    [
                        ft.Icon(ft.Icons.VIDEOCAM, size=64, color=WHITE),
                        ft.Text(
                            shot.path.stem[:2] + ":" + shot.path.stem[2:4] + ":" + shot.path.stem[4:6],
                            color=WHITE,
                            size=16,
                        ),
                        ft.Text(
                            f"{shot.path.stat().st_size / 1e6:.1f} MB" if shot.path.exists() else "",
                            color=WHITE,
                            size=13,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    tight=True,
                ),
                width=w,
                height=h * 0.6,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
                alignment=ft.Alignment.CENTER,
            )
        )

        def close(e=None) -> None:
            page.pop_dialog()

        def step(d: int):
            def h_(e) -> None:
                close()
                review(i + d)

            return h_

        def delete(e) -> None:
            close()
            sess.remove(shot)
            redraw()

            def undo(e2) -> None:
                sess.undo(shot)
                redraw()

            page.show_dialog(
                ft.SnackBar(
                    ft.Text(t("capture_deleted")), action=t("capture_undo"), on_action=undo, duration=6000
                )
            )

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(f"{i + 1} / {len(sess.shots)}", size=14),
                content=body,
                inset_padding=ft.Padding.all(12),
                content_padding=ft.Padding.all(8),
                actions=[
                    ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=step(-1), disabled=i == 0),
                    ft.IconButton(
                        ft.Icons.CHEVRON_RIGHT, on_click=step(1), disabled=i >= len(sess.shots) - 1
                    ),
                    ft.TextButton(t("capture_delete"), icon=ft.Icons.DELETE_OUTLINE, on_click=delete),
                    ft.TextButton(t("form_close"), on_click=close),
                ],
                actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

    # ---- 出る
    def leave() -> None:
        st["left"] = True
        page.on_resize = None

    async def finish(e=None) -> None:
        leave()
        await on_done(sess.paths())

    async def go_back(e=None) -> None:
        if st["recording"]:
            await toggle_record()
        n = len(sess.photos())
        if not n:
            leave()
            await on_cancel()
            return

        async def make(e2) -> None:
            page.pop_dialog()
            await finish()

        async def drop(e2) -> None:
            page.pop_dialog()
            leave()
            await on_cancel()

        page.show_dialog(
            ft.AlertDialog(
                content=ft.Text(t("capture_leave", n=n)),
                actions=[
                    ft.TextButton(t("capture_leave_drop"), on_click=drop),
                    ft.FilledButton(t("capture_done", n=n), on_click=make),
                ],
            )
        )

    async def back_gesture(e) -> None:
        """端末の「戻る」（下の線を横に払う、戻るボタン）。アプリを閉じずに、話すへ戻る。"""
        await e.control.confirm_pop(False)
        await go_back()

    page.on_resize = lambda e: redraw()

    async def start() -> None:
        await asyncio.sleep(0.3)  # カメラの部品が画面に載ってから
        if not sess.ready and not st["left"]:
            await open_camera()

    stack.controls[1:] = overlays()
    page.run_task(start)
    return ft.View(
        route="/",
        controls=[ft.SafeArea(stack, expand=True)],
        bgcolor=ft.Colors.BLACK,
        padding=0,
        can_pop=False,
        on_confirm_pop=back_gesture,
    )
