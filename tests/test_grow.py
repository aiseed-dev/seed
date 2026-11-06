# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed grow（計画の絵（仮説））。本物の claude は呼ばない。地名と座標は入れない。"""

import json
import xml.etree.ElementTree as ET

import pytest

from seed import cli, grow, local
from seed.records import Folder, Line, Plan

SVG_NS = "{http://www.w3.org/2000/svg}"

PLAN_LINES = [
    Line(
        "ground",
        "案 5、一部だけ壊して比べる。刈った筋の半分を案 3 で抜き、半分はそのまま。同じ物を播く",
        0.60,
    ),
    Line(
        "sow", "地面の支度を決めてから。刈った筋に、冬は ライムギかエンバク（宿主と覆いを兼ねる緑肥）", 0.45
    ),
    Line("sow", "刈っていない所には今の冬は播かない。オギの株の間に落とした種が負けるかが分からない", 0.55),
    Line(
        "cover", "刈って敷くことは、畑の中の物で養分を補給すること。刈った草（オギの茎）はそのまま敷く", 0.55
    ),
    Line("uncertain", "硬盤層の厚さと、その下が何か。棒は 20 cm で止まる", 0.70),
]


def scene(when="2026-12", **kw) -> dict:
    sc = {
        "when": when,
        "title": "刈った筋に播いて一か月",
        "from": [
            {"key": "sow", "text": "地面の支度を決めてから。刈った筋に、冬は ライムギかエンバク"},
            {"key": "cover", "text": "刈って敷くことは"},
        ],
        "see": [
            "刈った筋に二列の芽。高さ 5 cm ほど",
            "筋の間は刈った草の茎がそのまま",
            "刈っていない所はオギが立ったまま",
        ],
        "unsure": "芽が出るかは、播く時期と霜で変わる",
        "confidence": 0.45,
        "top": {
            "strips": [
                {
                    "state": "uncut",
                    "label": "刈っていない",
                    "grass": {"name": "オギ", "height_cm": 200},
                    "width": 2,
                },
                {"state": "sown", "label": "刈った筋", "crop": "ライムギ", "rows": 2, "width": 1},
                {"state": "cut", "label": "刈った筋（播かない半分）", "width": 1},
            ],
            "marks": [
                {"kind": "pool", "label": "雨の後に水が溜まるか"},
                {"kind": "hole", "label": "穴 30 cm"},
            ],
        },
        "side": {
            "hard_layer_cm": [20, 30],
            "mulch": {"label": "刈った草を敷く", "thickness_cm": 5},
            "ridge_cm": None,
            "roots": [{"name": "ライムギ", "depth_cm": 15}, {"name": "オギ", "depth_cm": 18}],
            "holes_cm": 30,
        },
    }
    sc.update(kw)
    return sc


def make_plan() -> Plan:
    p = Plan.new("ja", "2026-27 冬", "2026-11-02")
    p.reading = list(PLAN_LINES)
    return p


@pytest.fixture
def field(seedfolder):
    folder = Folder(seedfolder)
    folder.init()
    make_plan().write(folder.plan)
    return folder


def test_validate_keeps_good_scene_and_drops_scene_without_plan_line():
    bad = scene("2027-03", **{"from": [{"key": "sow", "text": "北側に小麦を播く"}]})
    got = grow.validate({"scenes": [scene(), bad]}, make_plan())
    assert [sc.when for sc in got.scenes] == ["2026-12"]
    assert len(got.skipped) == 1 and got.skipped[0].what is None
    assert "sow: 北側に小麦を播く" in got.skipped[0].reason
    # 空白を詰めて比べる（「冬は ライムギ」と「冬はライムギ」は同じ）
    spaced = scene(
        **{"from": [{"key": "sow", "text": "地面の支度を決めてから。 刈った筋に、冬はライムギかエンバク"}]}
    )
    assert len(grow.validate({"scenes": [spaced]}, make_plan()).scenes) == 1


