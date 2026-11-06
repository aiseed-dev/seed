# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path

import pytest

from seed import index
from seed.records import Connection, Line, Public


def make_public(id_: str, since: str = "2026-11-05", **kw) -> Public:
    p = Public(
        id=id_,
        place="徳島県 吉野川市",
        since=since,
        name="にじ",
        word="四年、何も入れていない畑。",
        coord=[34.05, 134.25],
        what=["自給農"],
        contact="discord:nijiseed",
        language="ja",
        **kw,
    )
    p.days["2026-11-05"] = [Line("overall", "草が大半", 0.8, "right")]
    return p


def write_connection(conn_dir: Path, to: str, src: str, day: str = "2026-11-05") -> None:
    d = conn_dir / to
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{day}-{src}.md").write_text(Connection(day, src, to, "よろしく").render() + "\n", encoding="utf-8")


def test_index_shape_counts_and_no_contact(tmp_path: Path):
    pub, conn = tmp_path, tmp_path / "connections"
    make_public("a-1", since="2026-11-04").write(pub / "a-1.md")
    make_public("b-2", since="2026-11-05").write(pub / "b-2.md")
    write_connection(conn, "a-1", "b-2")
    write_connection(conn, "a-1", "c-3")
    write_connection(conn, "b-2", "a-1")

    idx = index.build_index(pub, conn)
    assert set(idx) == {"built", "records", "total"}
    assert [r["id"] for r in idx["records"]] == ["b-2", "a-1"]  # 新しい公開が先
    a = idx["records"][1]
    assert a["connections"] == 2
    assert "contact" not in a
    assert a["coord"] == [34.05, 134.25]
    assert a["language"] == "ja" and a["observations"] == 1
    assert idx["total"] == {"records": 2, "connections": 3}


def test_index_skips_bad_files_with_warning(tmp_path: Path):
    make_public("ok-1").write(tmp_path / "ok-1.md")
    (tmp_path / "broken.md").write_text("---\nid: broken\n---\n", encoding="utf-8")
    bad = make_public("bad-1")
    bad.word = "電話 088-123-4567"
    bad.write(tmp_path / "bad-1.md")
    make_public("other-id").write(tmp_path / "named-wrong.md")
    with pytest.warns(UserWarning):
        idx = index.build_index(tmp_path, tmp_path / "connections")
    assert [r["id"] for r in idx["records"]] == ["ok-1"]


def test_write_index_writes_json(tmp_path: Path):
    make_public("a-1").write(tmp_path / "a-1.md")
    out = tmp_path / "index.json"
    idx = index.write_index(tmp_path, tmp_path / "connections", out)
    assert json.loads(out.read_text(encoding="utf-8"))["records"] == idx["records"]
    assert not list(tmp_path.glob("*.tmp"))


def test_index_empty_folder(tmp_path: Path):
    idx = index.build_index(tmp_path / "none", tmp_path / "none" / "connections")
    assert idx["records"] == [] and idx["total"] == {"records": 0, "connections": 0}
