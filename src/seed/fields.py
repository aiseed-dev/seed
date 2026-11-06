# SPDX-License-Identifier: AGPL-3.0-or-later
"""畑の一覧 fields.toml（docs/記録の形.md §19、設計書 §5.8）。

記録のフォルダー一つが一つの畑。畑が二つ以上ある時は、名を付けて一覧に書き、切り替える。
場所は SEED_FIELDS → ~/.config/seed/fields.toml。秘密は入れない（名とフォルダーと current だけ）。
無ければ空の一覧で、今まで通り --folder / SEED_FOLDER / 既定 ~/seed。
フォルダーを決める順: --folder > --field > current > SEED_FOLDER > 既定。
書くのは tomllib が読める素の形だけ（current = "..." と [[field]] の並び）。
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import settings as settings_mod

ENV_FIELDS = "SEED_FIELDS"
DEFAULT_FIELDS = "~/.config/seed/fields.toml"


class UnknownField(KeyError):
    """一覧に無い畑の名。"""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


@dataclass
class Field:
    name: str
    folder: str  # 書いたままの形（~ を含んでよい）

    @property
    def path(self) -> Path:
        return Path(self.folder).expanduser()


@dataclass
class Fields:
    current: str = ""
    fields: list[Field] = field(default_factory=list)

    def get(self, name: str) -> Field | None:
        return next((f for f in self.fields if f.name == name), None)

    @property
    def names(self) -> list[str]:
        return [f.name for f in self.fields]

    def add(self, name: str, folder: str) -> None:
        """足す。同じ名があればフォルダーを書き換える（並びは変えない）。"""
        old = self.get(name)
        if old is not None:
            old.folder = folder
        else:
            self.fields.append(Field(name, folder))

    def use(self, name: str) -> Field:
        f = self.get(name)
        if f is None:
            raise UnknownField(name)
        self.current = name
        return f

    def render(self) -> str:
        out = []
        if self.current:
            out += [f"current = {_toml_str(self.current)}", ""]
        for f in self.fields:
            out += ["[[field]]", f"name = {_toml_str(f.name)}", f"folder = {_toml_str(f.folder)}", ""]
        return "\n".join(out).rstrip("\n") + "\n" if out else ""

    @classmethod
    def parse(cls, text: str) -> Fields:
        data = tomllib.loads(text)
        items = data.get("field") or []
        fl = cls(current=str(data.get("current") or ""))
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict) and it.get("name") and it.get("folder"):
                fl.add(str(it["name"]), str(it["folder"]))
        return fl


def _toml_str(v: str) -> str:
    # JSON の文字の書き方は TOML の basic string として読める（settings と同じ）
    return json.dumps(str(v), ensure_ascii=False)


def fields_path(path: Path | str | None = None) -> Path:
    return Path(path or os.environ.get(ENV_FIELDS) or DEFAULT_FIELDS).expanduser()


def load_fields(path: Path | str | None = None) -> Fields:
    """一覧を読む。無ければ空。読めなければ一行知らせて空。"""
    p = fields_path(path)
    try:
        return Fields.parse(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Fields()
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        print(f"seed: {p} を読めない（{type(e).__name__}）。畑の一覧は空として扱う", file=sys.stderr)
        return Fields()


def save_fields(fl: Fields, path: Path | str | None = None) -> Path:
    """一覧を書く（秘密ではないので普通の許可）。"""
    p = fields_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(fl.render(), encoding="utf-8")
    os.replace(tmp, p)
    return p


def chosen(field: str | None = None, folder: str | None = None, path: Path | str | None = None) -> str | None:
    """--folder と --field と current から決まるフォルダー。どれも無ければ None（settings の既定に任せる）。

    一覧に無い名の --field は UnknownField。current が一覧に無い名なら、無い物として扱う。
    """
    if folder:
        return folder
    fl = load_fields(path)
    if field:
        f = fl.get(field)
        if f is None:
            raise UnknownField(field)
        return str(f.path)
    cur = fl.get(fl.current) if fl.current else None
    return str(cur.path) if cur else None


def resolve(field: str | None = None, folder: str | None = None, path: Path | str | None = None) -> Path:
    """記録のフォルダー。--folder > --field > current > SEED_FOLDER > 既定 ~/seed。"""
    got = chosen(field, folder, path)
    return Path(got).expanduser() if got else settings_mod.default_folder()


def switch_field(name: str, path: Path | str | None = None) -> Path:
    """アプリの切り替え: current を name にして書き、その畑のフォルダーを返す（Flet に依らない）。"""
    fl = load_fields(path)
    f = fl.use(name)
    save_fields(fl, path)
    return f.path


def selected_name(fl: Fields, root: Path) -> str | None:
    """今のフォルダー root に当たる畑の名（無ければ current、それも無ければ None）。"""
    root = Path(root).expanduser()
    for f in fl.fields:
        try:
            if f.path.resolve() == root.resolve():
                return f.name
        except OSError:
            continue
    return fl.current if fl.get(fl.current) else None
