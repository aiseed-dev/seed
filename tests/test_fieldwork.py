# SPDX-License-Identifier: AGPL-3.0-or-later
"""畑の文字の仕事: seed lot / ledger / weather / procedure（記録の形 §15〜18、設計書 §5.7）。"""

import datetime as dt
import functools

import httpx

from seed import cli, ledger, lots, procedure, weather
from seed.records import DIRECTIVE_RE, Folder, Line, Observation, Plan

LAT, LON = 34.0512, 134.2534  # テストの座標（本物ではない）


def run(folder, *argv):
    return cli.main([*argv, "--folder", str(folder)])


# ---------------------------------------------------------------- lot


def test_lot_add_and_list(seedfolder, capsys):
    assert (
        run(
            seedfolder,
            "lot", "add", "--lot", "2026-aoi-kabocha", "--crop", "かぼちゃ", "--variety", "在来",
            "--place", "元田んぼの南", "--year", "2026", "--from", "2025-aoi-kabocha", "--note", "3 本から",
        )
        == 0
    )  # fmt: skip
    text = (seedfolder / "lots.md").read_text(encoding="utf-8")
    assert text.startswith("## Lots\n")
    want = (
        "- lot: 2026-aoi-kabocha | crop: かぼちゃ | variety: 在来 | place: 元田んぼの南 | year: 2026"
        " | from: 2025-aoi-kabocha | note: 3 本から"
    )
    assert want in text
    assert "[0." not in text  # 本人の行に確からしさは付かない
    capsys.readouterr()
    assert run(seedfolder, "lot", "list") == 0
    assert want in capsys.readouterr().out
    # 同じ名は足さない、名の形
    assert run(seedfolder, "lot", "add", "--lot", "2026-aoi-kabocha", "--crop", "a", "--variety", "b",
               "--place", "c", "--year", "2026") == 1  # fmt: skip
    assert run(seedfolder, "lot", "add", "--lot", "Bad Name", "--crop", "a", "--variety", "b",
               "--place", "c", "--year", "2026") == 1  # fmt: skip
    assert "同じ名のロット" in capsys.readouterr().err
    assert len(lots.read_lots(seedfolder / "lots.md")) == 1


def test_lot_keeps_farmer_text(tmp_path):
    path = tmp_path / "lots.md"
    path.write_text("メモ: 本人の文\n\n## Lots\n\n(none)\n\n## Notes\n- note: 残る\n", encoding="utf-8")
    lots.add_lot(tmp_path, lots.Lot("a-1", "豆", "在来", "北", "2026"))
    lots.add_lot(tmp_path, lots.Lot("a-2", "豆", "在来", "北", "2027", from_="a-1"))
    text = path.read_text(encoding="utf-8")
    assert "メモ: 本人の文" in text and "- note: 残る" in text and "(none)" not in text
    assert text.index("lot: a-1") < text.index("lot: a-2") < text.index("## Notes")
    assert [x.from_ for x in lots.read_lots(path)] == ["", "a-1"]


def test_lot_rejects_bar(tmp_path):
    try:
        lots.add_lot(tmp_path, lots.Lot("a-1", "豆 | x", "在来", "北", "2026"))
    except lots.LotError as e:
        assert e.word == "field_bar"
    else:
        raise AssertionError("| を通した")


# ---------------------------------------------------------------- ledger


