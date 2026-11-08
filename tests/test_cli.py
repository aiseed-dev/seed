# SPDX-License-Identifier: AGPL-3.0-or-later
import json

import httpx
import pytest
from test_photos import make_jpeg

from seed import cli
from seed import client as seed_client
from seed.client import Client
from seed.records import Observation, Public


def mock_server(monkeypatch, handler):
    """cli が作る Client に MockTransport を差す。"""

    def make(server, token, language, **kw):
        return Client(server, token, language, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(seed_client, "Client", make)


READING = {
    "lines": [
        {"key": "overall", "text": "草が大半", "confidence": 0.8},
        {"key": "soil_surface", "text": "地表は見えない", "confidence": 0.85},
    ],
    "data": [{"key": "geology", "text": "砂岩（出典: 産総研、確認日 2026-11-05）"}],
    "model": "claude-opus-5-5",
    "usage": {},
}


def test_init(seedfolder, capsys):
    assert cli.main(["init", "--folder", str(seedfolder)]) == 0
    assert (seedfolder / "seed.toml").exists()
    assert (seedfolder / "observations").is_dir() and (seedfolder / "place.md").exists()
    assert not (seedfolder.parent / "home-seed-unused").exists()
    assert "用意しました" in capsys.readouterr().out


def test_observe_claude_code_then_mark_and_say(seedfolder, photo, capsys):
    f = str(seedfolder)
    assert (
        cli.main(["observe", "--folder", f, "--claude-code", str(photo), "--say", "did: 今日は見ただけ"]) == 0
    )
    out = capsys.readouterr().out
    assert "Claude Code" in out and "SKILL.md" in out
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    text = path.read_text(encoding="utf-8")
    assert "## Reading (none)" in text and "- did: 今日は見ただけ" in text
    obs = Observation.read(path)
    assert obs.photos == ["photos/2026-11-05/142107.jpg"]
    assert obs.location["points"] == 1
    assert obs.language == "ja"

    # 本人の Claude が読みを書いたとする
    obs.reread([cli.Line("overall", "草が大半", 0.8)], "claude-code")
    obs.write(path)
    assert (
        cli.main(["mark", "2026-11-05-142107", "overall", "wrong", "--reason", "北側は低い", "--folder", f])
        == 0
    )
    assert "違う" in capsys.readouterr().out
    assert cli.main(["--folder", f, "say", "2026-11-05-142107", "saw", "北の端だけ草が低い"]) == 0
    obs = Observation.read(path)
    assert obs.reading[0].render() == "- overall: 草が大半 [0.80]  → farmer: wrong (北側は低い)"
    assert obs.record[-1].text == "北の端だけ草が低い"


def test_mark_unknown(seedfolder, capsys):
    cli.main(["init", "--folder", str(seedfolder)])
    assert cli.main(["mark", "2026-01-01-000000", "overall", "right", "--folder", str(seedfolder)]) == 1
    assert "見つかりません" in capsys.readouterr().err


def test_observe_prints_coarse_coord(seedfolder, photo, capsys):
    """端末に出す座標は小数 2 桁。観察のファイルの中は元の精度のまま。"""
    assert cli.main(["observe", "--folder", str(seedfolder), "--claude-code", str(photo)]) == 0
    out = capsys.readouterr().out
    assert "34.05" in out and "134.25" in out
    assert "34.0512" not in out and "134.2534" not in out
    obs = Observation.read(seedfolder / "observations" / "2026-11-05-142107.md")
    assert [round(c, 4) for c in obs.location["center"]] == [34.0512, 134.2534]


def test_observe_without_server_keeps_observation(seedfolder, photo, capsys):
    code = cli.main(
        ["observe", "--folder", str(seedfolder), "--server-url", "http://127.0.0.1:9", str(photo)]
    )
    assert code == 2
    captured = capsys.readouterr()
    assert "サーバーに届きません（http://127.0.0.1:9）" in captured.err
    assert "Claude Code" in captured.out
    assert (seedfolder / "observations" / "2026-11-05-142107.md").exists()


def test_observe_on_server_writes_reading(seedfolder, photo, monkeypatch):
    seen = {}

    def handler(req):
        seen["body"] = req.read()
        return httpx.Response(200, json=READING)

    mock_server(monkeypatch, handler)
    assert cli.main(["observe", "--folder", str(seedfolder), str(photo)]) == 0
    assert b"34.0512" in seen["body"]
    obs = Observation.read(seedfolder / "observations" / "2026-11-05-142107.md")
    assert obs.model == "claude-opus-5-5"
    assert [l.key for l in obs.reading] == ["overall", "soil_surface"]
    assert obs.data[0].key == "geology" and obs.lookup
    # 照会の行は place.md（農地のデータベース）にも足され、二度目は増えない
    place = (seedfolder / "place.md").read_text(encoding="utf-8")
    assert "- geology: 砂岩" in place and "## Record\n(none)" in place
    assert cli.main(["observe", "--folder", str(seedfolder), str(photo)]) == 0
    assert (seedfolder / "place.md").read_text(encoding="utf-8").count("- geology: 砂岩") == 1
    # 次の読みには place.md の Data と Record が渡る
    (seedfolder / "place.md").write_text(
        place.replace("## Record\n(none)", "## Record\n- saw: 北側は湿る"), encoding="utf-8"
    )
    assert cli.main(["observe", "--folder", str(seedfolder), str(photo)]) == 0
    assert "- geology: 砂岩".encode() in seen["body"] and "北側は湿る".encode() in seen["body"]


def test_observe_refuses_heic_without_pillow_heif(seedfolder, tmp_path, capsys, monkeypatch):
    from seed import photos

    monkeypatch.setattr(photos, "heic_ready", lambda: False)
    p = tmp_path / "a.heic"
    p.write_bytes(b"x")
    assert cli.main(["observe", "--folder", str(seedfolder), "--claude-code", str(p)]) == 1
    assert "HEIC" in capsys.readouterr().err


def test_publish(seedfolder, photo, monkeypatch, capsys):
    f = str(seedfolder)
    mock_server(monkeypatch, lambda req: httpx.Response(200, json=READING))
    cli.main(["observe", "--folder", f, str(photo), "--say", "did: 見ただけ"])
    cli.main(["mark", "--folder", f, "2026-11-05-142107", "overall", "right"])
    capsys.readouterr()

    args = [
        "publish",
        "--folder",
        f,
        "2026-11-05-142107",
        "--place",
        "徳島県 吉野川市",
        "--word",
        "四年、何も入れていない畑。",
    ]
    # id が形に合わなければ止まる
    assert cli.main([*args, "--id", "Bad ID", "--name", "にじ", "--local"]) == 1
    assert "id は" in capsys.readouterr().err

    sent = {}

    def handler(req):
        sent["json"] = req.read().decode()
        return httpx.Response(200, json={"id": "yoshino-1", "url": "https://seed.test/public/yoshino-1.md"})

    mock_server(monkeypatch, handler)
    code = cli.main(
        [
            *args,
            "--id",
            "yoshino-1",
            "--name",
            "にじ",
            "--coord",
            "--what",
            "自給農、放棄地",
            "--next",
            "売る",
        ]
    )
    assert code == 0
    assert "公開しました" in capsys.readouterr().out
    pub = Public.read(seedfolder / "public" / "yoshino-1.md")
    lines = pub.days["2026-11-05"]
    # その日の一枚（選んだ物が無ければ最初の写真）、判定の付いた読み（overall）と data と record。判定の無い soil_surface は入らない
    assert [l.key for l in lines] == ["photo", "overall", "geology", "did"]
    assert pub.coord == [34.05, 134.25]
    assert pub.what == ["自給農", "放棄地"] and pub.next == ["売る"]
    assert "photos/" not in sent["json"]


def test_publish_file_sends_the_draft_as_read(seedfolder, photo, monkeypatch, capsys):
    """下書き（--local）→ 本人が読む（手で直してもよい）→ --file で同じ文を送る。"""
    f = str(seedfolder)
    mock_server(monkeypatch, lambda req: httpx.Response(200, json=READING))
    cli.main(["observe", "--folder", f, str(photo), "--say", "did: 見ただけ"])
    cli.main(["mark", "--folder", f, "2026-11-05-142107", "overall", "right"])
    base = ["publish", "--folder", f]
    draft_args = [
        *base,
        "2026-11-05-142107",
        "--id",
        "draft-1",
        "--place",
        "徳島県",
        "--word",
        "見本の一言",
        "--name",
        "見本",
    ]
    sent: list[str] = []

    def handler(req):
        sent.append(json.loads(req.read().decode())["markdown"])
        return httpx.Response(200, json={"id": "draft-1", "url": "https://seed.test/public/draft-1.md"})

    mock_server(monkeypatch, handler)
    assert cli.main([*draft_args, "--local"]) == 0 and sent == []  # 「出す」の前には送らない
    draft = seedfolder / "public" / "draft-1.md"
    # 本人が読んで、Claude が手で一言を直した物を、そのまま送る
    text = draft.read_text(encoding="utf-8").replace("見本の一言", "見本の一言（直した）")
    draft.write_text(text, encoding="utf-8")
    capsys.readouterr()
    assert cli.main([*base, "--file", str(draft)]) == 0
    assert sent == [text]  # 送られた文はファイルの中身と同じ
    assert "公開しました" in capsys.readouterr().out
    assert draft.read_text(encoding="utf-8") == text  # 組み直して書き換えない

    # サーバーが預かった（state が pending）なら、読まれてから載る事を言う
    mock_server(
        monkeypatch, lambda req: httpx.Response(200, json={"id": "draft-1", "url": "u", "state": "pending"})
    )
    assert cli.main([*base, "--file", str(draft)]) == 0
    assert "サーバーの人が読んでから、載ります" in capsys.readouterr().out
    mock_server(monkeypatch, handler)

    # 形の悪いファイルは送らない
    bad = seedfolder / "public" / "bad.md"
    for body in (
        text.replace("見本の一言（直した）", "電話 090-1234-5678"),  # 電話の形
        text.replace("id: draft-1", "id: Bad ID"),  # id の形
        "前書きの無い文\n",
        text.replace("place:", "secret: x\nplace:"),  # 知らない鍵
    ):
        bad.write_text(body, encoding="utf-8")
        assert cli.main([*base, "--file", str(bad)]) == 1, body
        assert "直す所" in capsys.readouterr().err
    assert cli.main([*base, "--file", str(seedfolder / "public" / "none.md")]) == 1
    assert len(sent) == 1
    # --file 無しで観察も --id も無ければ止まる。--file 無しの動きは今まで通り
    assert cli.main(base) == 1 and "--file" in capsys.readouterr().err
    assert cli.main(draft_args) == 0 and len(sent) == 2 and sent[1] == Public.read(draft).render()


def test_publish_local_without_lines(seedfolder, photo, capsys):
    f = str(seedfolder)
    cli.main(["observe", "--folder", f, "--claude-code", str(photo)])
    capsys.readouterr()
    code = cli.main(
        [
            "publish",
            "--folder",
            f,
            "2026-11-05-142107",
            "--id",
            "a-1",
            "--place",
            "x",
            "--word",
            "y",
            "--name",
            "n",
            "--local",
        ]
    )
    assert code == 1
    assert "行が一つも" in capsys.readouterr().err


@pytest.fixture
def package_skill(tmp_path, monkeypatch):
    """共通の手引きの代わり。"""
    src = tmp_path / "pkg-skill"
    src.mkdir()
    (src / "SKILL.md").write_text("---\nname: seed\n---\n# 手引き\n", encoding="utf-8")
    (src / "06-畑を読む.md").write_text("# 06\n", encoding="utf-8")
    monkeypatch.setattr(cli, "package_skill", lambda: src)
    return src


def test_init_copies_skill_and_keeps_edits(seedfolder, package_skill, capsys):
    f = str(seedfolder)
    assert cli.main(["skill-path", "--folder", f]) == 1
    assert "seed init" in capsys.readouterr().err
    assert cli.main(["init", "--folder", f]) == 0
    assert "写しました" in capsys.readouterr().out
    mine = seedfolder / "skill" / "SKILL.md"
    assert mine.read_text(encoding="utf-8").startswith("---")
    # 本人が直した手引きは、もう一度 init しても上書きしない
    mine.write_text("# 直した\n", encoding="utf-8")
    (package_skill / "SKILL.md").write_text("# 新しい版\n", encoding="utf-8")
    assert cli.main(["init", "--folder", f]) == 0
    assert "上書きしません" in capsys.readouterr().out
    assert mine.read_text(encoding="utf-8") == "# 直した\n"
    assert cli.main(["skill-path", "--folder", f]) == 0
    assert capsys.readouterr().out.strip() == str(seedfolder / "skill")


def test_init_without_package_skill(seedfolder, monkeypatch, capsys):
    monkeypatch.setattr(cli, "package_skill", lambda: None)
    assert cli.main(["init", "--folder", str(seedfolder)]) == 0
    assert "skill/" in capsys.readouterr().err
    assert not (seedfolder / "skill").exists()


def test_package_skill_finds_repository_skill():
    # 開発中はリポジトリの skill/（まだ無い枝もある）
    p = cli.package_skill()
    assert p is None or (p / "SKILL.md").is_file()


def test_previous_observation_is_sent(seedfolder, tmp_path, monkeypatch, capsys):
    f = str(seedfolder)
    first = make_jpeg(tmp_path / "in" / "1.jpg", taken="2026:11:05 14:21:07")
    later = make_jpeg(tmp_path / "in" / "2.jpg", lat=34.0513, taken="2026:11:12 09:00:00")
    far = make_jpeg(tmp_path / "in" / "3.jpg", lat=35.0, taken="2026:11:13 09:00:00")
    sent = []

    def handler(req):
        sent.append(req.read())
        return httpx.Response(200, json=READING)

    mock_server(monkeypatch, handler)
    assert cli.main(["observe", "--folder", f, str(first), "--say", "did: 刈った"]) == 0
    assert b'name="previous"' not in sent[0]
    assert cli.main(["observe", "--folder", f, str(later)]) == 0
    assert b'name="previous"' in sent[1]
    assert "- did: 刈った".encode() in sent[1] and b"date: '2026-11-05'" in sent[1]
    # 100 m より遠い所は同じ場所ではない
    assert cli.main(["observe", "--folder", f, str(far)]) == 0
    assert b'name="previous"' not in sent[2]
    # 自分の Claude で読む手順にも前の観察が出る
    capsys.readouterr()
    again = make_jpeg(tmp_path / "in" / "4.jpg", taken="2026:11:20 09:00:00")
    assert cli.main(["observe", "--folder", f, "--claude-code", str(again)]) == 0
    out = capsys.readouterr().out
    assert "observations/2026-11-12-090000.md も一緒に" in out
    assert str(seedfolder / "skill" / "SKILL.md") in out


def test_split_tags():
    assert cli.split_tags("自給農、放棄地, 藍") == ["自給農", "放棄地", "藍"]
    assert cli.split_tags(None) == []


def test_app_screens_import():
    # 画面は import できることだけ確かめる（動かすのは flet run で）
    from seed.app import main

    assert [sc.route for sc in main.SCREENS] == ["/", "/photos"]
    assert callable(main.main) and callable(main.run)


def test_strings_have_same_words():
    from seed.app.strings import STRINGS, error_text, key_label, s

    assert set(STRINGS["ja"]) == set(STRINGS["en"])
    assert s("nav_talk", "ja") == "話す" and s("nav_photos", "en") == "Photos"
    assert s("right", "ja") == "合う" and s("wrong", "sw") == "wrong"
    assert key_label("change", "ja") == "変化" and key_label("change", "en") == "Change"
    assert key_label("geology", "ja") == "geology"
    e = seed_client.ClientError("server_unreachable", "x")
    assert (
        error_text(e, "ja", server="http://a")
        == "サーバーに届きません（http://a）。少しして試すか、「自分の Claude で読む」で。"
    )
    e = seed_client.ClientError("server_rejected", "x", detail=["自分には送れない"])
    assert "（自分には送れない）" in error_text(e, "ja") and "[" not in error_text(e, "ja")
    e = seed_client.ClientError("server_rejected", "x", detail=["a", "b"])
    assert error_text(e, "en").endswith("(a, b)") and error_text(e, "ja").endswith("（a、b）")


def test_observe_candidate_and_owner_warning(seedfolder, photo, capsys):
    f = str(seedfolder)
    assert (
        cli.main(
            [
                "observe",
                "--folder",
                f,
                "--claude-code",
                "--candidate",
                str(photo),
                "--say",
                "note: 道から撮った",
            ]
        )
        == 0
    )
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    assert "kind: candidate" in path.read_text(encoding="utf-8")
    assert Observation.read(path).kind == "candidate"
    capsys.readouterr()
    args = ["publish", "--folder", f, "2026-11-05-142107", "--id", "c-1", "--place", "x", "--word", "y"]
    assert cli.main([*args, "--name", "n", "--local"]) == 0
    assert "所有者の名前・住所は公開しない" in capsys.readouterr().err


def test_missing_app_extra_is_one_sentence(seedfolder, monkeypatch, capsys):
    # clone して pip install -e . だけ（app extra 無し）で写真のコマンドを使ったとき
    def no_pil(st, args):
        raise ModuleNotFoundError("No module named 'PIL'", name="PIL")

    monkeypatch.setitem(cli.COMMANDS, "observe", no_pil)
    assert cli.main(["observe", "--folder", str(seedfolder), "x.jpg"]) == 1
    assert ".[app]" in capsys.readouterr().err


def test_init_shows_keep_and_free_space(seedfolder, capsys):
    assert cli.main(["init", "--folder", str(seedfolder), "--keep", "research"]) == 0
    out = capsys.readouterr().out
    assert "残す量は research" in out and "ディスクの空きは" in out
    assert 'keep = "research"' in (seedfolder / "seed.toml").read_text()


def test_keep_shows_and_changes(seedfolder, capsys):
    cli.main(["init", "--folder", str(seedfolder)])
    assert cli.main(["keep", "--folder", str(seedfolder)]) == 0
    assert "残す量は photos" in capsys.readouterr().out
    assert cli.main(["keep", "--folder", str(seedfolder), "text"]) == 0
    assert "残す量を text にしました" in capsys.readouterr().out
    assert 'keep = "text"' in (seedfolder / "seed.toml").read_text()


def test_prune_shows_then_deletes_only_with_yes(seedfolder, capsys, monkeypatch):
    cli.main(["init", "--folder", str(seedfolder)])
    raw = seedfolder / "observations" / "2026-11-05-142107.raw"
    raw.mkdir(parents=True)
    (raw / "answer.json").write_text("{}")
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    assert cli.main(["prune", "--folder", str(seedfolder)]) == 0
    out = capsys.readouterr().out
    assert "2026-11-05-142107.raw" in out and "消しませんでした" in out and raw.exists()
    assert cli.main(["prune", "--folder", str(seedfolder), "--yes"]) == 0
    assert "1 個" in capsys.readouterr().out and not raw.exists()
    assert cli.main(["prune", "--folder", str(seedfolder)]) == 0
    assert "消す物はありません" in capsys.readouterr().out


def test_observe_ask_written_and_validated(seedfolder, photo, capsys):
    f = str(seedfolder)
    args = ["observe", "--folder", f, "--claude-code", str(photo)]
    assert cli.main([*args, "--ask", "grow,soil", "--ask", "names", "--say", "ask: 果樹は向くか"]) == 0
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    obs = Observation.read(path)
    assert obs.ask == ["grow", "soil", "names"]
    assert [l.text for l in obs.record if l.key == "ask"] == ["果樹は向くか"]
    assert "ask: [grow, soil, names]" in path.read_text(encoding="utf-8")
    capsys.readouterr()
    assert cli.main([*args, "--ask", "weather"]) == 1
    assert "--ask" in capsys.readouterr().err


def test_observe_research_keeps_raw(seedfolder, photo, tmp_path, monkeypatch, capsys):
    from test_local import ANSWER, fake_claude

    from seed import local

    cli.main(["init", "--folder", str(seedfolder), "--keep", "research"])
    exe = fake_claude(tmp_path, ANSWER)
    monkeypatch.setattr(local, "available", lambda: str(exe))
    assert cli.main(["observe", "--folder", str(seedfolder), str(photo)]) == 0
    raws = list((seedfolder / "observations").glob("*.raw"))
    assert len(raws) == 1 and (raws[0] / "meta.json").exists()


def test_init_with_bulk_shows_both_disks_and_prune_reaches_it(seedfolder, tmp_path, capsys):
    bulk = tmp_path / "hdd" / "field"
    assert cli.main(["init", "--folder", str(seedfolder), "--bulk", str(bulk)]) == 0
    out = capsys.readouterr().out
    assert "重い物の置き場を" in out and str(bulk) in out and "そこの空きは" in out
    assert bulk.is_dir() and f'bulk = "{bulk}"' in (seedfolder / "seed.toml").read_text()
    (bulk / "originals" / "2026-11-05").mkdir(parents=True)
    (bulk / "originals" / "2026-11-05" / "142107.heic").write_bytes(b"x" * 10)
    assert cli.main(["prune", "--folder", str(seedfolder), "--yes"]) == 0
    assert not (bulk / "originals").exists()
    assert cli.main(["keep", "--folder", str(seedfolder), "--bulk", ""]) == 0
    assert "戻しました" in capsys.readouterr().out


def test_plan_claude_code_then_say_and_mark(seedfolder, photo, capsys):
    f = str(seedfolder)
    assert (
        cli.main(
            ["plan", "--folder", f, "--claude-code", "--season", "2026-27 冬", "--decided", "南側は草のまま"]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "plan.md" in out and "09 章" in out
    from seed.records import Plan

    plan = Plan.read(seedfolder / "plan.md")
    assert plan.season == "2026-27 冬" and [l.key for l in plan.record] == ["decided"] and plan.reading == []
    assert cli.main(["say", "--folder", f, "plan", "did", "北側を刈った"]) == 0
    assert [l.key for l in Plan.read(seedfolder / "plan.md").record] == ["decided", "did"]
    (seedfolder / "plan.md").write_text(
        Plan.read(seedfolder / "plan.md")
        .render()
        .replace("## Plan (none)\n(none)", "## Plan (claude-code)\n- sow: 北側に小麦 [0.70]"),
        encoding="utf-8",
    )
    assert cli.main(["mark", "--folder", f, "plan", "sow", "wrong", "--reason", "種が無い"]) == 0
    assert Plan.read(seedfolder / "plan.md").reading[0].reason == "種が無い"
    assert cli.main(["say", "--folder", f, "plan", "saw", "x"]) == 1  # 計画の本人の行は decided, did


def test_plan_local_writes_plan(seedfolder, tmp_path, monkeypatch, capsys):
    from test_local import PLAN_ANSWER, fake_claude

    from seed import local
    from seed.records import Plan

    exe = fake_claude(tmp_path, PLAN_ANSWER)
    monkeypatch.setattr(local, "available", lambda: str(exe))
    assert cli.main(["plan", "--folder", str(seedfolder), "--local"]) == 0
    plan = Plan.read(seedfolder / "plan.md")
    assert plan.model == "claude-opus-5-5" and [l.key for l in plan.reading] == [
        "sow",
        "uncertain",
        "next_to_observe",
    ]
    assert "claude-opus-5-5" in capsys.readouterr().out


def test_init_invite_and_invite_command(seedfolder, capsys, credentials_in_tmp):
    f = str(seedfolder)
    assert cli.main(["init", "--folder", f, "--invite", "inv-abc"]) == 0
    # 招待コードは credentials.toml に。seed.toml には書かない（設計書 §5.1）
    assert "inv-abc" not in (seedfolder / "seed.toml").read_text(encoding="utf-8")
    assert 'invite = "inv-abc"' in credentials_in_tmp.read_text(encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["invite", "--folder", f]) == 0
    assert "inv-abc" in capsys.readouterr().out
    assert cli.main(["invite", "--folder", f, ""]) == 0
    assert 'invite = ""' in credentials_in_tmp.read_text(encoding="utf-8")
    assert "invite =" not in (seedfolder / "seed.toml").read_text(encoding="utf-8")


def test_invite_list_shows_names_and_code_heads_only(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("SEED_INVITES", raising=False)
    inv = tmp_path / "invites.toml"
    inv.write_text(
        '[codes]\n"abcd-secret-rest-1" = "よしの"\n"wxyz-secret-rest-2" = "あい"\n', encoding="utf-8"
    )
    folder = tmp_path / "nofolder"
    assert cli.main(["invite", "--folder", str(folder), "--list", "--invites", str(inv)]) == 0
    out = capsys.readouterr().out
    assert "2 件" in out and "よしの" in out and "あい" in out and "abcd…" in out and "wxyz…" in out
    assert "secret" not in out
    assert not folder.exists()  # サーバーの上で seed.toml を作らない
    monkeypatch.setenv("SEED_INVITES", str(inv))
    assert cli.main(["invite", "--folder", str(folder), "--list"]) == 0
    assert "よしの" in capsys.readouterr().out
    inv.write_text("[codes\n", encoding="utf-8")
    assert cli.main(["invite", "--folder", str(folder), "--list"]) == 1
    monkeypatch.delenv("SEED_INVITES")
    assert cli.main(["invite", "--folder", str(folder), "--list"]) == 2


# ---- seed marks


def test_marks_wrong_by_key_with_chapter_lines(seedfolder, capsys):
    from test_records import make_marked_folder

    f = make_marked_folder(seedfolder)
    cli.copy_skill(f)
    before = {p: p.read_text(encoding="utf-8") for p in (f.root / "observations").glob("*.md")}
    assert cli.main(["marks", "--folder", str(seedfolder)]) == 0
    out = capsys.readouterr().out
    assert "違う 4（観察 2 件、plan.md）" in out and "合う" not in out.split("\n## ")[0]
    # key の順は読みの順 → 計画の順。key の中は古い順
    assert [l for l in out.splitlines() if l.startswith("## ")] == [
        "## soil_surface — 違う 1",
        "## plants — 違う 2",
        "## sow — 違う 1",
    ]
    plants = out.split("## plants")[1].split("## sow")[0]
    assert plants.index("2026-11-02 15:34:02 の観察、前の読み: 草丈 1 m のススキ [0.50]") < plants.index(
        "2026-11-05 14:21:07 の観察: ススキらしいイネ科が優占 [0.70]"
    )
    assert "→ 違う（ススキではなくてオギ）" in plants and "→ 違う（3 m はある）" in plants
    # 06 章の当たる行: 表の行と、太字の語で始まる箇条書き
    assert f"06 章: {f.skill / '06-畑を読む.md'}" in out
    assert "| `plants` |" in plants and "**草。**" in plants
    assert "| `soil_surface` |" in out.split("## soil_surface")[1] and "**裸地。**" in out
    assert out.split("## sow")[1].strip().endswith("06 章に対応する行無し")
    assert "合う" not in out.split("## sow")[1]
    assert not (seedfolder / "seed.toml").exists()  # 何も作らない
    assert {p: p.read_text(encoding="utf-8") for p in (f.root / "observations").glob("*.md")} == before


def test_marks_all_and_key(seedfolder, capsys):
    from test_records import make_marked_folder

    make_marked_folder(seedfolder)
    assert cli.main(["marks", "--folder", str(seedfolder), "--all"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# 合う／違うの付いた行") and "違う 4、合う 3" in out
    assert "## overall — 合う 1" in out and "plan.md、前の読み: 刈った草を敷く [0.70]\n  → 合う" in out
    assert cli.main(["marks", "--folder", str(seedfolder), "--key", "plants"]) == 0
    out = capsys.readouterr().out
    assert [l for l in out.splitlines() if l.startswith("## ")] == ["## plants — 違う 2"]
    assert "（key: plants）" in out
    assert cli.main(["marks", "--folder", str(seedfolder), "--key", "overall"]) == 0
    assert "違うの付いた行はまだ無い（key: overall）。合うは 1 行（--all で出す）" in capsys.readouterr().out


def test_marks_json(seedfolder, capsys):
    import json

    from test_records import make_marked_folder

    make_marked_folder(seedfolder)
    assert cli.main(["marks", "--folder", str(seedfolder), "--json", "--key", "plants"]) == 0
    got = json.loads(capsys.readouterr().out)
    assert [(m["when"], m["earlier"], m["reason"], m["name"]) for m in got["marks"]] == [
        ("2026-11-02 15:34:02", True, "3 m はある", "2026-11-02-153402"),
        ("2026-11-05 14:21:07", False, "ススキではなくてオギ", "2026-11-05-142107"),
    ]
    assert got["marks"][0]["source"] == "observation" and got["marks"][0]["verdict"] == "wrong"
    assert any("`plants`" in l["text"] for l in got["chapter_lines"]["plants"])  # パッケージの 06 章
    assert got["chapter"].endswith("06-畑を読む.md")


def test_marks_nothing(seedfolder, capsys):
    import json

    assert cli.main(["marks", "--folder", str(seedfolder)]) == 0  # フォルダーが無くても
    assert capsys.readouterr().out.strip() == "合う／違うの付いた行はまだ無い"
    cli.main(["init", "--folder", str(seedfolder)])
    capsys.readouterr()
    assert cli.main(["marks", "--folder", str(seedfolder), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["marks"] == []


def test_chapter_lines_skips_code_and_comments():
    # 行番号: 1 見出し、2 見出し、3-4 箇条書き、6-8 コード、9-10 注釈、11-13 表、14 見出し、15 箇条書き
    text = """# 02
## この畑の草の名前（本人）
- **草。** 種類、高さ
  続きの行

```
- plants: 例の行 `plants` [0.70]
```
<!-- 本人が書く: `plants`
-->
| key | 書くこと |
|---|---|
| `plants` | 草の種類 |
### `overall` から `next_to_observe` まで
- 撮った場所の偏りを `overall` に書きます
"""
    assert cli.chapter_lines(text, "plants") == [
        (2, "## この畑の草の名前（本人）"),
        (3, "- **草。** 種類、高さ続きの行"),
        (13, "| `plants` | 草の種類 |"),
    ]
    assert cli.chapter_lines(text, "overall") == [(15, "- 撮った場所の偏りを `overall` に書きます")]
    assert cli.chapter_lines(text, "sow") == []


def test_publish_sends_chosen_photo(seedfolder, photo, monkeypatch, capsys):
    """seed publish --photo: photo の行が入り、縮めた写真が一緒に送られる。手元に無ければ送らない。"""
    import base64

    f = str(seedfolder)
    mock_server(monkeypatch, lambda req: httpx.Response(200, json=READING))
    cli.main(["observe", "--folder", f, str(photo), "--say", "did: 見ただけ"])
    sent: list[dict] = []

    def handler(req):
        sent.append(json.loads(req.read().decode()))
        return httpx.Response(200, json={"id": "p-1", "url": "https://seed.test/public/p-1.md"})

    mock_server(monkeypatch, handler)
    args = [
        "publish",
        "--folder",
        f,
        "2026-11-05-142107",
        "--id",
        "p-1",
        "--place",
        "徳島県",
        "--word",
        "畑",
        "--name",
        "見本",
    ]
    assert cli.main([*args, "--photo", "142107"]) == 0
    name = "2026-11-05_142107.jpg"
    assert sent[0]["markdown"].count(f"- photo: {name}") == 1 and list(sent[0]["photos"]) == [name]
    assert base64.b64decode(sent[0]["photos"][name]).startswith(b"\xff\xd8")
    capsys.readouterr()
    assert cli.main([*args, "--photo", "999999"]) == 1 and "999999" in capsys.readouterr().err
    (seedfolder / "photos" / "2026-11-05" / "142107.jpg").unlink()
    assert cli.main(["publish", "--folder", f, "--file", str(seedfolder / "public" / "p-1.md")]) == 1
    assert name in capsys.readouterr().err and len(sent) == 1


def test_init_writes_claude_md_and_keeps_edits(seedfolder, capsys):
    from seed import claude_md

    f = str(seedfolder)
    assert cli.main(["init", "--folder", f]) == 0
    assert "CLAUDE.md を書いた" in capsys.readouterr().out
    mine = seedfolder / "CLAUDE.md"
    body = mine.read_text(encoding="utf-8")
    assert "skill/SKILL.md" in body and "plugins/" in body
    mine.write_text("# 直した\n", encoding="utf-8")
    assert cli.main(["init", "--folder", f]) == 0
    assert "CLAUDE.md はもうある" in capsys.readouterr().out
    assert mine.read_text(encoding="utf-8") == "# 直した\n"
    assert "skill/SKILL.md" in claude_md.text("en")
