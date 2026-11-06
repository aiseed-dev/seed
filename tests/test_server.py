# SPDX-License-Identifier: AGPL-3.0-or-later
"""サーバーのテスト。Claude は呼ばない（read.call を差し替える）。fieldnotes も差し替える。"""

import json
import re
import sys
import types
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest
from fastapi.testclient import TestClient

from seed import lookup as L
from seed import records as R
from seed.records import READING_KEYS, Line, Public
from seed.server import limits as LM
from seed.server import read as RD
from seed.server.main import create_app
from seed.server.settings import Settings

TOKEN = "t" * 32
INVITE = "inv-test-code-1234"
OTHER = "o" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 100


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        api_key="test-key",
        public_dir=tmp_path / "public",
        daily_usd=20.0,
        daily_reads=200,
        per_token_reads=10,
        per_ip_reads=20,
        model="claude-opus-5-5",
        skill_dir=tmp_path / "no-skill",
        invites={INVITE: "てすと"},
        open=True,  # 既存のテストは招待コード無しで打つ。認証のテストは open=False で別に
    )


@pytest.fixture(autouse=True)
def no_fieldnotes(monkeypatch):
    monkeypatch.setattr(L, "_load", lambda: None)
    L.clear_cache()
    yield
    L.clear_cache()


def fake_message(lines=None, stop_reason="end_turn", model="claude-opus-5-5", category=None):
    payload = {"lines": lines if lines is not None else []}
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category=category) if category else None,
        content=[SimpleNamespace(type="text", text=json.dumps(payload, ensure_ascii=False))],
        model=model,
        usage=SimpleNamespace(
            input_tokens=5000, output_tokens=1500, cache_read_input_tokens=8000, cache_creation_input_tokens=0
        ),
    )


@pytest.fixture
def calls(monkeypatch):
    """read.call を差し替え、渡された引数を残す。返す物は calls.reply で変えられる。"""
    seen = SimpleNamespace(kwargs=[], reply=fake_message())

    async def call(client, **kwargs):
        seen.kwargs.append(kwargs)
        if isinstance(seen.reply, Exception):
            raise seen.reply
        return seen.reply

    monkeypatch.setattr(RD, "call", call)
    return seen