def test_validate_short_prefix_needs_one_line():
    short = scene(**{"from": [{"key": "sow", "text": "刈っ"}]})  # 一行に決まっても 8 字より短い
    assert grow.validate({"scenes": [short]}, make_plan()).scenes == []
    unique = scene(**{"from": [{"key": "sow", "text": "刈っていない所には"}]})  # 短くても一行に決まる
    assert len(grow.validate({"scenes": [unique]}, make_plan()).scenes) == 1
    p = make_plan()
    p.reading.append(Line("sow", "刈って敷く所にはダイズ", 0.5))
    p.reading.append(Line("sow", "刈って敷く所にはソバ", 0.5))
    amb = scene(**{"from": [{"key": "sow", "text": "刈って敷く所には"}]})
    got = grow.validate({"scenes": [amb]}, p)
    assert got.scenes == [] and "30" in got.skipped[0].reason


def test_validate_lowers_confidence_to_the_source_lines():
    got = grow.validate({"scenes": [scene(confidence=0.9)]}, make_plan())
    assert got.scenes[0].confidence == pytest.approx(0.45)  # sow 0.45、cover 0.55 の小さい方
    assert got.adjusted and "0.90" in got.adjusted[0].reason and "0.45" in got.adjusted[0].reason


def test_validate_drops_words_not_in_the_plan():
    sc = scene()
    sc["top"]["strips"][1]["crop"] = "トマト"
    sc["top"]["strips"].append({"state": "pond", "label": "池", "width": 1})
    sc["top"]["marks"].append({"kind": "tree", "label": "木"})
    sc["side"]["roots"].append({"name": "ダイコン", "depth_cm": 40})
    got = grow.validate({"scenes": [sc]}, make_plan())
    (only,) = got.scenes
    assert only.strips[1].crop is None and only.strips[1].label == "刈った筋"  # 筋は残り、作物だけ落ちる
    assert [st.state for st in only.strips] == ["uncut", "sown", "cut"]
    assert [m.kind for m in only.marks] == ["pool", "hole"]
    assert [r.name for r in only.side.roots] == ["ライムギ", "オギ"]
    whats = {k.what for k in got.skipped}
    assert {"トマト", "池", "木", "ダイコン"} <= whats


def test_validate_at_most_six_in_time_order():
    months = ["2027-08", "2027-01", "2026-12", "2027-03", "2027-05", "2027-02", "2027-10"]
    got = grow.validate({"scenes": [scene(m) for m in months]}, make_plan())
    assert [sc.when for sc in got.scenes] == [
        "2026-12",
        "2027-01",
        "2027-02",
        "2027-03",
        "2027-05",
        "2027-08",
    ]
    assert [k.scene.split()[0] for k in got.skipped] == ["2027-10"]
    assert len(grow.validate({"scenes": [scene(m) for m in months]}, make_plan(), 2).scenes) == 2


def test_validate_drops_directive_and_bad_when():
    sc = scene(see=["芽が出る", "早く播くべき"])
    got = grow.validate({"scenes": [sc, scene("2027-13"), scene("2027-02", title="刈るべき")]}, make_plan())
    assert len(got.scenes) == 1 and got.scenes[0].see == ["芽が出る"]


def test_svg_is_xml_with_mark_when_labels_and_layer():
    sc = scene()
    sc["title"] = "<播く> & 敷く"
    got = grow.validate({"scenes": [sc]}, make_plan())
    svg = grow.render_scene(
        got.scenes[0], 1, "ja", {"model": "claude-opus-5-5", "day": "2026-11-04", "since": "2026-11-02"}
    )
    root = ET.fromstring(svg)
    assert root.tag == f"{SVG_NS}svg" and root.get("viewBox") == "0 0 1280 720"
    assert root.get("font-family") == "sans-serif"
    assert root.find(f"{SVG_NS}style") is None and root.find(f".//{SVG_NS}image") is None
    texts = [t.text or "" for t in root.iter(f"{SVG_NS}text")]
    joined = "\n".join(texts)
    for part in (
        "計画の絵（仮説）",
        "2026-12",
        "<播く> & 敷く",
        "刈っていない",
        "刈った筋",
        "ライムギ",
        "[0.45]",
    ):
        assert part in joined, part
    assert "固い層 20〜30 cm" in joined and "穴 30 cm" in joined
    assert (
        "Claude（claude-opus-5-5）が 2026-11-04 に plan.md（since 2026-11-02）の行から。seed grow" in joined
    )
    en = grow.render_scene(got.scenes[0], 1, "en", {})
    assert "Planned (hypothesis)" in en


