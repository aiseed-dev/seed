# SPDX-License-Identifier: AGPL-3.0-or-later
"""照会の data 行の日本語化（server/lookup_ja.py）。枠の文は fieldnotes-farm の lookup_jp.py と lookup.py の物。"""

from __future__ import annotations

from seed.records import Line
from seed.server import lookup as L
from seed.server import lookup_ja as J


def test_is_ja():
    assert J.is_ja("ja") and J.is_ja("ja-JP") and J.is_ja("ja_JP")
    assert not J.is_ja("en") and not J.is_ja("") and not J.is_ja(None)


def test_address():
    assert (
        J.to_ja("Address: 徳島県石井町 高川原 (市区町村コード 36341)")
        == "住所: 徳島県石井町 高川原（市区町村コード 36341）"
    )
    assert (
        J.to_ja("Address: none at this point (sea or outside Japan)")
        == "住所: この地点には無い（海か日本の外）"
    )


def test_parcel():
    caveat = (
        ". 筆ポリゴン are reference for the position and shape of farmland, drawn by hand over aerial "
        "photos for the 面積調査 with 田/畑 read by eye; they show neither 筆界 nor rights"
    )
    out = J.to_ja(
        "Parcel (筆ポリゴン): the field point lies in no parcel (land outside the 面積調査, such as a garden); within 100 m, 27 parcels (26 田, 1 畑)"
        + caveat
    )
    assert (
        out
        == "筆ポリゴン: 畑の地点はどの筆にも入らない（庭など、面積調査の外の土地）。100 m 以内に 27 筆（田 26、畑 1）。"
        + J.FUDE_CAVEAT_JA
    )
    out = J.to_ja(
        "Parcel (筆ポリゴン): the field point lies in a parcel of 1517 m², read as 田 in 2020 (id abc-1); within 100 m, 4 other parcels (4 田)"
        + caveat
    )
    assert (
        out
        == "筆ポリゴン: 畑の地点は 1517 m² の筆の中にある。2020 年に 田 と読まれた（id abc-1）。100 m 以内に他に 4 筆（田 4）。"
        + J.FUDE_CAVEAT_JA
    )
    nav = J.to_ja(
        "全国農地ナビ (eMAFF農地ナビ): the 農業委員会's farmland map, with the 農振 zoning and whether a parcel is idle; it takes no coordinates in a link, so search the address above"
    )
    assert (
        nav.startswith("全国農地ナビ（eMAFF農地ナビ）: 農業委員会の農地の地図。") and "上の住所で探す" in nav
    )


def test_elevation_and_landform():
    assert J.to_ja("Elevation 6.9 m (DEM: 1m（レーザ）)") == "標高 6.9 m（DEM: 1m（レーザ））"
    assert J.to_ja("Elevation: no value here in the GSI DEM") == "標高: 国土地理院の DEM にこの地点の値が無い"
    assert (
        J.to_ja("Landform: 氾濫平野・海岸平野 (氾濫平野; code 3030101)")
        == "地形分類: 氾濫平野・海岸平野（氾濫平野、コード 3030101）"
    )
    assert J.to_ja("Made ground: unknown class (?; code 9)") == "人工地形: 不明な区分（?、コード 9）"
    assert J.to_ja("Landform: not mapped at this point") == "地形分類: この地点は未整備"


def test_faults_and_hazard():
    assert (
        J.to_ja(
            "Active faults: nearest fault line 3.0 km SW; on the other side 4.0 km SE (an estimate: red lines read by colour from the map image, searched 4.1 km round; the tiles carry no fault names)"
        )
        == "活断層: 最も近い断層線は 3.0 km 南西。反対側に 4.0 km 南東（推定: 地図の画像の赤い線を色で読んだ物。4.1 km の範囲を探した。タイルに断層の名は無い）"
    )
    assert (
        J.to_ja(
            "Active faults: nearest fault line 190 m S (an estimate: red lines read by colour from the map image, searched 1.0 km round; the tiles carry no fault names)"
        )
        == "活断層: 最も近い断層線は 190 m 南（推定: 地図の画像の赤い線を色で読んだ物。1.0 km の範囲を探した。タイルに断層の名は無い）"
    )
    assert (
        J.to_ja("Active faults: no fault line on the 活断層図 within 4.1 km")
        == "活断層: 4.1 km 以内に活断層図の断層線は無い"
    )
    assert J.to_ja(
        "Active faults: no 活断層図 sheet covers this area (it maps the faults near cities only)"
    ).startswith("活断層: この範囲を覆う活断層図の図葉が無い")
    assert (
        J.to_ja("土砂災害警戒区域: the field is outside; none within 1.0 km")
        == "土砂災害警戒区域: 畑は外。1.0 km 以内に無い"
    )
    assert (
        J.to_ja("土砂災害警戒区域: the field is outside; nearest 140 m S (土石流)")
        == "土砂災害警戒区域: 畑は外。最も近い物は 140 m 南（土石流）"
    )
    assert (
        J.to_ja("洪水浸水想定区域: the field is INSIDE one (想定最大規模)")
        == "洪水浸水想定区域: 畑はその中にある（想定最大規模）"
    )


