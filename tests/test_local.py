# SPDX-License-Identifier: AGPL-3.0-or-later
"""手元の claude で読む（seed.local）。本物の claude は呼ばず、同じ形で答える偽の実行ファイルを使う。"""

import json
import stat
import sys
from pathlib import Path

import pytest

from seed import local
from seed.records import Folder, Line, Observation

ANSWER = {
    "lines": [
        {"key": "next_to_observe", "text": "来週までに刈るべき", "confidence": 0.9},
        {"key": "overall", "text": "草丈 1 m を超える草が大半", "confidence": 0.8},
        {"key": "soil_surface", "text": "地表は見えない", "confidence": 0.85},
    ]
}


def fake_claude(tmp_path: Path, answer: dict | None = None, is_error: bool = False, result: str = "") -> Path:
    """渡された引数を args.json に残し、--output-format json の形で答える偽の claude。"""
    out = {
        "type": "result",
        "is_error": is_error,
        "result": result,
        "structured_output": answer,
        "modelUsage": {"claude-opus-5-5": {}} if not is_error else {},
        "total_cost_usd": 0.0,
        "duration_ms": 1,
    }
    script = tmp_path / "claude"
    script.write_text(
        "#!" + sys.executable + "\n"
        "import json, sys\n"
        f"open({str(tmp_path / 'args.json')!r}, 'w').write(json.dumps(sys.argv[1:], ensure_ascii=False))\n"
        f"print(json.dumps({json.dumps(out, ensure_ascii=False)!r} and {out!r}, ensure_ascii=False))\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


@pytest.fixture
def folder(tmp_path):
    f = Folder(tmp_path / "seed")
    f.init()
    (f.skill).mkdir(parents=True, exist_ok=True)
    (f.skill / "SKILL.md").write_text("# 手引き\n読み方であって、やり方ではない。\n")
    (f.skill / local.CHAPTER_READ).write_text("# 06 畑を読む\n")
    (f.skill / "02-地質と土.md").write_text("# 02 地質と土\n")
    (f.photos / "2026-11-05").mkdir(parents=True)
    (f.photos / "2026-11-05" / "142107.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    return f


def obs_for(language="ja") -> Observation:
    o = Observation(date="2026-11-05", time="14:21:07", language=language)
    o.photos = ["photos/2026-11-05/142107.jpg"]
    o.location = {"center": [34.0512, 134.2534], "points": 1, "extent_m": 0}
    o.record = [Line("said", "土は固い")]
    return o


def test_read_parses_demotes_and_sorts(tmp_path, folder, monkeypatch):
    exe = fake_claude(tmp_path, ANSWER)
    monkeypatch.setattr(local, "available", lambda: str(exe))
    got = local.read(folder, obs_for(), model="opus")
    assert got.model == "claude-opus-5-5"
    assert [l.key for l in got.lines] == ["overall", "soil_surface", "uncertain"]  # 判定は uncertain に
    assert got.lines[-1].confidence is not None and "刈るべき" in got.lines[-1].text
    args = json.loads((tmp_path / "args.json").read_text())
    assert args[0] == "-p"
    assert "--system-prompt" in args and "読み方であって" in args[args.index("--system-prompt") + 1]
    assert args[args.index("--model") + 1] == "opus"
    assert args[args.index("--tools") + 1] == "Read"
    prompt = args[1]
    assert str(folder.root / "photos/2026-11-05/142107.jpg") in prompt
    assert "(142107)" in prompt and "土は固い" in prompt and "前の観察はありません" in prompt


def test_prompt_adds_heading_when_exif_has_it(folder, monkeypatch):
    import datetime as dt

    from seed import photos

    monkeypatch.setattr(
        photos, "exif_info", lambda p: photos.PhotoInfo(34.0, 134.0, dt.datetime(2026, 11, 5), 270.0)
    )
    text = local.prompt(folder, obs_for("ja"), None)
    assert "(142107、西向き)" in text
    text = local.prompt(folder, obs_for("en"), None)
    assert "(142107, facing W)" in text


def test_prompt_carries_place_record(folder):
    folder.init()
    folder.place.write_text("## Data\n(none)\n\n## Record\n- saw: 北側は湿る\n", encoding="utf-8")
    text = local.prompt(folder, obs_for(), None)
    assert "place.md の Record" in text and "- saw: 北側は湿る" in text


def test_prompt_carries_asks(folder):
    o = obs_for()
    text = local.prompt(folder, o, None)
    assert "知りたいこと" not in text and "- ask:" not in text
    o.ask = ["grow", "access"]
    o.record.append(Line("ask", "果樹は向くか"))
    text = local.prompt(folder, o, None)
    assert "- ask: grow, access" in text
    assert "- grow: この土地で何が育つか" in text and "- access: 借りられるか" in text
    assert "- ask: 果樹は向くか" in text and "overall` の先頭でそれに答えます" in text


def test_prompt_carries_previous_observation(folder):
    prev = obs_for()
    prev.reading = [Line("overall", "前の読み", 0.7)]
    prev.model = "claude-code"
    text = local.prompt(folder, obs_for(), prev)
    assert "前の観察" in text and "前の読み" in text


def test_auth_error_becomes_local_auth(tmp_path, folder, monkeypatch):
    exe = fake_claude(tmp_path, None, is_error=True, result="Failed to authenticate: OAuth session expired")
    monkeypatch.setattr(local, "available", lambda: str(exe))
    with pytest.raises(local.LocalError) as e:
        local.read(folder, obs_for())
    assert e.value.word == "local_auth"


def test_missing_claude(folder, monkeypatch):
    monkeypatch.setattr(local, "available", lambda: None)
    with pytest.raises(local.LocalError) as e:
        local.read(folder, obs_for())
    assert e.value.word == "local_missing"


def test_env_overrides_command(monkeypatch):
    monkeypatch.delenv(local.ENV_COMMAND, raising=False)
    assert local.command() == "claude"
    monkeypatch.setenv(local.ENV_COMMAND, "/opt/bin/claude")
    assert local.command() == "/opt/bin/claude"


def test_raw_dir_keeps_what_was_sent_and_returned(tmp_path, folder, monkeypatch):
    exe = fake_claude(tmp_path, ANSWER)
    monkeypatch.setattr(local, "available", lambda: str(exe))
    obs = obs_for()
    raw = folder.raw_dir(obs)
    local.read(folder, obs, raw_dir=raw)
    assert raw == folder.observations / "2026-11-05-142107.raw"
    assert sorted(p.name for p in raw.iterdir()) == ["answer.json", "meta.json", "prompt.md", "system.md"]
    assert "読み方であって" in (raw / "system.md").read_text()
    assert "土は固い" in (raw / "prompt.md").read_text()
    meta = json.loads((raw / "meta.json").read_text())
    assert meta["model"] == ["claude-opus-5-5"] and meta["photos"] == obs.photos
    assert len(meta["skill_hash"]) == 16 and meta["skill_hash"] == local.skill_hash(folder)
    assert "<system.md>" in meta["command"] and "<prompt.md>" in meta["command"]
    assert json.loads((raw / "answer.json").read_text())["structured_output"] == ANSWER
    # 手引きを直すとハッシュが変わる
    (folder.skill / "SKILL.md").write_text("# 手引き\n直した。\n")
    assert local.skill_hash(folder) != meta["skill_hash"]


def test_without_raw_dir_nothing_is_written(tmp_path, folder, monkeypatch):
    exe = fake_claude(tmp_path, ANSWER)
    monkeypatch.setattr(local, "available", lambda: str(exe))
    obs = obs_for()
    local.read(folder, obs)
    assert not folder.raw_dir(obs).exists()


PLAN_ANSWER = {
    "lines": [
        {"key": "sow", "text": "北側に小麦", "confidence": 0.7},
        {"key": "ground", "text": "一度だけ起こすべき", "confidence": 0.5},
        {"key": "next_to_observe", "text": "12 月の湿り", "confidence": 0.6},
    ]
}


def test_plan_prompt_and_plan(tmp_path, folder, monkeypatch):
    from seed.records import Plan

    folder.init()
    o = obs_for()
    o.reading = [Line("overall", "草が大半", 0.8, "right")]
    o.write(folder.observation_path(o))
    folder.place.write_text(
        "## Data\n- soil: 褐色低地土（出典: 農研機構、確認日 2026-11-02）\n\n## Record\n- saw: 北側は湿る\n",
        encoding="utf-8",
    )
    plan = Plan.new("ja", "2026-27 冬", "2026-11-03")
    plan.say("decided", "南側は草のまま")
    text = local.plan_prompt(folder, plan, [o])
    for part in (
        "ground … next_to_observe",
        "数字（収量",
        "`mix`",
        "season: 2026-27 冬",
        "褐色低地土",
        "北側は湿る",
        "南側は草のまま",
        "observations/2026-11-05-142107.md",
        "草が大半",
    ):
        assert part in text, part
    assert "観察はまだありません" in local.plan_prompt(folder, plan, [])

    (folder.skill / "09-栽培計画.md").write_text("# 09 栽培計画\n数字を書きません。\n", encoding="utf-8")
    exe = fake_claude(tmp_path, PLAN_ANSWER)
    monkeypatch.setattr(local, "available", lambda: str(exe))
    got = local.plan(folder, plan, model="opus")
    assert got.model == "claude-opus-5-5"
    assert [l.key for l in got.lines] == [
        "sow",
        "uncertain",
        "next_to_observe",
    ]  # 09 の順。判定の形の ground は uncertain に
    args = json.loads((tmp_path / "args.json").read_text())
    system = args[args.index("--system-prompt") + 1]
    assert "読み方であって" in system and "09 栽培計画" in system and "# 06 畑を読む" not in system
    schema = json.loads(args[args.index("--json-schema") + 1])
    assert "mix" in schema["properties"]["lines"]["items"]["properties"]["key"]["enum"]
    assert "草が大半" in args[1]


def test_old_named_copy_gets_chapters_from_package(tmp_path, monkeypatch):
    """11-05 より前の写し（章の名前が旧い）でも、SKILL.md は本人の物、章はパッケージの物で補う。"""
    import seed.cli

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "SKILL.md").write_text("# 共通の手引き\n", encoding="utf-8")
    (pkg / "06-畑を読む.md").write_text("# 06 共通の畑を読む\n", encoding="utf-8")
    (pkg / "02-地質と土.md").write_text("# 02 共通の地質と土\n", encoding="utf-8")
    (pkg / "04-生物.md").write_text("# 04 共通の生物\n", encoding="utf-8")
    monkeypatch.setattr(seed.cli, "package_skill", lambda: pkg)
    f = Folder(tmp_path / "seed")
    f.skill.mkdir(parents=True)
    (f.skill / "SKILL.md").write_text("# 本人の手引き\n", encoding="utf-8")
    (f.skill / "02-畑を読む.md").write_text("# 旧い 02 畑を読む\n", encoding="utf-8")

    text = local.system_prompt(f)
    assert "本人の手引き" in text and "共通の手引き" not in text
    assert "旧い 02" not in text
    order = [text.index(s) for s in ("06 共通の畑を読む", "02 共通の地質と土", "04 共通の生物")]
    assert order == sorted(order)

    (f.skill / "06-畑を読む.md").write_text("# 06 本人の畑を読む\n", encoding="utf-8")
    text = local.system_prompt(f)
    assert "06 本人の畑を読む" in text and "06 共通の畑を読む" not in text
    assert "02 共通の地質と土" in text and "04 共通の生物" in text


def test_not_logged_in_is_local_auth():
    with pytest.raises(local.LocalError) as e:
        local._check({"is_error": True, "result": "Not logged in · Please run /login"})
    assert e.value.word == "local_auth"