def test_svg_open_bottom_layer():
    sc = scene()
    sc["side"]["hard_layer_cm"] = [20, None]
    got = grow.validate({"scenes": [sc]}, make_plan())
    svg = grow.render_scene(got.scenes[0], 1, "ja", {})
    assert "固い層 20 cm〜（下端は分からない）" in svg


def test_render_writes_captions_and_svgs(field, tmp_path, capsys):
    bad = scene("2027-03", **{"from": [{"key": "sow", "text": "北側に小麦を播く"}]})
    path = tmp_path / "elsewhere" / "scenario.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps({"language": "ja", "scenes": [scene(), bad]}, ensure_ascii=False), encoding="utf-8"
    )
    assert cli.main(["grow", "--folder", str(field.root), "--render", str(path)]) == 0
    day = next((field.root / "grow").glob("20*"))
    svgs = sorted(day.glob("*.svg"))
    assert [p.name for p in svgs] == ["01-2026-12.svg"]
    ET.parse(svgs[0])
    assert json.loads((day / "scenario.json").read_text(encoding="utf-8"))["scenes"][0]["when"] == "2026-12"
    md = (day / "captions.md").read_text(encoding="utf-8")
    assert "これは仮説" in md and "`seed publish` では送らない" in md
    assert "sow: 地面の支度を決めてから。刈った筋に、冬は ライムギかエ" in md
    assert "## 省いた場面・省いた要素" in md and "北側に小麦を播く" in md
    out = capsys.readouterr().out
    assert "描いた場面 1" in out and "01-2026-12.svg" in out and "seed publish には入りません" in out
    # 記録は変えない
    assert Plan.read(field.plan).reading == PLAN_LINES


def test_render_path_relative_to_folder(field, monkeypatch, tmp_path):
    rel = "grow/2026-11-01/scenario.json"
    (field.root / rel).parent.mkdir(parents=True)
    (field.root / rel).write_text(json.dumps({"scenes": [scene()]}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["grow", "--folder", str(field.root), "--render", rel]) == 0


def test_render_nothing_and_bad_json(field, tmp_path, capsys):
    p = tmp_path / "s.json"
    p.write_text('{"scenes": []}', encoding="utf-8")
    assert cli.main(["grow", "--folder", str(field.root), "--render", str(p)]) == 2
    p.write_text("not json", encoding="utf-8")
    assert cli.main(["grow", "--folder", str(field.root), "--render", str(p)]) == 2
    assert "シナリオを読めません" in capsys.readouterr().err


def test_publish_does_not_send_grow(field, photo, tmp_path, capsys):
    f = str(field.root)
    assert cli.main(["observe", "--folder", f, "--claude-code", "--say", "did: 刈った", str(photo)]) == 0
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"scenes": [scene()]}, ensure_ascii=False), encoding="utf-8")
    assert cli.main(["grow", "--folder", f, "--render", str(path)]) == 0
    name = next((field.root / "observations").glob("*.md")).stem
    assert (
        cli.main(
            [
                "publish",
                "--folder",
                f,
                name,
                "--id",
                "c-1",
                "--place",
                "x",
                "--word",
                "y",
                "--name",
                "n",
                "--local",
            ]
        )
        == 0
    )
    pubs = list((field.root / "public").glob("*.md"))
    assert pubs
    for pub in pubs:
        text = pub.read_text(encoding="utf-8")
        assert "刈った筋に播いて一か月" not in text and "grow/" not in text and "計画の絵" not in text


def test_no_plan_returns_2(seedfolder, capsys):
    assert cli.main(["grow", "--folder", str(seedfolder)]) == 2
    assert "seed plan" in capsys.readouterr().err
    folder = Folder(seedfolder)
    folder.init()
    Plan.new("ja", today="2026-11-02").write(folder.plan)  # ## Plan が空
    assert cli.main(["grow", "--folder", str(seedfolder)]) == 2
    assert not (seedfolder / "grow").exists()


