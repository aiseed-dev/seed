# SPDX-License-Identifier: AGPL-3.0-or-later
"""どれだけ残すか（seed.keep）。"""

from seed import keep
from seed.records import Folder, Observation


def _folder(tmp_path):
    f = Folder(tmp_path / "seed")
    f.init()
    (f.originals / "2026-11-05").mkdir(parents=True)
    (f.originals / "2026-11-05" / "142107.heic").write_bytes(b"x" * 3000)
    obs = Observation(date="2026-11-05", time="14:21:07", language="ja")
    raw = f.raw_dir(obs)
    raw.mkdir(parents=True)
    (raw / "answer.json").write_text("{}" * 500)
    return f, raw


def test_levels_and_what_each_keeps():
    assert keep.LEVELS == ("text", "photos", "research") and keep.DEFAULT == "photos"
    assert not keep.full_jpeg("text") and keep.full_jpeg("photos") and keep.full_jpeg("research")
    assert not keep.originals("photos") and keep.originals("research")
    assert not keep.raw("photos") and keep.raw("research")


def test_prune_plan_lists_only_what_the_level_drops(tmp_path):
    f, raw = _folder(tmp_path)
    assert keep.prune_plan(f, "research") == []
    plan = keep.prune_plan(f, "photos")
    assert [p for p, _ in plan] == [f.originals, raw]
    assert [b for _, b in plan] == [3000, 1000]
    assert keep.sizes(f)["originals"] == 3000 and keep.sizes(f)["raw"] == 1000


def test_prune_deletes_the_plan_and_nothing_else(tmp_path):
    f, raw = _folder(tmp_path)
    freed = keep.prune(keep.prune_plan(f, "text"))
    assert freed == 4000
    assert not f.originals.exists() and not raw.exists()
    assert f.place.exists() and f.photos.exists()


def test_free_bytes_walks_up_to_an_existing_parent(tmp_path):
    assert keep.free_bytes(tmp_path / "not" / "yet") > 0