def client_for(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def post_read(c: TestClient, photos=(JPEG,), **fields):
    data = {"token": TOKEN, **fields}
    files = [("photos", (f"{i}.jpg", p, "image/jpeg")) for i, p in enumerate(photos)]
    return c.post("/api/read", data={k: v for k, v in data.items() if v is not None}, files=files)


# ---------------------------------------------------------------- 起動、入口


def test_health_without_key_and_read_is_503(settings):
    c = client_for(replace(settings, api_key=None))
    h = c.get("/health").json()
    assert h["read"] is False and h["lookup"] is False and h["talk"] is False
    assert h["remaining"] == {"reads": 200, "talks": 300, "usd": 20.0}
    assert post_read(c).status_code == 503


def test_entry_page_empty(settings):
    r = client_for(settings).get("/")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "Claude と一緒に種を播く" in r.text
    assert "https://discord.gg/Q8pwMH2uTA" in r.text and 'pip install "seed-farm[app]"' in r.text
    assert "公開された記録 0 件" in r.text
    assert "default-src 'none'" in r.headers["content-security-policy"]


# ---------------------------------------------------------------- 読み


def test_read_shape_and_request(settings, calls):
    calls.reply = fake_message(
        [
            {"key": "next_to_observe", "text": "根元の土を一枚", "confidence": 0.7},
            {
                "key": "overall",
                "text": "草が大半。\n作物は見えない",
                "confidence": 0.8,
                "basis": "06 畑を読む",
            },
            {"key": "plants", "text": "今すぐ刈るべき", "confidence": 0.6},
            {"key": "water", "text": "水は見えない", "confidence": 1.7},
        ]
    )
    c = client_for(settings)
    r = post_read(
        c, photos=(JPEG, JPEG), record="今日は見ただけ", language="ja", place_data="- soil: 褐色低地土"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"lines", "data", "model", "usage", "markdown"}
    keys = [x["key"] for x in body["lines"]]
    assert keys == ["overall", "water", "uncertain", "next_to_observe"]  # 順と、判定の形の格下げ
    assert body["lines"][0] == {
        "key": "overall",
        "text": "草が大半。 作物は見えない（06 畑を読む）",
        "confidence": 0.8,
    }
    assert body["lines"][1]["confidence"] == 1.0
    assert body["data"] == []
    md = body["markdown"]
    assert md.startswith("## Reading (claude-opus-5-5)\n- overall: ") and "\n## Data\n(none)\n" in md
    for line in md.splitlines():
        assert line.startswith("## ") or line == "" or line == "(none)" or Line.parse(line)
    assert body["usage"]["output_tokens"] == 1500

    kw = calls.kwargs[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["fallbacks"] == "default" and kw["betas"] == [RD.FALLBACK_BETA]
    assert kw["output_config"]["effort"] == "medium"
    schema = kw["output_config"]["format"]["schema"]
    assert schema["properties"]["lines"]["items"]["properties"]["key"]["enum"] == list(READING_KEYS)
    assert "thinking" not in kw
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "判定の行" in kw["system"][0]["text"]  # skill/ が無いので組み込みの決まり
    assert "ja" in kw["system"][1]["text"]
    content = kw["messages"][0]["content"]
    # 写真ごとに「写真 <名>」の札、その後に写真。名は送ったファイルの名の幹（行の中で写真を指す名）
    assert [b["type"] for b in content] == ["text", "image", "text", "image", "text"]
    assert [content[0]["text"], content[2]["text"]] == ["写真 0", "写真 1"]
    assert "今日の一枚: <写真の名>" in kw["system"][1]["text"] and "問い: " in kw["system"][1]["text"]
    assert "<record>\n今日は見ただけ\n</record>" in content[-1]["text"]
    assert "- soil: 褐色低地土" in content[-1]["text"]


PREVIOUS = """---
date: '2026-11-01'
time: '09:10:00'
photos:
- photos/2026-11-01/091000.jpg
location:
  center: [34.0512, 134.2534]
  points: 1
  extent_m: 0
model: claude-opus-5-5
language: ja
---
## Reading (claude-opus-5-5)
- overall: 草丈 1 m のススキが大半 [0.80]  → farmer: right

## Record
- did: 北側を刈った
"""


def test_read_with_previous(settings, calls):
    calls.reply = fake_message(
        [
            {"key": "next_to_observe", "text": "刈った跡を一枚", "confidence": 0.6},
            {"key": "change", "text": "北側の草が低くなった", "confidence": 0.7},
            {"key": "overall", "text": "ススキが大半", "confidence": 0.8},
        ]
    )
    body = post_read(client_for(settings), previous=PREVIOUS, record="今日は見ただけ").json()
    assert [x["key"] for x in body["lines"]] == ["overall", "change", "next_to_observe"]
    assert "- change: 北側の草が低くなった [0.70]" in body["markdown"]
    text = calls.kwargs[0]["messages"][0]["content"][-1]["text"]
    assert "<previous>\ndate: 2026-11-01 09:10:00\n## Reading" in text and "- did: 北側を刈った" in text
    # 本人の言葉（直した事を含む）を先に読ませる
    assert text.index("\n<record>\n") < text.index("</data>") < text.index("\n<previous>\n")
    assert "食い違う所は本人の言葉を取る" in text
    assert "34.0512" not in text and "091000.jpg" not in text  # 前書きの座標と写真の道は渡さない
    assert "change は書かない" not in text
    assert "- change: 前の観察からの変化" in calls.kwargs[0]["system"][0]["text"]


def test_read_with_ask_adds_block(settings, calls):
    c = client_for(settings)
    assert post_read(c, ask="grow, soil", language="ja").status_code == 200
    text = calls.kwargs[-1]["messages"][0]["content"][-1]["text"]
    assert "<ask>" in text and "- grow: この土地で何が育つか" in text and "- soil: 土と地質と水はけ" in text
    assert "今日の一枚の行の次の overall でそれに答える" in text
    assert post_read(c, language="ja").status_code == 200
    assert "<ask>" not in calls.kwargs[-1]["messages"][0]["content"][-1]["text"]


def test_read_without_previous(settings, calls):
    post_read(client_for(settings))
    text = calls.kwargs[0]["messages"][0]["content"][-1]["text"]
    assert "<previous>" not in text and "change は書かない" in text


def test_read_uses_skill_dir(settings, calls, tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# 手引きの本体\n", encoding="utf-8")
    (skill / "06-畑を読む.md").write_text("# 06\n", encoding="utf-8")
    (skill / "01-立ち位置.md").write_text("# 01\n", encoding="utf-8")
    RD.skill_text.cache_clear()
    post_read(client_for(replace(settings, skill_dir=skill)))
    text = calls.kwargs[0]["system"][0]["text"]
    assert text.index("手引きの本体") < text.index("# 01") < text.index("# 06")


def test_read_refusal(settings, calls):
    calls.reply = fake_message(stop_reason="refusal", category="cyber")
    body = post_read(client_for(settings)).json()
    assert body["refused"] is True and body["category"] == "cyber" and body["lines"] == []


def test_read_upstream_errors(settings, calls):
    import httpx2

    calls.reply = anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.anthropic.com"))
    r = post_read(client_for(settings))
    assert r.status_code == 504 and r.json()["kind"] == "timeout"
    calls.reply = fake_message(stop_reason="max_tokens")
    assert post_read(client_for(settings)).status_code == 502


@pytest.mark.parametrize(
    ("photos", "fields", "status"),
    [
        ((), {}, 400),
        ((JPEG,) * 7, {}, 400),
        ((b"\xff\xd8\xff" + b"\0" * (2 * 1024 * 1024),), {}, 413),
        ((b"\x89PNG\r\n" + b"\0" * 10,), {}, 415),
        ((JPEG,), {"token": None}, 400),
        ((JPEG,), {"token": "short"}, 400),
        ((JPEG,), {"center": "north"}, 400),
        ((JPEG,), {"center": "95,10"}, 400),
        ((JPEG,), {"ask": "grow,weather"}, 400),
    ],
)
def test_read_rejects(settings, calls, photos, fields, status):
    assert post_read(client_for(settings), photos=photos, **fields).status_code == status
    assert calls.kwargs == []


def test_read_total_size_limit(settings, calls):
    big = b"\xff\xd8\xff" + b"\0" * (1900 * 1024)
    assert post_read(client_for(settings), photos=(big,) * 5).status_code == 413
    assert calls.kwargs == []


def test_read_per_token_limit(settings, calls):
    c = client_for(replace(settings, per_token_reads=2))
    assert [post_read(c).status_code for _ in range(3)] == [200, 200, 429]
    assert c.get("/health").json()["remaining"]["reads"] == 198


def test_read_budget_limit(settings, calls):
    # 一回 ≈ 5000×4 + 1500×20 + 8000×0.2 = $0.0516 / 1M 倍
    c = client_for(replace(settings, daily_usd=0.06))
    codes = [post_read(c).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_read_with_center_adds_data_lines(settings, calls, monkeypatch):
    monkeypatch.setattr(L, "_load", fake_fieldnotes)
    body = post_read(client_for(settings), center="34.0512,134.2534").json()
    assert body["data"][0]["key"] == "elevation"
    assert "<data>\n- elevation: Elevation 12 m" in calls.kwargs[0]["messages"][0]["content"][-1]["text"]
    assert "## Data\n- elevation: " in body["markdown"]


# ---------------------------------------------------------------- 照会


def fake_fieldnotes():
    class Site:
        def __init__(self, lat=None, lon=None, country=""):
            self.lat, self.lon, self.country = lat, lon, country

    seen.append(1)
    sources = {
        "elevation_jp": lambda s: (
            [f"- `data` Elevation 12 m (DEM: 5a). — 出典：国土地理院 標高API, https://x/?lat={s.lat}"],
            {},
        ),
        "soil_jp": lambda s: (
            ["- `data` Soil type: 褐色低地土 (B). — 出典：農研機構、日本土壌インベントリー, https://y"],
            {},
        ),
        "hazard_jp": lambda s: (_ for _ in ()).throw(RuntimeError("down")),
        "elevation": lambda s: (
            ["- `data` Elevation 13 m. — Open-Meteo elevation API (Copernicus DEM), https://z"],
            {},
        ),
        "wikipedia": lambda s: (["- `reference` 何か (1 km N). — Wikipedia, https://w"], {}),
    }
    return Site, sources, {"elevation_jp": "国土地理院 標高API"}


seen: list[int] = []


def test_lookup_lines_cache_and_failures(monkeypatch):
    monkeypatch.setattr(L, "_load", fake_fieldnotes)
    seen.clear()
    lines = L.data_lines(34.05123, 134.25341)
    assert [x.key for x in lines] == ["elevation", "soil"]  # 日本では世界の粗い地図と Wikipedia は使わない
    assert lines[0].text.startswith("Elevation 12 m (DEM: 5a)（出典: 国土地理院 標高API、確認日 ")
    assert "http" not in lines[0].text and lines[0].confidence is None
    assert Line.parse(lines[0].render()) == lines[0]
    L.data_lines(34.0514, 134.2532)  # 3 桁で同じ鍵
    assert len(seen) == 1  # 二回目はキャッシュから
    # 日本の外
    world = L.data_lines(48.85, 2.35)
    assert [x.key for x in world] == ["elevation"] and "Open-Meteo" in world[0].text


def test_lookup_with_fake_fieldnotes_modules(monkeypatch):
    """本物の _load が fieldnotes.lookup と fieldnotes.site を読むこと。"""
    monkeypatch.undo()
    pkg = types.ModuleType("fieldnotes")
    fl = types.ModuleType("fieldnotes.lookup")
    site = types.ModuleType("fieldnotes.site")
    site.Site = fake_fieldnotes()[0]
    fl.SOURCES = {"elevation": lambda s: (["- `data` Elevation 3 m. — Open-Meteo, https://z"], {})}
    fl.NAMES = {}
    pkg.lookup, pkg.site = fl, site
    for name, mod in (("fieldnotes", pkg), ("fieldnotes.lookup", fl), ("fieldnotes.site", site)):
        monkeypatch.setitem(sys.modules, name, mod)
    L.clear_cache()
    assert L.available()
    assert L.data_lines(-33.9, 18.4)[0].text.startswith("Elevation 3 m（出典: Open-Meteo、")


def test_api_lookup(settings, monkeypatch):
    c = client_for(settings)
    assert c.get("/api/lookup", params={"lat": 34.05, "lon": 134.25}).json() == {
        "data": [],
        "note": "このサーバーには照会（fieldnotes-farm）が無い",
    }
    monkeypatch.setattr(L, "_load", fake_fieldnotes)
    assert c.get("/health").json()["lookup"] is True
    data = c.get("/api/lookup", params={"lat": 34.05, "lon": 134.25}).json()["data"]
    assert data[0]["key"] == "elevation" and set(data[0]) == {"key", "text"}
    assert data[0]["text"].startswith("Elevation 12 m (DEM: 5a)")
    ja = c.get("/api/lookup", params={"lat": 34.05, "lon": 134.25, "language": "ja_JP"}).json()["data"]
    assert ja[0]["text"].startswith("標高 12 m（DEM: 5a）（出典: 国土地理院 標高API、確認日 ")  # 本人の言語で
    assert c.get("/api/lookup", params={"lat": 100, "lon": 0}).status_code == 400


# ---------------------------------------------------------------- 公開


def public_md(id_="2026-11-05-yoshino-ai-1", word="四年、何も入れていない畑。", extra_front="") -> str:
    p = Public(id=id_, place="徳島県 吉野川市", since="2026-11-05", name="にじ", word=word, language="ja")
    p.days["2026-11-05"] = [Line("overall", "草が大半", 0.8, "right"), Line("did", "見ただけ")]
    text = p.render()
    return text.replace("\n---\n", "\n" + extra_front + "---\n", 1) if extra_front else text


def test_publish_overwrite_and_withdraw(settings):
    c = client_for(settings)
    rid = "2026-11-05-yoshino-ai-1"
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": public_md()})
    assert r.status_code == 200, r.text
    assert r.json()["id"] == rid and r.json()["url"].endswith(f"/public/{rid}.md")
    assert (settings.public_dir / f"{rid}.md").is_file()
    assert c.get("/index.json").json()["total"]["records"] == 1
    got = c.get(f"/public/{rid}.md")
    assert got.headers["content-type"].startswith("text/markdown") and Public.parse(got.text).id == rid
    owners = json.loads((settings.public_dir / ".owners.json").read_text())
    assert owners == {rid: LM.token_hash(TOKEN)} and TOKEN not in json.dumps(owners)

    # 別の token からは上書きも取り下げもできない
    assert (
        c.post("/api/publish", json={"token": OTHER, "markdown": public_md(word="乗っ取り")}).status_code
        == 403
    )
    assert c.request("DELETE", f"/api/publish/{rid}", json={"token": OTHER}).status_code == 403
    # 同じ token なら上書きできる
    assert (
        c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(word="書き直し")}).status_code
        == 200
    )
    assert c.get("/index.json").json()["records"][0]["word"] == "書き直し"
    assert c.request("DELETE", f"/api/publish/{rid}", json={"token": TOKEN}).status_code == 200
    assert c.get("/index.json").json()["total"]["records"] == 0
    assert c.get(f"/public/{rid}.md").status_code == 404
    assert c.request("DELETE", f"/api/publish/{rid}", json={"token": TOKEN}).status_code == 404


@pytest.mark.parametrize(
    "markdown",
    [
        public_md(extra_front="email: a@b.jp\n"),  # 知らない鍵
        public_md(word="電話は 088-123-4567"),  # 個人情報の形
        public_md(word="<script>x</script>"),  # HTML
        public_md(id_="Bad_ID"),
        public_md(word="あ" * 201),
        "id: x\n",  # 前書きが無い
        "---\nid: [\n---\n",  # YAML が壊れている
    ],
)
def test_publish_rejects(settings, markdown):
    c = client_for(settings)
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": markdown})
    assert r.status_code == 400, r.text
    assert not list(settings.public_dir.glob("*.md"))


@pytest.mark.parametrize("public_url", ["https://seed.aiseed.dev", "https://seed.aiseed.dev/"])
def test_publish_url_uses_public_url(settings, public_url):
    # 127.0.0.1:8010 で叩かれても、答えの url は外から開ける物でないといけない
    c = TestClient(create_app(replace(settings, public_url=public_url)), base_url="http://127.0.0.1:8010")
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": public_md()})
    assert r.status_code == 200, r.text
    assert r.json()["url"] == "https://seed.aiseed.dev/public/2026-11-05-yoshino-ai-1.md"


def test_publish_url_without_public_url(settings):
    c = TestClient(create_app(settings), base_url="http://127.0.0.1:8010")
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": public_md()})
    assert r.json()["url"] == "http://127.0.0.1:8010/public/2026-11-05-yoshino-ai-1.md"


def test_public_url_from_env(monkeypatch):
    monkeypatch.setenv("SEED_PUBLIC_URL", " https://seed.aiseed.dev ")
    assert Settings.from_env().public_url == "https://seed.aiseed.dev"
    monkeypatch.delenv("SEED_PUBLIC_URL")
    assert Settings.from_env().public_url == ""


def test_publish_rejects_existing_file_without_owner_and_short_token(settings):
    c = client_for(settings)
    (settings.public_dir / "2026-11-05-yoshino-ai-1.md").write_text(public_md(), encoding="utf-8")
    assert c.post("/api/publish", json={"token": TOKEN, "markdown": public_md()}).status_code == 403
    assert c.post("/api/publish", json={"token": "x", "markdown": public_md(id_="new-1")}).status_code == 400


def test_public_file_paths(settings):
    c = client_for(settings)
    assert c.get("/public/..%2Fsecret.md").status_code == 404
    assert c.get("/public/.owners.json").status_code == 404
    assert c.get("/public/nothing.md").status_code == 404


# ---------------------------------------------------------------- 繋がり


def test_connect_once_a_day(settings):
    c = client_for(settings)
    c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(id_="a-1")})
    c.post("/api/publish", json={"token": OTHER, "markdown": public_md(id_="b-2")})

    r = c.post("/api/connect", json={"token": OTHER, "to": "a-1", "from": "b-2", "word": "近くです"})
    assert r.status_code == 200 and r.json() == {"count": 1}
    again = c.post("/api/connect", json={"token": OTHER, "to": "a-1", "from": "b-2", "word": "もう一度"})
    assert again.status_code == 429
    files = list((settings.public_dir / "connections" / "a-1").glob("*-b-2.md"))
    assert len(files) == 1 and files[0].read_text(encoding="utf-8").endswith("b-2 → a-1: 近くです\n")

    # 公開していない人は token から作った名前で
    anon = LM.token_hash("n" * 32)[:8]
    r = c.post("/api/connect", json={"token": "n" * 32, "to": "a-1", "from": anon, "word": "はじめまして"})
    assert r.json() == {"count": 2}
    idx = c.get("/index.json").json()
    assert {x["id"]: x["connections"] for x in idx["records"]} == {"a-1": 2, "b-2": 0}
    assert idx["total"]["connections"] == 2


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"token": TOKEN, "to": "b-2", "from": "x-9", "word": "名乗り"}, 403),  # 他人の id
        ({"token": OTHER, "to": "b-2", "from": "a-1", "word": "なりすまし"}, 403),
        ({"token": TOKEN, "to": "a-1", "from": "a-1", "word": "自分"}, 400),
        ({"token": TOKEN, "to": "none-1", "from": "a-1", "word": "居ない"}, 404),
        ({"token": TOKEN, "to": "b-2", "from": "a-1", "word": "あ" * 201}, 400),
        ({"token": TOKEN, "to": "b-2", "from": "a-1", "word": "  "}, 400),
        ({"token": TOKEN, "to": "b-2", "from": "a-1", "word": "a@b.jp に"}, 400),
        ({"token": TOKEN, "to": "b-2", "from": "A_1", "word": "形"}, 400),
    ],
)
def test_connect_rejects(settings, body, status):
    c = client_for(settings)
    c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(id_="a-1")})
    c.post("/api/publish", json={"token": OTHER, "markdown": public_md(id_="b-2")})
    assert c.post("/api/connect", json=body).status_code == status