def test_without_claude_prints_steps(field, capsys):
    assert cli.main(["grow", "--folder", str(field.root)]) == 0  # conftest が claude を見つけない
    out = capsys.readouterr().out
    assert "Claude Code" in out and "09 章" in out and "seed grow --render grow/" in out
    assert not list((field.root / "grow").rglob("*.svg"))


def test_local_path_with_fake_run(field, monkeypatch, capsys):
    calls = {}

    def fake_run(cmd, cwd, timeout):
        calls["cmd"] = cmd
        return {
            "is_error": False,
            "structured_output": {"language": "ja", "scenes": [scene(confidence=0.8)]},
            "modelUsage": {"claude-opus-5-5": {}},
        }

    (field.skill).mkdir(parents=True, exist_ok=True)
    (field.skill / "SKILL.md").write_text("# 手引き\n", encoding="utf-8")
    (field.skill / local.CHAPTER_PLAN).write_text("# 09 栽培計画\n計画の絵（仮説）\n", encoding="utf-8")
    monkeypatch.setattr(local, "available", lambda: "/bin/claude")
    monkeypatch.setattr(local, "_run", fake_run)
    assert cli.main(["grow", "--folder", str(field.root), "--scenes", "3"]) == 0
    cmd = calls["cmd"]
    user = cmd[cmd.index("-p") + 1]
    assert "## Plan" in user and "ライムギかエンバク" in user and "最大 3" in user and "地名" in user
    assert "09 栽培計画" in cmd[cmd.index("--system-prompt") + 1]
    schema = json.loads(cmd[cmd.index("--json-schema") + 1])
    item = schema["properties"]["scenes"]["items"]
    assert schema["properties"]["scenes"]["maxItems"] == 3 and item["additionalProperties"] is False
    strip = item["properties"]["top"]["properties"]["strips"]["items"]
    assert strip["properties"]["state"]["enum"] == list(grow.STATES)
    day = next((field.root / "grow").glob("20*"))
    saved = json.loads((day / "scenario.json").read_text(encoding="utf-8"))
    assert saved["model"] == "claude-opus-5-5"
    md = (day / "captions.md").read_text(encoding="utf-8")
    assert "claude-opus-5-5" in md and "## 直した所" in md and "0.80" in md
    assert "Claude（claude-opus-5-5）" in (day / "01-2026-12.svg").read_text(encoding="utf-8")
    assert "描いた場面 1" in capsys.readouterr().out


def test_local_failure_prints_steps(field, monkeypatch, capsys):
    monkeypatch.setattr(local, "available", lambda: "/bin/claude")
    monkeypatch.setattr(local, "system_prompt", lambda folder, chapter: "x")
    monkeypatch.setattr(
        local, "_run", lambda cmd, cwd, timeout: {"is_error": True, "result": "Please authenticate"}
    )
    assert cli.main(["grow", "--folder", str(field.root), "--local"]) == 2
    assert "seed grow --render" in capsys.readouterr().out


def test_validate_drops_scene_from_a_line_marked_wrong():
    p = make_plan()
    p.reading[1] = p.reading[1].marked("wrong", "播く時期が違う")
    got = grow.validate({"scenes": [scene()]}, p)
    assert got.scenes == [] and "本人が違うと付けた行から" in got.skipped[0].reason


def test_strip_label_wraps_to_two_lines():
    assert grow.wrap2("刈った筋", 200, 14) == ["刈った筋"]
    two = grow.wrap2("刈った筋・穴を抜いた半分", 100, 14)
    assert len(two) == 2 and "".join(two) == "刈った筋・穴を抜いた半分"
    cut = grow.wrap2("刈った筋・穴を抜いた半分のさらに長い札の文", 60, 14)
    assert len(cut) == 2 and cut[1].endswith("…")
    sc = scene()
    sc["top"]["strips"][2]["label"] = "刈った筋・穴を抜いた半分"
    svg = grow.render_scene(grow.validate({"scenes": [sc]}, make_plan()).scenes[0], 1, "ja", {})
    texts = [t.text for t in ET.fromstring(svg).iter(f"{SVG_NS}text")]
    i = next(k for k, x in enumerate(texts) if x and x.startswith("刈った筋・"))
    assert texts[i] + texts[i + 1] == "刈った筋・穴を抜いた半分"  # 二行に折れ、切れない


