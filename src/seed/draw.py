# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed grow --draw — 計画の絵（仮説）のイラスト。設計書 §16.3 の 3、§16.5。

場面ごとに、Claude が書いた絵の指示（scenario.json の `prompt`）と、seed の図（SVG を PNG にした物）と、
本人が `--photo` で選んだ写真を、家の機械（halo）の sd-server（stable-diffusion.cpp、FLUX.2 klein 4B）に渡し、
戻った絵に「計画の絵（仮説）」の印、時期、題、確からしさを焼いて grow/<日>/NN-<時期>.png に置く。

- 送る物は prompt、図の PNG、選ばれた写真（EXIF を落とした写し）だけ。座標は送らない。
- prompt の無い場面は描かない。seed は文から prompt を作らない。
- 戻った絵はそのまま grow/<日>/raw/ に残す。印付きの方を人に見せる。
- seed publish では送らない（grow/ は公開の道に入らない）。
- halo の sd-server は 127.0.0.1:11435 に縛り、外向きは門（Caddy、:11445）だけ。門は Bearer の token が
  一致した時だけ通す（deploy/halo/）。token は credentials.toml の draw_token か環境変数 SEED_DRAW_TOKEN。
  URL に口が書かれていなければ門の口 11445 を使う（設計書 §5.4）。