# ---------------------------------------------------------------- Web の入口と閲覧


def test_entry_lists_records_escaped(settings):
    c = client_for(settings)
    c.post(
        "/api/publish", json={"token": TOKEN, "markdown": public_md(id_="a-1", word="藍の跡地 & <b>草</b>")}
    )
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(id_="a-1", word="藍の跡地 & 草")})
    assert r.status_code == 200
    page = c.get("/").text
    assert '<a href="/p/a-1">' in page and "藍の跡地 &amp; 草" in page
    assert "公開された記録 1 件" in page


def test_record_page(settings):
    c = client_for(settings)
    md = public_md(id_="a-1", extra_front="contact: discord:niji\n")
    assert c.post("/api/publish", json={"token": TOKEN, "markdown": md}).status_code == 200
    r = c.get("/p/a-1")
    assert r.status_code == 200
    t = r.text
    assert "<h1>にじ</h1>" in t and "徳島県 吉野川市" in t and "discord:niji" in t
    assert "<code>overall</code> 草が大半" in t and "[0.80]" in t and "→ 合う" in t
    assert "<code>did</code> 見ただけ" in t
    assert "<form" not in t and "seed のアプリで「ほかの人の畑を見たい」" in t  # 静的: 一言の欄は無い（設計書 §7.5）
    assert "/public/a-1.md" in t
    assert c.get("/p/none-1").status_code == 404
    assert c.get("/p/Bad_ID").status_code == 404