# ---------------------------------------------------------------- seed grow --draw（halo で絵に。server は httpx.MockTransport）

PROMPT = (
    "Watercolor illustration of a small field in early winter, seen from slightly above. On the left, tall standing "
    "grass; on the right, two strips of cut ground with two rows of young rye seedlings. No text, no labels, no "
    "people, no buildings."
)


def _png(size=(1024, 1024), color=(80, 140, 70)) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _parts(request) -> dict[str, list[bytes]]:
    """multipart の中身を name → [本体] に。"""
    import re as _re

    boundary = _re.search(r"boundary=([^;]+)", request.headers["content-type"]).group(1).encode()
    out: dict[str, list[bytes]] = {}
    for chunk in request.content.split(b"--" + boundary)[1:-1]:
        head, _, body = chunk.partition(b"\r\n\r\n")
        name = _re.search(rb'name="([^"]+)"', head).group(1).decode()
        fname = _re.search(rb'filename="([^"]+)"', head)
        out.setdefault(name, []).append((fname.group(1).decode() if fname else None, body[:-2]))
    return out


def fake_server(calls: list, status: int = 200, got=(1024, 1024)):
    import base64

    import httpx

    def handler(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "sd-cpp-local"}]})
        calls.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": "boom"})
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(_png(got)).decode()}]})

    return httpx.MockTransport(handler)


@pytest.fixture
def drawn_day(field, monkeypatch):
    """grow/2026-11-04/scenario.json に、prompt のある場面と無い場面。"""
    from seed import draw

    monkeypatch.delenv(draw.ENV_URL, raising=False)
    day = field.root / "grow" / "2026-11-04"
    day.mkdir(parents=True)
    scenes = [scene(prompt=PROMPT, negative="photo, text"), scene("2027-04")]
    (day / "scenario.json").write_text(
        json.dumps({"language": "ja", "model": "claude-opus-5-5", "scenes": scenes}, ensure_ascii=False),
        encoding="utf-8",
    )
    return day


