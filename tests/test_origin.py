# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed origin。ネットに出ない（偽のタイルを返す物に差し替える）。座標は本物でない値（35.0, 135.0）。"""

import io

import pytest
from PIL import Image
from test_photos import make_jpeg

from seed import cli, origin
from seed.records import Folder, Line, Observation

LAT, LON = 35.0, 135.0
PLACE = """## Data
- place_name: Address: 試験県試験市 (市区町村コード 99999)（出典: 国土地理院 逆ジオコーダ、確認日 2026-11-02）
- elevation: Elevation 12.3 m (DEM: 5m（レーザ）)（出典: 国土地理院 標高API、確認日 2026-11-02）
- landform: Landform: 扇状地 (扇状地; code 10501)（出典: 国土地理院 ベクトルタイル「地形分類（自然地形）」、確認日 2026-11-02）
- hazard: 土砂災害警戒区域: the field is outside; none within 1.0 km（出典: ハザードマップポータルサイト、確認日 2026-11-02）
- hazard: 洪水浸水想定区域: the field is INSIDE one (想定最大規模)（出典: ハザードマップポータルサイト、確認日 2026-11-02）
- soil: Soil type: 試験土 (X1). The soil map contains errors (誤差を含む), read from the map colour at the point（出典: 農研機構、日本土壌インベントリー (CC BY 4.0)、確認日 2026-11-02）
- history: 試しの碑 (memorial, 2.1 km NE; start_date: 1995)（出典: OpenStreetMap (ODbL)、確認日 2026-11-02）
- history: 試しの祠（路傍の祠、900 m 南）（出典: OpenStreetMap (ODbL)、確認日 2026-11-02）
- geology: 出典の無い行

## Record
(none)
"""


def png(color, size=256) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (size, size), color).save(buf, "PNG")
    return buf.getvalue()


SOLID = png((200, 220, 180, 255))
CLEAR = png((0, 0, 0, 0))


class FakeFetch:
    """層ごとに 404（None）、透明、色のどれかを返す。取った URL を数える。"""

    def __init__(self, missing=(), clear=()):
        self.missing, self.clear, self.urls = set(missing), set(clear), []

    def __call__(self, url):
        self.urls.append(url)
        layer = "soil" if "soil-inventory" in url else url.split("/")[-4]
        if layer in self.missing:
            return None
        if layer in self.clear:
            return CLEAR
        return SOLID

    def close(self):
        pass


@pytest.fixture
def field(seedfolder):
    """座標の入った観察一つ（写真一枚）と place.md のあるフォルダー。"""
    folder = Folder(seedfolder)
    folder.init()
    folder.place.write_text(PLACE, encoding="utf-8")
    make_jpeg(seedfolder / "photos" / "2026-11-05" / "142107.jpg", lat=LAT, lon=LON, size=(80, 60))
    obs = Observation(
        date="2026-11-05",
        time="14:21:07",
        photos=["photos/2026-11-05/142107.jpg"],
        location={"center": [LAT, LON], "points": 1, "extent_m": 40},
        language="ja",
        reading=[Line("overall", "読みの行は出さない", 0.8)],
    )
    obs.write(folder.observation_path(obs))
    return seedfolder


def use(monkeypatch, fetch, mp4=False):
    monkeypatch.setattr(origin, "HttpFetch", lambda: fetch)
    if not mp4:
        monkeypatch.setattr(origin, "ffmpeg_module", lambda: None)


def run(field, *extra):
    return cli.main(["origin", "--folder", str(field), "--size", "640x360", "--seconds", "0.5", *extra])


def test_tile_math_known_values():
    assert origin.world_px(0.0, 0.0, 1) == (256.0, 256.0)
    x, y, px, py = origin.tile_of(35.0, 135.0, 10)
    assert (x, y) == (896, 405)  # 35°N 135°E は z10 で 896/405
    assert px == pytest.approx(0.0) and 0 <= py < 256
    assert origin.metres_per_px(0.0, 0) == pytest.approx(156543.03, abs=0.01)


