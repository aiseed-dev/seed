# SPDX-License-Identifier: AGPL-3.0-or-later
"""入口と公開された記録の HTML（静的サイト。設計書 §7.5）。

公開ファイルが届く・取り下げられる・一言が届くたびに write_site が SEED_PUBLIC_DIR/site/ に書き出し、
Caddy がそのまま配る。FastAPI の / と /p/<id> も同じ HTML を返す（開発中の確認用）。
静的なページには「一言を送る」の欄を置かない。一言はアプリから、招待コード付きで送る。
"""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from .. import index, lang
from .. import records as R
from .settings import Settings

DISCORD = "https://discord.gg/Q8pwMH2uTA"
SOURCE = "https://github.com/aiseed-dev/seed"
LEAD = "畑を始めてみませんか。畑の写真を撮って、自分の Claude と話します。その土地の成り立ち（地質、土、歴史）も調べてくれます。記録が残り、人と繋がれます。自給農から、その次へ。"

CSS = """
:root{--fg:#1d2420;--muted:#5d6b62;--bg:#fbfaf6;--line:#dcd8cc;--accent:#2f6b45}
@media (prefers-color-scheme: dark){:root{--fg:#e6e9e4;--muted:#a3ada6;--bg:#151916;--line:#333a35;--accent:#7cc495}}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;color:var(--fg);
background:var(--bg);max-width:44rem;margin:0 auto;padding:2rem 16px 4rem;line-height:1.75;overflow-wrap:anywhere}
a{color:var(--accent)}
h1{font-size:1.6rem;margin:0 0 .25rem}
h2{font-size:1.1rem;margin:2rem 0 .5rem;border-bottom:1px solid var(--line)}
.lead{font-size:1.15rem}
.muted,small{color:var(--muted)}
ul.records{list-style:none;padding:0}
ul.records li{border-top:1px solid var(--line);padding:.75rem 0;display:flow-root}
img.shot{display:block;width:100%;height:auto;margin:.5rem 0;border-radius:.3rem}
img.thumb{float:right;width:6rem;height:6rem;object-fit:cover;margin:0 0 .5rem .75rem;border-radius:.3rem}
ul.lines{padding-left:1.2rem}
.tag{display:inline-block;border:1px solid var(--line);border-radius:1rem;padding:0 .6rem;margin:0 .25rem .25rem 0;font-size:.85rem}
code{font-size:.9em;color:var(--muted)}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.2rem 1rem}
dt{color:var(--muted)}
dd{margin:0}
pre{background:var(--line);padding:.75rem;overflow-x:auto}
form{display:grid;gap:.5rem}
input,textarea,button{font:inherit;padding:.4rem .5rem;border:1px solid var(--line);border-radius:.3rem;
background:var(--bg);color:var(--fg);width:100%}
button{background:var(--accent);color:var(--bg);border:0;cursor:pointer;width:auto;justify-self:start;padding:.4rem 1.2rem}
"""


def _e(x) -> str:
    return html.escape(str(x), quote=True)


def page_html(title: str, body: str, description: str = LEAD) -> str:
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<meta name="description" content="{_e(description)}">
<meta property="og:title" content="{_e(title)}"><meta property="og:description" content="{_e(description)}"><meta property="og:type" content="website">
<style>{CSS}</style></head><body>
{body}
<p class="muted"><small><a href="/">seed</a> · <a href="{_e(SOURCE)}">source (AGPL-3.0)</a></small></p>
</body></html>
"""


def _tags(words: list[str]) -> str:
    return "".join(f'<span class="tag">{_e(w)}</span>' for w in words)


def load_index(settings: Settings) -> dict:
    try:
        return json.loads(settings.index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return index.build_index(settings.public_dir, settings.connections_dir)


def entry_html(idx: dict) -> str:
    """入口（設計書 §6）。一行、何をする物か、約束、テスター募集、Discord、公開された記録の一覧。"""
    total = idx.get("total", {})
    items = []
    for r in idx.get("records", []):
        cover = r.get("photo")
        thumb = (
            f'<a href="/p/{_e(r["id"])}"><img class="thumb" src="{_e(cover)}" alt="" loading="lazy"></a>'
            if isinstance(cover, str) and cover.startswith("/photos/")
            else ""
        )
        items.append(
            f"""<li>{thumb}<a href="/p/{_e(r["id"])}"><strong>{_e(r.get("name", ""))}</strong></a>
