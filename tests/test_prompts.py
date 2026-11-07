# SPDX-License-Identifier: AGPL-3.0-or-later
"""写真の読み取りの指示（seed/prompts.py）が、手引き（skill/）と PC の道（local.prompt）に揃っているか。"""

from __future__ import annotations

from seed import prompts as P
from seed import records as R

JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 16


def test_task_lists_every_reading_key_in_order():
    """TASK の key の一覧は READING_KEYS から作る。SCHEMA の enum と同じ物が、同じ順で並ぶ。"""
    listed = [line[2:].split(":")[0] for line in P.TASK.splitlines() if line.startswith("- ")]
    assert listed == list(R.READING_KEYS)
    assert P.SCHEMA["properties"]["lines"]["items"]["properties"]["key"]["enum"] == list(R.READING_KEYS)
    assert set(P.KEY_WORDS) == set(R.READING_KEYS)  # どの key にも一言がある
    for key in ("tags", "access", "sun_slope", "surroundings"):
        assert f"- {key}: {P.KEY_WORDS[key]}" in P.TASK


def test_user_content_passes_date_time_kind_but_not_location():
    content = P.user_content(
        [JPEG], [], [], None, language="ja", date="2026-11-05", time="14:21:07", kind="candidate"
    )
    text = content[-1]["text"]
    assert "## 前書き\n- date: 2026-11-05\n- time: 14:21:07\n- kind: candidate\n" in text
    assert "location" not in text and "center" not in text
    assert text.index("## 前書き") < text.index("<data>")


def test_user_content_without_front():
    text = P.user_content([JPEG], [], [], None)[-1]["text"]
    assert "## 前書き" not in text
    text = P.user_content([JPEG], [], [], None, date="2026-11-05")[-1]["text"]
    assert "## 前書き\n- date: 2026-11-05\n" in text and "- time:" not in text and "- kind:" not in text


def test_read_request_carries_the_front():
    body = P.read_request(
        "claude-opus-5-5", None, [JPEG], language="ja", date="2026-11-05", time="09:00:00", kind="own"
    )
    text = body["messages"][0]["content"][-1]["text"]
    assert "- date: 2026-11-05\n- time: 09:00:00\n- kind: own" in text


def test_skill_text_adds_sources_md_only(tmp_path):
    """章は資料を sources.md の番号で引くので sources.md を足す。sources-*.md と plants/ は足さない。"""
    skill = tmp_path / "skill"
    (skill / "plants" / "x").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# 手引きの本体\n", encoding="utf-8")
    (skill / "06-畑を読む.md").write_text("# 06\n", encoding="utf-8")
    (skill / "sources.md").write_text("# 資料\n3. 一次資料\n", encoding="utf-8")
    (skill / "sources-wildlife.md").write_text("# 資料の候補\n", encoding="utf-8")
    (skill / "plants" / "x" / "README.md").write_text("# 草の頁\n", encoding="utf-8")
    text = P.skill_text(skill)
    assert text.index("手引きの本体") < text.index("# 06") < text.index("3. 一次資料")
    assert "資料の候補" not in text and "草の頁" not in text
    blocks = P.system_blocks(skill, "ja")
    assert "3. 一次資料" in blocks[0]["text"] and blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_skill_text_without_sources_md(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# 手引きの本体\n", encoding="utf-8")
    assert P.skill_text(skill) == "# 手引きの本体\n"
