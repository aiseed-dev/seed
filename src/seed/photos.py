# SPDX-License-Identifier: AGPL-3.0-or-later
"""写真。EXIF の座標と時刻、縮小、EXIF の除去、フォルダーへの取り込み。ネットは使わない。

本人の photos/ には写真をそのまま写す（EXIF の座標も本人の物）。サーバーへ送るのは shrink() の
物だけで、EXIF は付けない（設計書 §9）。
"""

from __future__ import annotations

import datetime as dt
import io
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

from . import keep as keep_mod
from .records import Folder, Observation

MAX_SIDE = 1568  # Claude の画像の長辺の目安
QUALITY = 85
HEIC_SUFFIXES = (".heic", ".heif")
EARTH_R = 6_371_000.0


class PhotoError(Exception):
    """本人に見せる一文。word は表示の語（app/strings.py）の鍵。"""

    def __init__(self, word: str, path: Path | str, message: str) -> None:
        super().__init__(f"{Path(path).name}: {message}")
        self.word = word
        self.path = Path(path)


COMPASS = {
    "ja": ("北", "北東", "東", "南東", "南", "南西", "西", "北西"),
    "en": ("N", "NE", "E", "SE", "S", "SW", "W", "NW"),
}


def direction_word(heading: float | None, language: str = "en") -> str | None:
    """撮った方角（度、北 0、時計回り）を八方位の語に。無ければ None。"""
    if heading is None:
        return None
    words = COMPASS.get(language, COMPASS["en"])
    return words[int(((heading % 360) + 22.5) // 45) % 8]


@dataclass
class PhotoInfo:
    lat: float | None
    lon: float | None
    taken: dt.datetime | None
    heading: float | None = None  # 撮った方角（EXIF GPSImgDirection、度）。iPhone などが書く

    @property
    def has_coord(self) -> bool:
        return self.lat is not None and self.lon is not None


def heic_ready() -> bool:
    """iPhone の HEIC を Pillow で開けるようにする。pillow-heif が無ければ False。"""
    try:
        import pillow_heif
    except ImportError:
        return False
    pillow_heif.register_heif_opener()
    return True


def _open(path: Path) -> Image.Image:
    path = Path(path)
    if path.suffix.lower() in HEIC_SUFFIXES and not heic_ready():
        raise PhotoError(
            "heic",
            path,
            "HEIC needs pillow-heif (pip install 'seed-farm[heic]'), "
            "or set the camera to JPEG ('Most Compatible').",
        )
    try:
        return Image.open(path)
    except UnidentifiedImageError as e:
        raise PhotoError("not_image", path, "not an image Pillow can read") from e
    except OSError as e:
        raise PhotoError("not_image", path, str(e)) from e


def _degrees(dms, ref) -> float | None:
    """GPS の (度, 分, 秒) と N/S/E/W → 十進の度。"""
    try:
        d, m, s = (float(x) for x in dms)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    v = d + m / 60 + s / 3600
    if isinstance(ref, bytes):
        ref = ref.decode("ascii", "ignore")
    return -v if str(ref).upper() in ("S", "W") else v


def _taken(exif: Image.Exif) -> dt.datetime | None:
    sub = exif.get_ifd(ExifTags.IFD.Exif)
    for raw in (sub.get(ExifTags.Base.DateTimeOriginal), exif.get(ExifTags.Base.DateTime)):
        if raw:
            try:
                return dt.datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
    return None


def exif_info(path: Path | str) -> PhotoInfo:
    """座標と撮った時刻。無い物は None。"""
    with _open(Path(path)) as img:
        exif = img.getexif()
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        lat = lon = None
        if gps.get(2) and gps.get(4):
            lat = _degrees(gps[2], gps.get(1, "N"))
            lon = _degrees(gps[4], gps.get(3, "E"))
            if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                lat = lon = None
        heading = None
        try:
            if gps.get(17) is not None:  # GPSImgDirection
                heading = float(gps[17])
                if not (0 <= heading < 360):
                    heading = None
        except (TypeError, ValueError, ZeroDivisionError):
            heading = None
        return PhotoInfo(lat, lon, _taken(exif), heading)


def _dms(value: float) -> tuple:
    """十進の度 → EXIF の (度, 分, 秒)。秒は 1/10000 まで（緯度で約 3 mm）。"""
    from PIL.TiffImagePlugin import IFDRational

    v = abs(value)
    d = int(v)
    m = int((v - d) * 60)
    sec = round(((v - d) * 60 - m) * 60 * 10000)
    return (IFDRational(d, 1), IFDRational(m, 1), IFDRational(sec, 10000))


def stamp(
    jpeg: bytes,
    lat: float,
    lon: float,
    when: dt.datetime | None = None,
    altitude: float | None = None,
    heading: float | None = None,
    accuracy: float | None = None,
) -> bytes:
    """アプリのカメラで撮った写真（JPEG）に、撮った所と時刻を EXIF で書き込む。

    アプリのカメラの写真には座標が入らないので、撮った時に端末から取った位置をここで書く。
    書いた後は、電話のカメラの写真と同じに読める（exif_info）。画は圧縮し直さない（量子化の表を保つ）。
    """
    from PIL.TiffImagePlugin import IFDRational

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise PhotoError("not_image", "shot.jpg", "coordinates out of range")
    try:
        img = Image.open(io.BytesIO(jpeg))
        img.load()
    except (OSError, ValueError) as e:
        raise PhotoError("not_image", "shot.jpg", "not a photo") from e
    exif = img.getexif()
    gps: dict = {1: "N" if lat >= 0 else "S", 2: _dms(lat), 3: "E" if lon >= 0 else "W", 4: _dms(lon)}
    if altitude is not None:
        gps[5] = b"\x00" if altitude >= 0 else b"\x01"
        gps[6] = IFDRational(round(abs(altitude) * 100), 100)
    if heading is not None:
        gps[16] = "T"
        gps[17] = IFDRational(round((heading % 360) * 100), 100)
    if accuracy is not None and accuracy >= 0:
        gps[31] = IFDRational(round(accuracy * 100), 100)  # GPSHPositioningError（m）
    exif[ExifTags.IFD.GPSInfo] = gps
    if when is not None:
        text = when.strftime("%Y:%m:%d %H:%M:%S")
        sub = dict(exif.get_ifd(ExifTags.IFD.Exif))
        sub[ExifTags.Base.DateTimeOriginal] = text
        exif[ExifTags.IFD.Exif] = sub
        exif[ExifTags.Base.DateTime] = text
    out = io.BytesIO()
    if img.format == "JPEG":
        img.save(out, "JPEG", exif=exif, quality="keep", subsampling="keep")
    else:
        img.convert("RGB").save(out, "JPEG", exif=exif, quality=QUALITY)
    return out.getvalue()


def shrink(path: Path | str, max_side: int = MAX_SIDE, quality: int = QUALITY) -> bytes:
    """向きを直してから長辺 max_side に縮めた JPEG。EXIF は付けない。"""
    with _open(Path(path)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
        return buf.getvalue()


def strip_exif(src: Path | str, dst: Path | str) -> None:
    """EXIF（座標を含む）を除いた写しを作る。向きは画素に焼き込む。公開に一枚付けるとき用。"""
    with _open(Path(src)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        clean = Image.new(img.mode, img.size)
        clean.paste(img)
        clean.save(dst, "JPEG", quality=95)


def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(h))


def center_and_extent(points: list[tuple[float, float]]) -> tuple[tuple[float, float], float]:
    """重心と、重心から最も遠い点までの距離の 2 倍（m）。畑一枚の広さなので平均で足りる。"""
    if not points:
        raise ValueError("座標が一つも無い")
    center = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    return center, 2 * max(_distance_m(center, p) for p in points)


FAR_M = 50.0


def far_photos(rel_paths: list[str], infos: list[PhotoInfo], limit_m: float = FAR_M) -> list[tuple[str, int]]:
    """ほかの写真の真ん中（中央値）から limit_m より離れた写真と、その距離（m）。

    一枚だけ座標が飛んでいると、重心と広がりがその一枚で広がる。本人に、別の場所なら別の観察に
    分けるよう伝えるための物。座標のある写真が 3 枚未満なら空。
    """
    pts = [(r, (i.lat, i.lon)) for r, i in zip(rel_paths, infos, strict=True) if i.has_coord]
    if len(pts) < 3:
        return []
    lats = sorted(p[1][0] for p in pts)
    lons = sorted(p[1][1] for p in pts)
    mid = (lats[len(lats) // 2], lons[len(lons) // 2])
    out = []
    for r, pt in pts:
        d = _distance_m(mid, pt)
        if d > limit_m:
            out.append((r, round(d)))
    return out


def location(infos: list[PhotoInfo]) -> dict | None:
    """観察の前書きの location（記録の形 §3）。座標が無ければ None。

    ほかの写真の中央値から FAR_M より離れた座標（GPS の飛び。撮り始めの一、二枚に多い）は重心と
    広がりに入れず、数を `excluded` に書く。観察には残る（far_photos が本人に知らせる）。
    """
    pts = [(i.lat, i.lon) for i in infos if i.has_coord]
    if not pts:
        return None
    far = {
        r for r, _ in far_photos([str(i) for i in range(len(pts))], [PhotoInfo(a, b, None) for a, b in pts])
    }
    used = [p for i, p in enumerate(pts) if str(i) not in far]
    (lat, lon), extent = center_and_extent(used)
    out = {"center": [round(lat, 6), round(lon, 6)], "points": len(used), "extent_m": round(extent)}
    if far:
        out["excluded"] = len(far)
    return out


def _when(path: Path, info: PhotoInfo) -> dt.datetime:
    return info.taken or dt.datetime.fromtimestamp(path.stat().st_mtime)


def import_photos(folder: Folder, paths: list[Path | str], keep: str = keep_mod.DEFAULT) -> list[str]:
    """写真を photos/<YYYY-MM-DD>/<HHMMSS>.jpg に写し、撮った順の相対の道を返す。

    日と時刻は EXIF、無ければファイルの時刻。同じ秒の写真は -1, -2 を付ける。同じ中身がもうあれば写さずにその道を返す。
    keep（keep.py）で写し方が変わる: text は読み用の大きさに縮める（EXIF は残す）、photos 以上は JPEG はそのまま、
    ほかの形は元の大きさの JPEG に直す。research はさらに、写した JPEG と中身の違う元（HEIC など）を originals/ に残す。
    """
    items = []
    for p in map(Path, paths):
        info = exif_info(p)  # 読めない物はここで止まる
        items.append((_when(p, info), p))
    out = []
    for when, p in sorted(items, key=lambda x: x[0]):
        day = folder.photos / when.strftime("%Y-%m-%d")
        day.mkdir(parents=True, exist_ok=True)
        stem = when.strftime("%H%M%S")
        # 同じ中身かは、写す形（JPEG）で比べる。HEIC を二度入れても増えない
        payload = _as_jpeg(p) if keep_mod.full_jpeg(keep) else _read_size(p)
        dst = day / f"{stem}.jpg"
        n = 0
        while dst.exists() and not _same(dst, payload):
            n += 1
            dst = day / f"{stem}-{n}.jpg"
        if not dst.exists():
            dst.write_bytes(payload)
        if keep_mod.originals(keep):
            _keep_original(folder, p, dst, payload)
        out.append(dst.relative_to(folder.root).as_posix())
    return out


def _as_jpeg(p: Path) -> bytes:
    """JPEG はそのままの中身。ほかの形（HEIC、PNG）は EXIF を付けたまま JPEG に直した中身。"""
    with _open(p) as img:
        if img.format == "JPEG":
            return p.read_bytes()
        exif = img.getexif()
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=95, exif=exif)
        return buf.getvalue()


def _read_size(p: Path, max_side: int = keep_mod.READ_SIDE) -> bytes:
    """読み用の大きさ（長辺 max_side）の JPEG。EXIF（座標、時刻、向き）はそのまま付ける。keep が text のとき。"""
    with _open(p) as img:
        exif = img.getexif()
        if max(img.size) <= max_side and img.format == "JPEG":
            return p.read_bytes()
        img = img.convert("RGB")
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=QUALITY, exif=exif)
        return buf.getvalue()


def _keep_original(folder: Folder, src: Path, dst: Path, payload: bytes) -> Path | None:
    """写した JPEG と中身が違う元（HEIC など）を originals/<日>/<同じ名>.<元の拡張子> に写す。同じなら写さない。"""
    if src.suffix.lower() in (".jpg", ".jpeg") and src.read_bytes() == payload:
        return None
    orig = folder.originals / dst.parent.name / (dst.stem + src.suffix.lower())
    if not orig.exists():
        orig.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, orig)
    return orig


def _same(a: Path, payload: bytes) -> bool:
    return a.stat().st_size == len(payload) and a.read_bytes() == payload


def far_in(folder: Folder, obs: Observation, limit_m: float = FAR_M) -> list[tuple[str, int]]:
    """観察の写真のうち、ほかから離れた物（far_photos を観察に対して）。"""
    infos = [exif_info(folder.root / r) for r in obs.photos]
    return far_photos(list(obs.photos), infos, limit_m)


def observation_for(folder: Folder, rel_paths: list[str], language: str) -> Observation:
    """取り込んだ写真から観察の骨（前書きだけ）を作る。同じ名の観察があればそれを読んで返す。

    日と時刻は最初の写真（撮った順）の物。読みはまだ無い（model は None）。
    """
    infos = [exif_info(folder.root / r) for r in rel_paths]
    first = _when(folder.root / rel_paths[0], infos[0])
    obs = Observation(date=first.strftime("%Y-%m-%d"), time=first.strftime("%H:%M:%S"), language=language)
    path = folder.observation_path(obs)
    if path.exists():
        obs = Observation.read(path)
        obs.photos = list(dict.fromkeys(obs.photos + list(rel_paths)))
        infos = [exif_info(folder.root / r) for r in obs.photos]
    else:
        obs.photos = list(rel_paths)
    obs.location = location(infos)
    return obs


def shrunk(folder: Folder, obs: Observation) -> list[bytes]:
    """観察の写真を、サーバーへ送る形（縮小、EXIF 無し）に。"""
    return [shrink(folder.root / r) for r in obs.photos]
