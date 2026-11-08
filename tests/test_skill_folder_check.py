# SPDX-License-Identifier: AGPL-3.0-or-later
"""skill-folder/check.py（読むだけの道具）のテスト。"""

import importlib.util
import zipfile
from pathlib import Path

import pytest
from test_photos import make_jpeg

SCRIPT = Path(__file__).resolve().parent.parent / "skill-folder" / "check.py"

LAT, LON = 34.0512, 134.2534
COORD_TEXTS = ("34.05", "134.25", "34,05", "134,25")


@pytest.fixture(scope="module")
def check():
    spec = importlib.util.spec_from_file_location("skill_folder_check", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(check, capsys, *argv) -> tuple[int, list[str]]:
    code = check.main(list(map(str, argv)))
    out = capsys.readouterr().out
    lines = out.splitlines()
    for line in lines:
        assert not any(t in line for t in COORD_TEXTS), line
    return code, lines


def observation(field: Path, name: str, photos: list[str], lat: float, lon: float, extent: int) -> Path:
    p = field / "observations" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\n"
        "date: '2026-11-05'\n"
        "time: '14:21:07'\n"
        f"photos: [{', '.join(photos)}]\n"
        "location:\n"
        f"  center: [{lat}, {lon}]\n"
        "  points: 1\n"
        f"  extent_m: {extent}\n"
        "model: claude-opus-5-5\n"
        "language: ja\n"
        "---\n\n"
        "## Reading (claude-opus-5-5)\n"
        "- overall: 草が大半 [0.80]\n",
        encoding="utf-8",
    )
    return p


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_help_does_no_work(check, capsys):
    with pytest.raises(SystemExit) as e:
        check.main(["--help"])
    assert e.value.code == 0
    assert "compare" in capsys.readouterr().out


def test_bad_args_exit_2(check, tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        check.main(["compare", str(tmp_path)])  # --keep が無い
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        check.main(["refs", str(tmp_path / "無い畑")])
    assert e.value.code == 2


def test_compare_counts_per_file_zip_entries_and_jpeg(check, tmp_path, capsys):
    keep = tmp_path / "originals"
    keep.mkdir()
    (keep / "a.heic").write_bytes(b"same-content")
    field = tmp_path / "field"
    make_jpeg(field / "photos" / "2026-11-05" / "142107.jpg")
    make_jpeg(field / "photos" / "2026-11-06" / "080000-1.jpg", taken="2026:11:06 08:00:00")

    cand = tmp_path / "uploads"
    cand.mkdir()
    # 中身の同じ二つは、二つと数える
    (cand / "one.heic").write_bytes(b"same-content")
    (cand / "two.heic").write_bytes(b"same-content")
    # 時刻で JPEG が在る写真（中身は違う）
    make_jpeg(cand / "IMG_1.JPG", size=(30, 30))
    # 何処にも無い写真
    make_jpeg(cand / "IMG_2.JPG", taken="2026:10:01 09:00:00", size=(31, 31))
    # zip: 残す方と同じ物、-1 の付いた JPEG が在る写真、無い物
    with zipfile.ZipFile(cand / "Photos.zip", "w") as zf:
        zf.writestr("x/a.heic", b"same-content")
        zf.write(make_jpeg(tmp_path / "src" / "z.jpg", taken="2026:11:06 08:00:00", size=(33, 33)), "z.jpg")
        zf.writestr("note.txt", b"other")
    before = snapshot(tmp_path)

    code, lines = run(check, capsys, "compare", "--keep", keep, "--photos", field, cand)
    assert code == 0
    assert "  同じ物が在る 3、JPEG で入っている 2、見つからない 2" in lines
    assert "  見つからない: IMG_2.JPG" in lines
    assert "  見つからない: Photos.zip:note.txt" in lines
    assert snapshot(tmp_path) == before  # 何も書かず、消さない


def test_compare_without_photos_does_not_look_for_jpeg(check, tmp_path, capsys):
    keep = tmp_path / "keep"
    keep.mkdir()
    cand = make_jpeg(tmp_path / "IMG_1.JPG")
    code, lines = run(check, capsys, "compare", "--keep", keep, cand)
    assert code == 0
    assert "  同じ物が在る 0、JPEG で入っている 0、見つからない 1" in lines


def test_near_gives_metres_only(check, tmp_path, capsys):
    field = tmp_path / "field"
    observation(field, "2026-11-05-142107.md", ["photos/2026-11-05/142107.jpg"], LAT, LON, 12)
    observation(field, "2026-11-06-080000.md", [], LAT + 0.0009, LON, 30)  # 北へ約 100 m
    up = tmp_path / "uploads"
    make_jpeg(up / "near.jpg", lat=LAT + 0.0001, lon=LON)  # 約 11 m
    make_jpeg(up / "far.jpg", lat=LAT - 0.009, lon=LON)  # 約 1 km
    make_jpeg(up / "nogps.jpg", lat=None, lon=None)
    (up / "memo.txt").write_text("x", encoding="utf-8")

    code, lines = run(check, capsys, "near", field, up)
    assert code == 0
    assert "観察の広がり（extent_m）の最大: 30 m" in lines
    spread = next(line for line in lines if line.startswith("観察の真ん中どうしの最大の距離"))
    assert 95 <= int(spread.split(": ")[1].split()[0]) <= 105
    near = next(line for line in lines if line.startswith("near.jpg"))
    assert 8 <= int(near.split("まで ")[1].split()[0]) <= 14
    far = next(line for line in lines if line.startswith("far.jpg"))
    assert int(far.split("まで ")[1].split()[0]) > 900
    assert "nogps.jpg: 座標が無い" in lines
    assert not any("memo.txt" in line for line in lines)


def test_refs_counts_missing(check, tmp_path, capsys):
    field = tmp_path / "field"
    make_jpeg(field / "photos" / "2026-11-05" / "142107.jpg")
    observation(
        field,
        "2026-11-05-142107.md",
        ["photos/2026-11-05/142107.jpg", "photos/2026-11-05/142200.jpg"],
        LAT,
        LON,
        0,
    )
    code, lines = run(check, capsys, "refs", field)
    assert code == 0
    assert "2026-11-05-142107.md: 在る 1、無い 1" in lines
    assert "  無い: photos/2026-11-05/142200.jpg" in lines
    assert lines[-1] == "観察 1: 写真が在る 1、無い 1"


def test_outside_lists_what_seed_does_not_see(check, tmp_path, capsys):
    root = tmp_path / "seed"
    for rel in (
        "photos/2026-11-05/1.jpg",
        "fields/rokuse/photos/2026-11-05/1.jpg",
        "fields/rokuse/videos/a.mp4",
        "fields/rokuse/public/p.png",
        "notes/x.jpg",
        "public-home/y.jpg",
        "uploads/2026-11-02/IMG_1.HEIC",
        "uploads/2026-11-02/IMG_2.HEIC",
        "uploads/6畝地/Photos.zip",
        "uploads/6畝地/clip.MOV",
        "fields/rokuse/写真/a.jpg",
        "島根/b.jpeg",
        ".unzip-1/c.jpg",
        "uploads/.hidden.jpg",
        "uploads/memo.txt",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    code, lines = run(check, capsys, "outside", root)
    assert code == 0
    assert lines[0] == "seed が見ない写真・動画・zip: 6 個（4 か所）"
    assert "  uploads/2026-11-02: 写真 2" in lines
    assert "  uploads/6畝地: 動画 1、zip 1" in lines
    assert "  fields/rokuse/写真: 写真 1" in lines
    assert "  島根: 写真 1" in lines
