# SPDX-License-Identifier: AGPL-3.0-or-later
import tomllib

from seed import settings


def test_load_creates_with_token_and_language(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGUAGE", "ja_JP.UTF-8")
    s = settings.load(tmp_path)
    path = tmp_path / "seed.toml"
    assert path.exists() and s.path == path
    assert len(s.token) >= 32
    assert s.language == "ja"
    assert s.place_level == "city"
    assert s.server_url == "https://seed.aiseed.dev"
    assert s.records.root == tmp_path
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert "token" not in data and "invite" not in data  # 秘密は seed.toml に書かない（設計書 §5.1）
    cred = tomllib.loads(s.credentials.read_text(encoding="utf-8"))
    assert cred["token"] == s.token
    # もう一度読んでも token は変わらない
    assert settings.load(tmp_path).token == s.token


def test_roundtrip_keeps_unicode_quotes_and_unknown_keys(tmp_path):
    (tmp_path / "seed.toml").write_text(
        'name = "にじ"\nlanguage = "en"\ntoken = "abc"\nfuture = [1, 2]\n', encoding="utf-8"
    )
    s = settings.load(tmp_path)
    assert s.name == "にじ" and s.language == "en" and s.token == "abc"
    s.name = 'に"じ\\'
    s.save()
    data = tomllib.loads((tmp_path / "seed.toml").read_text(encoding="utf-8"))
    assert "token" not in data
    assert data["name"] == 'に"じ\\'
    assert data["future"] == [1, 2]
    assert data["folder"] == str(tmp_path)


def test_bad_place_level_falls_back(tmp_path):
    (tmp_path / "seed.toml").write_text('place_level = "street"\ntoken = "t"\nlanguage = "ja"\n')
    assert settings.load(tmp_path).place_level == "city"


def test_default_folder_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_FOLDER", str(tmp_path / "f"))
    assert settings.settings_path() == tmp_path / "f" / "seed.toml"
    s = settings.load(create=False)
    assert not (tmp_path / "f" / "seed.toml").exists()
    assert s.token
    # 記録のフォルダーも同じ所（~/seed に書かない）
    assert s.records.root == tmp_path / "f"
    settings.load()
    assert settings.load().records.root == tmp_path / "f"


def test_server_strips_slash():
    assert settings.Settings(server_url="http://localhost:8000/").server == "http://localhost:8000"


def test_keep_default_and_fallback(tmp_path):
    assert settings.load(tmp_path).keep == "photos"
    (tmp_path / "seed.toml").write_text('keep = "everything"\ntoken = "t"\nlanguage = "ja"\n')
    assert settings.load(tmp_path).keep == "photos"
    (tmp_path / "seed.toml").write_text('keep = "research"\ntoken = "t"\nlanguage = "ja"\n')
    assert settings.load(tmp_path).keep == "research"


def test_bulk_makes_folder_put_originals_elsewhere(tmp_path):
    (tmp_path / "seed.toml").write_text(f'bulk = "{tmp_path / "hdd"}"\ntoken = "t"\nlanguage = "ja"\n')
    f = settings.load(tmp_path).records
    assert f.bulk == tmp_path / "hdd" and f.originals == tmp_path / "hdd" / "originals"
    assert f.photos == tmp_path / "photos"
    assert settings.load(tmp_path / "other").records.bulk is None


# ---------------------------------------------------------------- 秘密（設計書 §5.1）


def test_secrets_not_written_to_seed_toml(tmp_path, credentials_in_tmp):
    s = settings.load(tmp_path / "f")
    s.invite, s.draw_token, s.anthropic_key = "inv-fake-0001", "draw-fake-0001", "sk-fake-key-0001"
    s.save()
    text = (tmp_path / "f" / "seed.toml").read_text(encoding="utf-8")
    assert s.token not in text and "inv-fake-0001" not in text and "draw-fake-0001" not in text
    assert "sk-fake-key-0001" not in text and "sk-fake-key-0001" not in repr(
        s
    )  # 鍵は例外の文やログにも出ない
    for key in settings.SECRETS:
        assert key not in tomllib.loads(text)
    cred = tomllib.loads(credentials_in_tmp.read_text(encoding="utf-8"))
    assert cred == {
        "token": s.token,
        "invite": "inv-fake-0001",
        "draw_token": "draw-fake-0001",
        "anthropic_key": "sk-fake-key-0001",
    }
    again = settings.load(tmp_path / "f")
    assert (again.token, again.invite, again.draw_token) == (s.token, "inv-fake-0001", "draw-fake-0001")


def test_credentials_are_600(tmp_path, credentials_in_tmp):
    import os

    old = os.umask(0o022)
    try:
        settings.load(tmp_path)
    finally:
        os.umask(old)
    assert credentials_in_tmp.stat().st_mode & 0o777 == 0o600
    assert credentials_in_tmp.parent.stat().st_mode & 0o777 == 0o700
    credentials_in_tmp.chmod(0o644)  # 誰かが広げても、次に書くときに戻す
    settings.load(tmp_path).save()
    assert credentials_in_tmp.stat().st_mode & 0o777 == 0o600


def test_credentials_path_from_env_and_given(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_CREDENTIALS", str(tmp_path / "c.toml"))
    assert settings.credentials_path() == tmp_path / "c.toml"
    assert (
        settings.credentials_path(tmp_path / "box" / "credentials.toml")
        == tmp_path / "box" / "credentials.toml"
    )
    monkeypatch.delenv("SEED_CREDENTIALS")
    assert str(settings.credentials_path()).endswith(".config/seed/credentials.toml")


def test_old_seed_toml_secrets_move_to_credentials_once(tmp_path, credentials_in_tmp, capsys):
    tok = "f" * 32
    (tmp_path / "seed.toml").write_text(
        f'name = "にじ"\nlanguage = "ja"\ntoken = "{tok}"\ninvite = "inv-fake-0002"\n', encoding="utf-8"
    )
    s = settings.load(tmp_path)
    assert s.token == tok and s.invite == "inv-fake-0002"
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "credentials" in err and tok not in err and "inv-fake-0002" not in err
    text = (tmp_path / "seed.toml").read_text(encoding="utf-8")
    assert tok not in text and "inv-fake-0002" not in text and 'name = "にじ"' in text
    cred = tomllib.loads(credentials_in_tmp.read_text(encoding="utf-8"))
    assert cred["token"] == tok and cred["invite"] == "inv-fake-0002"
    # 二度目は何も言わない
    assert settings.load(tmp_path).token == tok
    assert capsys.readouterr().err == ""


def test_conflicting_old_token_is_kept_not_lost(tmp_path, credentials_in_tmp, capsys):
    settings.load(tmp_path / "a")  # 一つ目のフォルダーが credentials に token を作る
    other = "g" * 32
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "seed.toml").write_text(f'language = "ja"\ntoken = "{other}"\n', encoding="utf-8")
    capsys.readouterr()
    s = settings.load(tmp_path / "b")
    assert s.token == other  # このフォルダーで公開した物を取り下げられるように
    assert other in (tmp_path / "b" / "seed.toml").read_text(encoding="utf-8")
    assert other not in credentials_in_tmp.read_text(encoding="utf-8")
    assert "SEED_CREDENTIALS" in capsys.readouterr().err
