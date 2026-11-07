"""畑の一覧 fields.toml（記録の形 §19、設計書 §5.8）。"""

import tomllib
from pathlib import Path

import pytest

from seed import cli
from seed import fields as fields_mod


def test_missing_list_is_empty(fields_in_tmp):
    assert not fields_in_tmp.exists()
    fl = fields_mod.load_fields()
    assert fl.fields == [] and fl.current == ""


def test_save_and_load_round_trip(fields_in_tmp):
    fl = fields_mod.Fields(current="自分の畑")
    fl.add("自分の畑", "~/farm/seed")
    fl.add("知人の田", '~/farm/知人の "田"')
    path = fields_mod.save_fields(fl)
    assert path == fields_in_tmp
    text = path.read_text(encoding="utf-8")
    assert text.startswith('current = "自分の畑"')
    assert "[[field]]" in text
    data = tomllib.loads(text)
    assert data["field"][1]["folder"] == '~/farm/知人の "田"'
    back = fields_mod.load_fields()
    assert back == fl
    assert back.get("自分の畑").path == Path.home() / "farm" / "seed"
    # 同じ名を足すとフォルダーを書き換え、並びは変えない
    back.add("自分の畑", "/x")
    assert back.names == ["自分の畑", "知人の田"] and back.get("自分の畑").folder == "/x"


def test_bad_file_is_empty(fields_in_tmp, capsys):
    fields_in_tmp.parent.mkdir(parents=True)
    fields_in_tmp.write_text("current = [", encoding="utf-8")
    assert fields_mod.load_fields().fields == []
    assert "読めない" in capsys.readouterr().err