def test_scenes_skip_404_and_clear_and_fall_back_to_gif(field, monkeypatch, capsys):
    fetch = FakeFetch(missing={"soil", "ort_riku10", "lcmfc2"}, clear={"ort_USA10"})
    use(monkeypatch, fetch)
    assert run(field) == 0
    out, err = capsys.readouterr()
    day = max((field / "origin").glob("20*"))
    names = sorted(p.name for p in (day / "frames").glob("*.png"))
    assert names[:3] == ["01-std-z11.png", "02-std-z13.png", "03-std-z15.png"]
    kinds = [n.split("-", 1)[1].removesuffix(".png") for n in names]
    assert kinds == [
        "std-z11",
        "std-z13",
        "std-z15",
        "relief",
        "landform",  # lcmfc2 が 404 なので lcm25k_2012
        "flood",
        "sediment",  # 重ねる色が無くても、data 行があれば地図は出す
        "photo-1961",
        "photo-1974",
        "photo-1979",
        "photo-1984",
        "photo-1987",
        "photo-latest",
        "history",
        "own-photo",
    ]
    # 404 と透明の場面は省いて、そう出す
    assert "省いた: 土壌図（その場所にタイルが無い（404））" in out
    assert "省いた: 空中写真 1936〜1942年頃（その場所にタイルが無い（404））" in out
    assert "省いた: 空中写真 1945〜1950年（その場所のタイルが透明" in out
    # mp4 が無ければ GIF
    gif = day / "origin.gif"
    assert gif.exists() and not (day / "origin.mp4").exists()
    with Image.open(gif) as im:
        assert im.n_frames == len(names) and im.size == (640, 360)
    assert "imageio-ffmpeg" in err
    assert "公開するかはあなたが選びます" in out
    # 一回に取るのは上限以下。キャッシュに置く
    assert len(fetch.urls) <= origin.BUDGET
    assert (field / "origin" / "tiles" / "std" / "11").is_dir()
    assert list((field / "origin" / "tiles" / "soil").rglob("*.none"))


def test_captions_come_from_data_lines(field, monkeypatch, capsys):
    use(monkeypatch, FakeFetch(missing={"lcmfc2"}))
    assert run(field) == 0
    md = next((field / "origin").glob("20*/captions.md")).read_text(encoding="utf-8")
    # 英語の枠は日本語に、出典は行のまま
    assert "住所: 試験県試験市（市区町村コード 99999）" in md
    assert "標高 12.3 m（DEM: 5m（レーザ））" in md
    assert "洪水浸水想定区域: 畑はその中にある（想定最大規模）" in md
    assert "土砂災害警戒区域: 畑は外。1.0 km 以内に無い" in md
    assert "土壌図には誤差が含まれる" in md
    assert "国土地理院 標高API（2026-11-02）" in md
    assert "農研機構、日本土壌インベントリー（CC BY 4.0）の土壌図" in md
    assert "数値地図25000（土地条件）" in md  # 地形分類の出典は使った層の物
    assert "試しの碑（記念碑、約 2.1 km 北東）" in md and "試しの祠（路傍の祠、約 900 m 南）" in md
    assert "© OpenStreetMap contributors（ODbL）" in md
    assert "Claude が確認。確認日" in md and "https://maps.gsi.go.jp/development/ichiran.html" in md
    # 出典の無い行、Claude の読みの行、座標は入れない
    assert "出典の無い行" not in md and "読みの行は出さない" not in md
    assert "35.0" not in md and "135.0" not in md
    # 判定の語を書かない
    assert "べき" not in md and "しなさい" not in md


def test_cache_means_no_second_fetch(field, monkeypatch, capsys):
    first = FakeFetch()
    use(monkeypatch, first)
    assert run(field) == 0
    assert first.urls
    second = FakeFetch()
    use(monkeypatch, second)
    assert run(field) == 0
    assert second.urls == []
    assert "ネットから 0 枚" in capsys.readouterr().out


def test_budget_stops_fetching(field, monkeypatch, capsys):
    monkeypatch.setattr(origin, "BUDGET", 5)
    fetch = FakeFetch()
    use(monkeypatch, fetch)
    assert run(field) == 0
    assert len(fetch.urls) == 5
    assert "上限（5 枚）" in capsys.readouterr().out


