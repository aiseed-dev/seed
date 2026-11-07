# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed コマンド。init / home / observe / identify / mark / marks / say / plan / publish / app / skill-path / keep / prune / invite / origin / grow / lot / ledger / weather / procedure / field / project。

行を対話で選ぶのはアプリに任せ、publish は判定の付いた読みの行と data と record を全部入れる。
文は本人の言語（seed.toml の language）で出す。
写真（Pillow）とサーバー（httpx）は app extra の物なので、使うコマンドの中で読む（init は無くても動く）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from importlib import resources
from pathlib import Path

from . import claude_md, highlights, lang
from . import fields as fields_mod
from . import keep as keep_mod
from . import settings as settings_mod
from .app.strings import error_text, s
from .records import (
    ASKS,
    PHOTO_KEY,
    PLAN_KEYS,
    PLAN_RECORD_KEYS,
    PUBLIC_PHOTOS_MAX,
    READING_KEYS,
    RECORD_KEYS,
    Folder,
    Line,
    Mark,
    Observation,
    Plan,
    Public,
    coarse_coord,
    parse_asks,
    photo_rel,
    public_photo_name,
    sort_reading,
)
from .settings import Settings

TAG_SPLIT_RE = re.compile(r"\s*[,、]\s*")
APP_MODULES = ("PIL", "httpx", "flet")  # pip install "seed-farm[app]" で入る物


# ---------------------------------------------------------------- アプリと共有する手続き


SHARED_SKILL = Path(sys.prefix) / "share" / "seed-farm" / "skill"  # pyproject の data-files の行き先


def package_skill() -> Path | None:
    """共通の手引き（パッケージの skill/）。入れた物 → 開発中のリポジトリの skill/ の順に探す。"""
    try:
        p = resources.files("seed") / "skill"
        if p.is_dir():
            return Path(str(p))
    except (ModuleNotFoundError, TypeError):
        pass
    repo = Path(__file__).resolve().parents[2] / "skill"
    for p in (SHARED_SKILL, repo):
        if (p / "SKILL.md").is_file():
            return p
    return None


def copy_skill(folder: Folder) -> str:
    """共通の手引きを ~/seed/skill/ に写す（記録の形 §9）。あれば触らない。畑は、畑にもプロジェクトの根にも無ければ根に写す。

    'copied'、'kept'（もうある。本人の物なので上書きしない）、'missing'（共通の手引きが無い）。
    """
    if folder.skill.exists():
        return "kept"
    src = package_skill()
    if src is None:
        return "missing"
    shutil.copytree(src, folder.skill, ignore=shutil.ignore_patterns("__pycache__", "*.py", "*.pyc"))
    return "copied"


def prepare(folder: Folder, language: str | None = None) -> str:
    """フォルダーを作り、手引きを写す。seed init とアプリの始まり。

    language を渡すと CLAUDE.md も置く（もうあれば触らない）。CLAUDE.md と手引きはプロジェクトの根に一つ。
    プロジェクト全体（畑が幾つも）の時は、記録の中身は作らない（畑ごとに在る）。
    """
    if not folder.whole:
        folder.init()
    if language is not None:
        claude_md.write(folder.project or folder.root, language)
    return copy_skill(folder)


def claude_steps(lg: str, folder: Folder, obs: Observation, folder_label: str | None = None) -> str:
    """自分の Claude で読む手順。同じ場所の前の観察があれば一緒に読ませる。"""
    text = s(
        "claude_steps",
        lg,
        folder=folder_label or folder.root,
        skill=folder.skill / "SKILL.md",
        obs=f"observations/{obs.filename}",
    )
    prev = folder.previous_observation(obs)
    if prev:
        text += "\n" + s("claude_previous", lg, prev=f"observations/{prev.filename}")
    return text


def observation_name(obs: Observation) -> str:
    return obs.filename.removesuffix(".md")


def find_observation(folder: Folder, name: str) -> Path:
    """'2026-11-05-142107'、'…md'、道のどれでも。"""
    p = Path(name)
    if p.suffix == ".md" and p.exists():
        return p
    cand = folder.observations / f"{p.name.removesuffix('.md')}.md"
    if cand.exists():
        return cand
    raise FileNotFoundError(name)


def split_tags(text: str | None) -> list[str]:
    return [t for t in TAG_SPLIT_RE.split(text or "") if t]


def default_lines(obs: Observation) -> list[Line]:
    """公開に入れる既定の行: 判定の付いた読み、data、record。"""
    return [l for l in obs.reading if l.judged] + list(obs.data) + list(obs.record)


def make_public(
    st: Settings,
    observations: list[Observation],
    selected: list[list[Line]] | None = None,
    *,
    public_id: str,
    place: str,
    word: str,
    what: list[str] = (),
    next_: list[str] = (),
    with_coord: bool = False,
    contact: str | None = None,
    name: str | None = None,
    since: str | None = None,
    photos: list[str] | None = None,
    folder: Folder | None = None,
) -> Public:
    """観察と選んだ行から公開ファイルを作る。

    写真は日の頭に `photo` の行で。公開は成長の記録なので、photos（相対の道。resolve_photos で引いた物）が None なら、
    同じ場所を日を追って撮った写真を日ごとに一枚（album.growth。folder が要る）。二日以上に渡る場所が無ければ、
    入る日ごとにその日の今日の一枚（無ければ最初の写真）。新しい日から PUBLIC_PHOTOS_MAX 枚まで。
    """
    pub = Public(
        id=public_id.strip(),
        place=place.strip(),
        since=since or dt.date.today().isoformat(),
        name=(name or st.name).strip(),
        word=word.strip(),
        what=list(what),
        next=list(next_),
        contact=contact or None,
        language=st.language,
    )
    if with_coord:
        loc = next((o.location for o in observations if o.location), None)
        if loc:
            pub.coord = coarse_coord(loc["center"])
    for i, obs in enumerate(observations):
        lines = default_lines(obs) if selected is None else selected[i]
        if lines:
            pub.add(obs, lines)
    by_day: dict[str, list[str]] = {}
    if photos is None:
        from . import album  # 写真の位置を読む（Pillow）。写真を選び直す道では要らない

        grown = album.growth(folder, observations) if folder is not None else {}
        for obs in sorted(observations, key=lambda o: (o.date, o.time), reverse=True):
            rel = grown.get(obs.date) if grown else highlights.today(obs)[0]
            name = public_photo_name(rel) if rel else None
            if name and obs.date in pub.days and obs.date not in by_day and len(by_day) < PUBLIC_PHOTOS_MAX:
                by_day[obs.date] = [name]
    else:
        day_of = {r: o.date for o in observations for r in o.photos}
        for rel in photos:
            name = public_photo_name(rel)
            if name and rel in day_of and name not in by_day.get(day_of[rel], []):
                by_day.setdefault(day_of[rel], []).append(name)
    for day, names in by_day.items():
        pub.days[day] = [Line(PHOTO_KEY, n) for n in names] + pub.days.get(day, [])
    return pub


def resolve_photos(observations: list[Observation], refs: list[str]) -> list[str]:
    """写真の指し方（相対の道 photos/…、公開の名、ファイルの名の幹）を、観察の写真の相対の道に。無い物は ValueError。"""
    known: dict[str, str] = {}
    for o in observations:
        for r in o.photos:
            for k in (r, public_photo_name(r), Path(r).stem):
                if k:
                    known.setdefault(k, r)
    out = []
    for ref in refs:
        rel = known.get(str(ref).strip())
        if rel is None:
            raise ValueError(str(ref)[:80])
        out.append(rel)
    return list(dict.fromkeys(out))


def public_photos(folder: Folder, pub: Public) -> tuple[dict[str, bytes], list[str]]:
    """公開ファイルの photo の行が指す写真を、送る形（長い辺 1280、JPEG、EXIF 無し）に。(名 → 中身, 手元に無い名)。"""
    from . import photos as photos_mod

    out: dict[str, bytes] = {}
    missing: list[str] = []
    for name in pub.photo_names():
        rel = photo_rel(name)
        path = folder.root / rel if rel else None
        if path is None or not path.is_file():
            missing.append(name)
            continue
        out[name] = photos_mod.for_public(path)
    return out, missing


def keep_model_lines(obs: Observation, before: list[Line]) -> None:
    """読みを置き換えた後に、Pl@ntNet の行（モデルの読み。設計書 §17）を戻す。判定も付いたまま。"""
    from . import identify

    kept = [l for l in before if identify.is_model_line(l)]
    if kept and not any(identify.is_model_line(l) for l in obs.reading):
        obs.reading = sort_reading([*obs.reading, *kept])


def home_photos(folder: Folder, obs: Observation, sources: list[Path | str] | None = None) -> list[bytes]:
    """家のサーバーへ送る写真（縮めず、座標の入った元のまま）。sources（撮った元の JPEG）があればそれ。"""
    if sources:
        got = [Path(p).read_bytes() for p in sources]
        if all(b.startswith(b"\xff\xd8\xff") for b in got):
            return got
    return [(folder.root / r).read_bytes() for r in obs.photos]


def read_on_server(
    st: Settings, folder: Folder, obs: Observation, sources: list[Path | str] | None = None
) -> None:
    """サーバーで読み、観察に入れる。失敗は ClientError のまま上げる。

    家のサーバー（seed home。設計書 §5.13）には、写真を縮めずに（sources があれば撮った元を）送り、
    畑の名を添える。写真と観察の本物は PC に置かれる。
    """
    from . import client, photos

    center = obs.location["center"] if obs.location else None
    prev = folder.previous_observation(obs)  # 同じ場所の直前の観察。あれば読みに change が付く
    before = list(obs.reading)
    home = client.is_home(st.server)
    with client.Client(st.server, st.token, st.language, invite=st.invite) as c:
        reading = c.read(
            home_photos(folder, obs, sources) if home else photos.shrunk(folder, obs),
            center,
            folder.place_data(),
            # 場所について本人が確かめたことも、本人の言葉として渡す。家のサーバーは観察に書くので観察の行だけ
            obs.record if home else [*folder.place_record(), *obs.record],
            previous=prev.render() if prev else None,
            ask=obs.ask,
            names=[Path(r).stem for r in obs.photos],
            field=(folder.root.name if folder.project is not None else "") if home else None,
        )
    client.apply_reading(obs, reading)
    keep_model_lines(obs, before)
    if reading.data:
        folder.add_place_data(reading.data)  # 農地のデータベース（記録の形 §4）。無い物だけ足す


