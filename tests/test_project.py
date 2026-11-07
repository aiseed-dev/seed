# SPDX-License-Identifier: AGPL-3.0-or-later
"""一つのプロジェクトに畑を幾つも（設計書 §5.12）。

fields/<名>/ の畑、seed.toml の field、seed field new/use/list と seed project、共有の物（skill、CLAUDE.md、plugins）を
畑 → プロジェクトの根の順に探す事、アプリの上の端の名と板、プロジェクト全体の写真と話す。
"""

from __future__ import annotations

import tomllib

import flet as ft
import pytest
from test_app import FakePage, run, texts, walk

from seed import claude_md, cli, local
from seed import fields as fields_mod
from seed import settings as settings_mod
from seed.app import gallery, talk
from seed.app.main import App
from seed.records import Folder


@pytest.fixture(autouse=True)
def no_lookup(monkeypatch):
    """土地の照会は網に出るので、呼ばない。"""
    from seed import lookup as L

    monkeypatch.setattr(L, "available", lambda: False)


@pytest.fixture
def project(seedfolder):
    """畑が二つ（北、南）のプロジェクト。seed.toml は seed field new が作る。"""
    assert cli.main(["field", "new", "北", "--folder", str(seedfolder)]) == 0
    assert field_of(seedfolder, "北") == "北"  # 作った畑が今の畑
    assert cli.main(["field", "new", "南", "--folder", str(seedfolder)]) == 0
    assert field_of(seedfolder, "南") == "南"
    assert cli.main(["field", "use", "all", "--folder", str(seedfolder)]) == 0  # テストは全体から始める
    return seedfolder


def field_of(project, name: str) -> str:
    return tomllib.loads((project / "seed.toml").read_text(encoding="utf-8")).get("field", "")


def observe_in(project, tmp_path, name: str, taken: str) -> None:
    from test_photos import make_jpeg

    a = make_jpeg(tmp_path / "in" / name / "a.jpg", taken=taken)
    folder = project / "fields" / name
    assert cli.main(["observe", "--folder", str(folder), "--claude-code", str(a)]) == 0


# ---------------------------------------------------------------- CLI


def test_field_new_makes_records_and_keeps_shared_at_root(project, capsys):
    north = project / "fields" / "北"
    assert (north / "observations").is_dir() and (north / "place.md").is_file()
    assert (project / "seed.toml").is_file() and not (north / "seed.toml").exists()
    assert (project / "skill" / "SKILL.md").is_file() and not (north / "skill").exists()
    assert (project / "CLAUDE.md").is_file() and not (north / "CLAUDE.md").exists()
    assert not (project / "observations").exists()  # 根に記録の中身は作らない
    assert cli.main(["field", "new", "北", "--folder", str(project)]) == 0
    assert "もうある" in capsys.readouterr().out
    assert cli.main(["field", "new", "../外", "--folder", str(project)]) == 1