def test_lat_lon_args_and_errors(seedfolder, monkeypatch, capsys):
    use(monkeypatch, FakeFetch())
    Folder(seedfolder).init()
    # 座標が無い
    assert run(seedfolder) == 1
    assert "中心の座標がありません" in capsys.readouterr().err
    # 片方だけ
    assert run(seedfolder, "--lat", "35.0") == 1
    # フォルダーの外へは書かない
    assert run(seedfolder, "--lat", "35.0", "--lon", "135.0", "--out", str(seedfolder.parent / "else")) == 1
    assert "中にだけ置きます" in capsys.readouterr().err
    # 座標を渡せば作る。place.md に行が無ければ地図だけ、史跡と写真の場面は省く
    assert run(seedfolder, "--lat", "35.0", "--lon", "135.0") == 0
    out = capsys.readouterr().out
    assert "省いた: 近くの史跡（place.md に history の行が無い）" in out
    assert "省いた: 本人の写真（一番新しい観察に写真が無い）" in out


def test_history_places_from_both_forms():
    lines = [
        Line(
            "history",
            "A (memorial, 2.1 km NE; start_date: 1995)（出典: OpenStreetMap (ODbL)、確認日 2026-11-02）",
        ),
        Line("history", "B（路傍の祠、900 m 南）（出典: OpenStreetMap (ODbL)、確認日 2026-11-02）"),
        Line("history", "壊れた行（出典: OpenStreetMap (ODbL)、確認日 2026-11-02）"),
    ]
    got = origin.history_places(origin.facts(lines, "ja"))
    assert [(p.name, p.metres, p.direction) for p in got] == [("A", 2100.0, "NE"), ("B", 900.0, "S")]
    assert origin.place_label(got[0], "en") == "A (memorial, about 2.1 km NE)"


def test_size_and_output_dir(tmp_path):
    assert origin.parse_size(None) == (1280, 720)
    assert origin.parse_size("641x361") == (640, 360)
    with pytest.raises(ValueError):
        origin.parse_size("big")
    f = Folder(tmp_path / "seed")
    assert origin.output_dir(f, None, "2026-11-04") == (tmp_path / "seed" / "origin" / "2026-11-04").resolve()
    with pytest.raises(ValueError):
        origin.output_dir(f, str(tmp_path / "x"), "2026-11-04")


def test_mp4_when_imageio_ffmpeg_is_there(field, monkeypatch, capsys):
    pytest.importorskip("imageio_ffmpeg")
    if origin.ffmpeg_module() is None:
        pytest.skip("ffmpeg の実行ファイルが無い")
    use(monkeypatch, FakeFetch(), mp4=True)
    assert (
        cli.main(["origin", "--folder", str(field), "--size", "320x240", "--seconds", "0.2", "--fps", "5"])
        == 0
    )
    day = next((field / "origin").glob("20*"))
    assert (day / "origin.mp4").stat().st_size > 0 and not (day / "origin.gif").exists()


def test_soil_is_laid_over_the_standard_map(tmp_path):
    """土壌図の透明な画素（区画の外）からは下の標準地図が見え、黒くならない。色の所は重なる。"""
    half = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    half.paste((200, 0, 0, 255), (0, 0, 128, 256))  # 左半分だけ土壌の色
    buf = io.BytesIO()
    half.save(buf, "PNG")
    soil, std = buf.getvalue(), png((0, 200, 0, 255))

    def fetch(url):
        return soil if "soil-inventory" in url else std

    plan = origin.Plan(LAT, LON, None, [], "ja", size=(640, 360))
    tiles = origin.Tiles(tmp_path / "tiles", fetch)
    frames, _ = origin.build(plan, tiles, origin.Fonts(origin.find_font()))
    img = next(f for f in frames if f.name == "soil").image
    colors = set(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())
    assert (0, 200, 0) in colors  # 下の地図がそのまま
    assert (150, 50, 0) in colors  # 土壌の色を 0.75 で重ねた所
    assert (0, 0, 0) not in colors
    src = next(f for f in frames if f.name == "soil").map_source
    assert "国土地理院 標準地図" in src and "日本土壌インベントリー（CC BY 4.0）" in src