def test_soil():
    assert (
        J.to_ja(
            "Soil type: 細粒質水田化褐色低地土 (F4c1t1). 次表層の土性が重埴土である水田化褐色低地土。 The soil map contains errors (誤差を含む), read from the map colour at the point"
        )
        == "土壌: 細粒質水田化褐色低地土（F4c1t1）。次表層の土性が重埴土である水田化褐色低地土。 土壌図には誤差が含まれる。地点の地図の色から読んだ"
    )
    assert (
        J.to_ja(
            "Soil type: 褐色低地土 (B). The soil map contains errors (誤差を含む), read from the map colour at the point"
        )
        == "土壌: 褐色低地土（B）。土壌図には誤差が含まれる。地点の地図の色から読んだ"
    )
    assert (
        J.to_ja("Soil type: the soil map has no tile here (outside its coverage)")
        == "土壌: 土壌図のタイルがこの地点に無い（範囲の外）"
    )
    assert (
        J.to_ja("Soil type: not mapped at this point (no colour on the soil map)")
        == "土壌: この地点は未整備（土壌図に色が無い）"
    )
    assert (
        J.to_ja(
            "Soil type: the map's colour here, RGB (1, 2, 3), is not in its legend; not guessed. Look at the map: https://x/#5/34/134"
        )
        == "土壌: この地点の地図の色 RGB (1, 2, 3) は凡例に無い。推測しない。地図を見る: https://x/#5/34/134"
    )


def test_historic():
    assert (
        J.to_ja(
            "慶応2年洪水痕跡 (memorial, 2.1 km NE; hazard:name: 慶応2年寅の大水（1866年9月15日）; start_date: 1995)"
        )
        == "慶応2年洪水痕跡（記念碑、2.1 km 北東。災害の名: 慶応2年寅の大水（1866年9月15日）。年代: 1995）"
    )
    assert (
        J.to_ja("前山峰のお地蔵さん (wayside_shrine, 2.9 km S)")
        == "前山峰のお地蔵さん（路傍の祠、2.9 km 南）"
    )
    assert (
        J.to_ja("田中家住宅 (yes, 1.1 km N; wikipedia: ja:田中家住宅 (石井町))")
        == "田中家住宅（史跡（種類の記載なし）、1.1 km 北。Wikipedia: ja:田中家住宅 (石井町)）"
    )
    assert J.to_ja("古い橋 (bridge, 0.3 km W)") == "古い橋（bridge、0.3 km 西）"  # 表に無い種類は英語のまま


def test_unknown_frame_passes_through():
    assert J.to_ja("Something new the lookup says") == "Something new the lookup says"


def _fake():
    class Site:
        def __init__(self, lat=None, lon=None, country=""):
            self.lat, self.lon, self.country = lat, lon, country

    sources = {
        "elevation_jp": lambda s: (
            ["- `data` Elevation 12 m (DEM: 5a). — 出典：国土地理院 標高API, https://x"],
            {},
        ),
        "hazard_jp": lambda s: (
            [
                "- `data` 洪水浸水想定区域: the field is outside; none within 1.0 km. — 出典：ハザードマップポータルサイト, https://h"
            ],
            {},
        ),
    }
    return Site, sources, {"elevation_jp": "国土地理院 標高API"}


def test_data_lines_language(monkeypatch):
    monkeypatch.setattr(L, "_load", _fake)
    L.clear_cache()
    en = L.data_lines(34.05, 134.25)
    ja = L.data_lines(34.05, 134.25, "ja")  # 二回目はキャッシュから、言語だけ違う
    assert en[0].text.startswith("Elevation 12 m (DEM: 5a)（出典: 国土地理院 標高API、確認日 ")
    assert ja[0].text.startswith("標高 12 m（DEM: 5a）（出典: 国土地理院 標高API、確認日 ")
    assert ja[1].text.startswith(
        "洪水浸水想定区域: 畑は外。1.0 km 以内に無い（出典: ハザードマップポータルサイト、確認日 "
    )
    assert [x.key for x in ja] == ["elevation", "hazard"]
    assert Line.parse(ja[0].render()) == ja[0]
    # ja でない言語は英語のまま
    assert L.data_lines(34.05, 134.25, "fr")[0].text == en[0].text