def test_ledger_add_sum_invoice(seedfolder, capsys):
    seedfolder.mkdir(parents=True)
    (seedfolder / "seed.toml").write_text('name = "テストの名"\nlanguage = "ja"\n', encoding="utf-8")
    assert run(seedfolder, "ledger", "add", "--date", "2026-11-20", "--kind", "sale", "--yen", "1800",
               "--what", "かぼちゃ 3 本", "--lot", "2026-aoi-kabocha", "--to", "近所の A") == 0  # fmt: skip
    assert run(seedfolder, "ledger", "add", "--date", "2026-11-22", "--kind", "cost", "--yen", "600",
               "--what", "種（えん麦）") == 0  # fmt: skip
    assert run(seedfolder, "ledger", "add", "--date", "2026-11-25", "--kind", "help", "--yen", "5000",
               "--what", "書類を読んで手伝った", "--to", "近所の A") == 0  # fmt: skip
    assert run(seedfolder, "ledger", "add", "--date", "2026-12-01", "--kind", "sale", "--yen", "900",
               "--what", "大根", "--to", "近所の A") == 0  # fmt: skip
    text = (seedfolder / "ledger.md").read_text(encoding="utf-8")
    assert "- 2026-11-20 | sale | 1800 | かぼちゃ 3 本 | lot: 2026-aoi-kabocha | to: 近所の A" in text
    assert "- 2026-11-22 | cost | -600 | 種（えん麦）" in text  # 掛かった物は負
    entries = ledger.read_entries(seedfolder / "ledger.md")
    assert ledger.sums(ledger.month_entries(entries, "2026-11")) == {
        "sale": 1800, "cost": -600, "help": 5000, "other": 0, "net": 6200,
    }  # fmt: skip
    capsys.readouterr()
    assert run(seedfolder, "ledger", "sum", "--month", "2026-11") == 0
    out = capsys.readouterr().out
    assert "差引: 6200" in out and "掛かった (cost): -600" in out

    assert run(seedfolder, "ledger", "invoice", "--to", "近所の A", "--month", "2026-11") == 0
    today = dt.date.today().isoformat()
    inv = seedfolder / "ledger" / f"invoice-{today}-近所の-A.md"
    body = inv.read_text(encoding="utf-8")
    assert "- from: テストの名" in body and "- to: 近所の A" in body
    assert "- 2026-11-20 | sale | 1800 | かぼちゃ 3 本 | lot: 2026-aoi-kabocha" in body
    assert "書類を読んで手伝った" in body
    assert "種（えん麦）" not in body and "大根" not in body  # 掛かった物と別の月は入れない
    assert "- total: 6800 円" in body
    assert "税の計算はしていない" in body


def test_ledger_invoice_nothing_and_bad_month(seedfolder, capsys):
    assert run(seedfolder, "ledger", "invoice", "--to", "B", "--month", "2026-11") == 1
    assert not (seedfolder / "ledger").exists()
    assert "何も書いていない" in capsys.readouterr().err
    assert run(seedfolder, "ledger", "sum", "--month", "2026-13") == 1
    assert "月の形" in capsys.readouterr().err


def test_ledger_parses_trailing_bar():
    e = ledger.Entry.parse("- 2026-11-22 | cost | -600 | 種（えん麦） | ")
    assert e and e.what == "種（えん麦）" and e.yen == -600 and not e.lot


# ---------------------------------------------------------------- weather


def answer(days=("2026-11-05", "2026-11-06")):
    n = len(days)
    return {
        "latitude": 34.05,
        "longitude": 134.25,
        "daily": {
            "time": list(days),
            "temperature_2m_max": [18.24, None][:n],
            "temperature_2m_min": [9.1, None][:n],
            "precipitation_sum": [0.0, None][:n],
            "sunshine_duration": [26640.0, None][:n],
        },
    }


def mock_fetch(monkeypatch, handler):
    monkeypatch.setattr(
        weather, "fetch", functools.partial(weather.fetch, transport=httpx.MockTransport(handler))
    )


def test_weather_fetch_writes_rounded_and_replaces(seedfolder, monkeypatch, capsys):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=answer())

    mock_fetch(monkeypatch, handler)
    args = (
        "weather",
        "fetch",
        "--from",
        "2026-11-05",
        "--to",
        "2026-11-06",
        "--lat",
        str(LAT),
        "--lon",
        str(LON),
    )
    assert run(seedfolder, *args) == 0
    q = seen[0].url.params
    assert str(seen[0].url).startswith(weather.ARCHIVE_URL)
    assert q["latitude"] == "34.05" and q["longitude"] == "134.25"  # 2 桁に丸めて送る
    assert q["timezone"] == "Asia/Tokyo" and q["start_date"] == "2026-11-05" and q["end_date"] == "2026-11-06"
    assert q["daily"] == "temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration"
    assert "0512" not in str(seen[0].url) and "2534" not in str(seen[0].url)

    path = seedfolder / "weather" / "2026-11.md"
    text = path.read_text(encoding="utf-8")
    today = dt.date.today().isoformat()
    assert text.startswith(
        "見比べる一次資料: 気象庁 過去の気象データ検索 https://www.data.jma.go.jp/stats/etrn/"
    )
    assert (
        "- 2026-11-05: 最高 18.2 ℃、最低 9.1 ℃、降水 0.0 mm、日照 7.4 h"
        f"（出典: Open-Meteo 過去データ https://open-meteo.com/ 、確認日 {today}）"
    ) in text
    assert "2026-11-06:" not in text  # 値の無い日は書かない
    assert "1 日は値が無い" in capsys.readouterr().out
    assert "0512" not in text  # 座標はファイルに書かない

    # 同じ日は置き換え。本人が足した行は残る
    path.write_text(text.replace("## Data\n", "## Data\n\n- note: 本人の行\n"), encoding="utf-8")

    def handler2(request):
        a = answer(("2026-11-05",))
        a["daily"]["temperature_2m_max"] = [20.0]
        return httpx.Response(200, json=a)

    mock_fetch(monkeypatch, handler2)
    assert (
        run(seedfolder, *args[:3], "2026-11-05", "--to", "2026-11-05", "--lat", str(LAT), "--lon", str(LON))
        == 0
    )
    text = path.read_text(encoding="utf-8")
    assert text.count("- 2026-11-05:") == 1 and "最高 20.0 ℃" in text
    assert "- note: 本人の行" in text
    capsys.readouterr()
    assert run(seedfolder, "weather", "show", "--month", "2026-11") == 0
    assert "最高 20.0 ℃" in capsys.readouterr().out