def test_record_page_escapes_lines(settings):
    c = client_for(settings)
    p = Public(id="x-1", place="吉野川市", since="2026-11-05", name="にじ", word="一言")
    p.days["2026-11-05"] = [Line("note", 'a "q" & b')]
    p.write(settings.public_dir / "x-1.md")
    t = c.get("/p/x-1").text
    assert "a &quot;q&quot; &amp; b" in t


def test_connect_without_token_from_web(settings):
    c = client_for(settings)
    c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(id_="a-1")})
    r = c.post("/api/connect", json={"to": "a-1", "from": "やまだ はなこ", "word": "近くで畑をしています"})
    assert r.status_code == 200, r.text
    assert r.json() == {"count": 1}
    files = list((settings.public_dir / "connections" / "a-1").glob("*.md"))
    assert len(files) == 1 and files[0].name.split("-n-")[1].endswith(".md")  # ファイル名に呼び名を使わない
    assert files[0].read_text(encoding="utf-8").endswith("やまだ_はなこ → a-1: 近くで畑をしています\n")
    # 同じ呼び名から同じ相手へは 1 日 1 回
    again = c.post("/api/connect", json={"to": "a-1", "from": "やまだ はなこ", "word": "もう一度"})
    assert again.status_code == 429
    assert c.get("/index.json").json()["records"][0]["connections"] == 1


