# SPDX-License-Identifier: AGPL-3.0-or-later
"""設定 seed.toml（docs/記録の形.md §7）と秘密 credentials.toml の読み書き。

seed.toml の置き場所は記録のフォルダーの中（既定は ~/seed/seed.toml）。無ければ作り、language を決める。
秘密（token、invite、draw_token）は記録のフォルダーに置かない（設計書 §5.1）。
~/.config/seed/credentials.toml（許可 600。SEED_CREDENTIALS で場所を変えられる）に分ける。
Web 版は人ごとの箱の中の credentials.toml（load の credentials で渡す）。
seed.toml に古い token / invite があれば credentials へ移して seed.toml から消し、標準エラーに一行知らせる。
書くのは tomllib が読める素の形だけ（値は文字だけなので、依存を足さずに自分で書く）。
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import lang
from .records import Folder

DEFAULT_FOLDER = "~/seed"
DEFAULT_SERVER = "https://seed.aiseed.dev"
PLACE_LEVELS = ("prefecture", "city", "oaza")
KEEP_LEVELS = ("text", "photos", "research")  # keep.LEVELS と同じ（keep.py は records に依る）
FILENAME = "seed.toml"
ENV_FOLDER = "SEED_FOLDER"  # テストや別の畑用に、既定のフォルダーを変える
ENV_SERVER = "SEED_SERVER_URL"
ENV_CREDENTIALS = "SEED_CREDENTIALS"  # 秘密の置き場を変える（テストや別の人）
DEFAULT_CREDENTIALS = "~/.config/seed/credentials.toml"
CREDENTIALS_FILENAME = "credentials.toml"  # Web 版の人ごとの箱の中の名
SECRETS = ("token", "invite", "draw_token")  # seed.toml に書かない欄

COMMENTS = {
    "language": "本人の言葉の言語。無ければ OS の言語",
    "place_level": " / ".join(PLACE_LEVELS),
    "keep": " / ".join(KEEP_LEVELS) + "。どれだけ残すか（seed keep で変える）",
    "read": "local / server。アプリで写真を読む所。空なら手元の Claude が在ればそれ、無ければサーバー",
    "bulk": "重い物（写真の元 originals/）を置く別の盤の道。空なら記録のフォルダーの中（seed keep --bulk で変える）",
}

CREDENTIAL_COMMENTS = {
    "token": "触らない。公開の書き直しと取り下げに使う",
    "invite": "招待コード（Discord で渡す）。サーバーで読む・公開・一言に要る",
    "draw_token": "seed grow --draw の描く機械（halo の門）の token。Authorization: Bearer で送る",
}


@dataclass
class Settings:
    folder: str = DEFAULT_FOLDER
    server_url: str = DEFAULT_SERVER
    name: str = ""
    language: str = ""
    place_level: str = "city"
    keep: str = "photos"
    bulk: str = ""
    read: str = ""  # アプリの読み方（local / server）。空なら手元の Claude が在ればそれ
    token: str = ""
    invite: str = ""
    draw_token: str = ""
    extra: dict = field(default_factory=dict)  # 知らない鍵。消さずに書き戻す
    path: Path | None = field(default=None, compare=False)
    override_url: str | None = field(default=None, compare=False)  # この回だけのサーバー。書かない
    credentials: Path | None = field(default=None, compare=False)  # 秘密の置き場
    cred_extra: dict = field(default_factory=dict, compare=False)  # credentials の知らない鍵
    # credentials に別の値があって移せなかった秘密。seed.toml に残して書き戻す（消すと失う）
    kept_inline: set = field(default_factory=set, compare=False)

    @property
    def records(self) -> Folder:
        return Folder(Path(self.folder), bulk=Path(self.bulk).expanduser() if self.bulk else None)

    @property
    def server(self) -> str:
        """呼ぶサーバー。override_url → 環境変数 SEED_SERVER_URL → server_url。前の二つはファイルに書かない。"""
        return (self.override_url or os.environ.get(ENV_SERVER) or self.server_url).rstrip("/")

    def render(self) -> str:
        """seed.toml の文。秘密は書かない（移せなかった物だけ残す）。"""
        out = []
        for f in fields(self):
            if f.name in NOT_WRITTEN:
                continue
            if f.name in SECRETS and f.name not in self.kept_inline:
                continue
            line = f"{f.name} = {_toml_str(getattr(self, f.name))}"
            if f.name in COMMENTS:
                line = f"{line:<30} # {COMMENTS[f.name]}"
            out.append(line)
        out += [f"{k} = {_toml_value(v)}" for k, v in self.extra.items() if not isinstance(v, dict)]
        for k, v in self.extra.items():  # 表（例 [grow] server）は最後に、表のまま書き戻す
            if isinstance(v, dict):
                out += ["", f"[{k}]"] + [f"{kk} = {_toml_value(vv)}" for kk, vv in v.items()]
        return "\n".join(out) + "\n"

    def render_credentials(self) -> str:
        out = ["# seed の秘密（設計書 §5.1）。人に見せない、写さない、記録のフォルダーに置かない"]
        for k in SECRETS:
            if k in self.kept_inline:
                continue
            line = f"{k} = {_toml_str(getattr(self, k))}"
            out.append(f"{line:<40} # {CREDENTIAL_COMMENTS[k]}")
        out += [f"{k} = {_toml_value(v)}" for k, v in self.cred_extra.items() if not isinstance(v, dict)]
        return "\n".join(out) + "\n"

    def save(self, path: Path | None = None) -> Path:
        path = Path(path or self.path or settings_path(Path(self.folder)))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        self.path = path
        self.save_credentials()
        return path

    def save_credentials(self) -> Path:
        """credentials.toml を 600 で書く（中身が同じなら触らない。許可だけは直す）。"""
        cred = Path(self.credentials or credentials_path())
        text = self.render_credentials()
        old = None
        try:
            old = cred.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass
        if old != text:
            write_secret(cred, text)
        else:
            os.chmod(cred, 0o600)
        self.credentials = cred
        return cred

    @classmethod
    def parse(cls, text: str) -> Settings:
        data = tomllib.loads(text)
        known = {f.name for f in fields(cls)} - NOT_WRITTEN
        s = cls(**{k: str(v) for k, v in data.items() if k in known})
        s.extra = {k: v for k, v in data.items() if k not in known}
        return s


NOT_WRITTEN = frozenset({"extra", "path", "override_url", "credentials", "cred_extra", "kept_inline"})


def write_secret(path: Path, text: str) -> None:
    """秘密のファイルを、はじめから 600 で書く（置き換えで。親のフォルダーは 700 で作る）。"""
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)  # umask や既にあった tmp の許可に依らない
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)
    os.replace(tmp, path)


def credentials_path(given: Path | str | None = None) -> Path:
    """秘密の置き場。given（Web 版の箱）→ 環境変数 SEED_CREDENTIALS → ~/.config/seed/credentials.toml。"""
    return Path(given or os.environ.get(ENV_CREDENTIALS) or DEFAULT_CREDENTIALS).expanduser()


def read_credentials(path: Path) -> dict:
    """credentials.toml を読む。無いか読めなければ空。"""
    try:
        return tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        print(f"seed: {path} を読めない（{type(e).__name__}）。秘密は空として扱う", file=sys.stderr)
        return {}


def _toml_str(v: str) -> str:
    # JSON の文字の書き方は TOML の basic string として読める
    return json.dumps(str(v), ensure_ascii=False)


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    return _toml_str(v)


def default_folder() -> Path:
    return Path(os.environ.get(ENV_FOLDER) or DEFAULT_FOLDER).expanduser()


def _folder_text() -> str:
    """既定のフォルダーを seed.toml に書く形で。~/seed はそのまま ~/seed と書く。"""
    return os.environ.get(ENV_FOLDER) or DEFAULT_FOLDER


def settings_path(folder: Path | str | None = None) -> Path:
    return Path(folder or default_folder()).expanduser() / FILENAME


def load(
    folder: Path | str | None = None, create: bool = True, credentials: Path | str | None = None
) -> Settings:
    """設定を読む。無ければ（create なら）作って書く。足りない token と language は足して書き戻す。

    folder を渡すと、そのフォルダーの seed.toml を使い、folder もそこにする。
    秘密は credentials（Web 版の箱の credentials.toml）か credentials_path() から読む。
    seed.toml に古い token / invite / draw_token があれば credentials へ移し、seed.toml から消す。
    """
    path = settings_path(folder)
    if path.exists():
        s = Settings.parse(path.read_text(encoding="utf-8"))
        s.path = path
        if folder is not None:
            s.folder = str(Path(folder).expanduser())
    else:
        # 新しく作るときは seed.toml を置くフォルダーが記録のフォルダー
        s = Settings(folder=str(Path(folder).expanduser()) if folder else _folder_text(), path=path)
    changed = not path.exists()
    s.credentials = credentials_path(credentials)
    cred = read_credentials(s.credentials)
    s.cred_extra = {k: v for k, v in cred.items() if k not in SECRETS}
    moved, kept = [], []
    for k in SECRETS:
        inline = getattr(s, k)  # seed.toml に書かれていた値（古い形）
        stored = str(cred.get(k) or "")
        if inline and stored and inline != stored:
            kept.append(k)  # 両方に違う値。消すと失うので seed.toml に残す
            s.kept_inline.add(k)
        elif inline:
            moved.append(k)
        else:
            setattr(s, k, stored)
    if moved:
        changed = True
        if create:
            print(
                f"seed: {', '.join(moved)} を {path} から {s.credentials} に移した（秘密は記録のフォルダーに置かない）",
                file=sys.stderr,
            )
    if kept:
        print(
            f"seed: {', '.join(kept)} が {path} と {s.credentials} で違うので移さなかった。"
            f"このフォルダー用に {ENV_CREDENTIALS} で別の置き場を指すと移せる",
            file=sys.stderr,
        )
    if not s.token:
        s.token, changed = secrets.token_urlsafe(24), True
    if not s.language:
        s.language, changed = lang.default_language(None), True
    if s.place_level not in PLACE_LEVELS:
        s.place_level, changed = "city", True
    if s.keep not in KEEP_LEVELS:
        s.keep, changed = "photos", True
    if not s.credentials.exists():
        changed = True
    if changed and create:
        s.save(path)
    return s
