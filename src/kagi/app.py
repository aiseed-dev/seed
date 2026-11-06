"""係の机の画面 `kagi app`（Flet の PC 版。設計書 §3.3）。

`build_cards` は Flet を使わない純粋な関数で、在庫・口・走査・記録の結果を札の文字と表に変える。
`flet` は `run` と `make_main` の中で遅く import する（kagi の本体は標準ライブラリだけのまま）。
鍵の値は読まない。札に出るのは在庫の id と欄の名、口の番号、path:line と種類、記録の連番と理由だけ。
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
from pathlib import Path

from kagi import audit, inventory, machine, ports, report, scan

SEED_COLOR = "#5B7A3A"  # seed の theme と同じ種の色
FONT = "Roboto"  # Flet 1.1 の既定の字体は日本語の字形を持たない（seed の theme.py と同じ理由）
MAX_WIDTH = 900
WEB_PORT_ENV = "KAGI_APP_WEB_PORT"  # 確かめる時だけ。あればブラウザのタブで開く（127.0.0.1 だけ）


def _inventory_card(d: Path, days: int, today: dt.date) -> dict:
    card = {"title": "在庫", "summary": "", "error": None, "columns": ["id", "何", "中身"], "rows": []}
    try:
        res = inventory.check(inventory.load(d / "inventory.toml"), days, today)
    except inventory.Refused as e:
        card["error"] = f"読まなかった: {e}"
        return card
    card["summary"] = (
        f"件数 {res.count}、期限切れ {len(res.by('expired'))}、{days} 日以内 {len(res.by('soon'))}、"
        f"抜け {len(res.by('missing'))}、形の誤り {len(res.by('invalid'))}"
    )
    for p in ("expired", "missing", "invalid", "soon"):
        for f in res.by(p):
            card["rows"].append([f.id, inventory.LABEL[p], f.detail])
    return card


def _ports_card(d: Path, ss_file: Path | None, host: str | None) -> dict:
    card = {
        "title": "口",
        "summary": "",
        "error": None,
        "columns": ["差", "host", "port", "bind", "process"],
        "rows": [],
    }
    if ss_file is None:
        card["summary"] = "突き合わせていない（ss -ltnp の写しのファイルを選ぶ）"
        return card
    try:
        table = ports.load(d / "ports.toml")
        text = Path(ss_file).read_text("utf-8")
    except inventory.Refused as e:
        card["error"] = f"読まなかった: {e}"
        return card
    except (OSError, UnicodeDecodeError) as e:
        card["error"] = f"ss の出力を読めない: {ss_file} ({type(e).__name__})"
        return card
    diff = ports.compare(table, ports.parse_ss(text), host)
    head = f"機械 {host}" if host else "表の全部の機械"
    card["summary"] = (
        f"{head}（{Path(ss_file).name}）: 表に無い口 {len(diff.unlisted)}、"
        f"表にあって開いていない口 {len(diff.closed)}、外向きで表と違う口 {len(diff.outward)}"
    )
    for l in diff.unlisted:
        card["rows"].append(["表に無い口", host or "", str(l.port), l.bind, l.process])
    for p in diff.closed:
        card["rows"].append(
            [
                "表にあって開いていない",
                str(p.get("host", "")),
                str(p["port"]),
                str(p.get("bind", "")),
                str(p.get("service", "")),
            ]
        )
    for l, want in diff.outward:
        card["rows"].append([f"外向きで表と違う（表は {want}）", host or "", str(l.port), l.bind, l.process])
    return card


def _machines_card(d: Path, now: dt.datetime | None = None) -> dict:
    """機械の札。機械ごとの一行と、直す物の表。値は無い（指紋とアカウントの名と口だけ）。"""
    card = {
        "title": "機械",
        "summary": "",
        "error": None,
        "columns": ["host", "役", "写し", "直す", "直す物"],
        "rows": [],
        "detail_columns": ["host", "何", "見た物"],
        "detail": [],
    }
    try:
        rows = report.machine_rows(d, now)
    except inventory.Refused as e:
        card["summary"] = "機械の表が無い（machines.toml。kagi init で雛形）"
        card["error"] = str(e) if (d / machine.FILENAME).exists() else None
        return card
    n = sum(1 for r in rows if r["fixes"])
    none = sum(1 for r in rows if r["facts"] is None)
    card["summary"] = f"機械 {len(rows)} 台、直す物のある機械 {n}、写しの無い機械 {none}"
    for r in rows:
        card["rows"].append(
            [
                r["host"],
                r["role"],
                r["facts"] or "無い",
                "" if r["fixes"] is None else str(r["fixes"]),
                "、".join(r["what"]),
            ]
        )
        card["detail"] += [[r["host"], f.what, f.result] for f in r["findings"] if f.fix]
    return card


def collect_machine(d: Path, host: str, local: bool = False, env: dict | None = None, runner=None) -> Path:
    """写しを取って置く。ssh を使った時は記録に一行（署名の鍵があれば）。"""
    m = machine.load(Path(d) / machine.FILENAME).machine(host)
    alias = None if local else str(m.get("ssh", host))
    text = machine.collect(alias, runner)
    path = machine.save_facts(d, host, text)
    if not local:
        try:
            key = audit.find_key(env)
            audit.add(
                Path(d) / "audit.log", key, (env or os.environ).get("USER", "?"), "machine.collect", host
            )
        except (audit.NoKey, ValueError, OSError):
            pass
    return path


def fix_text(d: Path, host: str) -> str:
    """直す手の文（走らせない）。"""
    for r in report.machine_rows(d):
        if r["host"] == host and r["facts"]:
            facts = machine.load_facts(Path(d) / machine.FACTS_DIR / r["facts"])
            return machine.fix_script(host, facts, r["findings"])
    raise inventory.Refused(f"{host} の写しが無い")


def _scan_card(scan_paths: list[Path], excludes: list[str] | None) -> dict:
    card = {"title": "走査", "summary": "", "error": None, "lines": []}
    if not scan_paths:
        card["summary"] = "走らせていない（場所を選ぶ）"
        return card
    r = scan.scan(list(scan_paths), excludes)
    card["summary"] = f"読んだファイル {r.files}、飛ばした {r.skipped}、見つかった {len(r.hits)}"
    card["lines"] = [f"{h.path}:{h.line}  {h.kind}" for h in r.hits]  # 値は Hit に無い
    return card


def _audit_card(d: Path, env: dict | None) -> dict:
    card = {"title": "記録", "summary": "", "error": None, "key": False, "warning": None, "failures": []}
    try:
        key = audit.find_key(env)
    except audit.NoKey as e:
        card["summary"] = "検証していない（署名の鍵が無い。手引き §3）"
        card["error"] = str(e)
        return card
    card["key"] = True
    card["warning"] = key.warning
    try:
        n, fails = audit.verify(d / "audit.log", key)
    except (OSError, UnicodeDecodeError) as e:
        card["error"] = f"記録を読めない ({type(e).__name__})"
        return card
    if fails:
        card["summary"] = f"検証が落ちた（{n} 行のうち {len(fails)} 件）"
        card["failures"] = [f"{f.where}: {f.reason}" for f in fails]
    else:
        card["summary"] = f"ok {n} lines"
    return card


def build_cards(
    d: Path,
    ss_file: Path | None = None,
    scan_paths: list[Path] | None = None,
    *,
    host: str | None = None,
    excludes: list[str] | None = None,
    days: int = 30,
    today: dt.date | None = None,
    env: dict | None = None,
) -> dict:
    """五つの札の中身（文字と表）。Flet を使わない。値は入れない。"""
    d = Path(d)
    today = today or dt.date.today()
    return {
        "dir": str(d),
        "inventory": _inventory_card(d, days, today),
        "ports": _ports_card(d, ss_file, host),
        "machines": _machines_card(d),
        "scan": _scan_card(list(scan_paths or []), excludes),
        "audit": _audit_card(d, env),
    }


def write_report(
    d: Path,
    ss_file: Path | None = None,
    scan_paths: list[Path] | None = None,
    *,
    host: str | None = None,
    days: int = 30,
    today: dt.date | None = None,
) -> tuple[Path, str]:
    """`report` の Markdown を作り、作業の場所の `report-<日>.md` に書く。道と文を返す。"""
    today = today or dt.date.today()
    text = report.build(
        Path(d), days, ss_file, host, [str(p) for p in scan_paths] if scan_paths else None, today=today
    )
    out = Path(d) / f"report-{today.isoformat()}.md"
    out.write_text(text, "utf-8")
    return out, text


def make_main(d: Path):
    import flet as ft

    d = Path(d)

    async def main(page: ft.Page) -> None:
        page.title = "kagi"
        page.theme = ft.Theme(color_scheme_seed=SEED_COLOR, font_family=FONT)
        page.dark_theme = ft.Theme(color_scheme_seed=SEED_COLOR, font_family=FONT)
        page.theme_mode = ft.ThemeMode.SYSTEM
        picker = ft.FilePicker()  # 参照を持っておく（無いと外される）
        st: dict = {"ss": None, "scan": [], "report": None, "fix": None}
        mc_field = ft.TextField(label="host（機械の表の名）", dense=True, width=220)

        ss_field = ft.TextField(label="ss -ltnp の写しのファイル", dense=True, width=420)
        host_field = ft.TextField(label="host（表に機械が二つ以上なら）", dense=True, width=220)
        scan_field = ft.TextField(label="走査する場所", dense=True, width=420)
        actor = ft.TextField(label="actor", dense=True, width=160)
        action = ft.TextField(label="action", dense=True, width=200)
        detail = ft.TextField(label="detail", dense=True, width=320)
        body = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)

        def muted(text: str) -> ft.Text:
            return ft.Text(text, size=13, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True)

        def err(text: str) -> ft.Text:
            return ft.Text(text, color=ft.Colors.ERROR, selectable=True)

        def table(columns: list[str], rows: list[list[str]]) -> ft.Control:
            return ft.Row(
                [
                    ft.DataTable(
                        columns=[ft.DataColumn(ft.Text(c, weight=ft.FontWeight.W_600)) for c in columns],
                        rows=[
                            ft.DataRow(cells=[ft.DataCell(ft.Text(v, selectable=True)) for v in r])
                            for r in rows
                        ],
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            )

        def card(title: str, controls: list[ft.Control]) -> ft.Card:
            head = ft.Text(title, theme_style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.W_600)
            return ft.Card(content=ft.Container(ft.Column([head, *controls], spacing=8), padding=16))

        def toast(text: str) -> None:
            page.show_dialog(ft.SnackBar(ft.Text(text)))

        def host() -> str | None:
            return (host_field.value or "").strip() or None

        def render() -> None:
            c = build_cards(d, st["ss"], st["scan"], host=host())
            inv, prt, scn, aud = c["inventory"], c["ports"], c["scan"], c["audit"]

            inv_c: list[ft.Control] = [err(inv["error"])] if inv["error"] else [ft.Text(inv["summary"])]
            if inv["rows"]:
                inv_c.append(table(inv["columns"], inv["rows"]))

            prt_c: list[ft.Control] = [
                ft.Row(
                    [
                        ss_field,
                        host_field,
                        ft.OutlinedButton("選ぶ", icon=ft.Icons.FOLDER_OPEN, on_click=pick_ss),
                        ft.FilledButton("突き合わせる", on_click=use_ss),
                    ],
                    wrap=True,
                ),
                err(prt["error"]) if prt["error"] else ft.Text(prt["summary"]),
            ]
            if prt["rows"]:
                prt_c.append(table(prt["columns"], prt["rows"]))

            mch = c["machines"]
            mch_c: list[ft.Control] = [
                ft.Row(
                    [
                        mc_field,
                        ft.FilledButton("写しを取る（ssh）", icon=ft.Icons.SYNC, on_click=collect),
                        ft.OutlinedButton("直す手を見る", on_click=show_fix),
                    ],
                    wrap=True,
                ),
                ft.Text(mch["summary"]),
            ]
            if mch["error"]:
                mch_c.append(err(mch["error"]))
            if mch["rows"]:
                mch_c.append(table(mch["columns"], mch["rows"]))
            if mch["detail"]:
                mch_c.append(table(mch["detail_columns"], mch["detail"]))
            if st["fix"]:
                mch_c += [
                    muted("直す手（kagi は走らせない。人が読んで、機械の端末で一つずつ）"),
                    ft.Container(
                        ft.Text(st["fix"], font_family="monospace", size=13, selectable=True),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        padding=12,
                        border_radius=8,
                    ),
                ]

            scn_c: list[ft.Control] = [
                ft.Row(
                    [
                        scan_field,
                        ft.OutlinedButton("選ぶ", icon=ft.Icons.FOLDER_OPEN, on_click=pick_scan),
                        ft.FilledButton("走らせる", on_click=use_scan),
                    ],
                    wrap=True,
                ),
                ft.Text(scn["summary"]),
            ]
            if scn["lines"]:
                scn_c.append(
                    ft.Container(
                        ft.Text("\n".join(scn["lines"]), font_family="monospace", size=13, selectable=True),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        padding=12,
                        border_radius=8,
                    )
                )

            aud_c: list[ft.Control] = [ft.Text(aud["summary"])]
            if aud["warning"]:
                aud_c.append(err(f"注意: {aud['warning']}"))
            aud_c += [err(f) for f in aud["failures"]]
            if aud["key"]:
                if aud["error"]:
                    aud_c.append(err(aud["error"]))
                aud_c.append(
                    ft.Row(
                        [actor, action, detail, ft.FilledButton("一行足す", icon=ft.Icons.ADD, on_click=add)],
                        wrap=True,
                    )
                )
            else:
                aud_c.append(muted(aud["error"] or ""))

            rep_c: list[ft.Control] = [
                ft.FilledButton("報告を作る", icon=ft.Icons.DESCRIPTION_OUTLINED, on_click=make_report)
            ]
            if st["report"]:
                path, text = st["report"]
                rep_c += [
                    muted(f"書いた: {path}"),
                    ft.Container(
                        ft.Text(text, font_family="monospace", size=13, selectable=True),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        padding=12,
                        border_radius=8,
                    ),
                ]

            body.controls = [
                ft.Text(
                    "kagi — 係の机", theme_style=ft.TextThemeStyle.HEADLINE_SMALL, weight=ft.FontWeight.W_600
                ),
                muted(f"作業の場所: {c['dir']}"),
                card("在庫", inv_c),
                card("口", prt_c),
                card("機械", mch_c),
                card("走査", scn_c),
                card("記録", aud_c),
                card("報告", rep_c),
                muted("鍵の値はこの画面に出ない（K-13）。"),
            ]
            page.update()

        def path_of(field: ft.TextField) -> Path | None:
            v = (field.value or "").strip()
            return Path(v).expanduser() if v else None

        async def pick_ss(e) -> None:
            files = await picker.pick_files(dialog_title="ss -ltnp の写しを選ぶ")
            if files and files[0].path:
                ss_field.value = files[0].path
                await use_ss(e)
            elif files:
                toast("道が取れない（ブラウザで開いた時）。道を書いて「突き合わせる」")

        async def use_ss(e) -> None:
            st["ss"] = path_of(ss_field)
            render()

        async def collect(e) -> None:
            h = (mc_field.value or "").strip()
            if not h:
                toast("host を書く")
                return
            toast(f"{h} の写しを取っている")
            try:
                await asyncio.to_thread(collect_machine, d, h)
            except inventory.Refused as ex:
                toast(str(ex))
                return
            st["fix"] = None
            render()

        async def show_fix(e) -> None:
            h = (mc_field.value or "").strip()
            try:
                st["fix"] = fix_text(d, h)
            except inventory.Refused as ex:
                toast(str(ex))
                return
            render()

        async def pick_scan(e) -> None:
            path = await picker.get_directory_path(dialog_title="走査する場所を選ぶ")
            if path:
                scan_field.value = path
                await use_scan(e)

        async def use_scan(e) -> None:
            p = path_of(scan_field)
            st["scan"] = [p] if p else []
            render()

        async def add(e) -> None:
            vals = [(f.value or "").strip() for f in (actor, action, detail)]
            if not all(vals):
                toast("actor、action、detail の三つを書く")
                return
            try:
                key = audit.find_key()
                seq = audit.add(d / "audit.log", key, *vals)
            except audit.NoKey:
                toast("署名の鍵が無い（手引き §3）")
                return
            except (ValueError, OSError) as ex:
                toast(str(ex) if isinstance(ex, ValueError) else f"記録に書けない ({type(ex).__name__})")
                return
            action.value = detail.value = ""
            toast(f"足した: seq {seq}")
            render()

        async def make_report(e) -> None:
            try:
                st["report"] = await asyncio.to_thread(write_report, d, st["ss"], st["scan"], host=host())
            except OSError as ex:
                toast(f"報告を書けない ({type(ex).__name__})")
                return
            render()

        page.add(ft.Container(body, width=MAX_WIDTH, padding=16, expand=True))
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        render()

    return main


def run(d: Path) -> None:
    """PC の窓で開く。`KAGI_APP_WEB_PORT` がある時だけ、確かめるためにブラウザのタブで開く。"""
    import flet as ft

    port = os.environ.get(WEB_PORT_ENV, "").strip()
    if port.isdigit():
        ft.run(make_main(d), view=ft.AppView.WEB_BROWSER, host="127.0.0.1", port=int(port))
    else:
        ft.run(make_main(d))
