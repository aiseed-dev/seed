# SPDX-License-Identifier: AGPL-3.0-or-later
"""設定 seed.toml（docs/記録の形.md §7）と秘密 credentials.toml の読み書き。

seed.toml の置き場所は記録のフォルダーの中（既定は ~/seed/seed.toml）。無ければ作り、language を決める。
秘密（token、invite、draw_token、anthropic_key）は記録のフォルダーに置かない（設計書 §5.1）。
~/.config/seed/credentials.toml（許可 600。SEED_CREDENTIALS で場所を変えられる）に分ける。
seed.toml に古い token / invite があれば credentials へ移して seed.toml から消し、標準エラーに一行知らせる。
書くのは tomllib が読める素の形だけ（値は文字だけなので、依存を足さずに自分で書く）。
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import tomllib
from dataclasses import dataclass, fields
from dataclasses import field as _field  # 欄の名 field（今の畑）と重ならないように
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
CREDENTIALS_FILENAME = "credentials.toml"
SECRETS = ("token", "invite", "draw_token", "anthropic_key")  # seed.toml に書かない欄
DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"  # 自分の鍵で呼ぶ時の既定（サーバーの読みと同じ）
ROUTES = ("local", "key", "server")  # Claude を呼ぶ所: 手元の Claude Code、自分の鍵、サーバー

COMMENTS = {
    "language": "本人の言葉の言語。無ければ OS の言語",
    "place_level": " / ".join(PLACE_LEVELS),
    "keep": " / ".join(KEEP_LEVELS) + "。どれだけ残すか（seed keep で変える）",
    "read": "local / key / server。アプリで Claude を呼ぶ所（読み取りと話す）。空なら手元の Claude、自分の鍵、サーバーの順",
    "claude_model": "自分の鍵で呼ぶモデル。空なら claude-opus-5-5。費用は本人に掛かる（claude-sonnet-5-5、claude-haiku-5-5 は安い）",
    "field": "今の畑（fields/ の下のフォルダーの名）。空ならプロジェクト全体（seed field use で変える）",
    "setup": "later なら、アプリを開いた時に準備の画面を出さない（歯車の「準備を見直す」からは開ける）",
    "home_start": "auto なら、PC のアプリを開いた時に、スマートフォンから写真を受ける seed home を始める（歯車で選ぶ）",
    "bulk": "重い物（写真の元 originals/）を置く別の盤の道。空なら記録のフォルダーの中（seed keep --bulk で変える）",
}

CREDENTIAL_COMMENTS = {
    "token": "触らない。公開の書き直しと取り下げに使う",
    "invite": "招待コード（Discord で渡す）。サーバーで読む・公開・一言に要る",
    "draw_token": "seed grow --draw の描く機械（halo の門）の token。Authorization: Bearer で送る",
    "anthropic_key": "自分の Claude の鍵（Anthropic の API の鍵）。アプリが Anthropic の API に直に送るだけ",
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
    field: str = ""  # 今の畑（設計書 §5.12）。fields/ が無いプロジェクトでは使わない
    read: str = ""  # Claude を呼ぶ所（local / key / server）。空なら在る物を ROUTES の順に
    claude_model: str = ""  # 自分の鍵で呼ぶモデル。空なら DEFAULT_CLAUDE_MODEL
    setup: str = ""  # 準備の画面（設計書 §5.19）。"later" は「今はしない」を押した。空なら足りない時に出す
    home_start: str = (
        ""  # "auto" は PC のアプリを開いた時に seed home を子として始める（設計書 §5.19）。空なら始めない
    )
    token: str = ""
    invite: str = ""
    draw_token: str = ""
    anthropic_key: str = _field(default="", repr=False)  # 値を repr（例外の文、ログ）に出さない
    extra: dict = _field(default_factory=dict)  # 知らない鍵。消さずに書き戻す
    path: Path | None = _field(default=None, compare=False)
    override_url: str | None = _field(default=None, compare=False)  # この回だけのサーバー。書かない
    credentials: Path | None = _field(default=None, compare=False)  # 秘密の置き場
    cred_extra: dict = _field(default_factory=dict, compare=False)  # credentials の知らない鍵
    # credentials に別の値があって移せなかった秘密。seed.toml に残して書き戻す（消すと失う）
    kept_inline: set = _field(default_factory=set, compare=False)
    # この回だけの畑（--field、畑のフォルダーを指す --folder）。書かない
    pick: str | None = _field(default=None, compare=False)

    @property
    def project(self) -> Path:
        """プロジェクトフォルダー（seed.toml の在る所）。"""
        return Path(self.folder).expanduser()

    @property
    def field_names(self) -> list[str]:
        """プロジェクトの畑（fields/ の下のフォルダー）の名、名の順。fields/ が無いか空なら []。"""
        return field_names(self.project)

    @property
    def current_field(self) -> str | None:
        """選んでいる畑の名。畑が一つ（fields/ が無い）か、プロジェクト全体なら None。"""
        name = self.pick if self.pick is not None else self.field
        return name if name and name in self.field_names else None

    @property
    def whole(self) -> bool:
        """畑が幾つもあるプロジェクトの全体を見ている。"""
        return bool(self.field_names) and self.current_field is None

    @property
    def records(self) -> Folder:
        bulk = Path(self.bulk).expanduser() if self.bulk else None
        name = self.current_field
        if name is not None:
            return self.field_folder(name)
        return Folder(self.project, bulk=bulk, whole=self.whole)

    def field_folder(self, name: str) -> Folder:
        """プロジェクトの畑一つの Folder（全体の時に畑ごとに見る）。"""
        bulk = Path(self.bulk).expanduser() if self.bulk else None
        return Folder(
            self.project / FIELDS_DIR / name,
            bulk=bulk / FIELDS_DIR / name if bulk else None,
            project=self.project,
        )

    @property
    def model(self) -> str:
        """自分の鍵で呼ぶモデル。"""
        return self.claude_model.strip() or DEFAULT_CLAUDE_MODEL

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
            if f.name == "field" and not self.field:  # 畑が一つのプロジェクトには書かない
                continue
            if f.name == "setup" and not self.setup:  # 「今はしない」を押すまでは書かない
                continue
            if f.name == "home_start" and not self.home_start:  # 選ぶまでは書かない
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


NOT_WRITTEN = frozenset({"extra", "path", "override_url", "credentials", "cred_extra", "kept_inline", "pick"})
FIELDS_DIR = "fields"  # プロジェクトの中の畑の置き場（設計書 §5.12）


def field_names(project: Path | str) -> list[str]:
    """プロジェクトの畑の名（fields/ の下のフォルダー。. で始まる物は除く）。"""
    d = Path(project).expanduser() / FIELDS_DIR
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith("."))


def read_field(project: Path | str) -> str:
    """seed.toml の field を読むだけ（作らない、秘密を読まない）。無いか読めなければ空。"""
    try:
        data = tomllib.loads(settings_path(project).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return ""
    return str(data.get("field") or "")


def write_field(project: Path | str, name: str) -> Settings:
    """seed.toml の field を name（空ならプロジェクト全体）にして書く。"""
    st = load(project)
    st.field = name
    st.save()
    return st


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
    """秘密の置き場。given → 環境変数 SEED_CREDENTIALS → ~/.config/seed/credentials.toml。"""
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
    秘密は credentials（渡された置き場）か credentials_path() から読む。
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