def test_draw_sends_prompt_figure_and_photo_and_stamps(field, drawn_day, photo, monkeypatch, capsys):
    import io

    from PIL import Image

    from seed import draw

    calls: list = []
    monkeypatch.setattr(draw, "TRANSPORT", fake_server(calls))
    f = str(field.root)
    rc = cli.main(
        ["grow", "--folder", f, "--draw", "--server", "http://192.168.100.6:11435", "--photo", str(photo)]
    )
    assert rc == 0
    assert len(calls) == 1  # prompt の無い 2027-04 は頼まない
    req = calls[0]
    assert req.url.path == "/v1/images/edits"
    parts = _parts(req)
    prompt = parts["prompt"][0][1].decode()
    assert prompt.startswith(PROMPT) and "<sd_cpp_extra_args>" in prompt
    extra = json.loads(prompt.split("<sd_cpp_extra_args>")[1].split("</sd_cpp_extra_args>")[0])
    assert extra["sample_params"] == {
        "sample_steps": 4,
        "sample_method": "euler",
        "guidance": {"txt_cfg": 1.0},
    }
    assert extra["negative_prompt"] == "photo, text"
    assert parts["size"][0][1] == b"1280x720"
    images = parts["image[]"]
    assert [n for n, _ in images] == ["01-2026-12.png", "photo-1.jpg"]
    with Image.open(io.BytesIO(images[0][1])) as fig:
        assert fig.size == (1280, 720)  # 図の SVG を PNG に
    with Image.open(io.BytesIO(images[1][1])) as ph:
        exif = ph.getexif()
        assert not exif.get_ifd(0x8825) and 0x8825 not in exif  # GPS が落ちている
    assert b"34.05" not in req.content and b"134.25" not in req.content
    # 戻った絵は raw にそのまま、印付きは 1280x720 に合わせて
    raw = drawn_day / "raw" / "01-2026-12.png"
    with Image.open(raw) as r:
        assert r.size == (1024, 1024)
    with Image.open(drawn_day / "01-2026-12.png") as im:
        assert im.size == (1280, 720)
        rgb = im.convert("RGB")
        reds = sum(1 for x in range(16, 200) if rgb.getpixel((x, 17)) == (179, 38, 30))
        assert reds > 50  # 印の赤い枠
        assert rgb.getpixel((640, 400)) == (80, 140, 70)  # 絵の中は戻ったまま
    assert not (drawn_day / "02-2027-04.png").exists()
    assert (drawn_day / "01-2026-12.svg").is_file() and (drawn_day / "02-2027-04.svg").is_file()
    md = (drawn_day / "captions.md").read_text(encoding="utf-8")
    assert "| 図 | 絵 |" in md and "[01-2026-12.png](01-2026-12.png)" in md
    assert "## 絵の作り方" in md and PROMPT in md and "`01-2026-12.svg`" in md and "photo-1" not in md
    assert "http://192.168.100.6:11435" in md and "FLUX.2 klein 4B" in md and "秒" in md
    assert "写真は家の外に出ていない" in md
    assert "### 描かなかった場面" in md and "prompt）が無い" in md
    assert "## Claude の照らし" in md and "（まだ。" in md  # conftest は claude を見つけない
    out = capsys.readouterr().out
    assert "01: " in out and "秒" in out and "01-2026-12.png" in out and "captions.md" in out
    assert "Claude Code" in out  # 照らしの手順


def test_draw_photo_path_in_captions_is_relative_to_folder(field, drawn_day, monkeypatch):
    from test_photos import make_jpeg

    from seed import draw

    p = make_jpeg(field.root / "photos" / "2026-11-04" / "IMG_1.jpg")
    monkeypatch.setattr(draw, "TRANSPORT", fake_server([]))
    assert (
        cli.main(
            [
                "grow",
                "--folder",
                str(field.root),
                "--draw",
                "--server",
                "http://localhost:1",
                "--photo",
                str(p),
            ]
        )
        == 0
    )
    md = (drawn_day / "captions.md").read_text(encoding="utf-8")
    assert "`photos/2026-11-04/IMG_1.jpg`" in md and str(field.root) not in md.split("## 絵の作り方")[1]


def test_draw_without_server_returns_2_and_keeps_svg(field, drawn_day, capsys):
    assert cli.main(["grow", "--folder", str(field.root), "--draw"]) == 2
    assert "描く server がありません" in capsys.readouterr().err
    assert (drawn_day / "01-2026-12.svg").is_file() and not list(drawn_day.glob("*.png"))


def test_draw_server_500_returns_2_and_keeps_svg(field, drawn_day, monkeypatch, capsys):
    from seed import draw

    monkeypatch.setattr(draw, "TRANSPORT", fake_server([], status=500))
    monkeypatch.setenv(draw.ENV_URL, "http://10.0.0.5:11435")
    assert cli.main(["grow", "--folder", str(field.root), "--draw", "--day", "2026-11-04"]) == 2
    assert "描けませんでした" in capsys.readouterr().err
    assert (drawn_day / "01-2026-12.svg").is_file() and not list(drawn_day.glob("*.png"))
    assert "途中で止まった" in (drawn_day / "captions.md").read_text(encoding="utf-8")


def test_draw_server_not_answering_returns_2(field, drawn_day, monkeypatch, capsys):
    import httpx

    from seed import draw

    def down(request):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(draw, "TRANSPORT", httpx.MockTransport(down))
    assert (
        cli.main(["grow", "--folder", str(field.root), "--draw", "--server", "http://192.168.100.6:9"]) == 2
    )
    assert "応えません" in capsys.readouterr().err
    assert (drawn_day / "01-2026-12.svg").is_file()


