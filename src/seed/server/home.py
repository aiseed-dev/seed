# SPDX-License-Identifier: AGPL-3.0-or-later
"""家のサーバー（設計書 §5.13）。スマートフォン → PC の一方通行。

`seed home` が SEED_HOME=<プロジェクト> で立てる。受けた写真は `seed observe` と同じ道で
そのプロジェクトの畑に写真と観察として置き、PC の Claude Code（無ければサーバーの鍵）で読む。
話すは、その畑のフォルダーで PC の Claude Code に言葉を渡し、返事の文だけを返す。
プロジェクトフォルダーの外には何も書かない。
"""

from __future__ import annotations

import datetime as dt
import socket
import tempfile
import threading
from pathlib import Path

from .. import settings as settings_mod
from ..records import Folder, Line, Observation

PHOTO_MAX = 12 * 1024 * 1024  # 元のまま（座標入り）の一枚
PHOTOS_TOTAL_MAX = 60 * 1024 * 1024
HOME_FILE = "home.toml"  # 招待コード（秘密。公開しない）
PUBLIC_DIR = "public-home"  # 家のサーバーの公開の置き場（手元で公開を試せるように）
TALK_MODEL = "claude-code"
ZERO_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
}


def project(home: Path) -> settings_mod.Settings:
    """プロジェクトの設定（読むだけ。書かない）。"""
    return settings_mod.load(home, create=False)


def folder_for(st: settings_mod.Settings, field: str | None) -> Folder:
    """記録を置く畑。field の名の畑 → 今の畑（seed.toml の field） → プロジェクトの根（畑が一つの形）。"""
    names = st.field_names
    name = (field or "").strip()
    if name and name in names:
        return st.field_folder(name)
    cur = settings_mod.read_field(st.project)
    if cur and cur in names:
        return st.field_folder(cur)
    bulk = Path(st.bulk).expanduser() if st.bulk else None
    return Folder(st.project, bulk=bulk)


def store(
    st: settings_mod.Settings,
    folder: Folder,
    photos: list[bytes],
    record: list[Line] = (),
    ask: list[str] = (),
) -> Observation:
    """受けた JPEG を畑に取り込み、観察を書く（読みはまだ）。一時のファイルも畑の中に置き、終われば消す。"""
    from ..cli import ingest

    folder.root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.root, prefix=".home-") as d:
        paths = []
        for i, b in enumerate(photos):
            p = Path(d) / f"{i + 1}.jpg"
            p.write_bytes(b)
            paths.append(p)
        obs = ingest(folder, paths, st.keep, st.language)
    have = {(l.key, l.text) for l in obs.record}
    for l in record:
        if l.key in Observation.RECORD_KEYS and (l.key, l.text) not in have:
            obs.say(l.key, l.text)
            have.add((l.key, l.text))
    obs.ask = list(dict.fromkeys([*obs.ask, *ask]))
    obs.write(folder.observation_path(obs))
    return obs


def add_data(folder: Folder, obs: Observation, data: list[Line]) -> None:
    """照会の行を観察と place.md に足す（無い物だけ）。"""
    if not data:
        return
    have = {(l.key, l.text) for l in obs.data}
    obs.data += [l for l in data if (l.key, l.text) not in have]
    obs.lookup = dt.date.today().isoformat()
    folder.add_place_data(data)


def last_user_text(messages: object) -> str | None:
    """やり取りの終わりの本人の言葉（role が user の最後の文）。無ければ None。"""
    if not isinstance(messages, list):
        return None
    for m in reversed(messages):
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, str):
            text = c
        elif isinstance(c, list):
            text = "\n".join(
                str(b.get("text") or "") for b in c if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            text = ""
        if text.strip():
            return text.strip()
    return None


def reply(text: str) -> dict:
    """端末の ServerTransport が終わりの答えとして読む形。"""
    return {
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": dict(ZERO_USAGE),
        "model": TALK_MODEL,
    }


DISCOVERY_PORT = 8801


def answer_discovery(url: str, port: int = DISCOVERY_PORT, stop: threading.Event | None = None) -> None:
    """同じ網のスマートフォンの「seed?」に、この PC の URL を返す（UDP）。stop が立つまで続く。"""
    stop = stop or threading.Event()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("0.0.0.0", port))
        sock.settimeout(0.5)
        while not stop.is_set():
            try:
                data, addr = sock.recvfrom(1024)
            except TimeoutError:
                continue
            if data.startswith(b"seed?"):
                sock.sendto(b"seed-home " + url.encode(), addr)
    except OSError:
        pass  # 口が使えなくても、家のサーバー自体は動かす
    finally:
        sock.close()