<span class="muted">{_e(r.get("place", ""))} · {_e(r.get("since", ""))}</span><br>
{_e(r.get("word", ""))}<br>
{_tags(r.get("what") or [])}{_tags(r.get("next") or [])}
<small>観察 {int(r.get("observations") or 0)} · 繋がり {int(r.get("connections") or 0)}</small></li>"""
        )
    listing = (
        f'<ul class="records">{"".join(items)}</ul>'
        if items
        else '<p class="muted">まだ公開された記録はありません。</p>'
    )
    body = f"""<h1>seed — Claude と一緒に種を播く</h1>
<p class="lead">{_e(LEAD)}</p>
<p>Claude は「こうしなさい」とは言いません。写真に何が見えたか、次に何を見ると良さそうかを話してくれます。決めるのは畑です。</p>
<p>畑は一枚ずつ違います。本に書いてある事より、みんなの畑の記録の方が役に立ちます。だから、見せてもよい所を持ち寄って、近い畑の人と繋がれるようにしました。</p>
<p>写真と記録は、あなたの手元に残ります。ここに出るのは、<strong>あなたが見せてもよいと決めた写真と言葉だけ</strong>です。写真からは、撮った場所の情報を外してあります。</p>
<p><strong>一緒に使ってくれる人を探しています。</strong>
<a href="{_e(DISCORD)}">Discord「AI と一緒に自給農」</a>で、気軽に声をかけてください。招待コードをお渡しします。分からない事も、そこで聞いてください。</p>
<h2>PC で使う</h2>
<p>GitHub から取ってきて、そのフォルダーで入れます。</p>
<pre>git clone https://github.com/aiseed-dev/seed.git
cd seed
python -m venv .venv
.venv/bin/pip install -e ".[app]"
.venv/bin/flet run</pre>
<p class="muted"><small>Windows、macOS、Linux で動きます。Windows では <code>.venv\\Scripts\\</code> の下の物を使います。中身と手引きは <a href="{_e(SOURCE)}">リポジトリ</a> にあります。スマートフォンだけの人は、Discord で声をかけてください。</small></p>
<h2>公開された記録 {int(total.get("records", 0))} 件 · 繋がり {int(total.get("connections", 0))} 件</h2>
{listing}
<p class="muted"><small><a href="/index.json">index.json</a></small></p>"""
    return page_html("seed — Claude と一緒に種を播く", body)


def _line_html(line: R.Line) -> str:
    s = f"<code>{_e(line.key)}</code> {_e(line.text)}"
    if line.confidence is not None:
        s += f' <small class="muted">[{line.confidence:.2f}]</small>'
    if line.verdict:
        s += f" → {_e(lang.t(line.verdict, 'ja'))}"
        if line.reason:
            s += f"（{_e(line.reason)}）"
    return f"<li>{s}</li>"


def _day_html(pub: R.Public, day: str) -> str:
    """一日。写真（photo の行）を頭に大きく、文の行はその下に（分け方は Public.day_parts。アプリの札と同じ）。"""
    shots, lines = pub.day_parts(day)
    imgs = "".join(
        f'<img class="shot" src="{_e(R.photo_url(pub.id, n))}" alt="{_e(day)}" loading="lazy">' for n in shots
    )
    rows = "".join(_line_html(x) for x in lines) or ("" if shots else "<li>(none)</li>")
    listing = f'<ul class="lines">{rows}</ul>' if rows else ""
    return f"<h2>{_e(day)}</h2>{imgs}{listing}"


def showable(pub: R.Public) -> bool:
    """頁にしてよいか。検査が通り、細かい座標（小数 3 桁以上）が無い物だけ（設計書 §5.2）。

    サーバーを通った物は通る。public/ に直に置かれた物の守り。
    """
    return not pub.check() and not R.fine_coords(pub.render())


def record_html(pub: R.Public, connections: int) -> str:
    """公開された記録の閲覧（設計書 §7.1）。一言はアプリから。"""
    rows = [("場所", pub.place), ("公開した日", pub.since)]
    if pub.coord and len(pub.coord) == 2:
        lat, lon = R.coarse_coord(pub.coord)  # 前書きは丸めてあるはず。頁でも 2 桁より細かく出さない
        rows.append(("座標", f"{lat}, {lon}（約 1 km の粗さ。本人が選んだ）"))
    if pub.contact:
        rows.append(("連絡", pub.contact))
    rows += [("言語", pub.language), ("観察", str(pub.observations)), ("繋がり", str(connections))]
    facts = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in rows)
    days = "".join(_day_html(pub, day) for day in sorted(pub.days))  # 成長の記録。古い日から
    body = f"""<p><small><a href="/">← 入口</a></small></p>