def test_resolve_order(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_FOLDER", str(tmp_path / "env"))
    # 一覧が無ければ SEED_FOLDER
    assert fields_mod.resolve() == tmp_path / "env"
    assert fields_mod.chosen() is None
    fl = fields_mod.Fields()
    fl.add("a", str(tmp_path / "a"))
    fl.add("b", str(tmp_path / "b"))
    fields_mod.save_fields(fl)
    assert fields_mod.resolve() == tmp_path / "env"  # current が無ければ SEED_FOLDER
    fields_mod.switch_field("a")
    assert fields_mod.resolve() == tmp_path / "a"  # current > SEED_FOLDER
    assert fields_mod.resolve(field="b") == tmp_path / "b"  # --field > current
    assert fields_mod.resolve(field="b", folder=str(tmp_path / "f")) == tmp_path / "f"  # --folder > --field
    with pytest.raises(fields_mod.UnknownField):
        fields_mod.resolve(field="無い")
    monkeypatch.delenv("SEED_FOLDER")
    fields_mod.save_fields(fields_mod.Fields())
    # 本物の ~/seed（seed.toml がある）を読まないよう、HOME を tmp に向ける
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert fields_mod.resolve() == tmp_path / "home" / "seed"


def test_cwd_with_seed_toml_wins(tmp_path, monkeypatch):
    here = tmp_path / "here"
    here.mkdir()
    other = tmp_path / "plain"
    other.mkdir()
    fl = fields_mod.Fields()
    fl.add("a", str(tmp_path / "a"))
    fl.add("b", str(tmp_path / "b"))
    fields_mod.save_fields(fl)
    fields_mod.switch_field("a")
    monkeypatch.setenv("SEED_FOLDER", str(tmp_path / "env"))
    monkeypatch.chdir(other)  # seed.toml が無ければ効かない
    assert fields_mod.resolve() == tmp_path / "a"
    (here / "seed.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(here)
    assert fields_mod.resolve() == here  # 今いるフォルダー > current
    assert fields_mod.resolve(field="b") == here  # 今いるフォルダー > --field
    assert fields_mod.resolve(folder=str(tmp_path / "f")) == tmp_path / "f"  # --folder が先


def test_current_not_in_list_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_FOLDER", str(tmp_path / "env"))
    fields_mod.save_fields(fields_mod.Fields(current="消えた畑"))
    assert fields_mod.resolve() == tmp_path / "env"


def test_switch_field_writes_current_and_returns_folder(tmp_path):
    fl = fields_mod.Fields(current="a")
    fl.add("a", str(tmp_path / "a"))
    fl.add("b", str(tmp_path / "b"))
    fields_mod.save_fields(fl)
    assert fields_mod.switch_field("b") == tmp_path / "b"
    assert fields_mod.load_fields().current == "b"
    assert fields_mod.selected_name(fields_mod.load_fields(), tmp_path / "a") == "a"
    assert fields_mod.selected_name(fields_mod.load_fields(), tmp_path / "zzz") == "b"
    with pytest.raises(fields_mod.UnknownField):
        fields_mod.switch_field("無い")
    assert fields_mod.load_fields().current == "b"


def test_cli_field_add_list_use(tmp_path, seedfolder, capsys, fields_in_tmp):
    a, b = tmp_path / "farm-a", tmp_path / "farm-b"
    assert cli.main(["field", "list"]) == 0
    assert "まだ無い" in capsys.readouterr().out
    assert cli.main(["field", "add", "自分の畑", str(a)]) == 0
    assert cli.main(["field", "add", "知人の田", str(b)]) == 0
    assert not a.exists() and not b.exists()  # 一覧に足すだけで、フォルダーは作らない
    assert cli.main(["field", "use", "知人の田"]) == 0
    capsys.readouterr()
    assert cli.main(["field", "list"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("  自分の畑") and out[1].startswith("* 知人の田")
    assert cli.main(["field", "use", "無い"]) == 1
    assert "一覧に無い" in capsys.readouterr().err
    assert tomllib.loads(fields_in_tmp.read_text(encoding="utf-8"))["current"] == "知人の田"


def test_cli_field_option_chooses_folder(tmp_path, seedfolder, capsys):
    a, b = tmp_path / "farm-a", tmp_path / "farm-b"
    cli.main(["field", "add", "a", str(a)])
    cli.main(["field", "add", "b", str(b)])
    cli.main(["field", "use", "a"])
    assert cli.main(["init"]) == 0  # current の畑
    assert (a / "seed.toml").is_file() and not b.exists()
    assert cli.main(["init", "--field", "b"]) == 0
    assert (b / "seed.toml").is_file()
    other = tmp_path / "other"
    assert cli.main(["init", "--field", "b", "--folder", str(other)]) == 0  # --folder が勝つ
    assert (other / "seed.toml").is_file()
    assert cli.main(["--field", "b", "skill-path"]) == 0
    assert str(b) in capsys.readouterr().out
    assert cli.main(["init", "--field", "無い"]) == 1
    assert "一覧に無い" in capsys.readouterr().err


def test_cli_without_list_keeps_default(seedfolder, monkeypatch, tmp_path):
    monkeypatch.setenv("SEED_FOLDER", str(seedfolder))
    assert cli.main(["init"]) == 0
    assert (seedfolder / "seed.toml").is_file()


def test_remember_folder_adds_and_reuses(fields_in_tmp, tmp_path):
    a = tmp_path / "farm" / "畑A"
    a.mkdir(parents=True)
    assert fields_mod.remember_folder(a) == "畑A"
    fl = fields_mod.load_fields()
    assert fl.names == ["畑A"] and fl.current == "畑A"
    # 書き方を変えても同じ名で、重ならない
    assert fields_mod.remember_folder(a / "." / "..") == "farm"
    assert fields_mod.remember_folder(a / ".." / "畑A") == "畑A"
    assert fields_mod.load_fields().names == ["畑A", "farm"]
    assert fields_mod.load_fields().current == "畑A"


def test_remember_folder_distinct_names_and_home(fields_in_tmp, tmp_path):
    x = tmp_path / "p" / "同じ"
    y = tmp_path / "q" / "同じ"
    z = tmp_path / "q" / "同じ" / "同じ"
    for d in (x, y, z):
        d.mkdir(parents=True, exist_ok=True)
    assert fields_mod.remember_folder(x) == "同じ"
    assert fields_mod.remember_folder(y) == "q/同じ"
    assert fields_mod.remember_folder(z) == "同じ/同じ"
    assert fields_mod.load_fields().names == ["同じ", "q/同じ", "同じ/同じ"]
    # 名と親の名まで同じなら番号
    w = tmp_path / "r" / "q" / "同じ"
    w.mkdir(parents=True)
    assert fields_mod.remember_folder(w) == "q/同じ 2"


def test_remember_folder_writes_home_as_tilde(fields_in_tmp, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    d = tmp_path / "farm" / "畑B"
    d.mkdir(parents=True)
    assert fields_mod.remember_folder(d) == "畑B"
    assert fields_mod.load_fields().get("畑B").folder == "~/farm/畑B"
    assert fields_mod.remember_folder("~/farm/畑B") == "畑B"
    assert fields_mod.load_fields().names == ["畑B"]