"""

from __future__ import annotations

import datetime as dt
import io
import ipaddress
import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageOps

from . import grow as G
from .app.strings import s

ENV_URL = "SEED_DRAW_URL"
ENV_TOKEN = "SEED_DRAW_TOKEN"
DEFAULT_PORT = 11445  # halo の門（Caddy）。sd-server そのもの（11435）は機械の外から届かない
SIZE = (1280, 720)
TIMEOUT_S = 180.0
PING_S = 10.0
MAX_PHOTOS = 3
PHOTO_SIDE = 1536  # 写真の長辺（参照に渡す大きさ）
MODEL = "FLUX.2 klein 4B"
MACHINE = "halo"
STEPS, CFG, SAMPLER = 4, 1.0, "euler"
RAW = "raw"
TRANSPORT = None  # テストで httpx.MockTransport を差す
SIZE_RE = re.compile(r"^(\d{2,4})[xX×](\d{2,4})$")

# 印の色（SVG の図と同じ赤）
MARK_RED = (179, 38, 30)
INK = (34, 34, 34)
MUTED = (110, 110, 110)


class DrawError(Exception):
    """描けなかった。word は strings の鍵（draw_no_server, draw_unreachable, draw_unauthorized, draw_failed）。"""

    def __init__(self, word: str, detail: str = "") -> None:
        super().__init__(detail or word)
        self.word = word
        self.detail = detail


# ---------------------------------------------------------------- server の場所


def server_url(given: str | None, extra: dict | None) -> str | None:
    """--server > 環境変数 SEED_DRAW_URL > seed.toml の [grow] server。無ければ None。

    口の無い URL（http://halo.local）には門の口 11445 を足す。
    """
    table = (extra or {}).get("grow")
    from_toml = table.get("server") if isinstance(table, dict) else None
    for v in (given, os.environ.get(ENV_URL), from_toml):
        if isinstance(v, str) and v.strip():
            return with_default_port(v.strip().rstrip("/"))
    return None


def with_default_port(url: str) -> str:
    u = urlparse(url)
    if not u.scheme or not u.hostname:
        return url
    try:
        if u.port is not None:
            return url
    except ValueError:
        return url
    host = f"[{u.hostname}]" if ":" in u.hostname else u.hostname
    auth = url.split("//", 1)[1].split("@", 1)[0] + "@" if "@" in u.netloc else ""
    return u._replace(netloc=f"{auth}{host}:{DEFAULT_PORT}").geturl()


def token(given: str | None) -> str | None:
    """門の token。環境変数 SEED_DRAW_TOKEN > credentials.toml の draw_token。無ければ None（門の無い server）。"""
    for v in (os.environ.get(ENV_TOKEN), given):
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def auth_headers(tok: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def is_lan(url: str) -> bool:
    """家の中の server か（localhost、127.*、::1、192.168.*、10.*）。名前で書かれた他の host は外とみなす。"""
    host = (urlparse(url).hostname or "").lower()
    if host in ("localhost",) or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    return ip.version == 4 and (str(ip).startswith("192.168.") or str(ip).startswith("10."))


def parse_size(text: str | None) -> tuple[int, int]:
    if not text:
        return SIZE
    m = SIZE_RE.match(text.strip())
    if not m:
        raise ValueError(text)
    w, h = int(m.group(1)), int(m.group(2))
    if not (64 <= w <= 4096 and 64 <= h <= 4096):
        raise ValueError(text)
    return w, h


# ---------------------------------------------------------------- 参照の画像


def svg_png(svg: Path, size: tuple[int, int] = SIZE) -> bytes:
    """seed の図（SVG）を PNG に。resvg（wheel だけ、cairo は要らない）。"""
    import resvg_py

    return bytes(
        resvg_py.svg_to_bytes(svg_path=str(svg), width=size[0], height=size[1], background="#ffffff")
    )


def clean_photo(path: Path) -> bytes:
    """本人の写真を、向きを直して縮め、EXIF（座標を含む）を落とした JPEG に。

    photos/ の写真は EXIF の座標を持ったまま（本人の物）。photos.shrink で落とした上で、
    送る前にもう一度、画素だけの新しい画像に写して落とす。
    """
    from .photos import shrink

    first = shrink(path, PHOTO_SIDE)
    with Image.open(io.BytesIO(first)) as img:
        img = img.convert("RGB")
        clean = Image.new("RGB", img.size)
        clean.paste(img)
    buf = io.BytesIO()
    clean.save(buf, "JPEG", quality=92)
    return buf.getvalue()


# ---------------------------------------------------------------- server に頼む


def extra_args(negative: str | None = None) -> str:
    """sd-server の OpenAI 形に、steps、cfg、sampler を prompt の中で渡す（api.md の sd_cpp_extra_args）。"""
    body: dict = {
        "sample_params": {"sample_steps": STEPS, "sample_method": SAMPLER, "guidance": {"txt_cfg": CFG}}
    }
    if negative:
        body["negative_prompt"] = negative
    return f"<sd_cpp_extra_args>{json.dumps(body, ensure_ascii=False)}</sd_cpp_extra_args>"


def ping(client, base: str) -> None:
    import httpx

    try:
        r = client.get(f"{base}/v1/models", timeout=PING_S)
    except httpx.HTTPError as e:
        raise DrawError("draw_unreachable", str(e) or type(e).__name__) from e
    if r.status_code == 401:
        raise DrawError("draw_unauthorized", "HTTP 401")
    if r.status_code >= 400:
        raise DrawError("draw_unreachable", f"HTTP {r.status_code}")


def request(
    client,
    base: str,
    prompt: str,
    negative: str | None,
    refs: list[tuple[str, bytes, str]],
    size: tuple[int, int],
    timeout: float = TIMEOUT_S,
) -> bytes:
    """POST /v1/images/edits（multipart、参照は image[]）。戻りの b64_json を画像のバイトで返す。"""
    import base64

    import httpx

    data = {
        "prompt": f"{prompt} {extra_args(negative)}",
        "size": f"{size[0]}x{size[1]}",
        "output_format": "png",
        "n": "1",
    }
    files = [("image[]", (name, blob, mime)) for name, blob, mime in refs]
    try:
        r = client.post(f"{base}/v1/images/edits", data=data, files=files, timeout=timeout)
    except httpx.HTTPError as e:
        raise DrawError("draw_failed", str(e) or type(e).__name__) from e
    if r.status_code == 401:
        raise DrawError("draw_unauthorized", "HTTP 401")
    if r.status_code >= 400:
        raise DrawError("draw_failed", f"HTTP {r.status_code}: {r.text[:200]}")
    try:
        got = r.json()["data"][0]["b64_json"]
        return base64.b64decode(got)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise DrawError("draw_failed", "no b64_json in the answer") from e


# ---------------------------------------------------------------- 印を焼く


def stamp(
    raw: bytes, scene: G.Scene, index: int, language: str, day: str, size: tuple[int, int], fonts
) -> Image.Image:
    """戻った絵を size に合わせ（違えば中央で切って縮める）、上の帯に印、時期、題、確からしさ、下の帯に何で描いたか。"""
    lg = language
    with Image.open(io.BytesIO(raw)) as src:
        img = src.convert("RGB")
    if img.size != size:
        img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    w, h = size
    k = h / 720  # 字の大きさは 720 の高さが基準
    over = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    top, foot = int(70 * k), int(30 * k)
    d.rectangle([0, 0, w, top], fill=(255, 255, 255, 225))
    d.rectangle([0, h - foot, w, h], fill=(255, 255, 255, 210))
    img = Image.alpha_composite(img.convert("RGBA"), over)
    d = ImageDraw.Draw(img)
    mark = s("grow_mark", lg)
    f_mark = fonts.get(max(10, int(20 * k)))
    mw = d.textlength(mark, font=f_mark) + 24 * k
    x0, y0 = 16 * k, 16 * k
    d.rectangle(
        [x0, y0, x0 + mw, y0 + 38 * k], fill=(255, 255, 255, 255), outline=MARK_RED, width=max(2, int(3 * k))
    )
    d.text((x0 + mw / 2, y0 + 19 * k), mark, font=f_mark, fill=MARK_RED, anchor="mm")
    conf = f"[{scene.confidence:.2f}]"
    f_conf = fonts.get(max(10, int(22 * k)))
    d.text((w - 20 * k, 36 * k), conf, font=f_conf, fill=INK, anchor="rm")
    left = x0 + mw + 20 * k
    right = w - 20 * k - d.textlength(conf, font=f_conf) - 20 * k
    f_when, f_title = fonts.get(max(10, int(17 * k))), fonts.get(max(10, int(22 * k)))
    cx = (left + right) / 2
    d.text((cx, 22 * k), f"{index:02d}  {scene.when}", font=f_when, fill=MUTED, anchor="mm")
    title = scene.title
    while title and d.textlength(title, font=f_title) > right - left:
        title = title[:-2] + "…"
    d.text((cx, 50 * k), title, font=f_title, fill=INK, anchor="mm")
    note = s("draw_footer", lg, model=MODEL, machine=MACHINE, day=day)
    d.text((w - 14 * k, h - foot / 2), note, font=fonts.get(max(9, int(14 * k))), fill=MUTED, anchor="rm")
    return img.convert("RGB")


# ---------------------------------------------------------------- 描く


@dataclass
class Drawn:
    index: int
    scene: G.Scene
    png: Path
    raw: Path
    refs: list[str]  # 渡した参照（図の名、写真の道）
    seconds: float
    at: str  # 頼んだ時刻（ISO、秒まで）
    got: tuple[int, int]  # server が返した大きさ


@dataclass
class Report:
    server: str
    size: tuple[int, int]
    photos: int = 0  # 渡した写真の数
    drawn: list[Drawn] = field(default_factory=list)
    skipped: list[tuple[int, G.Scene, str]] = field(default_factory=list)  # 描かなかった場面と理由
    error: DrawError | None = None
    checks: dict[int, dict] = field(default_factory=dict)  # 順 → {"by", "found": [(kind, what)], "error"}


def png_name(index: int, scene: G.Scene) -> str:
    return f"{index:02d}-{scene.when}.png"


def _rel(p: Path, root: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(p)


def draw(
    checked: G.Checked,
    out: Path,
    server: str,
    photos: list[Path],
    language: str,
    day: str,
    root: Path,
    size: tuple[int, int] = SIZE,
    transport=None,
    font: str | None = None,
    progress: Callable[[Drawn], None] | None = None,
    bearer: str | None = None,
) -> Report:
    """場面ごとに halo に頼み、raw と印付きの PNG を out に置く。SVG は先に out に書いてあること。

    bearer は門の token（Authorization: Bearer で送る）。無ければ付けない。

    server が応えなければ何も消さずに error を返す。途中で失敗すれば、そこまでの絵を残して error を返す。
    """
    import httpx

    from .origin import Fonts, find_font

    lg = language
    photos = list(photos)[:MAX_PHOTOS]
    report = Report(server, size, len(photos))
    with httpx.Client(transport=transport or TRANSPORT, headers=auth_headers(bearer)) as client:
        try:
            ping(client, server)
        except DrawError as e:
            report.error = e
            return report
        photo_refs = [(f"photo-{k + 1}.jpg", clean_photo(p), "image/jpeg") for k, p in enumerate(photos)]
        (out / RAW).mkdir(parents=True, exist_ok=True)
        for old in list(out.glob("[0-9][0-9]-*.png")) + list((out / RAW).glob("[0-9][0-9]-*.png")):
            old.unlink()
        fonts = Fonts(find_font(font))
        for i, sc in enumerate(checked.scenes, 1):
            if not sc.prompt:
                report.skipped.append((i, sc, s("draw_reason_no_prompt", lg)))
                continue
            svg = out / G.svg_name(i, sc)
            refs = [(svg.with_suffix(".png").name, svg_png(svg, SIZE), "image/png"), *photo_refs]
            at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
            t0 = time.monotonic()
            try:
                raw = request(client, server, sc.prompt, sc.negative, refs, size)
            except DrawError as e:
                report.error = e
                return report
            secs = time.monotonic() - t0
            name = png_name(i, sc)
            raw_path = out / RAW / name
            raw_path.write_bytes(raw)
            with Image.open(io.BytesIO(raw)) as im:
                got = im.size
            stamp(raw, sc, i, lg, day, size, fonts).save(out / name, "PNG", optimize=True)
            item = Drawn(
                i, sc, out / name, raw_path, [svg.name] + [_rel(p, root) for p in photos], secs, at, got
            )
            report.drawn.append(item)
            if progress:
                progress(item)
    return report


# ---------------------------------------------------------------- captions.md の節


def _quote(text: str) -> list[str]:
    return ["```text", text.strip(), "```"]


def captions(checked: G.Checked, language: str, meta: dict, report: Report) -> str:
    lg = language
    pictures = {d.index: d.png.name for d in report.drawn}
    notes = []
    if is_lan(report.server):
        notes.append(s("draw_md_lan", lg))
    tail = [s("draw_md_how", lg), ""]
    tail.append(
        s(
            "draw_md_how_about",
            lg,
            model=MODEL,
            machine=MACHINE,
            server=report.server,
            steps=STEPS,
            cfg=f"{CFG:g}",
            sampler=SAMPLER,
            size=f"{report.size[0]}x{report.size[1]}",
            photos=s("draw_md_with_photos", lg) if report.photos else "",
        )
    )
    for d in report.drawn:
        tail += [
            "",
            f"### {d.index:02d} {d.scene.when} {G.md_cell(d.scene.title)}",
            "",
            s("draw_md_prompt", lg),
            *_quote(d.scene.prompt or ""),
        ]
        if d.scene.negative:
            tail += [s("draw_md_negative", lg), *_quote(d.scene.negative)]
        tail += [
            "",
            "- " + s("draw_md_refs", lg, refs=", ".join(f"`{r}`" for r in d.refs)),
            "- " + s("draw_md_meta", lg, server=report.server, model=MODEL, at=d.at, secs=f"{d.seconds:.1f}"),
            "- " + s("draw_md_files", lg, png=d.png.name, raw=f"{RAW}/{d.raw.name}", w=d.got[0], h=d.got[1]),
        ]
    if report.skipped:
        tail += ["", s("draw_md_not_drawn", lg), ""]
        tail += [f"- {i:02d} {sc.when} {G.md_cell(sc.title)}: {why}" for i, sc, why in report.skipped]
    if report.error:
        tail += ["", s("draw_md_error", lg, detail=G.md_cell(str(report.error.detail or report.error.word)))]
    tail += ["", s("draw_md_check", lg), ""]
    if not report.checks:
        tail.append(s("draw_md_check_none", lg))
    for d in report.drawn:
        c = report.checks.get(d.index)
        if c is None:
            continue
        head = (
            f"- {d.index:02d} {d.scene.when}（{c.get('by')}）: "
            if lg == "ja"
            else f"- {d.index:02d} {d.scene.when} ({c.get('by')}): "
        )
        if c.get("error"):
            tail.append(head + s("draw_md_check_failed", lg, detail=G.md_cell(c["error"])))
        elif not c.get("found"):
            tail.append(head + "none")
        else:
            tail.append(head + "; ".join(f"{k}: {G.md_cell(w)}" for k, w in c["found"]))
    return G.captions_md(checked, lg, meta, pictures=pictures, notes=notes, tail=tail)
