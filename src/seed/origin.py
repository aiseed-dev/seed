# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed origin — 畑の成り立ちの動画（設計書 §15）。

座標から、公開の地図と空中写真のタイルを引いて順に並べ、字幕（place.md の data 行の事実）と出典を付ける。
AI は呼ばない。絵も作らない（作れば出典の無い物になる。作者 2026-11-04）。

- タイルの道は fieldnotes-farm 0.2.0 の lookup_jp.py（GSI、PORTAL、SOIL_TILE）と同じ。fieldnotes は任意の依存なので、
  ここに写して持つ。
- 取り方は差し替えられる（Fetch: url → bytes、404 は None、通信の失敗は例外）。テストは偽のタイルを渡す。
- 出力は本人のフォルダーの中だけ（origin/<日>/、タイルのキャッシュは origin/tiles/）。座標は書かない。
- 文は app/strings.py（ja と en）。data 行の英語の枠は lookup_ja で日本語にする。
"""

from __future__ import annotations

import datetime as dt
import io
import math
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from . import __version__, lookup_ja
from . import records as R
from .app.strings import s

TILE = 256
EARTH_R = 6378137.0  # Web メルカトルの球の半径
MAX_LAT = 85.05112878
BUDGET = 200  # 一回の実行で取るタイルの上限（キャッシュにある物は数えない）
PAUSE = 0.2  # タイルの間（秒）
DEFAULT_SIZE = (1280, 720)
BAND = 160  # 字幕の帯の高さ（720 のとき）
BASE_WIDTH = 640  # 地図の窓の幅（タイルの画素）。出力の幅をこれに合わせて拡げる（1280 なら 2 倍）
SECONDS = 3.0
FPS = 24
FADE = 0.5  # mp4 の場面の間の重ね（秒）
TERMS_CHECKED = "2026-11-04"  # 利用の条件を Claude が読んだ日
USER_AGENT = f"seed/{__version__} (+https://github.com/aiseed-dev/seed)"

GSI = "https://cyberjapandata.gsi.go.jp/xyz"
PORTAL = "https://disaportaldata.gsi.go.jp/raster"
SOIL = "https://soil-inventory.rad.naro.go.jp/tile/figure"

FONTS = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/bizud-gothic/BIZUDPGothic-Regular.ttf",
)

# 色
BG = (24, 24, 24)
TEXT = (245, 245, 245)
DIM = (185, 185, 185)
MARK = (214, 39, 40)
WHITE = (255, 255, 255)


@dataclass(frozen=True)
class Layer:
    """タイルの層。id はキャッシュのフォルダー名。"""

    id: str
    url: str  # {z} {x} {y}

    def tile_url(self, z: int, x: int, y: int) -> str:
        return self.url.format(z=z, x=x, y=y)


def _gsi(layer: str, ext: str = "png") -> Layer:
    return Layer(layer, f"{GSI}/{layer}/{{z}}/{{x}}/{{y}}.{ext}")


def _portal(layer: str) -> Layer:
    return Layer(layer, f"{PORTAL}/{layer}/{{z}}/{{x}}/{{y}}.png")


# 地理院タイル一覧（https://maps.gsi.go.jp/development/ichiran.html、2026-11-04 に読んだ）
STD = _gsi("std")  # 標準地図。基本測量成果（電子地形図（タイル））
RELIEF = _gsi("relief")  # 色別標高図 z5〜15
LANDFORMS = (  # 地形分類。その場所にある最初の物
    _gsi("lcmfc2"),  # 治水地形分類図 z11〜16
    _gsi("lcm25k_2012"),  # 数値地図25000（土地条件）z10〜16。基本測量成果
    _gsi("lcm25k"),  # 土地条件図（初期整備版）z14〜16。基本測量成果
)
FLOOD = _portal("01_flood_l2_shinsuishin_data")  # 洪水浸水想定区域（想定最大規模）z2〜17
SEDIMENT = (  # 土砂災害警戒区域（土石流、急傾斜地の崩壊、地すべり）z2〜17
    _portal("05_dosekiryukeikaikuiki"),
    _portal("05_kyukeishakeikaikuiki"),
    _portal("05_jisuberikeikaikuiki"),
)
SOIL_LAYER = Layer(
    "soil", f"{SOIL}/{{z}}/{{x}}/{{y}}.png"
)  # 農研機構 日本土壌インベントリー z15 が最も細かい
# 年代別の写真（古い順）。(層, 年代の語の鍵)。ort_riku10 は 1936〜1942 年頃で、東京 23 区と大阪だけ
PHOTOS = (
    (_gsi("ort_riku10"), "1936"),  # z13〜18
    (_gsi("ort_USA10"), "1945"),  # z10〜17
    (_gsi("ort_old10"), "1961"),  # z10〜17
    (_gsi("gazo1", "jpg"), "1974"),  # z10〜17
    (_gsi("gazo2", "jpg"), "1979"),
    (_gsi("gazo3", "jpg"), "1984"),
    (_gsi("gazo4", "jpg"), "1987"),
    (_gsi("seamlessphoto", "jpg"), "latest"),  # z14〜18
)
Z_STD = (11, 13, 15)
Z_RELIEF = 13
Z_LANDFORM = 15
Z_HAZARD = 14
Z_SOIL = 15
Z_PHOTO = 16
Z_HISTORY = 13
HISTORY_MAX = 4


# ---------------------------------------------------------------- 座標（Web メルカトル）


def world_px(lat: float, lon: float, z: int) -> tuple[float, float]:
    """緯度経度 → ズーム z の世界の画素（左上が 0, 0。一辺 256·2^z）。"""
    n = TILE * 2**z
    lat = max(-MAX_LAT, min(MAX_LAT, lat))
    phi = math.radians(lat)
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(phi) + 1.0 / math.cos(phi)) / math.pi) / 2.0 * n
    return x, y


def tile_of(lat: float, lon: float, z: int) -> tuple[int, int, float, float]:
    """緯度経度 → (タイルの x, y, タイルの中の画素 px, py)。"""
    x, y = world_px(lat, lon, z)
    tx, ty = int(x // TILE), int(y // TILE)
    return tx, ty, x - tx * TILE, y - ty * TILE


def metres_per_px(lat: float, z: int) -> float:
    return 2 * math.pi * EARTH_R * math.cos(math.radians(lat)) / (TILE * 2**z)


# ---------------------------------------------------------------- タイルを取る


Fetch = Callable[[str], "bytes | None"]  # 404 は None。通信の失敗は例外


class OverBudget(Exception):
    pass


class FetchFailed(Exception):
    pass


class HttpFetch:
    """httpx でタイルを取る。間に PAUSE 秒。"""

    def __init__(self, pause: float = PAUSE, timeout: float = 15.0) -> None:
        import httpx

        self._httpx = httpx
        self.client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
        self.pause = pause
        self._last = 0.0

    def __call__(self, url: str) -> bytes | None:
        wait = self._last + self.pause - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            r = self.client.get(url)
        finally:
            self._last = time.monotonic()
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.content

    def close(self) -> None:
        self.client.close()


class Tiles:
    """タイルのキャッシュ <cache>/<layer>/<z>/<x>/<y>.png。404 は <y>.none を置いて二度と取らない。"""

    def __init__(self, cache: Path, fetch: Fetch, budget: int | None = None) -> None:
        self.cache = Path(cache)
        self.fetch = fetch
        self.budget = BUDGET if budget is None else budget
        self.fetched = 0  # ネットから取った数（404 も含む）
        self.cached = 0  # キャッシュから読んだ数
        self.missing = 0  # 404（キャッシュの印も含む）

    def get(self, layer: Layer, z: int, x: int, y: int) -> Image.Image | None:
        png = self.cache / layer.id / str(z) / str(x) / f"{y}.png"
        none = png.with_suffix(".none")
        if png.exists():
            self.cached += 1
            with Image.open(png) as im:
                return im.convert("RGBA")
        if none.exists():
            self.cached += 1
            self.missing += 1
            return None
        if self.fetched >= self.budget:
            raise OverBudget
        self.fetched += 1
        try:
            data = self.fetch(layer.tile_url(z, x, y))
        except Exception as e:  # 通信の失敗はその場面を省くだけ
            raise FetchFailed(type(e).__name__) from e
        png.parent.mkdir(parents=True, exist_ok=True)
        if data is None:
            none.touch()
            self.missing += 1
            return None
        try:
            with Image.open(io.BytesIO(data)) as im:
                img = im.convert("RGBA")
        except (UnidentifiedImageError, OSError) as e:
            raise FetchFailed("not an image") from e
        img.save(png)
        return img


# ---------------------------------------------------------------- 地図の窓


@dataclass
class View:
    """中心と大きさ。scale は出力の画素 / タイルの画素。"""

    lat: float
    lon: float
    w: int
    h: int

    @property
    def scale(self) -> float:
        return self.w / BASE_WIDTH

    def px_per_m(self, z: int) -> float:
        return self.scale / metres_per_px(self.lat, z)


def transparent(img: Image.Image) -> bool:
    return img.getchannel("A").getextrema()[1] == 0


def mosaic(tiles: Tiles, layer: Layer, view: View, z: int) -> tuple[Image.Image | None, str | None]:
    """中心の周りの要るタイルだけをつなぎ、窓を切り出して (w, h) に拡げる。

    返すのは (画像 RGBA, None) か (None, 理由)。理由は missing（全部 404）、empty（全部透明）。
    OverBudget と FetchFailed はそのまま上げる。
    """
    cx, cy = world_px(view.lat, view.lon, z)
    sw, sh = view.w / view.scale, view.h / view.scale
    x0, y0 = cx - sw / 2, cy - sh / 2
    tx0, ty0 = math.floor(x0 / TILE), math.floor(y0 / TILE)
    tx1, ty1 = math.floor((x0 + sw) / TILE), math.floor((y0 + sh) / TILE)
    n = 2**z
    canvas = Image.new("RGBA", ((tx1 - tx0 + 1) * TILE, (ty1 - ty0 + 1) * TILE), (0, 0, 0, 0))
    got = filled = 0
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            if not 0 <= ty < n:
                continue
            img = tiles.get(layer, z, tx % n, ty)
            if img is None:
                continue
            got += 1
            if not transparent(img):
                filled += 1
                canvas.paste(img, ((tx - tx0) * TILE, (ty - ty0) * TILE))
    if not got:
        return None, "missing"
    if not filled:
        return None, "empty"
    left, top = x0 - tx0 * TILE, y0 - ty0 * TILE
    box = (round(left), round(top), round(left + sw), round(top + sh))
    return canvas.crop(box).resize((view.w, view.h), Image.Resampling.LANCZOS), None


def has_at_center(img: Image.Image, r: int = 2) -> bool:
    """中心の (2r+1)² 画素のどれかに色があるか。"""
    w, h = img.size
    a = img.getchannel("A").crop((w // 2 - r, h // 2 - r, w // 2 + r + 1, h // 2 + r + 1))
    return a.getextrema()[1] > 0


def over(base: Image.Image, top: Image.Image, alpha: float = 0.75) -> Image.Image:
    """base に top を alpha で重ねる。"""
    top = top.copy()
    top.putalpha(top.getchannel("A").point(lambda v: int(v * alpha)))
    return Image.alpha_composite(base, top)


# ---------------------------------------------------------------- data 行


DATA_SRC_RE = re.compile(r"^(?P<body>.*?)（出典: (?P<src>.+?)、確認日 (?P<day>\d{4}-\d{2}-\d{2})）$")
_DIRS = "N|NE|E|SE|S|SW|W|NW"
HIST_EN_RE = re.compile(
    rf"^(?P<name>.+?) \((?P<kind>[\w:]+), (?P<d>[\d.,]+) (?P<u>km|m) (?P<dir>{_DIRS})(?:; .+)?\)$"
)
_JA_DIRS = {v: k for k, v in lookup_ja.DIRECTIONS.items()}
HIST_JA_RE = re.compile(
    r"^(?P<name>.+?)（(?P<kind>[^、（）]+)、(?P<d>[\d.,]+) (?P<u>km|m) "
    rf"(?P<dir>{'|'.join(sorted(_JA_DIRS, key=len, reverse=True))})(?:。.+)?）$"
)
BEARING = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}


@dataclass
class Fact:
    """data 行の一つ。body は本人の言語にした文。"""

    key: str
    body: str
    raw: str
    src: str
    day: str

    @property
    def source(self) -> str:
        return f"{self.src}（{self.day}）"


def facts(lines: list[R.Line], language: str) -> list[Fact]:
    """place.md の data 行 → Fact。出典の付いていない行は使わない。"""
    out = []
    for l in lines:
        m = DATA_SRC_RE.match(l.text.strip())
        if not m:
            continue
        raw = m["body"].strip()
        body = lookup_ja.to_ja(raw) if lookup_ja.is_ja(language) else raw
        out.append(Fact(l.key, body, raw, m["src"].strip(), m["day"]))
    return out


@dataclass
class Place:
    """史跡の一つ。距離（m）と方位だけ。正確な座標は無い。"""

    name: str
    kind: str
    metres: float
    direction: str  # N, NE, …
    dist_text: str  # "2.1 km"


def history_places(fs: list[Fact]) -> list[Place]:
    out = []
    for f in fs:
        if f.key != "history":
            continue
        m = HIST_EN_RE.match(f.raw)
        direction = m["dir"] if m else None
        if not m:
            m = HIST_JA_RE.match(f.raw)
            direction = _JA_DIRS.get(m["dir"]) if m else None
        if not m or not direction:
            continue
        d = float(m["d"].replace(",", ""))
        out.append(
            Place(m["name"], m["kind"], d * (1000 if m["u"] == "km" else 1), direction, f"{m['d']} {m['u']}")
        )
    return out[:HISTORY_MAX]


def place_label(p: Place, language: str, short: bool = False) -> str:
    """字幕の語（名、種類、約の距離と方位）。short なら地図の上に置く短い物（種類を除く）。"""
    ja = lookup_ja.is_ja(language)
    kind = lookup_ja.KINDS.get(p.kind, p.kind) if ja else p.kind
    direction = lookup_ja.DIRECTIONS[p.direction] if ja else p.direction
    word = "origin_place_short" if short else "origin_place"
    return s(word, language, name=p.name, kind=kind, dist=p.dist_text, dir=direction)


# ---------------------------------------------------------------- 字（フォント）


def find_font(given: str | None = None) -> str | None:
    """--font → Noto Sans CJK（Regular、Bold）→ BIZ UDP ゴシック → fc-list :lang=ja の先頭。無ければ None。"""
    if given:
        return given if Path(given).expanduser().is_file() else None
    for p in FONTS:
        if Path(p).is_file():
            return p
    if shutil.which("fc-list"):
        try:
            got = subprocess.run(
                ["fc-list", ":lang=ja", "file"], capture_output=True, text=True, timeout=10, check=False
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return None
        for line in got.splitlines():
            p = line.strip().rstrip(":").strip()
            if p and Path(p).is_file():
                return p
    return None


class Fonts:
    def __init__(self, path: str | None) -> None:
        self.path = str(Path(path).expanduser()) if path else None
        self._cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

    def get(self, size: int):
        if size not in self._cache:
            if self.path:
                self._cache[size] = ImageFont.truetype(self.path, size, index=0)
            else:
                self._cache[size] = ImageFont.load_default(size=size)
        return self._cache[size]


def wrap(text: str, font, width: float) -> list[str]:
    """一文字ずつ折り返す（日本語）。英語は空白で切れればそこで。"""
    lines: list[str] = []
    cur = ""
    for ch in text:
        if font.getlength(cur + ch) <= width or not cur:
            cur += ch
            continue
        cut = cur.rfind(" ")
        if cut > len(cur) * 0.6 and ch != " ":
            lines.append(cur[:cut].rstrip())
            cur = cur[cut + 1 :] + ch
        else:
            lines.append(cur.rstrip())
            cur = ch.lstrip()
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def fit(texts: list[str], fonts: Fonts, width: float, max_lines: int, sizes: range):
    """大きい字から順に、max_lines に収まる大きさを探す。収まらなければ最小の字で切って「…」。"""
    font, lines = None, []
    for size in sizes:
        font = fonts.get(size)
        lines = [l for t in texts if t for l in wrap(t, font, width)]
        if len(lines) <= max_lines:
            return font, lines
    lines = lines[:max_lines]
    if lines:
        last = lines[-1]
        while last and font.getlength(last + "…") > width:
            last = last[:-1]
        lines[-1] = last + "…"
    return font, lines


# ---------------------------------------------------------------- 一枚の絵


@dataclass
class Frame:
    name: str  # ファイル名の一部（std-z11 など）
    title: str  # 場面の名（本人の言語）
    image: Image.Image  # 地図の部分（RGB、w × map_h）
    caption: list[str] = field(default_factory=list)
    map_source: str = ""
    data_sources: list[str] = field(default_factory=list)


@dataclass
class Skipped:
    name: str
    title: str
    reason: str  # 本人の言語の一文


def draw_mark(img: Image.Image, view: View, z: int | None, extent_m: float | None) -> Image.Image:
    """中心に畑の印。extent_m があれば、その半径の円を薄く。"""
    img = img.convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = img.width / 2, img.height / 2
    r = max(6, round(img.width / 128))
    if extent_m and z is not None:
        er = extent_m * view.px_per_m(z)
        if er > r + 4:
            d.ellipse(
                (cx - er, cy - er, cx + er, cy + er), fill=(255, 255, 255, 60), outline=(*MARK, 200), width=2
            )
    d.ellipse((cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3), outline=(*WHITE, 230), width=3)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*MARK, 255), width=max(3, r // 3))
    return Image.alpha_composite(img, layer)


def nice_length(m: float) -> float:
    """m 以下で、1・2・5 × 10^k の最大の長さ。"""
    k = 10 ** math.floor(math.log10(m))
    for f in (5, 2, 1):
        if f * k <= m:
            return f * k
    return k


def draw_scale(img: Image.Image, view: View, z: int, fonts: Fonts) -> Image.Image:
    """左下に縮尺の棒。"""
    img = img.convert("RGBA")
    ppm = view.px_per_m(z)
    metres = nice_length(img.width / 6 / ppm)
    bar = metres * ppm
    label = f"{metres / 1000:g} km" if metres >= 1000 else f"{metres:g} m"
    font = fonts.get(max(12, round(img.width / 70)))
    pad = round(img.width / 100)
    tw = font.getlength(label)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = pad * 2, img.height - pad * 2
    th = font.size if hasattr(font, "size") else 12
    d.rectangle((x - pad, y - th - pad * 2, x + max(bar, tw) + pad, y + pad), fill=(255, 255, 255, 200))
    d.rectangle((x, y - 4, x + bar, y), fill=(20, 20, 20, 255))
    d.text((x, y - th - pad), label, font=font, fill=(20, 20, 20, 255))
    return Image.alpha_composite(img, layer)


def draw_places(img: Image.Image, view: View, z: int, places: list[Place], language: str, fonts: Fonts):
    """中心から、方位に距離の所へ線と名前。窓の外なら縁で止めて「→」。"""
    img = img.convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = fonts.get(max(12, round(img.width / 60)))
    cx, cy = img.width / 2, img.height / 2
    margin = img.width / 40
    for p in places:
        b = math.radians(BEARING[p.direction])
        dx, dy = math.sin(b), -math.cos(b)
        dist = p.metres * view.px_per_m(z)
        # 窓の縁まで
        lim = min(
            (cx - margin) / abs(dx) if dx else math.inf,
            (cy - margin) / abs(dy) if dy else math.inf,
        )
        inside = dist <= lim
        t = dist if inside else lim
        ex, ey = cx + dx * t, cy + dy * t
        d.line((cx, cy, ex, ey), fill=(60, 60, 60, 230), width=3)
        r = 6
        if inside:
            d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=(*MARK, 255), outline=(*WHITE, 255), width=2)
        label = place_label(p, language, short=True) + ("" if inside else " →")
        tw = font.getlength(label)
        tx = ex + 10 if dx >= 0 else ex - 10 - tw
        tx = max(4, min(img.width - tw - 4, tx))
        ty = max(4, min(img.height - font.size - 8, ey - font.size / 2))
        d.text((tx, ty), label, font=font, fill=(20, 20, 20, 255), stroke_width=3, stroke_fill=(*WHITE, 255))
    return Image.alpha_composite(img, layer)


def fit_photo(path: Path, w: int, h: int) -> Image.Image:
    """本人の写真を地図の枠に収める（切らない）。"""
    from . import photos

    with photos._open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((w, h), Image.Resampling.LANCZOS)
        out = Image.new("RGB", (w, h), BG)
        out.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out


def compose(frame: Frame, size: tuple[int, int], fonts: Fonts, language: str) -> Image.Image:
    """地図と、下の帯（字幕 2 行まで、その下に小さく出典）を一枚に。"""
    w, h = size
    band = h - frame.image.height
    out = Image.new("RGB", (w, h), BG)
    out.paste(frame.image.convert("RGB"), (0, 0))
    d = ImageDraw.Draw(out)
    pad = round(w / 40)
    k = h / 720
    cap_font, cap = fit(frame.caption, fonts, w - pad * 2, 2, range(round(32 * k), round(19 * k) - 1, -1))
    srcs = [s("origin_map_source", language, src=frame.map_source)] if frame.map_source else []
    if frame.data_sources:
        srcs.append(s("origin_data_source", language, src="、".join(dict.fromkeys(frame.data_sources))))
    src_font, src_lines = fit(
        [s("origin_sep", language).join(srcs)],
        fonts,
        w - pad * 2,
        2,
        range(round(18 * k), round(13 * k) - 1, -1),
    )
    cap_h = (cap_font.size + round(8 * k)) if cap_font else 0
    src_h = (src_font.size + round(5 * k)) if src_font else 0
    y = h - band + round(12 * k)
    for line in cap:
        d.text((pad, y), line, font=cap_font, fill=TEXT)
        y += cap_h
    y = max(y + round(4 * k), h - round(10 * k) - src_h * len(src_lines))
    for line in src_lines:
        d.text((pad, y), line, font=src_font, fill=DIM)
        y += src_h
    return out


# ---------------------------------------------------------------- 場面


@dataclass
class Plan:
    """組み立ての材料。"""

    lat: float
    lon: float
    extent_m: float | None
    data: list[R.Line]
    language: str
    photo: Path | None = None  # 本人の写真（一番新しい観察の最初の物）
    photo_date: str | None = None
    photo_skip: str | None = None  # 写真を使わない理由の鍵（no_photo、far_photo）
    size: tuple[int, int] = DEFAULT_SIZE


def map_height(size: tuple[int, int]) -> int:
    """地図の部分の高さ。下の BAND（720 のとき）が字幕の帯。"""
    return size[1] - round(size[1] * BAND / 720)


class Skip(Exception):
    """場面を省く。code は origin_reason_<code> の鍵。"""

    def __init__(self, code: str, **kw) -> None:
        super().__init__(code)
        self.code, self.kw = code, kw


def need(got: tuple[Image.Image | None, str | None]) -> Image.Image:
    """mosaic の結果から画像を取る。無ければ Skip。"""
    img, why = got
    if img is None:
        raise Skip(why or "missing")
    return img


def build(plan: Plan, tiles: Tiles, fonts: Fonts) -> tuple[list[Frame], list[Skipped]]:
    """場面を順に作る。省いた物は Skipped に理由と一緒に。"""
    lg = plan.language
    w = plan.size[0]
    view = View(plan.lat, plan.lon, w, map_height(plan.size))
    fs = facts(plan.data, lg)
    frames: list[Frame] = []
    skipped: list[Skipped] = []

    def of(key: str, word: str | None = None) -> list[Fact]:
        return [f for f in fs if f.key == key and (word is None or word in f.body or word in f.raw)]

    def take(
        name: str,
        title: str,
        make: Callable[[], tuple[Image.Image, str]],
        z: int | None,
        *,
        caption: list[str] | None = None,
        facts_: list[Fact] = (),
        marked: bool = True,
    ) -> None:
        """make() は (地図, 地図の出典)。Skip、OverBudget、FetchFailed なら省く。"""
        try:
            img, source = make()
        except Skip as e:
            skipped.append(Skipped(name, title, s(f"origin_reason_{e.code}", lg, **e.kw)))
            return
        except OverBudget:
            skipped.append(Skipped(name, title, s("origin_reason_budget", lg, budget=tiles.budget)))
            return
        except FetchFailed as e:
            skipped.append(Skipped(name, title, s("origin_reason_failed", lg, detail=str(e))))
            return
        if marked:
            img = draw_mark(img, view, z, plan.extent_m)
        if z is not None:
            img = draw_scale(img, view, z, fonts)
        text = [f.body for f in facts_] if caption is None else caption
        frames.append(Frame(name, title, img.convert("RGB"), text, source, [f.source for f in facts_]))

    def plain(layer: Layer, z: int, source: str):
        return lambda: (need(mosaic(tiles, layer, view, z)), source)

    # 1. 標準地図、引いた所から寄る
    for z in Z_STD:
        take(
            f"std-z{z}",
            s("origin_scene_std", lg, z=z),
            plain(STD, z, s("origin_src_std", lg)),
            z,
            facts_=of("place_name") + of("elevation"),
        )
    # 2. 色別標高図
    take(
        "relief",
        s("origin_scene_relief", lg),
        plain(RELIEF, Z_RELIEF, s("origin_src_relief", lg)),
        Z_RELIEF,
        facts_=of("elevation"),
    )

    # 3. 地形分類。中心に色のある最初の層。どれも中心に色が無ければ、色のある最初の層
    def landform():
        first, codes = None, []
        for layer in LANDFORMS:
            img, why = mosaic(tiles, layer, view, Z_LANDFORM)
            if img is None:
                codes.append(why)
                continue
            source = s(f"origin_src_{layer.id}", lg)
            if has_at_center(img):
                return img, source
            first = first or (img, source)
        if first:
            return first
        raise Skip("missing" if all(c == "missing" for c in codes) else "empty")

    take("landform", s("origin_scene_landform", lg), landform, Z_LANDFORM, facts_=of("landform"))

    # 4. 洪水浸水想定区域、5. 土砂災害警戒区域を標準地図に重ねる。data 行があれば、重ねる色が無くても地図は出す
    def hazard(layers: tuple[Layer, ...], lines: list[Fact], source: str):
        def make():
            base = need(mosaic(tiles, STD, view, Z_HAZARD))
            painted = False
            for layer in layers:
                top, _ = mosaic(tiles, layer, view, Z_HAZARD)
                if top is not None:
                    base, painted = over(base, top), True
            if not painted and not lines:
                raise Skip("empty")
            return base, source

        return make

    flood = of("hazard", "洪水")
    take(
        "flood",
        s("origin_scene_flood", lg),
        hazard((FLOOD,), flood, s("origin_src_flood", lg)),
        Z_HAZARD,
        facts_=flood,
    )
    sediment = of("hazard", "土砂")
    take(
        "sediment",
        s("origin_scene_sediment", lg),
        hazard(SEDIMENT, sediment, s("origin_src_sediment", lg)),
        Z_HAZARD,
        facts_=sediment,
    )

    # 6. 土壌図を標準地図に重ねる（区画の外は透明なので、下の地図が見える）。土壌図の色が無ければ省く
    def soil():
        top = need(mosaic(tiles, SOIL_LAYER, view, Z_SOIL))
        base = need(mosaic(tiles, STD, view, Z_SOIL))
        return over(base, top), s("origin_src_soil", lg)

    take("soil", s("origin_scene_soil", lg), soil, Z_SOIL, facts_=of("soil"))

    # 7〜. 年代別の空中写真（ある年代だけ）
    for layer, era in PHOTOS:
        era_text = s(f"origin_era_{era}", lg)
        title = s("origin_scene_photo", lg, era=era_text)
        source = s("origin_src_latest" if era == "latest" else "origin_src_photo", lg, era=era_text)
        take(f"photo-{era}", title, plain(layer, Z_PHOTO, source), Z_PHOTO, caption=[title])

    # 次. 史跡。点の座標は無いので、中心から方位に距離の所
    places = history_places(fs)

    def history():
        if not places:
            raise Skip("no_lines", key="history")
        img = need(mosaic(tiles, STD, view, Z_HISTORY))
        return draw_places(img, view, Z_HISTORY, places, lg, fonts), s("origin_src_history", lg)

    take(
        "history",
        s("origin_scene_history", lg),
        history,
        Z_HISTORY,
        caption=[s("origin_sep", lg).join(place_label(p, lg) for p in places)],
        facts_=of("history")[:HISTORY_MAX],
    )

    # 最後. 本人の写真（Claude の読みの行は出さない）
    def own():
        if plan.photo is None or plan.photo_skip:
            raise Skip(plan.photo_skip or "no_photo")
        try:
            img = fit_photo(plan.photo, w, view.h)
        except Exception as e:  # 読めない写真は省くだけ
            raise Skip("failed", detail=type(e).__name__) from e
        return img, s("origin_src_own", lg, date=plan.photo_date)

    names = of("place_name")
    take(
        "own-photo",
        s("origin_scene_own", lg),
        own,
        None,
        marked=False,
        caption=[f.body for f in names] + [s("origin_own_caption", lg, date=plan.photo_date)],
        facts_=names,
    )
    return frames, skipped


# ---------------------------------------------------------------- 書き出し


def frame_files(frames: list[Frame]) -> list[str]:
    return [f"{i:02d}-{f.name}.png" for i, f in enumerate(frames, 1)]


def write_frames(images: list[Image.Image], frames: list[Frame], out: Path) -> list[Path]:
    d = out / "frames"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.png"):
        old.unlink()
    paths = []
    for name, img in zip(frame_files(frames), images, strict=True):
        p = d / name
        img.save(p)
        paths.append(p)
    return paths


def ffmpeg_module():
    """imageio-ffmpeg が入っていればそのモジュール、無ければ None。"""
    try:
        import imageio_ffmpeg  # type: ignore[import-not-found]

        imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 — 無い・壊れているときは GIF に落とす
        return None
    return imageio_ffmpeg


def write_mp4(images: list[Image.Image], path: Path, seconds: float, fps: int, fade: float = FADE) -> None:
    mod = ffmpeg_module()
    w, h = images[0].size
    writer = mod.write_frames(
        str(path),
        (w, h),
        fps=fps,
        codec="libx264",
        pix_fmt_out="yuv420p",
        macro_block_size=2,
        output_params=["-crf", "23"],
    )
    writer.send(None)
    hold = max(1, round(seconds * fps))
    n_fade = min(hold // 2, round(fade * fps)) if len(images) > 1 else 0
    for i, img in enumerate(images):
        rest = hold - (n_fade if i + 1 < len(images) else 0)
        data = img.tobytes()
        for _ in range(rest):
            writer.send(data)
        if i + 1 < len(images):
            nxt = images[i + 1]
            for k in range(n_fade):
                writer.send(Image.blend(img, nxt, (k + 1) / (n_fade + 1)).tobytes())
    writer.close()


def write_gif(images: list[Image.Image], path: Path, seconds: float) -> None:
    pal = [im.quantize(256) for im in images]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=round(seconds * 1000), loop=0)


def md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def captions_md(frames: list[Frame], skipped: list[Skipped], language: str, day: str) -> str:
    lg = language
    out = [
        s("origin_md_title", lg, date=day),
        "",
        s("origin_md_about", lg),
        "",
        s("origin_md_private", lg),
        "",
    ]
    out.append(s("origin_md_head", lg))
    out.append("|---|---|---|---|---|---|")
    for i, (f, name) in enumerate(zip(frames, frame_files(frames), strict=True), 1):
        cap = "<br>".join(md_cell(c) for c in f.caption)
        data = "<br>".join(md_cell(x) for x in dict.fromkeys(f.data_sources))
        out.append(
            f"| {i} | {md_cell(f.title)} | [{name}](frames/{name}) | {cap} | {md_cell(f.map_source)} | {data} |"
        )
    out += ["", s("origin_md_skipped", lg), ""]
    out += [f"- {md_cell(k.title)}: {k.reason}" for k in skipped] or [s("origin_md_none", lg)]
    out += ["", s("origin_md_terms", lg, day=TERMS_CHECKED), "", s("origin_terms", lg), ""]
    return "\n".join(out)


# ---------------------------------------------------------------- 中心と写真


def latest_located(folder: R.Folder) -> R.Observation | None:
    for path in reversed(folder.list_observations()):
        obs = R.Observation.read(path)
        if obs.location and obs.location.get("center"):
            return obs
    return None


def latest(folder: R.Folder) -> R.Observation | None:
    paths = folder.list_observations()
    return R.Observation.read(paths[-1]) if paths else None


PHOTO_NEAR_M = 500  # 観察の写真を使うのは、その観察の座標が中心からこの距離の内のときだけ


def make_plan(
    folder: R.Folder,
    language: str,
    lat: float | None = None,
    lon: float | None = None,
    size: tuple[int, int] = DEFAULT_SIZE,
) -> Plan | None:
    """中心（--lat/--lon、無ければ座標のある一番新しい観察）と、写真と data 行を集める。中心が無ければ None。"""
    extent = None
    if lat is None or lon is None:
        located = latest_located(folder)
        if located is None:
            return None
        lat, lon = located.location["center"]
        extent = located.location.get("extent_m")
    plan = Plan(float(lat), float(lon), extent, folder.place_data(), language, size=size)
    obs = latest(folder)
    if obs is None or not obs.photos or not (folder.root / obs.photos[0]).is_file():
        plan.photo_skip = "no_photo"
        return plan
    plan.photo, plan.photo_date = folder.root / obs.photos[0], obs.date
    if not obs.location or R._distance_m([plan.lat, plan.lon], obs.location["center"]) > PHOTO_NEAR_M:
        plan.photo_skip = "far_photo"
    return plan


def output_dir(folder: R.Folder, out: str | None, day: str) -> Path:
    """出力の場所。本人のフォルダーの中でなければ ValueError。"""
    root = folder.root.resolve()
    p = Path(out).expanduser() if out else folder.root / "origin" / day
    p = (p if p.is_absolute() else Path.cwd() / p).resolve()
    if p != root and root not in p.parents:
        raise ValueError(str(p))
    return p


def parse_size(text: str | None) -> tuple[int, int]:
    """'1280x720' → (1280, 720)。幅と高さは偶数に丸める（mp4 の yuv420p のため）。"""
    if not text:
        return DEFAULT_SIZE
    m = re.fullmatch(r"\s*(\d{3,4})\s*[xX×]\s*(\d{3,4})\s*", text)
    if not m:
        raise ValueError(text)
    w, h = int(m[1]) // 2 * 2, int(m[2]) // 2 * 2
    if w < 320 or h < 240:
        raise ValueError(text)
    return w, h


@dataclass
class Result:
    out: Path
    video: Path
    mp4: bool
    frames: list[Frame]
    skipped: list[Skipped]
    frame_paths: list[Path]
    captions: Path


def run(
    plan: Plan,
    tiles: Tiles,
    fonts: Fonts,
    out: Path,
    *,
    seconds: float = SECONDS,
    fps: int = FPS,
    day: str | None = None,
    video: bool = True,
) -> Result:
    """場面を作り、静止画、captions.md、動画（mp4 か GIF）を out に書く。video が False なら動画は作らない（アプリ）。"""
    day = day or dt.date.today().isoformat()
    frames, skipped = build(plan, tiles, fonts)
    out.mkdir(parents=True, exist_ok=True)
    images = [compose(f, plan.size, fonts, plan.language) for f in frames]
    paths = write_frames(images, frames, out)
    cap = out / "captions.md"
    cap.write_text(captions_md(frames, skipped, plan.language, day), encoding="utf-8")
    mp4 = ffmpeg_module() is not None
    video = out / ("origin.mp4" if mp4 else "origin.gif")
    if images and video:
        if mp4:
            write_mp4(images, video, seconds, fps)
        else:
            write_gif(images, video, seconds)
    return Result(out, video, mp4, frames, skipped, paths, cap)