def identify_photos(
    st: Settings, folder: Folder, obs: Observation, stems: list[str] | None = None, via: str | None = None
) -> list[Line]:
    """観察の写真を Pl@ntNet で確かめ、`plants` の行を観察に足す（設計書 §17）。

    写真は一枚ずつ送る（歩き撮りは別の株なので）。stems で写真を選ぶ。無ければ全部（枠を守るため 10 枚まで）。
    via: "local"（本人の鍵 PLANTNET_API_KEY）か "server"（サーバーの鍵、招待コード）。無ければ鍵があれば local、
    無ければ server。返すのは足した行。鍵も招待コードも無ければ IdentifyError。
    """
    from . import client, identify, photos

    chosen = [r for r in obs.photos if not stems or Path(r).stem in stems]
    if stems:
        missing = [x for x in stems if not any(Path(r).stem == x for r in obs.photos)]
        if missing:
            raise identify.IdentifyError("identify_no_photos", f"no such photo: {', '.join(missing)}")
    chosen = chosen[: identify.MAX_PER_OBSERVATION]
    if not chosen:
        raise identify.IdentifyError("identify_no_photos", "no photos")
    how = via or ("local" if identify.available() else "server")
    raw_dir = folder.raw_dir(obs) if keep_mod.raw(st.keep) else None
    today = dt.date.today().isoformat()
    added: list[Line] = []
    # 同じ写真の前の行は置き換える（判定が付いていれば残す）
    for rel in chosen:
        stem = Path(rel).stem
        image = photos.shrink(folder.root / rel)
        if how == "local":
            result = identify.identify([image], language=st.language)
        else:
            with client.Client(st.server, st.token, st.language, invite=st.invite) as c:
                result = c.identify([image])
        identify.save_raw(raw_dir, stem, result)
        line = identify.line_for(result, stem, st.language, today)
        if line is None:
            continue
        old = next((l for l in obs.reading if identify.is_model_line(l) and f"（{stem}）" in l.text), None)
        if old is not None:
            if old.text == line.text:
                continue
            obs.reading.remove(old)
        obs.reading.append(line)
        added.append(line)
    obs.reading = sort_reading(obs.reading)
    return added


def read_local(st: Settings, folder: Folder, obs: Observation, model: str | None = None):
    """手元の claude（Claude Code の CLI）で読み、観察に入れる。失敗は LocalError（ClientError）のまま上げる。

    返すのは client.Reading（usage に duration_ms）。
    """
    from . import client, local

    raw_dir = folder.raw_dir(obs) if keep_mod.raw(st.keep) else None
    before = list(obs.reading)
    reading = local.read(folder, obs, model=model, raw_dir=raw_dir)
    client.apply_reading(obs, reading)
    keep_model_lines(obs, before)
    return reading


def read_with_key(st: Settings, folder: Folder, obs: Observation):
    """本人の Claude の鍵（credentials.toml の anthropic_key）で、この端末から直に読み、観察に入れる。

    指示はサーバーの /api/read と同じ（prompts.read_request）。失敗は DirectError（ClientError）のまま上げる。
    """
    from . import client, direct

    skill = folder.skill if (folder.skill / "SKILL.md").is_file() else package_skill()
    before = list(obs.reading)
    reading = direct.read_with_key(st, folder, obs, skill)
    client.apply_reading(obs, reading)
    keep_model_lines(obs, before)
    return reading


def ingest(folder: Folder, paths: list[Path | str], keep: str, language: str) -> Observation:
    """写真を記録のフォルダーに取り込み、観察の骨を作る（seed observe と家のサーバーの /api/read で同じ道）。

    photos/<日>/<時刻>.jpg（EXIF は残す。keep の通り）。観察はまだ書かない。PhotoError はそのまま上げる。
    """
    from . import photos

    prepare(folder)
    rel = photos.import_photos(folder, paths, keep=keep)
    return photos.observation_for(folder, rel, language)


def how_to_read(args) -> str:
    """observe の読み方。--server / --local / --claude-code が無ければ、claude があれば手元、無ければサーバー。"""
    from . import local

    if getattr(args, "claude_code", False):
        return "claude_code"
    if getattr(args, "server", False):
        return "server"
    if getattr(args, "local", False):
        return "local"
    return "local" if local.available() else "server"


# ---------------------------------------------------------------- コマンド


def _out(text: str = "") -> None:
    print(text)


def _err(text: str) -> None:
    print(text, file=sys.stderr)


def _set_keep(st: Settings, level: str | None, bulk: str | None = None) -> bool:
    """keep と bulk を変えて保存する。知らない語なら False。bulk は "" で外す。"""
    changed = False
    if level is not None:
        if level not in keep_mod.LEVELS:
            _err(s("keep_bad", st.language, keep=level))
            return False
        st.keep, changed = level, True
        _out(s("keep_set", st.language, keep=level))
    if bulk is not None:
        st.bulk, changed = bulk.strip(), True
        if st.bulk:
            Path(st.bulk).expanduser().mkdir(parents=True, exist_ok=True)
            _out(s("bulk_set", st.language, bulk=st.bulk))
        else:
            _out(s("bulk_unset", st.language))
    if changed:
        st.save()
    return True


def _keep_status(st: Settings) -> None:
    lg = st.language
    _out(
        s(
            "keep_status",
            lg,
            keep=st.keep,
            desc=s(f"keep_desc_{st.keep}", lg),
            free=round(keep_mod.free_bytes(st.records.root) / 1e9),
            mb=keep_mod.PER_OBSERVATION_MB[st.keep],
        )
    )
    if st.records.bulk is not None:
        _out(s("keep_bulk", lg, bulk=st.records.bulk, free=round(keep_mod.free_bytes(st.records.bulk) / 1e9)))
    _out(s("keep_change", lg))


def _set_invite(st: Settings, code: str | None) -> None:
    if code is None:
        return
    st.invite = code.strip()
    st.save()
    _out(s("invite_set" if st.invite else "invite_unset", st.language))


def cmd_invite(st: Settings, args) -> int:
    """招待コードを見る・入れる（Discord で渡される。サーバーで読む・公開・一言に要る）。

    --list はサーバーの側の一覧（invites.toml）を読んで、呼び名とコードの先頭 4 桁だけを出す。
    失効はファイルから行を消すだけ（次の要求から効く。設計書 §7.5）。
    """
    if getattr(args, "list", False):
        return _list_invites(getattr(args, "invites", None))
    if args.code is not None:
        _set_invite(st, args.code)
    elif st.invite:
        _out(s("invite_status", st.language, code=st.invite))
    else:
        _out(s("invite_none", st.language))
    return 0


def _list_invites(path: str | None) -> int:
    import os
    import tomllib

    from .server.settings import _parse_invites

    path = path or os.environ.get("SEED_INVITES")
    if not path:
        _err("seed invite --list: --invites <invites.toml> か SEED_INVITES が要る")
        return 2
    try:
        codes = _parse_invites(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, TypeError) as e:
        _err(f"seed invite --list: {path} を読めない: {e}")
        return 1
    _out(f"{path}: {len(codes)} 件")
    for code, name in sorted(codes.items(), key=lambda kv: kv[1]):
        _out(f"  {code[:4]}…  {name}")
    return 0


def cmd_token(st: Settings, args) -> int:
    """相手ごとの token の台帳（サーバーの門。設計書 §5.9）: 出す、見る、取り消す。

    台帳に残るのはハッシュだけ。token は add の時に一度だけ出るので、その場で相手に渡す。
    台帳の場所は --file、無ければ SEED_TOKENS、無ければ ~/.config/aiseed/tokens.json。
    """
    from .server import gate

    path = gate.tokens_path(getattr(args, "file", None))
    try:
        if args.what == "add":
            code = gate.add(path, args.name, [args.scope], args.days, args.note or "")
            _err(
                f"{path}: {args.name} に出した（範囲 {args.scope}、{args.days} 日）。台帳に残るのはハッシュだけ。"
            )
            _err("下の一行が token。出るのはこの一度だけ。その人にだけ渡す:")
            _out(code)
        elif args.what == "revoke":
            n = gate.revoke(path, args.name)
            _out(f"{path}: {args.name} の token を取り消した（{n} 件）。サーバーでは次の要求から効かない。")
        else:
            rows = gate.rows(path)
            words = {"live": "生きている", "expired": "期限切れ", "revoked": "取り消した"}
            _out(f"{path}: {len(rows)} 件（生きている {sum(1 for r in rows if r['state'] == 'live')}）")
            for r in rows:
                tail = f"、取り消し {r['revoked']}" if r["revoked"] else ""
                note = f"　{r['note']}" if r["note"] else ""
                _out(
                    f"  {r['name']}　{','.join(r['scope'])}　{words[r['state']]}"
                    f"（{r['created']} 〜 {r['expires']}{tail}）{note}"
                )
    except gate.GateError as e:
        _err(f"seed token: {e}")
        return 1
    return 0


HOME_PORT = 8800
HOME_NAME = "home"  # home.toml の招待コードの呼び名
# 家のサーバーの一日の上限（招待コードは一つ、使うのは本人だけなので緩く。環境変数があればそれ）
HOME_LIMITS = {
    "SEED_DAILY_READS": "1000",
    "SEED_PER_TOKEN_READS": "500",
    "SEED_PER_IP_READS": "500",
    "SEED_DAILY_TALKS": "1000",
    "SEED_PER_TOKEN_TALKS": "500",
}


def home_invite(project: Path) -> tuple[Path, str]:
    """<プロジェクト>/home.toml の招待コード（一つ）。無ければ作る（600）。在ればそのまま使う。"""
    import secrets

    from .server.home import HOME_FILE
    from .server.settings import load_invites

    path = Path(project).expanduser() / HOME_FILE
    codes = load_invites(path) if path.exists() else {}
    if codes:
        return path, next(iter(codes))
    code = secrets.token_urlsafe(12)
    settings_mod.write_secret(
        path,
        "# seed home の招待コード（秘密。公開しない。消せば次の seed home で作り直す）\n"
        f'[codes]\n"{code}" = "{HOME_NAME}"\n',
    )
    return path, code


