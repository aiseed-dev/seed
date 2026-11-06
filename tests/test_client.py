# SPDX-License-Identifier: AGPL-3.0-or-later
import json

import httpx
import pytest

from seed.client import Client, ClientError
from seed.records import Line


def client(handler) -> Client:
    return Client("http://seed.test/", "tok", "ja", transport=httpx.MockTransport(handler))


READ_OK = {
    "lines": [
        {"key": "overall", "text": "草が大半", "confidence": 0.8},
        {"key": "Bad Key", "text": "落ちる", "confidence": 0.5},
        {"key": "plants", "text": "ススキ", "confidence": 0.6},
    ],
    "data": [{"key": "geology", "text": "砂岩（出典: 産総研、確認日 2026-11-05）"}],
    "model": "claude-opus-5-5",
    "usage": {"input_tokens": 10},
    "markdown": "## Reading",
}


def test_read_sends_multipart_and_returns_lines():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["body"] = req.read()
        seen["ctype"] = req.headers["content-type"]
        return httpx.Response(200, json=READ_OK)

    r = client(handler).read(
        [b"\xff\xd8one", b"\xff\xd8two"],
        center=(34.05, 134.25),
        place_data=[Line("geology", "砂岩")],
        record="did: 見ただけ",
    )
    assert seen["url"] == "http://seed.test/api/read"
    assert seen["ctype"].startswith("multipart/form-data")
    body = seen["body"]
    assert body.count(b'name="photos"') == 2
    for part in (b"34.05,134.25", "- geology: 砂岩".encode(), "did: 見ただけ".encode(), b"tok", b"ja"):
        assert part in body
    assert [(l.key, l.text, l.confidence) for l in r.lines] == [
        ("overall", "草が大半", 0.8),
        ("plants", "ススキ", 0.6),
    ]
    assert r.data[0].key == "geology" and r.data[0].confidence is None
    assert r.model == "claude-opus-5-5" and r.usage == {"input_tokens": 10}


def test_read_sends_ask_only_when_given():
    bodies = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(req.read())
        return httpx.Response(200, json=READ_OK)

    client(handler).read([b"\xff\xd8one"], ask=["grow", "soil"])
    client(handler).read([b"\xff\xd8one"])
    assert b'name="ask"' in bodies[0] and b"grow,soil" in bodies[0]
    assert b'name="ask"' not in bodies[1]


def test_read_refused():
    c = client(lambda req: httpx.Response(200, json={"refused": True, "category": "unclear"}))
    with pytest.raises(ClientError) as e:
        c.read([b"x"])
    assert e.value.word == "server_refused" and e.value.detail == "unclear"


@pytest.mark.parametrize(
    ("status", "word"), [(429, "server_limit"), (503, "server_busy"), (500, "server_error")]
)
def test_errors_carry_detail(status, word):
    c = client(lambda req: httpx.Response(status, json={"detail": "今日はここまで"}))
    with pytest.raises(ClientError) as e:
        c.read([b"x"])
    assert e.value.word == word and e.value.detail == "今日はここまで" and e.value.status == status


def test_unreachable():
    def handler(req):
        raise httpx.ConnectError("refused", request=req)

    with pytest.raises(ClientError) as e:
        client(handler).index()
    assert e.value.word == "server_unreachable"


def test_unreachable_real_port():
    # 何も聞いていない口。サーバーが無い間の本物の失敗
    c = Client("http://127.0.0.1:9", "tok", timeout=2)
    with pytest.raises(ClientError) as e:
        c.index()
    assert e.value.word in ("server_unreachable", "server_timeout")


def test_bad_json():
    with pytest.raises(ClientError) as e:
        client(lambda req: httpx.Response(200, text="<html>")).index()
    assert e.value.word == "server_bad_answer"


def test_no_photos():
    with pytest.raises(ClientError) as e:
        client(lambda req: httpx.Response(200)).read([])
    assert e.value.word == "no_photos"


def test_publish_unpublish_connect_index_public():
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.read() or b"null")
        calls.append((req.method, req.url.path, body))
        if req.url.path == "/api/publish":
            return httpx.Response(200, json={"id": "a-1", "url": "http://seed.test/public/a-1.md"})
        if req.url.path == "/api/connect":
            return httpx.Response(200, json={"count": 3})
        if req.url.path == "/index.json":
            return httpx.Response(200, json={"records": [{"id": "a-1"}]})
        if req.url.path == "/public/a-1.md":
            return httpx.Response(200, text="---\nid: a-1\n---\n")
        return httpx.Response(200, json={})

    c = client(handler)
    assert c.publish("---\nid: a-1\n---\n")["id"] == "a-1"
    c.unpublish("a-1")
    assert c.connect("a-1", "b-2", "よろしく") == 3
    idx = c.index()
    assert idx["total"] == {"records": 1, "connections": 0}
    assert c.public("a-1").startswith("---")
    assert calls[0] == ("POST", "/api/publish", {"token": "tok", "markdown": "---\nid: a-1\n---\n"})
    assert calls[1] == ("DELETE", "/api/publish/a-1", {"token": "tok"})
    assert calls[2] == (
        "POST",
        "/api/connect",
        {"token": "tok", "to": "a-1", "from": "b-2", "word": "よろしく"},
    )


def test_forbidden_on_unpublish():
    with pytest.raises(ClientError) as e:
        client(lambda req: httpx.Response(403, json={"detail": "token"})).unpublish("a-1")
    assert e.value.word == "server_forbidden"


def test_invite_is_sent_everywhere():
    bodies = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append((str(req.url.path), req.read()))
        if req.url.path.endswith("/api/connect"):
            return httpx.Response(200, json={"count": 1})
        if req.url.path.endswith("/api/publish"):
            return httpx.Response(200, json={"id": "x", "url": "u"})
        return httpx.Response(200, json=READ_OK)

    c = Client("http://seed.test", "tok", "ja", transport=httpx.MockTransport(handler), invite="inv-1")
    c.read([b"\xff\xd8one"])
    c.publish("---\n---\n")
    c.connect("to-1", "me", "hi")
    assert all(b"inv-1" in body for _, body in bodies), bodies


def test_invite_required_error_word():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "invite_required", "detail": ["招待コードが要る"]})

    with pytest.raises(ClientError) as e:
        client(handler).read([b"\xff\xd8one"])
    assert e.value.word == "server_invite"


def test_identify_via_server_parses_plantnet():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/identify" and b'name="photos"' in req.read()
        return httpx.Response(
            200,
            json={
                "plantnet": {
                    "results": [
                        {"score": 0.6, "species": {"scientificNameWithoutAuthor": "Solidago altissima"}}
                    ]
                },
                "candidates": [],
                "remaining": 3,
            },
        )

    r = client(handler).identify([b"\xff\xd8one"])
    assert r.best.scientific == "Solidago altissima" and r.best.score == 0.6
