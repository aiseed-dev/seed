# SPDX-License-Identifier: AGPL-3.0-or-later
"""写真を場所ごとに日の順に（album）。"""


def test_growth_takes_one_photo_a_day_from_the_place_seen_on_most_days(monkeypatch):
    """公開は成長の記録。同じ場所を一番多くの日に撮った所から、日ごとに一枚。二日以上に渡る場所が無ければ空。"""
    import datetime as dt

    from seed import album
    from seed.records import Observation

    def obs(day, rels):
        return Observation(date=day, time="09:00:00", photos=rels)

    def shot(rel, day, hour):
        return album.Shot(rel, dt.datetime.fromisoformat(f"{day}T{hour:02d}:00:00"), 34.0, 134.0)

    a = obs("2026-11-01", ["photos/2026-11-01/a1.jpg", "photos/2026-11-01/a2.jpg", "photos/2026-11-01/x.jpg"])
    b = obs("2026-11-03", ["photos/2026-11-03/b1.jpg", "photos/2026-11-03/y.jpg"])
    spots = [
        album.Spot(1, [shot("photos/2026-11-01/x.jpg", "2026-11-01", 8)]),
        album.Spot(
            2,
            [
                shot("photos/2026-11-01/a1.jpg", "2026-11-01", 9),
                shot("photos/2026-11-01/a2.jpg", "2026-11-01", 10),
                shot("photos/2026-11-03/b1.jpg", "2026-11-03", 9),
            ],
        ),
        album.Spot(0, [shot("photos/2026-11-03/y.jpg", "2026-11-03", 11)]),
    ]
    monkeypatch.setattr(album, "by_place", lambda folder, within_m=album.SPOT_M: spots)
    assert album.growth(None, [a, b]) == {
        "2026-11-01": "photos/2026-11-01/a1.jpg",
        "2026-11-03": "photos/2026-11-03/b1.jpg",
    }
    assert album.growth(None, [a]) == {}  # 一日だけでは成長の記録にならない