def test_connect_without_token_limit_per_ip(settings):
    c = client_for(settings)
    for i in range(1, 8):
        c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(id_=f"r-{i}")})
    codes = [
        c.post("/api/connect", json={"to": f"r-{i}", "from": "たろう", "word": "こんにちは"}).status_code
        for i in range(1, 8)
    ]
    assert codes == [200] * LM.CONNECT_PER_IP + [429] * (7 - LM.CONNECT_PER_IP)
    # 断られた物（検査で落ちた物）は数えない。token のある送り手は IP で数えない
    anon = LM.token_hash(OTHER)[:8]
    ok = c.post("/api/connect", json={"token": OTHER, "to": "r-7", "from": anon, "word": "アプリから"})
    assert ok.status_code == 200


@pytest.mark.parametrize(
    ("name", "status"),
    [
        ("a-1", 403),  # 公開されている id を名乗る
        ("", 400),
        ("あ" * 41, 400),
        ("<b>x</b>", 400),
        ("x → y", 400),
        ("a@b.jp", 400),
    ],
)
def test_connect_without_token_rejects_names(settings, name, status):
    c = client_for(settings)
    c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(id_="a-1")})
    c.post("/api/publish", json={"token": OTHER, "markdown": public_md(id_="b-2")})
    assert c.post("/api/connect", json={"to": "b-2", "from": name, "word": "一言"}).status_code == status
    assert not (settings.public_dir / "connections" / "b-2").exists()