<h1>{_e(pub.name)}</h1>
<p class="lead">{_e(pub.word)}</p>
<p>{_tags(pub.what)}{_tags(pub.next)}</p>
<dl>{facts}</dl>
<p class="muted"><small>数字 [0.00〜1.00] の付いた行は、AI の読みです（当たっているとは限りません）。→ の後は、本人が合う・違うを付けた物です。
出典の付いた行は資料です。ここにあるのは、この畑の人が見せてもよいと決めた写真と言葉だけです。</small></p>
{days}
<h2>一言を送る</h2>
<p>seed のアプリで「ほかの人の畑を見たい」と話すと、この畑へ一言を送れます。あなたの呼び名と一緒に、持ち主に届きます。
招待コードは <a href="{_e(DISCORD)}">Discord「AI と一緒に自給農」</a>でお渡しします。</p>
<p class="muted"><small><a href="/public/{_e(pub.id)}.md">公開ファイル（Markdown）</a></small></p>"""
    return page_html(f"{pub.name} — seed", body, description=pub.word or LEAD)


def not_found_html() -> str:
    return page_html("seed", '<h1>見つかりません</h1><p><a href="/">入口へ戻る</a></p>')


def write_site(settings: Settings) -> Path:
    """静的サイトを SEED_PUBLIC_DIR/site/ に書き出す。index.html、p/<id>.html、index.json、public/<id>.md、
    photos/<id>/<名>（photo の行が指す写真）。

    消えた記録のページと写真も消す。.owners.json と connections/ は写さない。
    """
    site = settings.site_dir
    (site / "p").mkdir(parents=True, exist_ok=True)
    (site / "public").mkdir(parents=True, exist_ok=True)
    idx = load_index(settings)
    (site / "index.html").write_text(entry_html(idx), encoding="utf-8")
    (site / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    (site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    keep: set[str] = set()
    for path in sorted(settings.public_dir.glob("*.md")):
        try:
            pub = R.Public.read(path)
        except (ValueError, TypeError, KeyError):
            continue
        if not showable(pub):
            continue
        n = index.count_connections(settings.connections_dir, pub.id)
        (site / "p" / f"{pub.id}.html").write_text(record_html(pub, n), encoding="utf-8")
        shutil.copyfile(path, site / "public" / path.name)
        _copy_photos(settings.public_dir / "photos" / pub.id, site / "photos" / pub.id, pub.photo_names())
        keep.add(pub.id)
    for old in (site / "p").glob("*.html"):
        if old.stem not in keep:
            old.unlink()
    for old in (site / "public").glob("*.md"):
        if old.stem not in keep:
            old.unlink()
    if (site / "photos").is_dir():
        for old in (site / "photos").iterdir():
            if old.name not in keep:
                shutil.rmtree(old, ignore_errors=True)
    return site


def _copy_photos(src: Path, dst: Path, names: list[str]) -> None:
    """記録の写真を site/ に写す（変わった物だけ）。指されていない物は消す。"""
    want = [n for n in names if R.safe_photo_name(n) and (src / n).is_file()]
    if want:
        dst.mkdir(parents=True, exist_ok=True)
    for n in want:
        s, d = src / n, dst / n
        if d.is_file() and d.stat().st_size == s.stat().st_size and d.stat().st_mtime >= s.stat().st_mtime:
            continue
        tmp = dst / f".{n}.tmp"
        shutil.copyfile(s, tmp)
        tmp.replace(d)
    if dst.is_dir():
        for old in dst.iterdir():
            if old.name not in want:
                old.unlink(missing_ok=True)
