import pytest


@pytest.fixture(autouse=True)
def no_local_claude(monkeypatch):
    """テストでは手元の claude を見つけない（見つかると observe の既定が手元になる）。使うテストは上書きする。"""
    from seed import local

    monkeypatch.setattr(local, "available", lambda: None)


@pytest.fixture(autouse=True)
def credentials_in_tmp(tmp_path, monkeypatch):
    """秘密の置き場（~/.config/seed/credentials.toml）にテストが書かないよう、tmp に向ける。"""
    path = tmp_path / "config" / "credentials.toml"
    monkeypatch.setenv("SEED_CREDENTIALS", str(path))
    return path


@pytest.fixture(autouse=True)
def fields_in_tmp(tmp_path, monkeypatch):
    """畑の一覧（~/.config/seed/fields.toml）も tmp に向ける。テストの中では始め無い。"""
    path = tmp_path / "config" / "fields.toml"
    monkeypatch.setenv("SEED_FIELDS", str(path))
    return path


@pytest.fixture
def seedfolder(tmp_path, monkeypatch):
    """本人のフォルダーの道（まだ無い）。言語は ja、サーバーの環境変数は無し。CLI と画面のテストで使う。"""
    monkeypatch.setenv("LANGUAGE", "ja")
    monkeypatch.delenv("SEED_SERVER_URL", raising=False)
    monkeypatch.setenv("SEED_FOLDER", str(tmp_path / "home-seed-unused"))
    return tmp_path / "seed"


@pytest.fixture
def photo(tmp_path):
    from test_photos import make_jpeg

    return make_jpeg(tmp_path / "in" / "IMG_0012.jpg")


@pytest.fixture(autouse=True)
def no_home_server(monkeypatch):
    """家のサーバーか（client.is_home）を聞きに網へ出ない。使うテストは上書きする。覚えもテストごとに空に。"""
    from seed import client

    client._HOME.clear()
    monkeypatch.setattr(client, "is_home", lambda *a, **k: False)
    yield
    client._HOME.clear()


@pytest.fixture(autouse=True)
def no_weather_fill(monkeypatch):
    """気象の穴埋め（網に出る）は、使うテスト以外では何もしない。"""
    from seed import weather

    monkeypatch.setattr(weather, "fill_missing", lambda *a, **k: 0)