def lan_ip() -> str:
    """家の網の中のこの PC の番地。外へは何も送らない（UDP の口を向けるだけ）。分からなければ名。"""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # 文書用の番地。繋ぎに行かず、出る口の番地だけを決める
        ip = s.getsockname()[0]
    except OSError:
        ip = ""
    finally:
        s.close()
    if not ip or ip.startswith("127."):
        return socket.gethostname()
    return ip


def home_env(project: Path, invites: Path) -> dict[str, str]:
    """家のサーバーに渡す環境変数（設計書 §5.13）。"""
    from .server.home import PUBLIC_DIR

    project = Path(project).expanduser()
    env = {
        "SEED_HOME": str(project),
        "SEED_INVITES": str(invites),
        "SEED_PUBLIC_DIR": str(project / PUBLIC_DIR),
    }
    skill = project / "skill"
    if (skill / "SKILL.md").is_file():
        env["SEED_SKILL_DIR"] = str(skill)
    return env


def cmd_home(st: Settings, args) -> int:
    """家のサーバー（設計書 §5.13）。スマートフォン → この PC のプロジェクトフォルダー、一方通行。"""
    import os

    from . import local

    lg = st.language
    try:
        import uvicorn

        from .server import main as server_main
    except ModuleNotFoundError:
        _err(s("home_need_server", lg))
        return 1
    project = st.project
    invites, code = home_invite(project)
    os.environ.update(home_env(project, invites))
    os.environ.pop("SEED_OPEN", None)
    for k, v in HOME_LIMITS.items():
        os.environ.setdefault(k, v)
    hosts = [lan_ip()] if args.host in ("0.0.0.0", "::") else [args.host]
    _out(s("home_start", lg, project=project))
    for h in hosts:
        _out(s("home_url", lg, url=f"http://{h}:{args.port}"))
    _out(s("home_code", lg, code=code))
    _out(s("home_how", lg))
    if local.available() is None:
        _err(s("home_no_claude", lg))
    uvicorn.run(server_main.create_app(), host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_init(st: Settings, args) -> int:
    got = prepare(st.records)
    _set_invite(st, getattr(args, "invite", None))
    _out(s("init_done", st.language, folder=st.records.root, settings=st.path))
    if got == "missing":
        _err(s("skill_missing", st.language))
    else:
        _out(s(f"skill_{got}", st.language, path=st.records.skill))
    _out(s(f"claude_md_{claude_md.write(st.records.project or st.records.root, st.language)}", st.language))
    if not _set_keep(st, getattr(args, "keep", None), getattr(args, "bulk", None)):
        return 1
    _keep_status(st)
    return 0


def cmd_keep(st: Settings, args) -> int:
    """残す量を見る・変える。"""
    if not _set_keep(st, args.level, args.bulk):
        return 1
    _keep_status(st)
    z = keep_mod.sizes(st.records)
    _out(s("keep_sizes", st.language, **{k: keep_mod.mb(v) for k, v in z.items()}))
    return 0


def cmd_prune(st: Settings, args) -> int:
    """今の keep では残さない物を、見せて、頷かれたら消す。"""
    lg = st.language
    plan = keep_mod.prune_plan(st.records, st.keep)
    if not plan:
        _out(s("prune_nothing", lg, keep=st.keep))
        return 0
    for path, size in plan:
        _out(s("prune_item", lg, path=path, mb=keep_mod.mb(size)))
    _out(s("prune_total", lg, keep=st.keep, mb=keep_mod.mb(sum(b for _, b in plan))))
    if not args.yes:
        try:
            answer = input(s("prune_confirm", lg))
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            _out(s("prune_cancel", lg))
            return 0
    freed = keep_mod.prune(plan)
    _out(s("prune_done", lg, n=len(plan), mb=keep_mod.mb(freed)))
    return 0


def cmd_observe(st: Settings, args) -> int:
    from . import photos
    from .client import ClientError

    folder, lg = st.records, st.language
    try:
        obs = ingest(folder, args.photos, st.keep, lg)
    except photos.PhotoError as e:
        _err(error_text(e, lg))
        return 1
    for said in args.say or []:
        key, sep, text = said.partition(":")
        if not sep or key.strip() not in RECORD_KEYS or not text.strip():
            _err(s("say_format", lg))
            return 1
        obs.say(key.strip(), text.strip())
    if args.candidate:
        obs.kind = "candidate"
    try:
        obs.ask = parse_asks(",".join(args.ask or []))
    except ValueError:
        _err(s("ask_bad", lg, asks=", ".join(ASKS)))
        return 1
    path = folder.observation_path(obs)
    code = 0
    how = how_to_read(args)
    if how == "local":
        _out(s("local_reading", lg))
        try:
            got = read_local(st, folder, obs, model=getattr(args, "model", None))
            ms = (got.usage or {}).get("duration_ms") or 0
            _out(s("local_done", lg, model=got.model, seconds=round(ms / 1000)))
        except (ClientError, photos.PhotoError) as e:
            _err(error_text(e, lg))
            code = 2
    elif how == "server":
        try:
            read_on_server(st, folder, obs)
        except (ClientError, photos.PhotoError) as e:
            _err(error_text(e, lg, server=st.server))
            code = 2
    if "names" in obs.ask and not args.no_identify:
        _identify_and_report(st, folder, obs, None, None, quiet_if_unavailable=True)
    obs.write(path)
    _out(s("saved_to", lg, path=path))
    if obs.location:
        loc = obs.location
        _out(
            s(
                "coord",
                lg,
                lat=loc["center"][0],
                lon=loc["center"][1],
                points=loc["points"],
                extent=loc["extent_m"],
            )
        )
        for rel, m in photos.far_in(folder, obs):
            _err(s("far_photo", lg, photo=rel, m=m))
    else:
        _out(s("no_coord", lg))
    if obs.reading:
        _out(f"\n## {s('Reading', lg)} ({obs.model})")
        for l in obs.reading:
            _out(l.render())
    if how == "claude_code" or code:
        _out("")
        _out(s("read_claude", lg))
        _out(claude_steps(lg, folder, obs))
    return code


PLAN_NAME = "plan"  # mark / say で栽培計画を指す名


def _load_obs(st: Settings, name: str) -> tuple[Path, Observation | Plan]:
    """観察の名（日-時刻）か "plan"（栽培計画）を読む。"""
    folder = st.records
    if name == PLAN_NAME:
        if not folder.plan.exists():
            raise FileNotFoundError(folder.plan)
        return folder.plan, Plan.read(folder.plan)
    path = find_observation(folder, name)
    return path, Observation.read(path)


def _identify_and_report(st, folder, obs, stems, via, quiet_if_unavailable=False) -> int:
    """Pl@ntNet で確かめて結果を出す。鍵も招待コードも無いときは、quiet なら一言だけ。"""
    from . import identify
    from .client import ClientError

    lg = st.language
    if quiet_if_unavailable and not identify.available() and not st.invite:
        _out(s("identify_unavailable", lg))
        return 0
    try:
        added = identify_photos(st, folder, obs, stems, via)
    except ClientError as e:
        _err(error_text(e, lg))
        return 2
    if not added:
        _out(s("identify_none", lg))
    for l in added:
        _out(l.render())
    return 0


def cmd_identify(st: Settings, args) -> int:
    """草の名を Pl@ntNet で確かめる（設計書 §17）。observe の後に、写真を選んで。"""
    lg = st.language
    try:
        path, obs = _load_obs(st, args.observation)
    except FileNotFoundError:
        _err(s("observation_not_found", lg, name=args.observation))
        return 1
    via = "server" if args.server else "local" if args.local else None
    code = _identify_and_report(st, st.records, obs, args.photos or None, via)
    obs.write(path)
    _out(s("saved_to", lg, path=path))
    return code


def cmd_mark(st: Settings, args) -> int:
    lg = st.language
    try:
        path, obs = _load_obs(st, args.observation)
        obs.mark(args.key, args.verdict, args.reason, args.text)
    except FileNotFoundError:
        _err(s("observation_not_found", lg, name=args.observation))
        return 1
    except KeyError as e:
        _err(str(e.args[0]))
        return 1
    obs.write(path)
    _out(s("marked", lg, key=args.key, verdict=s(args.verdict, lg)))
    return 0


def cmd_say(st: Settings, args) -> int:
    lg = st.language
    try:
        path, obs = _load_obs(st, args.observation)
        obs.say(args.key, args.text)
    except FileNotFoundError:
        _err(s("observation_not_found", lg, name=args.observation))
        return 1
    except ValueError as e:
        _err(str(e))
        return 1
    obs.write(path)
    _out(s("said_added", lg, key=args.key))
    return 0


def publish_file(st: Settings, path: Path) -> int:
    """在る下書き（public/<id>.md）を、中身をそのまま送る。本人が読んだ文と送る文を同じにするため、組み直さない。"""
    import yaml

    from . import client

    lg = st.language
    try:
        text = path.read_text(encoding="utf-8")
        pub = Public.parse(text)
    except FileNotFoundError:
        _err(s("fix_these", lg) + f": {path}")
        return 1
    except (OSError, UnicodeDecodeError, ValueError, TypeError, KeyError, yaml.YAMLError) as e:
        _err(s("fix_these", lg) + ":")
        _err(f"- {path.name}: {e}")
        return 1
    bad = pub.check()
    if not pub.days:
        bad.append(s("nothing_selected", lg))
    if bad:
        _err(s("fix_these", lg) + ":")
        for b in bad:
            _err(f"- {b}")
        return 1
    shots = _photos_to_send(st, pub)
    if shots is None:
        return 1
    try:
        with client.Client(st.server, st.token, lg, invite=st.invite) as c:
            got = c.publish(text, shots)
    except client.ClientError as e:
        _err(error_text(e, lg, server=st.server))
        return 2
    _out(s("published", lg, url=got.get("url") or got.get("id")))
    return 0


def _photos_to_send(st: Settings, pub: Public) -> dict[str, bytes] | None:
    """photo の行が指す写真を送る形に。手元に無い写真があれば、その名を出して None（送らない）。"""
    shots, missing = public_photos(st.records, pub)
    if missing:
        _err(s("draft_photo_missing", st.language, names=", ".join(missing)))
        return None
    return shots


def cmd_publish(st: Settings, args) -> int:
    from . import client

    lg = st.language
    if args.file:
        return publish_file(st, Path(args.file).expanduser())
    if not (args.observations and args.id and args.place and args.word):
        _err(s("publish_needs", lg))
        return 1
    try:
        observations = [_load_obs(st, n)[1] for n in args.observations]
    except FileNotFoundError as e:
        _err(s("observation_not_found", lg, name=e.args[0]))
        return 1
    try:
        chosen = resolve_photos(observations, args.photo) if args.photo else None
    except ValueError as e:
        _err(s("photo_not_in_observations", lg, name=e.args[0]))
        return 1
    pub = make_public(
        st,
        observations,
        public_id=args.id,
        place=args.place,
        word=args.word,
        what=split_tags(args.what),
        next_=split_tags(args.next),
        with_coord=args.coord,
        contact=args.contact,
        name=args.name,
        photos=chosen,
        folder=st.records,
    )
    if any(o.kind == "candidate" for o in observations):
        _err(s("owner_warning", lg))
    bad = pub.check()
    if not pub.days:
        bad.append(s("nothing_selected", lg))
    if bad:
        _err(s("fix_these", lg) + ":")
        for b in bad:
            _err(f"- {b}")
        return 1
    st.records.public.mkdir(parents=True, exist_ok=True)
    path = st.records.public / f"{pub.id}.md"
    pub.write(path)
    if args.local:
        _out(s("published_local", lg, path=path))
        return 0
    shots = _photos_to_send(st, pub)
    if shots is None:
        _out(s("published_local", lg, path=path))
        return 1
    try:
        with client.Client(st.server, st.token, lg, invite=st.invite) as c:
            got = c.publish(pub.render(), shots)
    except client.ClientError as e:
        _err(error_text(e, lg, server=st.server))
        _out(s("published_local", lg, path=path))
        return 2
    _out(s("published", lg, url=got.get("url") or got.get("id")))
    return 0


def load_plan(st: Settings, folder: Folder) -> Plan:
    """plan.md を読む。無ければ新しく作る（書くのは呼ぶ側）。"""
    if folder.plan.exists():
        return Plan.read(folder.plan)
    return Plan.new(st.language)


def plan_local(st: Settings, folder: Folder, plan: Plan, model: str | None = None):
    """手元の claude で栽培計画を立て、plan に入れる（判定と本人の行は残る）。"""
    from . import local

    reading = local.plan(folder, plan, model=model)
    plan.reread(reading.lines, reading.model)
    return reading


def plan_steps(lg: str, folder: Folder, folder_label: str | None = None) -> str:
    """自分の Claude で栽培計画を立てる手順。"""
    return s("plan_steps", lg, folder=folder_label or folder.root, skill=folder.skill / "SKILL.md")


def cmd_plan(st: Settings, args) -> int:
    from . import local
    from .client import ClientError

    folder, lg = st.records, st.language
    prepare(folder)
    plan = load_plan(st, folder)
    if args.season:
        plan.season = args.season
    for text in args.decided or []:
        plan.say("decided", text)
    for text in args.did or []:
        plan.say("did", text)
    code = 0
    how = (
        "claude_code" if args.claude_code else "local" if (args.local or local.available()) else "claude_code"
    )
    if how == "local":
        _out(s("local_reading", lg))
        try:
            got = plan_local(st, folder, plan, model=getattr(args, "model", None))
            ms = (got.usage or {}).get("duration_ms") or 0
            _out(s("local_done", lg, model=got.model, seconds=round(ms / 1000)))
        except ClientError as e:
            _err(error_text(e, lg))
            code = 2
    plan.write(folder.plan)
    _out(s("saved_to", lg, path=folder.plan))
    if plan.reading:
        _out(f"\n## Plan ({plan.model})")
        for l in plan.reading:
            _out(l.render())
    if how == "claude_code" or code:
        _out("")
        _out(plan_steps(lg, folder))
    return code


def cmd_photos(st: Settings, args) -> int:
    """写真を撮った場所ごとに、時の順に並べて出す（AI は使わない。細かい座標は出さない）。"""
    from . import album

    if not args.by_place:
        _err(s("photos_needs_by_place", st.language))
        return 1
    text = album.render_places(album.by_place(st.records), st.language)
    _out(text or s("photos_none_cli", st.language))
    return 0


def cmd_app(st: Settings | None, args) -> int:
    from .app.main import run  # flet は app のときだけ読む

    run(web=args.web, folder=args.folder, port=args.port, serve=args.serve)
    return 0


def cmd_skill_path(st: Settings, args) -> int:
    """本人の手引き（~/seed/skill/）の道。まだ写していなければ seed init を促す。"""
    p = st.records.skill
    if not (p / "SKILL.md").is_file():
        _err(s("skill_not_copied", st.language, path=p))
        return 1
    _out(str(p))
    return 0


# ---------------------------------------------------------------- seed marks（合う／違うの付いた行と 06 章）

CHAPTER_READ = "06-畑を読む.md"  # その畑での読み方。「違う」の理由で本人が直す章（設計書 §5.4b、手引き 08）
# 06 章の「写真から見る物」の箇条書きは key でなく太字の語で始まる（**草。** など）。その語と key の対応。
# 見出しにこの語があれば、その見出しも key に当たる（本人が足した「この畑の草の名前」など）
CHAPTER_WORDS = {
    "plants": ("草", "勢い"),
    "soil_surface": ("裸地", "地表"),
    "water": ("水",),
    "crops": ("作物",),
    "surroundings": ("まわり", "周り"),
}
_BACKTICK_RE = re.compile(r"`([a-z][a-z0-9_]*)`")
_BOLD_START_RE = re.compile(r"^(?:\s*[-*]|\s*\d+\.)\s+\*\*(?P<bold>[^*]+)\*\*")
_ITEM_START_RE = re.compile(r"^(?:#{1,6} |\||\s*[-*] |\s*\d+\. )")


def chapter_path(folder: Folder) -> Path | None:
    """06 章の道。本人の手引き（~/seed/skill/）にあればそれ、無ければパッケージの物。"""
    for base in (folder.skill, package_skill()):
        if base is not None and (base / CHAPTER_READ).is_file():
            return base / CHAPTER_READ
    return None


def _join(a: str, b: str) -> str:
    """折り返された行を繋ぐ。日本語の続きは空白を入れない。"""
    return a + b if (a and not a[-1].isascii()) or (b and not b[0].isascii()) else f"{a} {b}"


def chapter_items(text: str) -> list[tuple[int, str]]:
    """章を (行番号, 一項目) に分ける。項目は見出し、表の行、箇条書き（折り返しを繋ぐ）。

    コードの囲み（```）と HTML の注釈（<!-- -->）の中、表の区切りの行は読み飛ばす。行番号は 1 から。
    """
    items: list[tuple[int, str]] = []
    fence = comment = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if comment or line.lstrip().startswith("<!--"):
            comment = "-->" not in line
            continue
        if not line.strip():
            items.append((n, ""))  # 箇条書きの終わり
        elif _ITEM_START_RE.match(line):
            if not re.fullmatch(r"\|[\s|:-]+\|", line):
                items.append((n, line.strip()))
        elif items and items[-1][1] and not items[-1][1].startswith(("#", "|")):
            items[-1] = (items[-1][0], _join(items[-1][1], line.strip()))  # 箇条書きの続き
    return [(n, t) for n, t in items if t]


def chapter_lines(text: str, key: str) -> list[tuple[int, str]]:
    """章のうち key に当たる項目。

    - 見出し: `key` だけを名指しているか（いくつもの key を並べた見出しは除く）、CHAPTER_WORDS の語を含む
    - 表の行と箇条書き: `key` を含むか、CHAPTER_WORDS の語で始まる太字で始まる
    """
    words = CHAPTER_WORDS.get(key, ())
    out = []
    for n, item in chapter_items(text):
        named = set(_BACKTICK_RE.findall(item)) & {*READING_KEYS, *PLAN_KEYS}
        if item.startswith("#"):
            hit = named == {key} or any(w in item.lstrip("# ") for w in words)
        else:
            bold = _BOLD_START_RE.match(item)
            hit = f"`{key}`" in item or bool(bold and bold["bold"].startswith(words))
        if hit:
            out.append((n, item))
    return out


def _key_order(marks: list[Mark]) -> list[str]:
    """読みの key の順 → 栽培計画の key の順 → 知らない key は出てきた順。"""
    order = list(dict.fromkeys((*READING_KEYS, *PLAN_KEYS)))
    seen = list(dict.fromkeys(m.key for m in marks))
    return [k for k in order if k in seen] + [k for k in seen if k not in order]


def _where(m: Mark, lg: str) -> str:
    where = "plan.md" if m.source == "plan" else s("marks_where_obs", lg, when=m.when)
    return where + (s("marks_earlier", lg) if m.earlier else "")


def _count(marks: list[Mark], lg: str) -> str:
    return s("marks_sep", lg).join(
        f"{lang.t(v, lg)} {n}" for v in ("wrong", "right") if (n := sum(m.verdict == v for m in marks))
    )


def cmd_marks(st: Settings, args) -> int:
    """合う／違うの付いた行を key ごとに集め、本人の手引きの 06 章の当たる行と並べる。読むだけ。"""
    every, lg = st.records.marks(), st.language
    if args.key:
        every = [m for m in every if m.key == args.key]
    shown = every if args.all else [m for m in every if m.verdict == "wrong"]
    chapter = chapter_path(st.records)
    text = chapter.read_text(encoding="utf-8") if chapter else ""
    keys = _key_order(shown)
    if args.json:
        _out(
            json.dumps(
                {
                    "chapter": str(chapter) if chapter else None,
                    "marks": [{**vars(m), "name": m.name} for m in shown],
                    "chapter_lines": {
                        k: [{"line": n, "text": t} for n, t in chapter_lines(text, k)] for k in keys
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    about = s("marks_about", lg, key=args.key) if args.key else ""
    if not every:
        _out(s("marks_none", lg, about=about))
        return 0
    if not shown:
        _out(s("marks_no_wrong", lg, about=about, n=len(every)))
        return 0
    places = len({m.when for m in shown if m.source == "observation"})
    src = s("marks_src_obs", lg, n=places) + (
        s("marks_src_plan", lg) if any(m.source == "plan" for m in shown) else ""
    )
    _out(s("marks_title_all" if args.all else "marks_title_wrong", lg))
    _out("")
    _out(f"{_count(shown, lg)}（{src}）{about}" if lg == "ja" else f"{_count(shown, lg)} ({src}){about}")
    _out(s("marks_chapter", lg, path=chapter) if chapter else s("marks_chapter_missing", lg))
    for k in keys:
        group = [m for m in shown if m.key == k]
        _out("")
        _out(f"## {k} — {_count(group, lg)}")
        _out("")
        for m in group:
            conf = f" [{m.confidence:.2f}]" if m.confidence is not None else ""
            _out(f"- {_where(m, lg)}: {m.text}{conf}")
            _out(
                f"  → {lang.t(m.verdict, lg)}" + (s("marks_reason", lg, reason=m.reason) if m.reason else "")
            )
        _out("")
        found = chapter_lines(text, k) if text else []
        if not found:
            _out(s("marks_chapter_none", lg))
            continue
        _out(s("marks_chapter_lines", lg))
        for n, item in found:
            _out(s("marks_chapter_line", lg, n=n, item=item))
    return 0


# ---------------------------------------------------------------- seed origin（畑の成り立ちの動画。設計書 §15）


def cmd_origin(st: Settings, args) -> int:
    """座標から、公開の地図と空中写真を並べた動画を組む。AI は呼ばない。出力は本人のフォルダーの中だけ。"""
    lg, folder = st.language, st.records
    try:
        from . import origin
    except ModuleNotFoundError as e:
        _err(s("origin_need", lg, module=e.name))
        return 1
    if (args.lat is None) != (args.lon is None):
        _err(s("origin_latlon_pair", lg))
        return 1
    try:
        size = origin.parse_size(args.size)
    except ValueError:
        _err(s("origin_bad_size", lg, size=args.size))
        return 1
    day = dt.date.today().isoformat()
    try:
        out = origin.output_dir(folder, args.out, day)
    except ValueError as e:
        _err(s("origin_out_outside", lg, folder=folder.root, out=e.args[0]))
        return 1
    plan = origin.make_plan(folder, lg, args.lat, args.lon, size=size)
    if plan is None:
        _err(s("origin_no_coord", lg))
        return 1
    if args.lat is None:
        located = origin.latest_located(folder)
        _out(s("origin_center_obs", lg, when=f"{located.date} {located.time}", extent=plan.extent_m))
    else:
        _out(s("origin_center_args", lg))
    if args.font and not Path(args.font).expanduser().is_file():
        _err(s("origin_bad_font", lg, path=args.font))
        return 1
    font = origin.find_font(args.font)
    _out(s("origin_font", lg, path=font)) if font else _err(s("origin_no_font", lg))
    try:
        fetch = origin.HttpFetch()  # テストは偽のタイルを返す物に差し替える
    except ModuleNotFoundError as e:
        _err(s("origin_need", lg, module=e.name))
        return 1
    tiles = origin.Tiles(folder.root / "origin" / "tiles", fetch)
    _out(s("origin_fetching", lg, budget=tiles.budget))
    try:
        got = origin.run(plan, tiles, origin.Fonts(font), out, seconds=args.seconds, fps=args.fps, day=day)
    finally:
        fetch.close()
    _out(s("origin_made", lg, n=len(got.frames), names=s("origin_sep", lg).join(f.title for f in got.frames)))
    for k in got.skipped:
        _out(s("origin_skipped", lg, name=k.title, reason=k.reason))
    _out(s("origin_tiles", lg, fetched=tiles.fetched, cached=tiles.cached, missing=tiles.missing))
    if not got.frames:
        _err(s("origin_nothing", lg))
        _out(s("origin_wrote_captions", lg, path=got.captions))
        return 2
    _out(s("origin_wrote_video", lg, path=got.video))
    _out(s("origin_wrote_frames", lg, path=got.out / "frames", n=len(got.frame_paths)))
    _out(s("origin_wrote_captions", lg, path=got.captions))
    if not got.mp4:
        _err(s("origin_no_mp4", lg))
    _out(s("origin_private", lg))
    return 0


# ---------------------------------------------------------------- seed grow（計画の絵（仮説）。設計書 §16.3 の 1 と 2）


def grow_steps(lg: str, folder: Folder, out: Path) -> str:
    """自分の Claude（Claude Code）でシナリオを書く手順（C の道）。"""
    try:
        rel = out.relative_to(folder.root).as_posix()
    except ValueError:
        rel = str(out)
    return s("grow_steps", lg, folder=folder.root, skill=folder.skill / "SKILL.md", out=rel)


def _read_scenario(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("not a JSON object")
    return data


def cmd_grow(st: Settings, args) -> int:
    """plan.md の行から、季節ごとの図を線で描く。仮説の図で、出力は本人のフォルダーの grow/<日>/ だけ。"""
    from . import grow, local
    from .client import ClientError

    folder, lg = st.records, st.language
    plan = Plan.read(folder.plan) if folder.plan.is_file() else None
    if plan is None or not plan.reading:
        _err(s("grow_no_plan", lg))
        return 2
    lg = plan.language or lg
    if getattr(args, "draw", False):
        return grow_draw(st, args, folder, plan, lg)
    day = dt.date.today().isoformat()
    out = grow.output_dir(folder, day)
    scenario_path = out / grow.SCENARIO
    max_scenes = max(1, min(args.scenes or grow.MAX_SCENES, grow.MAX_SCENES))
    if args.render:
        src = Path(args.render).expanduser()
        if not src.is_absolute() and not src.exists() and (folder.root / src).exists():
            src = (
                folder.root / src
            )  # 手引きの「seed grow --render grow/<日>/scenario.json」はフォルダーからの道
        try:
            scenario = _read_scenario(src)
        except (OSError, ValueError, TypeError) as e:
            _err(s("grow_bad_json", lg, path=src, detail=e))
            return 2
        out.mkdir(parents=True, exist_ok=True)
        if src.resolve() != scenario_path.resolve():
            scenario_path.write_text(
                json.dumps(scenario, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )
    else:
        how = (
            "claude_code"
            if args.claude_code
            else "local"
            if (args.local or local.available())
            else "claude_code"
        )
        if how == "claude_code":
            out.mkdir(parents=True, exist_ok=True)
            _out(grow_steps(lg, folder, out))
            return 0
        _out(s("grow_reading", lg))
        try:
            scenario = local.grow(folder, plan, model=args.model, max_scenes=max_scenes)
        except ClientError as e:
            _err(error_text(e, lg))
            _out("")
            _out(grow_steps(lg, folder, out))
            return 2
        out.mkdir(parents=True, exist_ok=True)
        scenario_path.write_text(json.dumps(scenario, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    _out(s("grow_wrote_scenario", lg, path=scenario_path))
    checked = grow.validate(scenario, plan, max_scenes)
    meta = {"model": scenario.get("model") or local.DEFAULT_MODEL, "day": day, "since": plan.since}
    got = grow.write(checked, out, lg, meta)
    _out(s("grow_made", lg, n=len(checked.scenes)))
    for k in checked.skipped:
        _out(s("grow_skipped", lg, name=k.scene + (f" / {k.what}" if k.what else ""), reason=k.reason))
    for p in got.svgs:
        _out(s("grow_wrote_svg", lg, path=p))
    _out(s("grow_wrote_captions", lg, path=got.captions))
    if not checked.scenes:
        _err(s("grow_nothing", lg))
        return 2
    _out(s("grow_private", lg))
    return 0


def latest_grow_day(folder: Folder) -> str | None:
    root = folder.root / "grow"
    days = sorted(
        p.name
        for p in (root.iterdir() if root.is_dir() else [])
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name) and (p / "scenario.json").is_file()
    )
    return days[-1] if days else None


def grow_draw(st: Settings, args, folder: Folder, plan: Plan, lg: str) -> int:
    """seed grow --draw。scenario.json を検証して SVG を描き直し、prompt のある場面を halo で絵にする（設計書 §16.3 の 3）。"""
    from . import draw, grow, local
    from .client import ClientError

    day = args.day or latest_grow_day(folder)
    if not day or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        _err(s("draw_no_day", lg, day=day or "-"))
        return 2
    out = grow.output_dir(folder, day)
    try:
        scenario = _read_scenario(out / grow.SCENARIO)
    except (OSError, ValueError, TypeError) as e:
        _err(s("grow_bad_json", lg, path=out / grow.SCENARIO, detail=e))
        return 2
    try:
        size = draw.parse_size(args.size)
    except ValueError:
        _err(s("draw_bad_size", lg, size=args.size))
        return 2
    photos = [Path(p).expanduser() for p in args.photo]
    for p in photos:
        if not p.is_file():
            _err(s("draw_no_photo", lg, path=p))
            return 2
    if len(photos) > draw.MAX_PHOTOS:
        _err(s("draw_photos_over", lg, max=draw.MAX_PHOTOS))
        photos = photos[: draw.MAX_PHOTOS]
    checked = grow.validate(scenario, plan, args.scenes or grow.MAX_SCENES)
    meta = {"model": scenario.get("model") or local.DEFAULT_MODEL, "day": day, "since": plan.since}
    got = grow.write(checked, out, lg, meta)  # 図は今の scenario.json から描き直す（参照に渡す物）
    if not checked.scenes:
        _err(s("grow_nothing", lg))
        return 2
    server = draw.server_url(args.server, st.extra)
    if not server:
        _err(s("draw_no_server", lg, env=draw.ENV_URL))
        _out(s("grow_wrote_captions", lg, path=got.captions))
        return 2
    _out(s("draw_start", lg, server=server, n=sum(1 for sc in checked.scenes if sc.prompt)))

    def each(d) -> None:
        _out(s("draw_done", lg, i=f"{d.index:02d}", secs=f"{d.seconds:.1f}", path=d.png))

    report = draw.draw(
        checked,
        out,
        server,
        photos,
        lg,
        day,
        folder.root,
        size,
        progress=each,
        bearer=draw.token(st.draw_token),
    )
    for i, sc, why in report.skipped:
        _out(s("grow_skipped", lg, name=f"{i:02d} {sc.when} {sc.title}", reason=why))
    if report.drawn:
        if local.available():
            _out(s("draw_checking", lg))
            for d in report.drawn:
                try:
                    found = local.grow_check(d.png, d.scene, folder.root, model=args.model)
                    report.checks[d.index] = {"by": "Claude（claude -p）", "found": found}
                except ClientError as e:
                    report.checks[d.index] = {"by": "Claude（claude -p）", "error": error_text(e, lg)}
            if any("error" in c for c in report.checks.values()):
                _out(s("draw_check_steps", lg, folder=folder.root, out=out))
        else:
            _out(s("draw_check_steps", lg, folder=folder.root, out=out))
    cap = out / grow.CAPTIONS
    cap.write_text(draw.captions(checked, lg, meta, report), encoding="utf-8")
    _out(s("grow_wrote_captions", lg, path=cap))
    if report.error:
        _err(s(report.error.word, lg, server=server, detail=report.error.detail))
        return 2
    _out(s("grow_private", lg))
    return 0


# ---------------------------------------------------------------- 畑の文字の仕事（記録の形 §15〜18。設計書 §5.7）


def _field_error(e: Exception, lg: str) -> str:
    """LotError / LedgerError / WeatherError を一行に。"""
    kw = dict(getattr(e, "kw", {}) or {})
    detail = getattr(e, "detail", "")
    kw.setdefault("value", detail)
    kw.setdefault("detail", detail)
    return s(e.word, lg, **kw)


def cmd_lot(st: Settings, args) -> int:
    """種のロット lots.md。本人の行だけ（AI の行は無い）。"""
    from . import lots

    folder, lg = st.records, st.language
    path = lots.lots_path(folder.root)
    if args.act == "list":
        got = lots.read_lots(path)
        if not got:
            _out(s("lot_none", lg, path=path))
            return 0
        for lot in got:
            _out(lot.render())
        return 0
    lot = lots.Lot(
        lot=args.lot,
        crop=args.crop,
        variety=args.variety,
        place=args.place,
        year=str(args.year),
        from_=args.from_ or "",
        note=args.note or "",
    )
    try:
        lots.add_lot(folder.root, lot)
    except lots.LotError as e:
        _err(_field_error(e, lg))
        return 1
    _out(s("lot_added", lg, lot=lot.lot, path=path))
    _out(s("field_private", lg))
    return 0


def cmd_ledger(st: Settings, args) -> int:
    """帳簿 ledger.md。合計と請求書の下書き。税の計算はしない。"""
    from . import ledger

    folder, lg = st.records, st.language
    path = ledger.ledger_path(folder.root)
    try:
        if args.act == "add":
            e = ledger.make_entry(args.date, args.kind, args.yen, args.what, args.lot or "", args.to or "")
            ledger.add_entry(folder.root, e)
            _out(s("ledger_added", lg, path=path, line=e.render()))
            _out(s("field_private", lg))
            return 0
        if args.act == "sum":
            got = ledger.month_entries(ledger.read_entries(path), args.month)
            total = ledger.sums(got)
            _out(s("ledger_sum_head", lg, month=args.month, n=len(got)))
            for kind in ledger.KINDS:
                _out(s("ledger_sum_row", lg, label=s(f"ledger_kind_{kind}", lg), yen=total[kind]))
            _out(s("ledger_net", lg, yen=total["net"]))
            return 0
        texts = {k: s(f"invoice_{k}", lg) for k in ("title", "self_writes", "yen", "no_tax")}
        out, items = ledger.write_invoice(folder.root, texts, st.name, args.to, args.month)
    except ledger.LotError as e:
        _err(_field_error(e, lg))
        return 1
    _out(s("invoice_written", lg, path=out, n=len(items), total=sum(e.yen for e in items)))
    _out(s("invoice_no_tax", lg))
    return 0


def cmd_weather(st: Settings, args) -> int:
    """気象の記録 weather/<YYYY-MM>.md。網に繋ぐのは fetch だけ。"""
    from . import ledger, weather

    folder, lg = st.records, st.language
    if args.act == "show":
        try:
            ledger.check_month(args.month)
        except ledger.LotError as e:
            _err(_field_error(e, lg))
            return 1
        text = weather.show(folder.root, args.month)
        if text is None:
            _out(s("weather_none", lg, month=args.month, path=weather.month_path(folder.root, args.month)))
            return 0
        _out(text.rstrip("\n"))
        return 0
    if (args.lat is None) != (args.lon is None):
        _err(s("weather_no_coord", lg))
        return 1
    center = (args.lat, args.lon) if args.lat is not None else weather.place_center(folder)
    if center is None:
        _err(s("weather_no_coord", lg))
        return 1
    lat, lon = weather.rounded(*center)
    try:
        start, end = weather.check_range(args.from_, args.to)
        _out(s("weather_sending", lg, lat=f"{lat:.2f}", lon=f"{lon:.2f}", start=start, end=end))
        days = weather.fetch(lat, lon, start, end)
    except weather.WeatherError as e:
        _err(_field_error(e, lg))
        return 2
    paths = weather.write_days(folder.root, days, lg)
    kept = [d for d in days if not d.empty]
    _out(s("weather_written", lg, n=len(kept), paths=", ".join(str(p) for p in paths) or "-"))
    if len(kept) < len(days):
        _out(s("weather_skipped", lg, n=len(days) - len(kept)))
    _out(s("field_private", lg))
    return 0


def cmd_procedure(st: Settings, args) -> int:
    """手続きの下書き procedures/<slug>/。判定は書かない。"""
    from . import procedure

    folder, lg = st.records, st.language
    make = procedure.PROCEDURES.get(args.slug)
    if make is None:
        _err(s("procedure_unknown", lg, slug=args.slug, known=", ".join(procedure.PROCEDURES)))
        return 1
    got = make(folder)
    _out(s("procedure_head", lg))
    _out(s("procedure_written", lg, path=got.out))
    if got.filled:
        _out(s("procedure_filled", lg, keys=", ".join(got.filled)))
    else:
        _out(s("procedure_filled_none", lg))
    if got.kept_checks or got.kept_lines:
        _out(s("procedure_kept", lg, checks=got.kept_checks, lines=got.kept_lines))
    _out(s("field_private", lg))
    return 0


# ---------------------------------------------------------------- seed project（プロジェクトの一覧。記録の形 §19）


def cmd_project(st: Settings | None, args) -> int:
    """プロジェクトの一覧（fields.toml）を足す・見る・切り替える。seed.toml は読まない・作らない。"""
    lg = lang.default_language(None)
    fl = fields_mod.load_fields()
    path = fields_mod.fields_path()
    if args.act == "add":
        fl.add(args.name, args.path)
        fields_mod.save_fields(fl)
        _out(s("project_added", lg, name=args.name, folder=args.path, path=path))
        return 0
    if args.act == "use":
        try:
            f = fl.use(args.name)
        except fields_mod.UnknownField:
            _err(s("project_unknown", lg, name=args.name, path=path))
            return 1
        fields_mod.save_fields(fl)
        _out(s("project_used", lg, name=f.name, folder=f.folder))
        return 0
    if not fl.fields:
        _out(s("project_none", lg, path=path))
        return 0
    for f in fl.fields:
        _out(f"{'*' if f.name == fl.current else ' '} {f.name}\t{f.folder}")
    return 0


# ---------------------------------------------------------------- seed field（プロジェクトの中の畑 fields/<名>/。設計書 §5.12）


def _field_project(args) -> Path:
    """畑の命令のプロジェクト。--folder > 今いるフォルダー > current > SEED_FOLDER > 既定（--field は見ない）。"""
    got, _ = fields_mod.locate(None, getattr(args, "folder", None))
    return Path(got).expanduser() if got else fields_mod.split_field(settings_mod.default_folder())[0]


# 畑一つ分の記録（根に記録を置いていたプロジェクトが初めて畑を作る時、その畑へ移す物）。共有の物は根に残す
ROOT_RECORDS = (
    "observations", "photos", "originals", "place.md", "plan.md", "next.md", "connections.md", "public",
    "lots.md", "ledger.md", "weather", "procedures", "origin", "grow",
)  # fmt: skip


def move_root_records(st: Settings, folder: Folder) -> list[str]:
    """根に記録（observations/ か photos/）があれば、畑 folder へ移す。移した物の名を返す（無ければ []）。"""
    root = st.project
    if not ((root / "observations").exists() or (root / "photos").exists()):
        return []
    folder.root.mkdir(parents=True, exist_ok=True)
    moved = []
    for n in ROOT_RECORDS:
        src = root / n
        if src.exists() and not (folder.root / n).exists():
            shutil.move(str(src), str(folder.root / n))
            moved.append(n)
    bulk = Path(st.bulk).expanduser() if st.bulk else None
    if bulk is not None and (bulk / "originals").exists() and folder.bulk is not None:
        folder.bulk.mkdir(parents=True, exist_ok=True)
        if not (folder.bulk / "originals").exists():
            shutil.move(str(bulk / "originals"), str(folder.bulk / "originals"))
            moved.append(str(bulk / "originals"))
    return moved


def cmd_field(st: Settings | None, args) -> int:
    """プロジェクトの中の畑を作る・選ぶ・見る。前の seed field add は seed project add に回す。"""
    lg = lang.default_language(None)
    if args.act == "add":  # 前の名（プロジェクトの一覧に足す）
        _err(s("field_add_alias", lg))
        return cmd_project(st, args)
    project = _field_project(args)
    names = settings_mod.field_names(project)
    if args.act == "new":
        name = args.name
        if not name or "/" in name or "\\" in name or name.startswith("."):
            _err(s("field_new_bad", lg, name=name))
            return 1
        st = settings_mod.load(project)
        lg = st.language
        folder = st.field_folder(name)
        existed = folder.root.exists()
        moved = move_root_records(st, folder) if not names else []
        if moved:
            _out(s("field_new_moved", lg, name=name, items="、".join(moved)))
        prepare(folder, st.language)
        settings_mod.write_field(project, name)  # 作った人は次にそこで記録する
        _out(
            s(
                "field_new_kept" if existed and not moved else "field_new_done",
                lg,
                name=name,
                folder=folder.root,
            )
        )
        return 0
    if args.act == "use":
        if args.name in ("all", ""):
            settings_mod.write_field(project, "")
            _out(s("field_set_whole", lg, project=project))
            return 0
        if args.name in names:
            settings_mod.write_field(project, args.name)
            _out(s("field_set", lg, name=args.name, project=project))
            return 0
        if fields_mod.load_fields().get(args.name) is not None:  # 前の意味: プロジェクトの一覧の名
            _err(s("field_use_project", lg, name=args.name))
            return cmd_project(st, args)
        _err(s("field_unknown", lg, name=args.name, project=project, path=fields_mod.fields_path()))
        return 1
    if not names:  # 畑が一つのプロジェクト: 前と同じくプロジェクトの一覧を出す
        if (project / settings_mod.FILENAME).is_file():
            _err(s("field_none_here", lg, project=project))
        return cmd_project(st, args)
    now = settings_mod.read_field(project)
    now = now if now in names else ""
    _out(f"{'*' if not now else ' '} {s('field_whole_mark', lg)}")
    for n in names:
        _out(f"{'*' if n == now else ' '} {n}\t{project / settings_mod.FIELDS_DIR / n}")
    return 0


# ---------------------------------------------------------------- 引数


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--folder", default=argparse.SUPPRESS, help="記録のフォルダー（既定 ~/seed）")
    common.add_argument(
        "--field",
        default=argparse.SUPPRESS,
        help="畑の名（プロジェクトの fields/ の下の物。無ければ seed project add で足したプロジェクトの名。--folder があればそちら）",
    )
    common.add_argument("--server-url", default=argparse.SUPPRESS, help="この回だけ使うサーバーの URL")

    p = argparse.ArgumentParser(
        prog="seed", parents=[common], description="自給農の畑を、自分の Claude と一緒に読む"
    )
    sub = p.add_subparsers(dest="command", required=True)

    i = sub.add_parser("init", parents=[common], help="フォルダーと seed.toml を作る")
    i.add_argument("--keep", choices=keep_mod.LEVELS, help="どれだけ残すか（text / photos / research）")
    i.add_argument("--bulk", help="重い物（写真の元）を置く別の盤の道。'' で外す")

    i.add_argument(
        "--invite", metavar="CODE", help="招待コード（Discord で渡す）。サーバーで読む・公開・一言に要る"
    )

    iv = sub.add_parser("invite", parents=[common], help="招待コードを見る・入れる")
    iv.add_argument("code", nargs="?", help="入れるコード。空の文字列で消す")
    iv.add_argument(
        "--list", action="store_true", help="サーバーの側の一覧を見る（呼び名とコードの先頭 4 桁だけ）"
    )
    iv.add_argument("--invites", metavar="PATH", help="--list で読む invites.toml（無ければ SEED_INVITES）")

    tk = sub.add_parser(
        "token", parents=[common], help="相手ごとの token（サーバーの門）を出す・見る・取り消す"
    )
    tks = tk.add_subparsers(dest="what", required=True)
    for name, hlp in (
        ("add", "一件出す（token は一度だけ出る）"),
        ("list", "台帳を見る（ハッシュは出さない）"),
        ("revoke", "取り消す"),
    ):
        t = tks.add_parser(name, parents=[common], help=hlp)
        t.add_argument(
            "--file", metavar="PATH", help="台帳（無ければ SEED_TOKENS、~/.config/aiseed/tokens.json）"
        )
        if name != "list":
            t.add_argument("name", help="呼び名（誰に渡すか）")
        if name == "add":
            t.add_argument(
                "--scope",
                choices=("member", "buyer", "admin"),
                default="member",
                help="member: 招待した人。buyer: 買い手（一言を送るだけ）",
            )
            t.add_argument("--days", type=int, default=90, help="期限（日。既定 90）")
            t.add_argument("--note", help="覚え書き（誰に、何のために）")

    k = sub.add_parser("keep", parents=[common], help="どれだけ残すかを見る・変える")
    k.add_argument("level", nargs="?", choices=keep_mod.LEVELS)
    k.add_argument("--bulk", help="重い物（写真の元）を置く別の盤の道。'' で外す")

    pr = sub.add_parser("prune", parents=[common], help="今の keep では残さない物を、見せてから消す")
    pr.add_argument("--yes", action="store_true", help="聞かずに消す")

    o = sub.add_parser("observe", parents=[common], help="写真を取り込んで観察を作る")
    o.add_argument("photos", nargs="+", type=Path)
    how = o.add_mutually_exclusive_group()
    how.add_argument(
        "--local",
        action="store_true",
        help="この PC の claude（Claude Code、サブスク）で読む（claude があれば既定）",
    )
    how.add_argument("--server", action="store_true", help="サーバーで読む（claude が無いときの既定）")
    how.add_argument(
        "--claude-code", action="store_true", help="読まずに観察を作り、Claude Code で読む手順を出す"
    )
    o.add_argument(
        "--model", help="--local のモデル（opus、sonnet、claude-opus-5-5 など。無ければ claude の既定）"
    )
    o.add_argument("--say", action="append", help="本人の言葉。'did: 今日は見ただけ' の形。何度でも")
    o.add_argument("--candidate", action="store_true", help="自分の畑でない場所（候補地）の写真")
    o.add_argument(
        "--no-identify",
        action="store_true",
        help="--ask names でも Pl@ntNet に送らない（既定は鍵か招待コードがあれば送る）",
    )
    o.add_argument(
        "--ask",
        action="append",
        metavar="WORD",
        help=f"知りたいこと（{', '.join(ASKS)}。コンマで複数、繰り返しも可）。自由な言葉は --say ask:文",
    )

    idp = sub.add_parser(
        "identify", parents=[common], help="草の名を Pl@ntNet で確かめ、plants の行を足す（写真は一枚ずつ）"
    )
    idp.add_argument("observation", help="観察の名（日-時刻）")
    idp.add_argument("photos", nargs="*", help="写真の名（例: 092817）。無ければ全部（10 枚まで）")
    idhow = idp.add_mutually_exclusive_group()
    idhow.add_argument("--local", action="store_true", help="本人の鍵 PLANTNET_API_KEY で（あれば既定）")
    idhow.add_argument("--server", action="store_true", help="サーバーの鍵で（招待コードが要る）")

    m = sub.add_parser("mark", parents=[common], help="読みの行に合う／違うを付ける")
    m.add_argument("observation", help="観察の名（日-時刻）か plan（栽培計画）")
    m.add_argument("key")
    m.add_argument("verdict", choices=("right", "wrong"))
    m.add_argument("--reason")
    m.add_argument("--text", help="同じ key の行が複数あるとき、どの文か")

    mk = sub.add_parser(
        "marks", parents=[common], help="合う／違うを付けた行を key ごとに集め、手引きの 06 章の行と並べる"
    )
    mk.add_argument("--all", action="store_true", help="合うの行も出す（既定は違うだけ）")
    mk.add_argument("--key", help="この key の行だけ（soil_surface など）")
    mk.add_argument("--json", action="store_true", help="JSON で出す")

    y = sub.add_parser("say", parents=[common], help="本人の行を足す（did, saw, said, note）")
    y.add_argument("observation", help="観察の名（日-時刻）か plan（栽培計画。key は decided, did）")
    y.add_argument("key", choices=tuple(dict.fromkeys((*RECORD_KEYS, *PLAN_RECORD_KEYS))))
    y.add_argument("text")

    pl = sub.add_parser(
        "plan", parents=[common], help="栽培計画 plan.md を立てる・立て直す（借りる・買えた畑で）"
    )
    pl.add_argument("--season", help="季節。本人の言葉で（例: 2026-27 冬）")
    pl.add_argument("--decided", action="append", metavar="TEXT", help="本人が決めたこと（繰り返し可）")
    pl.add_argument("--did", action="append", metavar="TEXT", help="実際にしたこと（繰り返し可）")
    plhow = pl.add_mutually_exclusive_group()
    plhow.add_argument("--local", action="store_true", help="この PC の claude で立てる（あれば既定）")
    plhow.add_argument(
        "--claude-code", action="store_true", help="立てずに plan.md を用意し、Claude Code で立てる手順を出す"
    )
    pl.add_argument("--model", help="--local のモデル（無ければ claude の既定）")

    u = sub.add_parser(
        "publish",
        parents=[common],
        help="観察から公開ファイルを作って送る（--file なら在る下書きをそのまま送る）",
    )
    u.add_argument("observations", nargs="*")
    u.add_argument(
        "--file", help="在る下書き（public/<id>.md）を、中身をそのまま送る。観察や --id などは要らない"
    )
    u.add_argument("--id")
    u.add_argument("--place")
    u.add_argument("--word")
    u.add_argument("--coord", action="store_true", help="座標を小数 2 桁で付ける")
    u.add_argument("--what", help="札。, か 、 で区切る")
    u.add_argument("--next", help="その次。, か 、 で区切る")
    u.add_argument("--name", help="呼び名（既定は seed.toml の name）")
    u.add_argument("--contact")
    u.add_argument(
        "--photo",
        action="append",
        help="出す写真（写真の名か photos/… の道。何度でも。一日 3 枚、全部で 12 枚まで）。無ければ日ごとに今日の一枚",
    )
    u.add_argument("--local", action="store_true", help="サーバーへ送らず public/ に書くだけ")

    ph = sub.add_parser("photos", parents=[common], help="写真を撮った場所ごとに、時の順に並べて出す")
    ph.add_argument(
        "--by-place",
        action="store_true",
        help="座標の近い物（20 m ほど）を一つの場所にまとめ、場所ごとに時の順",
    )
    ph.set_defaults(readonly=True)

    a = sub.add_parser("app", parents=[common], help="アプリを開く")
    a.add_argument("--web", action="store_true", help="この PC のブラウザで開く（画面の確かめ用、一人用）")
    a.add_argument(
        "--serve", action="store_true", help="やめた（人ごとに記録を置く Web 版）。一行知らせて終わる"
    )
    a.add_argument("--port", type=int, default=0)

    og = sub.add_parser(
        "origin",
        parents=[common],
        help="座標から、公開の地図と空中写真を並べた一分ほどの動画を組む（AI は使わない。出力はフォルダーの origin/）",
    )
    og.add_argument("--lat", type=float, help="中心の緯度（無ければ座標のある一番新しい観察）")
    og.add_argument("--lon", type=float, help="中心の経度")
    og.add_argument("--out", help="出力の場所（記録のフォルダーの中だけ。既定は origin/<日>/）")
    og.add_argument("--seconds", type=float, default=3.0, help="一場面の秒（既定 3）")
    og.add_argument("--fps", type=int, default=24, help="mp4 のコマ数（既定 24）")
    og.add_argument("--font", help="字幕のフォント（既定は Noto Sans CJK などを探す）")
    og.add_argument("--size", help="大きさ WxH（既定 1280x720）")

    gr = sub.add_parser(
        "grow",
        parents=[common],
        help="計画の行から、季節ごとの図を線で描く（仮説。出力はフォルダーの grow/<日>/。公開しない）",
    )
    gr.add_argument("--scenes", type=int, help="場面の数の上限（既定 6、6 まで）")
    grhow = gr.add_mutually_exclusive_group()
    grhow.add_argument(
        "--local", action="store_true", help="この PC の claude でシナリオを書く（あれば既定）"
    )
    grhow.add_argument(
        "--claude-code", action="store_true", help="書かずに、Claude Code でシナリオを書く手順を出す"
    )
    grhow.add_argument(
        "--render", metavar="PATH", help="書いた scenario.json を検証して描くだけ（Claude Code の道の二歩目）"
    )
    grhow.add_argument(
        "--draw",
        action="store_true",
        help="grow/<日>/scenario.json の prompt から、家の機械（halo）で絵にする（仮説の印を焼く）。"
        "halo の門（口 11445）には credentials.toml の draw_token（か SEED_DRAW_TOKEN）を Bearer で送る",
    )
    gr.add_argument("--model", help="--local のモデル（無ければ claude の既定）")
    gr.add_argument("--day", help="--draw の日 YYYY-MM-DD（既定は grow/ の一番新しい日）")
    gr.add_argument(
        "--server",
        help="--draw の server（既定は環境変数 SEED_DRAW_URL、seed.toml の [grow] server。口が無ければ 11445）",
    )
    gr.add_argument(
        "--photo",
        action="append",
        default=[],
        metavar="PATH",
        help="--draw の参照に渡す本人の写真（3 枚まで。EXIF を落として送る）",
    )
    gr.add_argument("--size", help="--draw の絵の大きさ WxH（既定 1280x720）")

    lt = sub.add_parser("lot", parents=[common], help="種のロット lots.md（場所と年で種を区別する）")
    ltsub = lt.add_subparsers(dest="act", required=True)
    la = ltsub.add_parser("add", parents=[common], help="ロットを一行足す")
    la.add_argument("--lot", required=True, help="ロットの名（[a-z0-9-]+。例 2026-aoi-kabocha）")
    la.add_argument("--crop", required=True, help="作物（本人の言葉）")
    la.add_argument("--variety", required=True, help="品種や在来の名（本人の言葉。写真で当てない）")
    la.add_argument("--place", required=True, help="採った場所（本人の言葉。公開しない）")
    la.add_argument("--year", required=True, help="採った年（4 桁）")
    la.add_argument("--from", dest="from_", help="親のロット。買った種なら 'bought（店の名）'")
    la.add_argument("--note")
    ltsub.add_parser("list", parents=[common], help="ロットの一覧").set_defaults(readonly=True)

    lg_ = sub.add_parser(
        "ledger", parents=[common], help="帳簿 ledger.md（売る、掛かる、手伝う）。税の計算はしない"
    )
    lgsub = lg_.add_subparsers(dest="act", required=True)
    lga = lgsub.add_parser("add", parents=[common], help="一件足す")
    lga.add_argument("--date", required=True, help="YYYY-MM-DD")
    lga.add_argument("--kind", required=True, choices=("sale", "cost", "help", "other"))
    lga.add_argument("--yen", required=True, type=int, help="円（整数。cost は負で記録する）")
    lga.add_argument("--what", required=True, help="何（本人の言葉）")
    lga.add_argument("--lot", help="ロットの名")
    lga.add_argument("--to", help="相手（呼び名）")
    lgs = lgsub.add_parser("sum", parents=[common], help="月の、種類ごとの合計と差引")
    lgs.add_argument("--month", required=True, help="YYYY-MM")
    lgs.set_defaults(readonly=True)
    lgi = lgsub.add_parser(
        "invoice", parents=[common], help="請求書の下書き ledger/invoice-<日>-<相手>.md（税の計算はしない）"
    )
    lgi.add_argument("--to", required=True, help="相手（ledger.md の to: と同じ言葉）")
    lgi.add_argument("--month", required=True, help="YYYY-MM")

    we = sub.add_parser(
        "weather", parents=[common], help="気象の記録 weather/<YYYY-MM>.md（Open-Meteo の過去データ）"
    )
    wesub = we.add_subparsers(dest="act", required=True)
    wf = wesub.add_parser(
        "fetch", parents=[common], help="日ごとの気象を取って足す（網に繋ぐ。座標は小数 2 桁に丸めて送る）"
    )
    wf.add_argument("--from", dest="from_", required=True, help="YYYY-MM-DD")
    wf.add_argument("--to", required=True, help="YYYY-MM-DD")
    wf.add_argument(
        "--lat", type=float, help="緯度（無ければ place.md の center か、座標のある一番新しい観察）"
    )
    wf.add_argument("--lon", type=float, help="経度")
    ws = wesub.add_parser("show", parents=[common], help="月の気象の記録を見る")
    ws.add_argument("--month", required=True, help="YYYY-MM")
    ws.set_defaults(readonly=True)

    pc = sub.add_parser(
        "procedure",
        parents=[common],
        help="手続きの下書き procedures/<slug>/（判定ではない。窓口で確かめる）",
    )
    pc.add_argument("slug", choices=("nochi-3jo",), help="nochi-3jo（農地法 3 条）")

    fd = sub.add_parser(
        "field", parents=[common], help="プロジェクトの中の畑 fields/<名>/（畑ごとに記録を分ける）"
    )
    fdsub = fd.add_subparsers(dest="act", required=True)
    fdn = fdsub.add_parser(
        "new", parents=[common], help="畑 fields/<名>/ を作る（記録の中身だけ。手引きは根に一つ）"
    )
    fdn.add_argument("name", metavar="NAME", help="畑の名")
    fdsub.add_parser("list", parents=[common], help="このプロジェクトの畑（今の畑に *）")
    fdu = fdsub.add_parser(
        "use", parents=[common], help="今の畑（seed.toml の field）を変える。all でプロジェクト全体"
    )
    fdu.add_argument("name", metavar="NAME", help="畑の名か all")
    fda = fdsub.add_parser("add", parents=[common], help="seed project add の前の名")
    fda.add_argument("name", metavar="NAME", help="プロジェクトの名")
    fda.add_argument("path", metavar="FOLDER", help="そのプロジェクトのフォルダー")

    pj = sub.add_parser("project", parents=[common], help="プロジェクトの一覧 ~/.config/seed/fields.toml")
    pjsub = pj.add_subparsers(dest="act", required=True)
    pja = pjsub.add_parser(
        "add", parents=[common], help="プロジェクトを一覧に足す（同じ名ならフォルダーを書き換える）"
    )
    pja.add_argument("name", metavar="NAME", help="プロジェクトの名")
    pja.add_argument("path", metavar="FOLDER", help="そのプロジェクトのフォルダー")
    pjsub.add_parser("list", parents=[common], help="プロジェクトの一覧（今の物に *）")
    pju = pjsub.add_parser("use", parents=[common], help="今のプロジェクト（current）を変える")
    pju.add_argument("name", metavar="NAME", help="プロジェクトの名")

    sub.add_parser("skill-path", parents=[common], help="手引き skill/ の道を出す")

    hm = sub.add_parser(
        "home",
        parents=[common],
        help="家の網にサーバーを立てる（スマートフォン → この PC のプロジェクトフォルダー、一方通行）",
    )
    hm.add_argument("--host", default="0.0.0.0", help="待つ番地（既定 0.0.0.0）")
    hm.add_argument("--port", type=int, default=HOME_PORT, help=f"待つ口（既定 {HOME_PORT}）")
    return p


COMMANDS = {
    "init": cmd_init,
    "observe": cmd_observe,
    "mark": cmd_mark,
    "marks": cmd_marks,
    "say": cmd_say,
    "plan": cmd_plan,
    "identify": cmd_identify,
    "publish": cmd_publish,
    "app": cmd_app,
    "photos": cmd_photos,
    "skill-path": cmd_skill_path,
    "keep": cmd_keep,
    "invite": cmd_invite,
    "token": cmd_token,
    "prune": cmd_prune,
    "origin": cmd_origin,
    "grow": cmd_grow,
    "lot": cmd_lot,
    "ledger": cmd_ledger,
    "weather": cmd_weather,
    "procedure": cmd_procedure,
    "field": cmd_field,
    "project": cmd_project,
    "home": cmd_home,
}
# プロジェクト全体（畑が幾つも）では使えない命令。記録は畑ごとに在る
FIELD_ONLY = frozenset(
    {
        "observe", "identify", "mark", "marks", "say", "plan", "publish", "photos", "prune",
        "origin", "grow", "lot", "ledger", "weather", "procedure",
    }
)  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command in ("field", "project"):
        return COMMANDS[args.command](None, args)
    try:
        args.folder, pick = fields_mod.locate(getattr(args, "field", None), getattr(args, "folder", None))
    except fields_mod.UnknownField as e:
        _err(s("project_unknown", lang.default_language(None), name=e.name, path=fields_mod.fields_path()))
        return 1
    if args.command == "app":
        if pick is not None:  # プロジェクトの畑を指した: アプリはその畑で開く
            base = Path(args.folder).expanduser() if args.folder else settings_mod.default_folder()
            args.folder = str(base / settings_mod.FIELDS_DIR / pick)
        return cmd_app(None, args)
    readonly = getattr(args, "list", False) or getattr(args, "readonly", False)
    quiet = args.command in ("skill-path", "marks", "origin", "grow") or readonly
    st = settings_mod.load(args.folder, create=not quiet)  # quiet は何も作らない
    st.pick = pick
    if args.command in FIELD_ONLY and st.whole:
        _err(s("field_need", st.language, names=", ".join(st.field_names)))
        return 1
    if quiet:
        return COMMANDS[args.command](st, args)
    st.override_url = getattr(args, "server_url", None)
    try:
        return COMMANDS[args.command](st, args)
    except ModuleNotFoundError as e:
        if e.name not in APP_MODULES:
            raise
        _err(s("need_app", st.language, module=e.name))
        return 1


if __name__ == "__main__":
    sys.exit(main())