def test_draw_no_scenario_returns_2(field, capsys):
    assert cli.main(["grow", "--folder", str(field.root), "--draw", "--server", "http://localhost:1"]) == 2
    assert "絵にするシナリオがありません" in capsys.readouterr().err


def test_server_url_order(monkeypatch):
    from seed import draw

    monkeypatch.delenv(draw.ENV_URL, raising=False)
    toml = {"grow": {"server": "http://192.168.1.2:11435/"}}
    assert draw.server_url(None, {}) is None
    assert draw.server_url(None, toml) == "http://192.168.1.2:11435"
    monkeypatch.setenv(draw.ENV_URL, "http://10.1.1.1:1")
    assert draw.server_url(None, toml) == "http://10.1.1.1:1"
    assert draw.server_url("http://localhost:2", toml) == "http://localhost:2"


def test_settings_keep_grow_table(tmp_path):
    from seed import settings as S

    st = S.Settings.parse('folder = "/x"\nkeep = "photos"\n\n[grow]\nserver = "http://192.168.1.2:11435"\n')
    assert st.extra == {"grow": {"server": "http://192.168.1.2:11435"}}
    again = S.Settings.parse(st.render())
    assert again.extra == st.extra and again.keep == "photos"


def test_is_lan():
    from seed.draw import is_lan

    for u in (
        "http://192.168.100.6:11435",
        "http://10.0.0.2",
        "http://localhost:11435",
        "http://127.0.0.1:1",
        "http://[::1]:1",
    ):
        assert is_lan(u), u
    for u in (
        "https://example.com",
        "http://172.16.0.1",
        "http://8.8.8.8",
        "http://192.169.0.1",
        "http://halo.lan",
    ):
        assert not is_lan(u), u


def test_parse_size():
    from seed.draw import parse_size

    assert parse_size(None) == (1280, 720) and parse_size("1024x1024") == (1024, 1024)
    with pytest.raises(ValueError):
        parse_size("big")


def test_prompt_with_coordinates_is_dropped():
    got = grow.validate({"scenes": [scene(prompt="a field at 34.0512, 134.2534, watercolor")]}, make_plan())
    assert got.scenes[0].prompt is None and any(k.what == "prompt" for k in got.adjusted)
    ok = grow.validate({"scenes": [scene(prompt=PROMPT)]}, make_plan())
    assert ok.scenes[0].prompt == PROMPT


def test_grow_check_reads_json(monkeypatch, tmp_path):
    calls = {}

    def fake_run(cmd, cwd, timeout):
        calls["cmd"] = cmd
        return {
            "is_error": False,
            "structured_output": {
                "found": [
                    {"kind": "structure", "what": "a wooden fence"},
                    {"kind": "weird", "what": "a sign"},
                ]
            },
        }

    monkeypatch.setattr(local, "available", lambda: "/bin/claude")
    monkeypatch.setattr(local, "_run", fake_run)
    sc = grow.validate({"scenes": [scene(prompt=PROMPT)]}, make_plan()).scenes[0]
    img = tmp_path / "01-2026-12.png"
    got = local.grow_check(img, sc, tmp_path)
    assert got == [("structure", "a wooden fence"), ("other", "a sign")]
    cmd = calls["cmd"]
    user = cmd[cmd.index("-p") + 1]
    assert str(img) in user and "刈った筋に二列の芽" in user and "ライムギ" in user
    assert cmd[cmd.index("--tools") + 1] == "Read"
    schema = json.loads(cmd[cmd.index("--json-schema") + 1])
    assert schema["required"] == ["found"]
    monkeypatch.setattr(local, "_run", lambda cmd, cwd, timeout: {"structured_output": {"found": []}})
    assert local.grow_check(img, sc, tmp_path) == []
    monkeypatch.setattr(local, "_run", lambda cmd, cwd, timeout: {"result": "not json"})
    with pytest.raises(local.LocalError):
        local.grow_check(img, sc, tmp_path)