# ---------------------------------------------------------------- 上限の部品


def test_limits_reset_on_new_day(monkeypatch):
    lim = LM.Limits(daily_reads=1, per_token_reads=5, per_ip_reads=5, daily_usd=1.0)
    monkeypatch.setattr(LM.Limits, "today", staticmethod(lambda: "2026-11-05"))
    lim.take(TOKEN, "1.2.3.4")
    with pytest.raises(LM.LimitReached):
        lim.take(TOKEN, "1.2.3.4")
    monkeypatch.setattr(LM.Limits, "today", staticmethod(lambda: "2026-11-06"))
    lim.take(TOKEN, "1.2.3.4")
    assert TOKEN not in repr(lim.by_token)


def test_cost_estimate():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert LM.cost_usd(usage) == 24.0
    assert (
        LM.cost_usd({"cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 1_000_000}) == 5.2
    )


# ---------------------------------------------------------------- 招待コードと静的サイト（設計書 §7.5）


def test_invite_required_when_not_open(settings, calls):
    c = client_for(replace(settings, open=False))
    assert post_read(c).status_code == 403 and post_read(c).json()["error"] == "invite_required"
    assert post_read(c, invite="wrong").status_code == 403
    assert post_read(c, invite=INVITE).status_code == 200
    assert c.get("/api/lookup?lat=34&lon=134").status_code == 403
    assert c.get(f"/api/lookup?lat=34&lon=134&invite={INVITE}").status_code == 200
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": "x"})
    assert r.status_code == 403
    r = c.post("/api/connect", json={"to": "2026-11-05-yoshino-ai-1", "from": "x", "word": "y"})
    assert r.status_code == 403
    assert c.get("/health").status_code == 200  # これだけ開いている
    assert c.get("/").status_code == 200


def _write_invites(path: Path, text: str) -> None:
    """書き換えて mtime を確かに動かす（同じ ns に当たっても大きさか mtime で変わるように）。"""
    import os

    before = path.stat().st_mtime_ns if path.exists() else 0
    path.write_text(text, encoding="utf-8")
    os.utime(path, ns=(before + 10**9, before + 10**9))


def test_invites_reread_without_restart(settings, calls, tmp_path, caplog):
    inv = tmp_path / "invites.toml"
    _write_invites(inv, f'[codes]\n"{INVITE}" = "てすと"\n')
    c = client_for(replace(settings, open=False, invites={}, invites_path=inv))
    assert c.get(f"/api/lookup?lat=34&lon=134&invite={INVITE}").status_code == 200
    _write_invites(inv, '[codes]\n"inv-new-5678" = "あたらしい"\n')  # 失効と追加
    assert c.get(f"/api/lookup?lat=34&lon=134&invite={INVITE}").status_code == 403
    assert c.get("/api/lookup?lat=34&lon=134&invite=inv-new-5678").status_code == 200
    _write_invites(inv, '[codes\n"broken" = \n')  # 壊れた TOML は前の一覧を保つ
    with caplog.at_level("WARNING", logger="seed.server"):
        assert c.get("/api/lookup?lat=34&lon=134&invite=inv-new-5678").status_code == 200
    assert sum("読めない" in r.getMessage() for r in caplog.records) == 1
    assert c.get("/api/lookup?lat=34&lon=134&invite=broken").status_code == 403
    _write_invites(inv, f'[codes]\n"{INVITE}" = "てすと"\n')  # 直せば効く
    assert c.get(f"/api/lookup?lat=34&lon=134&invite={INVITE}").status_code == 200
    inv.unlink()  # ファイルが無くなれば閉じる
    assert c.get(f"/api/lookup?lat=34&lon=134&invite={INVITE}").status_code == 403


def test_invites_open_still_lets_anyone_in(settings, calls, tmp_path):
    inv = tmp_path / "invites.toml"
    _write_invites(inv, '[codes]\n"x" = "y"\n')
    c = client_for(replace(settings, open=True, invites={}, invites_path=inv))
    assert c.get("/api/lookup?lat=34&lon=134").status_code == 200


def test_connect_with_invite_uses_invite_name_and_rebuilds_site(settings, calls):
    c = client_for(replace(settings, open=False))
    md = (
        "---\nid: 2026-11-05-yoshino-ai-1\nplace: 徳島県 吉野川市\nsince: '2026-11-05'\nwhat: [自給農]\nnext: [売る]\n"
        "name: にじ\nword: 四年、何も入れていない畑。\nlanguage: ja\nobservations: 1\n---\n## 2026-11-05\n- did: 見ただけ\n"
    )
    assert c.post("/api/publish", json={"token": TOKEN, "markdown": md, "invite": INVITE}).status_code == 200
    site = settings.site_dir
    assert (site / "index.html").is_file() and (site / "p" / "2026-11-05-yoshino-ai-1.html").is_file()
    assert (site / "public" / "2026-11-05-yoshino-ai-1.md").is_file() and (site / "index.json").is_file()
    page = (site / "p" / "2026-11-05-yoshino-ai-1.html").read_text(encoding="utf-8")
    assert "seed のアプリで「ほかの人の畑を見たい」" in page and "<form" not in page  # 静的: 欄は無い
    assert "畑を始めてみませんか" in (site / "index.html").read_text(encoding="utf-8")
    assert not (site / ".owners.json").exists() and not (site / "connections").exists()
    r = c.post(
        "/api/connect",
        json={"to": "2026-11-05-yoshino-ai-1", "from": "ignored", "word": "見ました", "invite": INVITE},
    )
    assert r.status_code == 200 and r.json()["count"] == 1
    conn_dir = settings.connections_dir / "2026-11-05-yoshino-ai-1"
    text = "".join(f.read_text(encoding="utf-8") for f in conn_dir.glob("*"))
    assert "てすと" in text and "ignored" not in text  # 送り主は招待コードの呼び名
    assert "<dt>繋がり</dt><dd>1</dd>" in (site / "p" / "2026-11-05-yoshino-ai-1.html").read_text(
        encoding="utf-8"
    )
    # 取り下げると静的な頁も消える
    assert (
        c.request(
            "DELETE", "/api/publish/2026-11-05-yoshino-ai-1", json={"token": TOKEN, "invite": INVITE}
        ).status_code
        == 200
    )
    assert not (site / "p" / "2026-11-05-yoshino-ai-1.html").exists()


def test_head_and_robots(settings, calls):
    c = client_for(settings)
    assert c.head("/").status_code == 200
    assert c.get("/robots.txt").text.startswith("User-agent")
    assert c.head("/p/nope").status_code == 404


# ---------------------------------------------------------------- Pl@ntNet（設計書 §17）


def test_identify_endpoint(settings, calls, monkeypatch):
    from seed import identify as I

    c = client_for(settings)
    files = [("photos", ("1.jpg", JPEG, "image/jpeg"))]
    monkeypatch.delenv(I.ENV_KEY, raising=False)
    assert c.post("/api/identify", data={"token": TOKEN}, files=files).status_code == 503
    monkeypatch.setenv(I.ENV_KEY, "k-server")
    seen = {}

    def fake(images, key=None, language="ja", **kw):
        seen.update(n=len(images), key=key, language=language)
        return I.parse(
            {
                "results": [
                    {"score": 0.7, "species": {"scientificNameWithoutAuthor": "Miscanthus sinensis"}}
                ],
                "remainingIdentificationRequests": 10,
            }
        )

    monkeypatch.setattr(I, "identify", fake)
    r = c.post("/api/identify", data={"token": TOKEN, "language": "ja"}, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidates"][0]["scientific"] == "Miscanthus sinensis" and body["remaining"] == 10
    assert seen == {"n": 1, "key": "k-server", "language": "ja"}  # サーバーの鍵（systemd が渡すか、環境変数）
    assert c.post("/api/identify", data={"token": TOKEN}, files=files * 6).status_code == 400
    assert (
        c.post(
            "/api/identify",
            data={"token": TOKEN},
            files=[("photos", ("1.png", b"\x89PNG" + b"\0" * 9, "image/png"))],
        ).status_code
        == 415
    )
    closed = client_for(replace(settings, open=False))
    assert closed.post("/api/identify", data={"token": TOKEN}, files=files).status_code == 403
    assert (
        closed.post("/api/identify", data={"token": TOKEN, "invite": INVITE}, files=files).status_code == 200
    )


# ---------------------------------------------------------------- 公開の座標（設計書 §5.2）
# 座標は見本 34.0512, 134.2534 と、その近くの偽の値だけ（本物の畑の座標は使わない）

FINE = re.compile(r"\d+\.\d{3,}")


def _no_fine_coords(text: str) -> bool:
    return not R.fine_coords(text) and "34.0512" not in text and "134.2534" not in text


def test_publish_rounds_fine_coord_in_front(settings):
    c = client_for(settings)
    md = public_md(extra_front="coord: [34.0512, 134.2534]\n")
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": md})
    assert r.status_code == 200, r.text
    stored = (settings.public_dir / "2026-11-05-yoshino-ai-1.md").read_text(encoding="utf-8")
    assert Public.parse(stored).coord == [34.05, 134.25]
    assert _no_fine_coords(stored)
    # 静的ページと索引にも細かい座標は出ない
    site = settings.site_dir
    for path in [site / "index.html", site / "index.json", site / "p" / "2026-11-05-yoshino-ai-1.html"]:
        text = path.read_text(encoding="utf-8")
        assert _no_fine_coords(text) and not FINE.search(text), path
    idx = c.get("/index.json").json()
    assert idx["records"][0]["coord"] == [34.05, 134.25]
    assert not FINE.search(json.dumps(idx))
    page = c.get("/p/2026-11-05-yoshino-ai-1").text
    assert "34.05, 134.25" in page and not FINE.search(page)


@pytest.mark.parametrize(
    "word",
    [
        "畑は 34.051 134.253 のあたり",
        "34.0512, 134.2534",
        "場所 34.0521、134.2541",
        "(-34.0512,-134.2534)",
    ],
)
def test_publish_rejects_fine_coords_in_text(settings, word):
    c = client_for(settings)
    r = c.post("/api/publish", json={"token": TOKEN, "markdown": public_md(word=word)})
    assert r.status_code == 400, r.text
    assert "座標" in r.text
    assert not list(settings.public_dir.glob("*.md"))


def test_publish_rejects_fine_coords_in_lines(settings):
    p = Public(id="2026-11-05-yoshino-ai-1", place="徳島県", since="2026-11-05", name="にじ", word="畑")
    p.days["2026-11-05"] = [Line("note", "測った所 34.0498 134.2560")]
    c = client_for(settings)
    assert c.post("/api/publish", json={"token": TOKEN, "markdown": p.render()}).status_code == 400


def test_publish_keeps_coarse_numbers(settings):
    # 2 桁の座標と、座標でない数（確からしさ、日付、一つだけの小数）は通す
    c = client_for(settings)
    md = public_md(word="34.05, 134.25 のあたり。pH 6.123 だった", extra_front="coord: [34.05, 134.25]\n")
    assert c.post("/api/publish", json={"token": TOKEN, "markdown": md}).status_code == 200


@pytest.mark.filterwarnings("ignore:fine-")
def test_pages_and_index_have_no_fine_coords(settings, tmp_path):
    # 古い形で public/ に直に置かれた（サーバーを通っていない）細かい座標は、検査で落ちて索引にも頁にも出ない
    from seed import index as IX
    from seed.server import pages as PG

    settings.public_dir.mkdir(parents=True)
    fine = public_md(id_="fine-1").replace("\n---\n", "\ncoord: [34.0512, 134.2534]\n---\n", 1)
    (settings.public_dir / "fine-1.md").write_text(fine, encoding="utf-8")
    (settings.public_dir / "fine-2.md").write_text(public_md(id_="fine-2", word="34.0507 134.2529"), "utf-8")
    coarse = Public(
        id="coarse-1", place="徳島県", since="2026-11-05", name="にじ", word="畑", coord=[34.05, 134.25]
    )
    coarse.days["2026-11-05"] = [Line("overall", "草が大半", 0.8)]
    (settings.public_dir / "coarse-1.md").write_text(coarse.render(), encoding="utf-8")
    with pytest.warns(UserWarning):
        idx = IX.build_index(settings.public_dir, settings.connections_dir)
    assert [r["id"] for r in idx["records"]] == ["coarse-1"]
    assert not FINE.search(json.dumps(idx))
    assert not FINE.search(PG.entry_html(idx))
    assert not FINE.search(PG.record_html(coarse, 0))
    # 静的サイトにも /p/ にも出ない
    site = PG.write_site(settings)
    for rid in ("fine-1", "fine-2"):
        assert not (site / "p" / f"{rid}.html").exists() and not (site / "public" / f"{rid}.md").exists()
    for path in site.rglob("*"):
        if path.is_file():
            assert not FINE.search(path.read_text(encoding="utf-8")), path
    c = client_for(settings)
    assert c.get("/p/fine-1").status_code == 404 and c.get("/p/fine-2").status_code == 404
    assert c.get("/p/coarse-1").status_code == 200