def test_field_new_moves_root_records_into_the_field(seedfolder, tmp_path, capsys):
    from test_photos import make_jpeg

    for i, taken in enumerate(("2026:11:05 14:21:07", "2026:11:06 09:00:00")):
        a = make_jpeg(tmp_path / "in" / f"{i}.jpg", taken=taken)
        assert cli.main(["observe", "--folder", str(seedfolder), "--claude-code", str(a)]) == 0
    assert len(list((seedfolder / "observations").glob("*.md"))) == 2
    assert (seedfolder / "place.md").is_file()
    capsys.readouterr()
    assert cli.main(["field", "new", "北", "--folder", str(seedfolder)]) == 0
    assert "畑「北」に移した" in capsys.readouterr().out
    north = seedfolder / "fields" / "北"
    assert len(list((north / "observations").glob("*.md"))) == 2
    assert list((north / "photos").rglob("*.jpg")) and (north / "place.md").is_file()
    assert not (seedfolder / "observations").exists() and not (seedfolder / "photos").exists()
    assert not (seedfolder / "place.md").exists()
    assert (seedfolder / "seed.toml").is_file() and (seedfolder / "skill").is_dir()  # 共有の物は根に
    assert (seedfolder / "CLAUDE.md").is_file()
    assert field_of(seedfolder, "北") == "北"
    capsys.readouterr()
    assert cli.main(["field", "list", "--folder", str(seedfolder)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "  （全体）" and out[1].startswith("* 北")
    # 二つ目の畑では移さない
    assert cli.main(["field", "new", "南", "--folder", str(seedfolder)]) == 0
    assert len(list((north / "observations").glob("*.md"))) == 2


def test_field_new_moves_bulk_originals(seedfolder):
    bulk = seedfolder.parent / "hdd"
    st = settings_mod.load(seedfolder)
    st.bulk = str(bulk)
    st.save()
    (seedfolder / "observations").mkdir()
    (bulk / "originals" / "2026-11-05").mkdir(parents=True)
    (bulk / "originals" / "2026-11-05" / "a.heic").write_bytes(b"x")
    assert cli.main(["field", "new", "北", "--folder", str(seedfolder)]) == 0
    assert (bulk / "fields" / "北" / "originals" / "2026-11-05" / "a.heic").is_file()
    assert not (bulk / "originals").exists()


def test_field_use_and_list(project, capsys):
    capsys.readouterr()
    assert cli.main(["field", "list", "--folder", str(project)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "* （全体）" and out[1].startswith("  北") and out[2].startswith("  南")
    assert cli.main(["field", "use", "南", "--folder", str(project)]) == 0
    assert field_of(project, "南") == "南"
    capsys.readouterr()
    assert cli.main(["field", "list", "--folder", str(project)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "  （全体）" and out[2].startswith("* 南")
    assert cli.main(["field", "use", "all", "--folder", str(project)]) == 0
    assert field_of(project, "") == ""
    assert cli.main(["field", "use", "無い", "--folder", str(project)]) == 1
    assert "一覧に無い" in capsys.readouterr().err


def test_resolve_with_fields(project, tmp_path):
    assert fields_mod.resolve(folder=str(project)) == project  # field が空: プロジェクト全体
    settings_mod.write_field(project, "北")
    assert fields_mod.resolve(folder=str(project)) == project / "fields" / "北"
    assert fields_mod.resolve(field="南", folder=str(project)) == project / "fields" / "南"  # --field が畑
    # 畑のフォルダーを指す --folder は、そのプロジェクトとその畑
    assert fields_mod.locate(None, str(project / "fields" / "南")) == (str(project), "南")
    settings_mod.write_field(project, "消えた畑")
    assert fields_mod.resolve(folder=str(project)) == project  # 無い畑は全体


def test_settings_records_follow_field(project):
    st = settings_mod.load(project)
    assert st.field_names == ["北", "南"] and st.whole and st.records.whole
    assert st.records.root == project and st.records.list_observations() == []
    st.pick = "北"
    assert st.records.root == project / "fields" / "北" and st.records.project == project
    assert not st.whole
    single = settings_mod.load(project / "fields" / "北" / "x")  # fields/ の無いフォルダーは今まで通り
    assert single.field_names == [] and single.records.project is None and not single.whole
    assert not [l for l in single.render().splitlines() if l.startswith("field =")]  # 空は書かない


def test_whole_project_refuses_record_commands(project, tmp_path, capsys):
    capsys.readouterr()
    assert cli.main(["photos", "--by-place", "--folder", str(project)]) == 1
    assert "プロジェクト全体" in capsys.readouterr().err
    assert cli.main(["photos", "--by-place", "--folder", str(project), "--field", "北"]) == 0
    observe_in(project, tmp_path, "北", "2026:11:05 14:21:07")
    assert list((project / "fields" / "北" / "observations").glob("*.md"))
    assert not (project / "fields" / "北" / "seed.toml").exists()
    capsys.readouterr()
    assert cli.main(["skill-path", "--folder", str(project / "fields" / "北")]) == 0
    assert capsys.readouterr().out.strip() == str(project / "skill")


def test_project_commands_and_field_alias(tmp_path, seedfolder, capsys, fields_in_tmp):
    a, b = tmp_path / "farm-a", tmp_path / "farm-b"
    assert cli.main(["project", "list"]) == 0
    assert "まだ無い" in capsys.readouterr().out
    assert cli.main(["project", "add", "自分の畑", str(a)]) == 0
    assert cli.main(["field", "add", "知人の田", str(b)]) == 0  # 前の名
    assert "seed project add" in capsys.readouterr().err
    assert cli.main(["project", "use", "自分の畑"]) == 0
    capsys.readouterr()
    assert cli.main(["project", "list"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("* 自分の畑") and out[1].startswith("  知人の田")
    # seed field use に一覧の名: seed project use と同じ（一行知らせる）
    assert cli.main(["field", "use", "知人の田"]) == 0
    assert "seed project use" in capsys.readouterr().err
    assert fields_mod.load_fields().current == "知人の田"
    assert cli.main(["project", "use", "無い"]) == 1


# ---------------------------------------------------------------- 共有の物


def test_shared_prefers_field_over_project(tmp_path):
    p = tmp_path / "p"
    f = p / "fields" / "a"
    f.mkdir(parents=True)
    folder = Folder(f, project=p)
    assert folder.shared("skill") == p / "skill" and folder.skill == p / "skill"
    (f / "skill").mkdir()
    assert folder.shared("skill") == f / "skill" and folder.skill == f / "skill"
    assert Folder(f).shared("plugins") == f / "plugins"  # 畑が一つなら根の物


def test_skill_from_project_root(project):
    (project / "skill" / "SKILL.md").write_text("# 本人の手引き 根の物\n", encoding="utf-8")
    folder = Folder(project / "fields" / "北", project=project)
    assert "本人の手引き 根の物" in local.system_prompt(folder)


def test_claude_md_at_project_root(tmp_path):
    p = tmp_path / "p"
    p.mkdir()
    folder = Folder(p / "fields" / "a", project=p)
    cli.prepare(folder, "ja")
    assert (p / claude_md.NAME).is_file() and not (folder.root / claude_md.NAME).exists()


def test_own_plugins_from_project_root(project):
    from seed.app import plugins

    (project / "plugins").mkdir()
    (project / "plugins" / "memo.py").write_text(
        'TITLE = {"ja": "メモ"}\nICON = "NOTES"\n\ndef build(app):\n    return []\n', encoding="utf-8"
    )
    folder = Folder(project / "fields" / "北", project=project)
    assert [p.route for p in plugins.own(folder)] == ["/p/memo"]


# ---------------------------------------------------------------- アプリ


def make_app(project, field: str = "") -> App:
    settings_mod.write_field(project, field)
    a = App(FakePage(), str(project))
    a.lang = "ja"
    return a


def test_app_bar_name_with_field(project):
    app = make_app(project, "北")
    assert app.field_name == "北" and app.folder.root == project / "fields" / "北"
    assert [f.root.name for f in app.fields] == ["北", "南"]
    assert app.view("/photos", []).appbar.title.value == f"{project.name} / 北 — 写真"
    whole = make_app(project)
    assert whole.whole and whole.field_name is None
    assert whole.view("/photos", []).appbar.title.value == f"{project.name} — 写真"


def test_app_opens_field_folder(project):
    app = App(FakePage(), str(project / "fields" / "南"))
    assert app.field_name == "南" and app.project == project
    assert field_of(project, "") == ""  # 開いただけでは seed.toml を変えない


def test_project_sheet_lists_whole_and_fields(project, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    fl = fields_mod.Fields()
    fl.add("知人の田", str(other))
    fields_mod.save_fields(fl)
    app = make_app(project, "北")
    app.show_projects()
    sheet = app.page.dialogs[-1]
    buttons = {c.content: c for c in walk(sheet) if isinstance(c, ft.TextButton)}
    assert buttons["北"].disabled and buttons["北"].icon == ft.Icons.CHECK
    assert not buttons["南"].disabled and not buttons["プロジェクト全体"].disabled
    assert "知人の田" in buttons and "別のフォルダーを開く" in buttons
    assert any(isinstance(c, ft.Divider) for c in walk(sheet))
    run(buttons["プロジェクト全体"].on_click(None))
    assert app.whole and field_of(project, "") == ""
    app.show_projects()
    buttons = {c.content: c for c in walk(app.page.dialogs[-1]) if isinstance(c, ft.TextButton)}
    assert buttons["プロジェクト全体"].disabled
    run(buttons["南"].on_click(None))
    assert app.field_name == "南" and field_of(project, "南") == "南"


def test_single_field_sheet_has_no_whole(seedfolder):
    app = App(FakePage(), str(seedfolder))
    app.show_projects()
    assert "プロジェクト全体" not in texts(app.page.dialogs[-1])


def in_order(control):
    """部品の木を、並びの順にたどる。"""
    import dataclasses

    yield control
    for f in dataclasses.fields(control):
        if f.name.startswith("_") or f.name == "parent":
            continue
        v = getattr(control, f.name, None)
        for x in v if isinstance(v, list) else [v]:
            if isinstance(x, ft.BaseControl):
                yield from in_order(x)


def subheadings(control) -> list[str]:
    return [
        c.value
        for c in in_order(control)
        if isinstance(c, ft.Text) and c.theme_style == ft.TextThemeStyle.TITLE_MEDIUM
    ]


def test_whole_gallery_has_a_section_per_field(project, tmp_path):
    observe_in(project, tmp_path, "北", "2026:11:05 14:21:07")
    observe_in(project, tmp_path, "南", "2026:11:06 09:00:00")
    app = make_app(project)
    v = gallery.view(app)
    heads = subheadings(v)
    assert heads.index("北") < heads.index("2026-11-05") and heads.index("南") < heads.index("2026-11-06")
    assert heads.index("北") < heads.index("南")
    tiles = [c for c in walk(v) if isinstance(c, ft.Image)]
    assert len(tiles) == 2
    one = make_app(project, "北")
    assert "南" not in subheadings(gallery.view(one)) and "北" not in subheadings(gallery.view(one))


def test_whole_talk_shows_fields_and_passes_rule(project, tmp_path, monkeypatch):
    observe_in(project, tmp_path, "北", "2026:11:05 14:21:07")
    app = make_app(project)
    assert "北" in subheadings(ft.Column(talk.conversation(app)))
    seen = {}

    def fake_run(cmd, cwd, timeout, env=None):
        seen.update(cmd=cmd, cwd=cwd)
        return {"result": "はい", "session_id": "s-1"}

    monkeypatch.setattr(local, "available", lambda: "/usr/bin/claude")
    monkeypatch.setattr(local, "_run", fake_run)
    run(talk.send(app, "北の草はどう？"))
    system = seen["cmd"][seen["cmd"].index("--system-prompt") + 1]
    assert "このプロジェクトには畑が幾つもあります: fields/北/、fields/南/。" in system
    assert "`seed field new <名>`" in system and "`seed field use <名>`" in system
    assert f"--folder {project}/fields/<名>" in system
    assert seen["cwd"] == project
    # 畑を選んでいる時は、その一行を足さない
    one = make_app(project, "北")
    run(talk.send(one, "北の草はどう？"))
    system = seen["cmd"][seen["cmd"].index("--system-prompt") + 1]
    assert "畑が幾つもあります" not in system and seen["cwd"] == project / "fields" / "北"


def test_whole_camera_button_opens_the_sheet(project):
    app = make_app(project)
    bar = talk.composer(app)
    assert "写真を送る、公開するは、畑を選んでからです。" in texts(bar)
    photo_button = next(c for c in walk(bar) if isinstance(c, ft.IconButton) and c.tooltip == "写真を選ぶ")
    run(photo_button.on_click(None))
    assert isinstance(app.page.dialogs[-1], ft.BottomSheet)
    one = make_app(project, "北")
    assert "写真を送る、公開するは、畑を選んでからです。" not in texts(talk.composer(one))


def test_land_plugin_per_field_in_whole(project):
    from seed.plugins import land as land_plugin

    app = make_app(project)
    heads = subheadings(ft.Column(land_plugin.build(app)))
    assert heads.index("北") < heads.index("南")