def test_weather_failures_one_line(seedfolder, monkeypatch, capsys):
    mock_fetch(monkeypatch, lambda r: httpx.Response(500, json={"error": True, "reason": "down"}))
    args = (
        "weather",
        "fetch",
        "--from",
        "2026-11-05",
        "--to",
        "2026-11-05",
        "--lat",
        str(LAT),
        "--lon",
        str(LON),
    )
    assert run(seedfolder, *args) == 2
    err = capsys.readouterr().err.strip()
    assert "HTTP 500" in err and "\n" not in err

    def boom(request):
        raise httpx.ConnectError("no network")

    mock_fetch(monkeypatch, boom)
    assert run(seedfolder, *args) == 2
    err = capsys.readouterr().err.strip()
    assert "繋がらない" in err and "\n" not in err
    mock_fetch(monkeypatch, lambda r: httpx.Response(200, json={"daily": {"time": ["2026-11-05"]}}))
    assert run(seedfolder, *args) == 2
    assert not (seedfolder / "weather").exists()


def test_weather_center_from_place_or_observation(seedfolder, monkeypatch, capsys):
    folder = Folder(seedfolder)
    folder.init()
    assert run(seedfolder, "weather", "fetch", "--from", "2026-11-05", "--to", "2026-11-05") == 1
    assert "座標が無い" in capsys.readouterr().err
    obs = Observation(date="2026-11-05", time="14:21:07", location={"center": [LAT, LON], "points": 1})
    obs.write(folder.observation_path(obs))
    assert weather.place_center(folder) == (LAT, LON)
    folder.place.write_text("## Data\n(none)\n\n## Record\n- center: 34.0712, 134.2034\n", encoding="utf-8")
    assert weather.place_center(folder) == (34.0712, 134.2034)
    seen = []

    def handler(request):
        seen.append(request.url.params["latitude"])
        return httpx.Response(200, json=answer(("2026-11-05",)))

    mock_fetch(monkeypatch, handler)
    assert run(seedfolder, "weather", "fetch", "--from", "2026-11-05", "--to", "2026-11-05") == 0
    assert seen == ["34.07"]


def test_weather_bad_range(seedfolder, capsys):
    future = (dt.date.today() + dt.timedelta(days=3)).isoformat()
    assert run(seedfolder, "weather", "fetch", "--from", "2026-11-05", "--to", future,
               "--lat", str(LAT), "--lon", str(LON)) == 2  # fmt: skip
    assert "日の範囲" in capsys.readouterr().err


# ---------------------------------------------------------------- procedure


JUDGEMENT_WORDS = (
    "許可が要る",
    "許可は要らない",
    "要らない",
    "すべき",
    "べき",
    "しなければならない",
    "しなさい",
)


def make_records(folder: Folder):
    folder.init()
    folder.add_place_data(
        [
            Line(
                "place_name",
                "住所: 徳島県テスト市見本町（市区町村コード 00000）（出典: 国土地理院、確認日 2026-11-05）",
            ),
            Line(
                "parcel",
                "筆ポリゴン: 畑の地点は 1,234 m² の筆の中にある。2020 年に 畑 と読まれた（id x）。"
                "（出典: 農林水産省 筆ポリゴン、確認日 2026-11-05）",
            ),
        ]
    )
    plan = Plan.new("ja", today="2026-11-06")
    plan.say("decided", "冬はえん麦を播く")
    plan.say("decided", "耕さない")
    plan.write(folder.plan)