def test_draw_with_claude_check_writes_section(field, drawn_day, monkeypatch):
    from seed import draw

    monkeypatch.setattr(draw, "TRANSPORT", fake_server([]))
    monkeypatch.setattr(local, "available", lambda: "/bin/claude")
    monkeypatch.setattr(
        local,
        "_run",
        lambda cmd, cwd, timeout: {
            "structured_output": {"found": [{"kind": "text", "what": "letters in the sky"}]}
        },
    )
    assert cli.main(["grow", "--folder", str(field.root), "--draw", "--server", "http://localhost:1"]) == 0
    md = (drawn_day / "captions.md").read_text(encoding="utf-8")
    check = md.split("## Claude の照らし")[1]
    assert "01 2026-12（Claude（claude -p））: text: letters in the sky" in check


# ---------------------------------------------------------------- halo の門（設計書 §5.4）。token は偽物


def _gate(calls: list, want: str | None):
    """Bearer が want と一致した時だけ通す門（want が None なら門の無い server）。"""
    import httpx

    inner = fake_server([])

    def handler(request):
        calls.append(request)
        if want is not None and request.headers.get("authorization") != f"Bearer {want}":
            return httpx.Response(401, text="unauthorized")
        return inner.handle_request(request)

    return httpx.MockTransport(handler)


def test_draw_sends_bearer_from_credentials(field, drawn_day, monkeypatch, credentials_in_tmp):
    from seed import draw
    from seed import settings as S

    monkeypatch.delenv(draw.ENV_TOKEN, raising=False)
    st = S.load(field.root)
    st.draw_token = "draw-fake-token-0001"
    st.save()
    calls: list = []
    monkeypatch.setattr(draw, "TRANSPORT", _gate(calls, "draw-fake-token-0001"))
    rc = cli.main(["grow", "--folder", str(field.root), "--draw", "--server", "http://192.168.100.6"])
    assert rc == 0
    assert calls and all(r.headers["authorization"] == "Bearer draw-fake-token-0001" for r in calls)
    assert all(r.url.port == 11445 for r in calls)  # 口の無い URL は門の口
    assert "draw-fake-token-0001" not in (drawn_day / "captions.md").read_text(encoding="utf-8")


def test_draw_token_env_wins_and_no_header_without_token(monkeypatch):
    from seed import draw

    monkeypatch.setenv(draw.ENV_TOKEN, "draw-fake-env-0002")
    assert draw.token("draw-fake-file-0003") == "draw-fake-env-0002"
    monkeypatch.delenv(draw.ENV_TOKEN)
    assert draw.token("draw-fake-file-0003") == "draw-fake-file-0003"
    assert draw.token("") is None and draw.auth_headers(None) == {}
    assert draw.auth_headers("x") == {"Authorization": "Bearer x"}


def test_draw_401_says_check_token(field, drawn_day, monkeypatch, capsys):
    from seed import draw

    monkeypatch.setenv(draw.ENV_TOKEN, "draw-fake-wrong-0004")
    calls: list = []
    monkeypatch.setattr(draw, "TRANSPORT", _gate(calls, "draw-fake-right-0005"))
    rc = cli.main(["grow", "--folder", str(field.root), "--draw", "--server", "http://192.168.100.6:11445"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "token を受けませんでした" in err and "draw_token" in err and "401" in err
    assert "draw-fake-wrong-0004" not in err
    assert (drawn_day / "01-2026-12.svg").is_file() and not list(drawn_day.glob("*.png"))


def test_draw_401_words_in_english():
    from seed.app.strings import s

    text = s("draw_unauthorized", "en", server="http://192.168.100.6:11445", detail="HTTP 401")
    assert "did not accept the token" in text and "SEED_DRAW_TOKEN" in text


def test_server_url_default_gate_port(monkeypatch):
    from seed import draw

    monkeypatch.delenv(draw.ENV_URL, raising=False)
    assert draw.server_url("http://192.168.1.2", {}) == "http://192.168.1.2:11445"
    assert draw.server_url("http://halo.local/", {}) == "http://halo.local:11445"
    assert draw.server_url("http://[::1]", {}) == "http://[::1]:11445"
    assert (
        draw.server_url("http://192.168.1.2:11435", {}) == "http://192.168.1.2:11435"
    )  # 書かれた口は変えない
