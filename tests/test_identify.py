# SPDX-License-Identifier: AGPL-3.0-or-later
"""草の名を確かめる: Pl@ntNet（設計書 §17）。本物の API は呼ばず、MockTransport で。"""

from __future__ import annotations

import json

import httpx
import pytest

from seed import cli, identify
from seed.records import Line, Observation

ANSWER = {
    "query": {"project": "all", "images": ["1.jpg"], "organs": ["auto"]},
    "results": [
        {
            "score": 0.71,
            "species": {
                "scientificNameWithoutAuthor": "Miscanthus sinensis",
                "scientificNameAuthorship": "Andersson",
                "genus": {"scientificNameWithoutAuthor": "Miscanthus"},
                "family": {"scientificNameWithoutAuthor": "Poaceae"},
                "commonNames": ["Chinese silver grass"],
            },
            "gbif": {"id": "2705109"},
        },
        {
            "score": 0.12,
            "species": {"scientificNameWithoutAuthor": "Miscanthus sacchariflorus", "commonNames": []},
        },
        {"score": 0.01, "species": {"scientificNameWithoutAuthor": "Imperata cylindrica"}},
    ],
    "remainingIdentificationRequests": 498,
}


def transport(status=200, body=ANSWER, seen=None):
    def handler(req: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(req)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def test_parse_and_line():
    r = identify.parse(ANSWER)
    assert [c.scientific for c in r.candidates] == [
        "Miscanthus sinensis",
        "Miscanthus sacchariflorus",
    ]  # 0.01 は落ちる
    assert r.best.score == 0.71 and r.best.gbif == "2705109" and r.remaining == 498
    line = identify.line_for(r, "092817", "ja", "2026-11-04")
    assert line.key == "plants" and line.confidence == 0.71
    assert (
        line.text
        == "Pl@ntNet（092817）: ススキ Miscanthus sinensis 0.71、オギ Miscanthus sacchariflorus 0.12（モデルの読み、2026-11-04）"
    )
    assert identify.is_model_line(line) and not identify.is_model_line(Line("plants", "ススキらしい", 0.5))
    en = identify.line_for(r, "092817", "en", "2026-11-04")
    assert "Chinese silver grass Miscanthus sinensis 0.71" in en.text and "model reading" in en.text
    assert identify.line_for(identify.Identification([]), "x") is None


def test_identify_sends_images_and_key(monkeypatch):
    seen = []
    monkeypatch.setenv(identify.ENV_KEY, "k-test")
    r = identify.identify([b"\xff\xd8one", b"\xff\xd8two"], language="ja", transport=transport(seen=seen))
    assert r.best.scientific == "Miscanthus sinensis"
    req = seen[0]
    assert req.url.host == "my-api.plantnet.org" and req.url.path == "/v2/identify/all"
    assert req.url.params["api-key"] == "k-test" and req.url.params["lang"] == "ja"
    body = req.read()
    assert body.count(b'name="images"') == 2 and body.count(b'name="organs"') == 2 and b"auto" in body


def test_identify_errors(monkeypatch):
    monkeypatch.delenv(identify.ENV_KEY, raising=False)
    with pytest.raises(identify.IdentifyError) as e:
        identify.identify([b"x"], transport=transport())
    assert e.value.word == "identify_no_key"
    assert (
        identify.identify(
            [b"x"], key="k", transport=transport(404, {"message": "Species not found"})
        ).candidates
        == []
    )
    for status, word in ((401, "identify_rejected"), (429, "identify_limit"), (500, "identify_failed")):
        with pytest.raises(identify.IdentifyError) as e:
            identify.identify([b"x"], key="k", transport=transport(status, {}))
        assert e.value.word == word
    with pytest.raises(identify.IdentifyError):
        identify.identify([], key="k", transport=transport())


def test_cli_identify_adds_lines_and_survives_reread(seedfolder, photo, monkeypatch, capsys):
    f = str(seedfolder)
    assert cli.main(["observe", "--folder", f, "--claude-code", str(photo)]) == 0
    monkeypatch.setenv(identify.ENV_KEY, "k-test")
    monkeypatch.setattr(
        identify, "identify", lambda images, key=None, language="ja", **kw: identify.parse(ANSWER)
    )
    capsys.readouterr()
    assert cli.main(["identify", "--folder", f, "2026-11-05-142107"]) == 0
    out = capsys.readouterr().out
    assert "Pl@ntNet（142107）" in out
    path = seedfolder / "observations" / "2026-11-05-142107.md"
    obs = Observation.read(path)
    assert len([l for l in obs.reading if identify.is_model_line(l)]) == 1
    # 同じ写真をもう一度 → 増えない。別の答え → 置き換わる
    assert cli.main(["identify", "--folder", f, "2026-11-05-142107", "142107"]) == 0
    assert len([l for l in Observation.read(path).reading if identify.is_model_line(l)]) == 1
    # 読みを置き換えても残る（判定も）
    obs = Observation.read(path)
    obs.mark("plants", "right")
    obs.write(path)
    obs = Observation.read(path)
    before = list(obs.reading)
    obs.reread([Line("overall", "草が大半", 0.8)], "claude-code")
    cli.keep_model_lines(obs, before)
    assert [l.key for l in obs.reading] == ["overall", "plants"] and obs.reading[1].verdict == "right"
    # 無い写真の名
    assert cli.main(["identify", "--folder", f, "2026-11-05-142107", "nope"]) == 2
    assert cli.main(["identify", "--folder", f, "no-such"]) == 1


def test_observe_ask_names_identifies_when_key(seedfolder, photo, tmp_path, monkeypatch, capsys):
    from test_photos import make_jpeg

    f = str(seedfolder)
    monkeypatch.setenv(identify.ENV_KEY, "k-test")
    monkeypatch.setattr(
        identify, "identify", lambda images, key=None, language="ja", **kw: identify.parse(ANSWER)
    )
    assert cli.main(["observe", "--folder", f, "--claude-code", "--ask", "names", str(photo)]) == 0
    obs = Observation.read(seedfolder / "observations" / "2026-11-05-142107.md")
    assert any(identify.is_model_line(l) for l in obs.reading)
    # 鍵も招待コードも無ければ一言だけで送らない
    monkeypatch.delenv(identify.ENV_KEY)
    capsys.readouterr()
    photo2 = make_jpeg(tmp_path / "in" / "IMG_0013.jpg", taken="2026:11:06 09:00:00")
    assert (
        cli.main(["observe", "--folder", f, "--claude-code", "--ask", "names", "--no-identify", str(photo2)])
        == 0
    )
    assert "Pl@ntNet" not in capsys.readouterr().out


def test_raw_saved_when_research(tmp_path):
    r = identify.parse(ANSWER)
    identify.save_raw(tmp_path / "x.raw", "092817", r)
    data = json.loads((tmp_path / "x.raw" / "plantnet-092817.json").read_text(encoding="utf-8"))
    assert data["remainingIdentificationRequests"] == 498
    identify.save_raw(None, "092817", r)  # 何もしない