def test_procedure_fills_from_records_without_judgement(seedfolder, capsys):
    folder = Folder(seedfolder)
    make_records(folder)
    assert run(seedfolder, "procedure", "nochi-3jo") == 0
    out = capsys.readouterr().out
    assert "判定ではない" in out
    d = seedfolder / "procedures" / "nochi-3jo"
    check = (d / "checklist.md").read_text(encoding="utf-8")
    draft = (d / "draft.md").read_text(encoding="utf-8")
    sources = (d / "sources.md").read_text(encoding="utf-8")
    for text in (check, draft, sources):
        assert text.startswith("これは AI の下書きで、判定ではない。出す前に農業委員会で確かめる。")
        for w in JUDGEMENT_WORDS:
            assert w not in text, w
        assert not DIRECTIVE_RE.search(text)
    assert "- location: 土地の所在（同 第二号） = 徳島県テスト市見本町" in draft
    assert "概算 1,234 m²" in draft and "測量や登記の数ではない" in draft
    assert "2020 年に 畑 と読まれた" in draft
    assert "冬はえん麦を播く；耕さない（下書き: plan.md の decided）" in draft
    assert "- applicant: " in draft and "（本人が書く）" in draft
    # checklist は出典付き（url と確認日）
    items = [l for l in check.splitlines() if l.startswith("- [ ] ")]
    assert len(items) == len(procedure.CHECKLIST)
    assert all("（出典: " in l and "確認日 " in l for l in items)
    assert "https://laws.e-gov.go.jp/law/327M50010000079" in check  # 施行規則
    for url in (procedure.LAW, procedure.REI, procedure.KISOKU):
        assert url in sources


def test_procedure_keeps_farmer_marks_and_lines(seedfolder, capsys):
    folder = Folder(seedfolder)
    make_records(folder)
    assert run(seedfolder, "procedure", "nochi-3jo") == 0
    d = seedfolder / "procedures" / "nochi-3jo"
    check = (d / "checklist.md").read_text(encoding="utf-8")
    check = check.replace("- [ ] registry: ", "- [x] registry: ").replace(
        "## Record\n\n(none)", "## Record\n\n- [ ] 印鑑を持って行く"
    )
    (d / "checklist.md").write_text(check, encoding="utf-8")
    draft = (d / "draft.md").read_text(encoding="utf-8")
    draft = draft.replace(
        "- chiban: 地番（同 第二号） = （本人が書く）", "- chiban: 地番（同 第二号） = 123 番"
    )
    draft += "- said: 窓口で様式をもらった\n"
    (d / "draft.md").write_text(draft, encoding="utf-8")
    plan = Plan.read(folder.plan)
    plan.say("decided", "春に大豆")
    plan.write(folder.plan)

    assert run(seedfolder, "procedure", "nochi-3jo") == 0
    assert "[x] 1 個、本人の行 2 行" in capsys.readouterr().out
    check = (d / "checklist.md").read_text(encoding="utf-8")
    assert "- [x] registry: " in check and "- [ ] window: " in check
    assert "- [ ] 印鑑を持って行く" in check
    draft = (d / "draft.md").read_text(encoding="utf-8")
    assert "- chiban: 地番（同 第二号） = 123 番" in draft  # 本人が書き換えた欄は残る
    assert "春に大豆" in draft  # 下書きの欄は置き換わる
    assert "- said: 窓口で様式をもらった" in draft
    assert draft.count("- chiban:") == 1


def test_procedure_empty_folder(seedfolder, capsys):
    assert run(seedfolder, "procedure", "nochi-3jo") == 0
    assert "埋めた欄は無い" in capsys.readouterr().out
    draft = (seedfolder / "procedures" / "nochi-3jo" / "draft.md").read_text(encoding="utf-8")
    assert "- location: 土地の所在（同 第二号） = （本人が書く）" in draft


def test_new_files_not_in_public(seedfolder):
    """lots、ledger、weather、procedures は公開ファイルの組み立てに入らない（publish は観察の行だけを読む）。"""
    folder = Folder(seedfolder)
    make_records(folder)
    lots.add_lot(seedfolder, lots.Lot("a-1", "豆", "在来", "北", "2026"))
    assert run(seedfolder, "procedure", "nochi-3jo") == 0
    assert not list((seedfolder / "public").glob("*"))
