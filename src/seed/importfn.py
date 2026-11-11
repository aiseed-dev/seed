# SPDX-License-Identifier: AGPL-3.0-or-later
"""fieldnotes の農場のフォルダーを、一度だけ seed の形にする（記録の形 §23。11-11 に一本化）。

元のフォルダーは読むだけで変えない。移す先はプロジェクトの fields/<畑の名>/。本人の判定と理由はそのまま移す。
決まった形に当てられない物（documents/、_compare/、surroundings/ の絵、lookup/*.json）は、捨てずに
プロジェクトの notes/fieldnotes/ に写す。網には出ない（照会も気象も引き直さない）。
"""

from __future__ import annotations

import datetime as dt
import filecmp
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import lookup as lookup_mod
from . import records as R
from . import walk

SKIP_DIRS = {"lookup", "surroundings", "documents", "weather"}  # records/ の下で、畑ではない物
CHANGE_KEYS = ("leaf_colour", "weed_height", "soil", "animal", "other")  # 前の観察からの変化 → change
SITE_LINE_RE = re.compile(
    r"^- `(?P<status>data|record|hypothesis|supported|refuted|reference)` (?P<text>.+)$"
)
VOICE_NOTE_RE = re.compile(r"^(?P<hm>\d{2}:\d{2}) (?P<text>.+?) \((?P<file>[^()]+)\)$")
PHOTO_RE = re.compile(r"^(?P<hms>\d{6})-(?P<name>.+)\.(?P<ext>jpe?g|png|heic)$", re.IGNORECASE)
VOICE_RE = re.compile(r"^(?P<hms>\d{6})-voice\.(?P<ext>\w+)$")
OVERLAY_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-overlay-(?P<n>\d+)\.jpg$")
DATE_IN_TEXT_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# site.md と lookup.md の見出し → data 行の key
SECTION_KEY = {
    "Location": "place_name",
    "Place": "place_name",
    "Parcel": "parcel",
    "Terrain": "landform",
    "Terrain and water": "water",
    "Geology": "geology",
    "Geology and soil": "geology",
    "Soil": "soil",
    "Faults and hazards": "hazard",
    "Surroundings": "surroundings",
    "History": "history",
    "History of the land": "history",
    "History and places nearby": "history",
    "Farming": "farming",
}
SITE_SOURCE = "fieldnotes の site.md"
LAST_SITE_HEADING = "How a hypothesis is checked"  # これより後は site.md の説明で、記録ではない


@dataclass
class Report:
    fields: list[str] = field(default_factory=list)
    observations: int = 0
    photos: int = 0
    voices: int = 0
    hypotheses: int = 0
    merged: int = 0  # 足りない物を足した、移す先に在った観察
    photos_there: int = 0  # 移す先に既に在って写さなかった写真
    kept: list[str] = field(default_factory=list)  # notes/fieldnotes/ に写した物


def is_farm(path: Path) -> bool:
    return (Path(path) / "records").is_dir()


def field_names(src: Path) -> list[str]:
    names = set()
    rec = src / "records"
    for d in rec.iterdir() if rec.is_dir() else []:
        if d.is_dir() and not d.name.startswith(("_", ".")) and d.name not in SKIP_DIRS:
            names.add(d.name)
    ph = src / "photos"
    for d in ph.iterdir() if ph.is_dir() else []:
        if d.is_dir() and not d.name.startswith(("_", ".")):
            names.add(d.name)
    return sorted(names)


# ---------------------------------------------------------------- site.md、lookup.md、surroundings.md


def _split_source(text: str) -> tuple[str, str, str | None]:
    """'<主張> — <出典>; <日>' → (主張, 出典, 日)。出典が無ければ ('…', '', None)。"""
    claim, sep, tail = text.rpartition(" — ")
    if not sep:
        return text.strip(), "", None
    day = DATE_IN_TEXT_RE.search(tail)
    return claim.strip().rstrip("。.").strip(), tail.strip().rstrip("."), day[1] if day else None


def _data_line(key: str, text: str, day: str) -> R.Line:
    claim, src, when = _split_source(text)
    src = re.sub(r",?\s*https?://\S+", "", src).strip() or SITE_SOURCE
    return R.Line(key, f"{claim}（出典: {src}、確認日 {when or day}）")


@dataclass
class Site:
    data: list[R.Line] = field(default_factory=list)
    record: list[R.Line] = field(default_factory=list)
    # (h の番号か None, 文, 判定, 理由)。番号は fieldnotes の check.py と同じ: site.md の `hypothesis` の行の順
    hypotheses: list[tuple[int | None, str, str | None, str | None]] = field(default_factory=list)
    center: tuple[float, float] | None = None


def read_site(src: Path, language: str, today: str) -> Site:
    out = Site()
    rec = src / "records"
    site = rec / "site.md"
    if site.exists():
        front, body = R.split_front(site.read_text(encoding="utf-8"))
        if front.get("lat") is not None and front.get("lon") is not None:
            out.center = (float(front["lat"]), float(front["lon"]))
        day = str(front.get("checked") or today)
        n = 0
        for title, block in R.split_sections(body):
            if title.strip() == LAST_SITE_HEADING:
                break
            key = SECTION_KEY.get(title.strip(), "note")
            for raw in block.splitlines():
                m = SITE_LINE_RE.match(raw.strip())
                if not m:
                    continue
                status, text = m["status"], m["text"].strip()
                if status in ("data", "reference"):
                    out.data.append(_data_line(key, text, day))
                elif status == "record":
                    claim, who, when = _split_source(text)
                    out.record.append(
                        R.Line("note", f"{claim}（{who or 'the farmer'}{'、' + when if when else ''}）")
                    )
                elif status == "hypothesis":
                    numbered = not text.startswith("—")  # check.py の HYPOTHESIS と同じ
                    n += numbered
                    out.hypotheses.append((n if numbered else None, text, None, None))
                elif status == "supported":
                    out.hypotheses.append((None, text, "right", None))
                else:  # refuted: "<主張>" — <誰の>; <何で違ったか>
                    claim, _, why = text.partition(" — ")
                    out.hypotheses.append((None, claim.strip().strip('"'), "wrong", why.strip() or None))
    looked = rec / "lookup.md"
    if looked.exists():
        front, body = R.split_front(looked.read_text(encoding="utf-8"))
        day = str(front.get("fetched") or today)
        for title, block in R.split_sections(body):
            key = SECTION_KEY.get(title.strip(), "note")
            for raw in block.splitlines():
                raw = raw.strip()
                if raw.startswith("- `hypothesis` "):
                    out.hypotheses.append((None, raw[len("- `hypothesis` ") :], None, None))
                    continue
                k = "elevation" if key == "landform" and "Elevation" in raw else key
                line = lookup_mod.to_line(k, raw, "fieldnotes の lookup.md", day, language)
                if line:
                    out.data.append(line)
    sur = rec / "surroundings.md"
    if sur.exists():
        for raw in sur.read_text(encoding="utf-8").splitlines():
            m = SITE_LINE_RE.match(raw.strip())
            if m and m["status"] == "hypothesis":
                out.hypotheses.append((None, m["text"].strip(), None, None))
            else:
                line = R.Line.parse(raw.strip())
                if line and line.confidence is not None:  # AI が地図から読んだ行（確からしさ付き）
                    out.hypotheses.append(
                        (None, f"{line.key}: {line.text} [{line.confidence:.2f}]", None, None)
                    )
    return out


def write_place(folder: R.Folder, site: Site) -> None:
    data, record = folder._place_sections()
    have = {l.render() for l in data + record}
    data = data + [l for l in site.data if l.render() not in have]
    if site.center and not any(l.key == "center" for l in record + data):
        lat, lon = site.center
        record = [R.Line("center", f"{lat}, {lon}（{SITE_SOURCE}）"), *record]
    record = record + [l for l in site.record if l.render() not in have]
    folder.place.write_text(
        R.render_section(R.H_DATA, data) + "\n" + R.render_section(R.H_RECORD, record), encoding="utf-8"
    )


def _hyp_line(key: str, text: str, verdict: str | None, reason: str | None) -> R.Line:
    m = re.search(r"\s*\[(\d(?:\.\d{1,2})?)\]$", text)
    conf = float(m[1]) if m else None
    body = text[: m.start()] if m else text
    return R.Line(key, body.strip(), conf, verdict, reason)


def write_hypotheses(folder: R.Folder, site: Site, expect: Path | None, language: str) -> int:
    path = folder.root / "hypotheses.md"
    h = R.Hypotheses.read(path)
    if not path.exists():
        h.language = language
    have = {l.text for l in h.lines}
    n = 0
    # 番号の付いた物（観察の ## Checks の h<n> が指す物）を先に、その番号のまま。残りはその後の番号
    for num, text, verdict, reason in sorted(site.hypotheses, key=lambda x: x[0] is None):
        line = _hyp_line(f"h{num}" if num else h.next_key(), text, verdict, reason)
        if line.text in have:
            continue
        if any(l.key == line.key for l in h.lines):  # 前に取り込んだ物と番号が重なる時だけ、後ろへ
            line = R.Line(h.next_key(), line.text, line.confidence, line.verdict, line.reason)
        h.lines.append(line)
        have.add(line.text)
        n += 1
    if expect and expect.exists():
        front, body = R.split_front(expect.read_text(encoding="utf-8"))
        model = None
        lines: list[R.Line] = []
        for title, block in R.split_sections(body):
            _name, arg = R.heading_arg(title)
            model = model or (arg if arg and arg != "none" else None)
            lines += [l for l in R.parse_lines(block) if R.CHECK_KEY_RE.match(l.key)]
        if lines and not h.expect:
            h.set_expect(lines, str(front.get("model") or model or "none"))
    h.lines.sort(key=lambda l: int(l.key[1:]) if R.CHECK_KEY_RE.match(l.key) else 0)
    h.write(path)
    return n


# ---------------------------------------------------------------- 一日の観察


def _index(day_dir: Path) -> dict[str, dict]:
    p = day_dir / "index.json"
    if not p.exists():
        return {}
    try:
        return {e["file"]: e for e in json.loads(p.read_text(encoding="utf-8")) if isinstance(e, dict)}
    except (ValueError, KeyError, TypeError):
        return {}


def _nth_name(hms: str, n: int, ext: str, suffix: str = "") -> str:
    """同じ時刻の n 番目の名。1 番目は <HHMMSS><suffix>.<ext>、後は -2、-3…。"""
    return f"{hms}{suffix}.{ext}" if n == 1 else f"{hms}{suffix}-{n}.{ext}"


@dataclass
class DayPhotos:
    moved: dict[str, str] = field(default_factory=dict)  # {元の名: 移す先の道}
    points: list[dict] = field(default_factory=list)  # 座標の入った index の項目
    photos: int = 0  # 新しく写した写真
    voices: int = 0  # 新しく写した録音
    already: int = 0  # 移す先に既に在って写さなかった写真


def _copy_day_photos(src_day: Path, folder: R.Folder, day: str) -> DayPhotos:
    """写真と録音を写す。同じ時刻の n 枚目は移す先の n 番目の名に当て、その名が既にあれば写さない（中身では比べない）。"""
    dest = folder.photos / day
    dest.mkdir(parents=True, exist_ok=True)
    out = DayPhotos()
    seen: dict[tuple[str, str], int] = {}  # (photo か voice, 時刻) → 何番目まで見たか
    for p in sorted(src_day.iterdir()):
        m = PHOTO_RE.match(p.name)
        v = VOICE_RE.match(p.name)
        if v:
            kind, hms, ext, suffix = "voice", v["hms"], v["ext"].lower(), "-voice"
        elif m:
            ext = "jpg" if m["ext"].lower() in ("jpg", "jpeg") else m["ext"].lower()
            kind, hms, suffix = "photo", m["hms"], ""
        else:
            continue
        n = seen[(kind, hms)] = seen.get((kind, hms), 0) + 1
        to = dest / _nth_name(hms, n, ext, suffix)
        if to.exists():
            out.already += kind == "photo"
        else:
            shutil.copy2(p, to)
            out.photos += kind == "photo"
            out.voices += kind == "voice"
        out.moved[p.name] = f"photos/{day}/{to.name}"
    idx = _index(src_day)
    out.points = [idx[k] for k in out.moved if k in idx]
    return out


def _location(points: list[dict]) -> dict | None:
    from .photos import PhotoInfo, location

    infos = [
        PhotoInfo(float(e["lat"]), float(e["lon"]), None)
        for e in points
        if e.get("lat") is not None and e.get("lon") is not None
    ]
    return location(infos) if infos else None


def _language_of(arg: str | None, lines: list[R.Line], fallback: str) -> str:
    if arg and "," in arg:
        lg = arg.split(",")[-1].strip()
        if re.fullmatch(r"[a-z]{2,3}(-[A-Za-z]+)?", lg):
            return lg
    if any(re.search(r"[぀-ヿ一-鿿]", l.text) for l in lines):
        return "ja"
    return fallback


def convert_day(text: str, photos: dict[str, str], location: dict | None, language: str) -> R.Observation:
    """fieldnotes の records/<field>/<date>.md の文 → seed の観察。photos は {元の道: 新しい道}。"""
    front, body = R.split_front(text)
    day = str(front.get("date"))
    old_photos = [str(p) for p in front.get("photos") or []]
    new_photos = [photos.get(Path(p).name, p) for p in old_photos] or sorted(photos.values())
    new_photos = [p for p in new_photos if not Path(p).stem.endswith("-voice")]
    first = next((Path(p).name for p in old_photos if PHOTO_RE.match(Path(p).name)), None)
    hms = PHOTO_RE.match(first)["hms"] if first else "000000"
    obs = R.Observation(
        date=day,
        time=f"{hms[:2]}:{hms[2:4]}:{hms[4:]}",
        photos=new_photos,
        location=location,
        coverage={str(k): float(v) for k, v in (front.get("coverage") or {}).items()},
        cover_range={str(k): [float(x) for x in v] for k, v in (front.get("cover_range") or {}).items()},
    )
    if obs.coverage:
        obs.cover_model = "sam-3.1"
    lines_all: list[R.Line] = []
    note_arg = None
    for title, block in R.split_sections(body):
        name, arg = R.heading_arg(title)
        lines, rest = R.split_block(block)
        lines_all += lines
        if name == "AI observation":
            obs.model = arg if arg and arg != "none" else obs.model
            obs.reading += [_reading_line(l) for l in lines]
        elif name == "Earlier AI lines":
            obs.earlier += [_reading_line(l) for l in lines]
        elif name == "Checks":
            obs.checks += lines
            obs.checks_model = arg if arg and arg != "none" else obs.checks_model
        elif name == "From the farmer's voice":
            via = f"（声から: {arg}）" if arg and arg != "none" else ""
            for l in lines:
                key = {"work": "did", "seen": "saw"}.get(l.key, "note")
                obs.record.append(R.Line(key, f"{l.text}{via}"))
        elif name == "Farmer note":
            note_arg = arg
            for para in (rest or "").splitlines():
                para = para.strip()
                if not para or para == R.EMPTY:
                    continue
                m = VOICE_NOTE_RE.match(para)
                if m:
                    voice = photos.get(m["file"], m["file"])
                    obs.record.append(
                        R.Line("said", f"{m['hm']} {m['text']}（書き取り、{Path(voice).name}）")
                    )
                else:
                    obs.record.append(R.Line("note", para))
            obs.record += [R.Line(l.key if l.key in R.RECORD_KEYS else "note", l.text) for l in lines]
        else:
            obs.kept_sections.append((title, block))
    obs.language = _language_of(note_arg, lines_all, language)
    return obs


def _reading_line(l: R.Line) -> R.Line:
    if l.key in CHANGE_KEYS:
        return R.Line("change", f"{l.key}: {l.text}", l.confidence, l.verdict, l.reason)
    return l


def _earlier_note(obs: R.Observation, language: str) -> str:
    """在る観察の Earlier reading に置く、行でない一文。"""
    model = obs.model or "none"
    if language == "ja":
        return f"fieldnotes の読み（{model}、{obs.date} の一日分）"
    return f"The fieldnotes reading ({model}, for the day {obs.date})"


def merge_into(have: R.Observation, old: R.Observation, overlays: list[Path], sam: Path) -> tuple[bool, bool]:
    """在る観察 have に、古い一日の old から足りない物だけを足す（記録の形 §23）。(足した物があるか, 入れられない物があるか)。

    have の photos、location、## Reading、model は変えない。書き戻すのは呼ぶ側。
    """
    added = left = False
    known = have.reading + have.earlier
    new = [l for l in old.reading + old.earlier if not any(l.same_statement(k) for k in known)]
    if new:
        have.earlier = have.earlier + new
        note = _earlier_note(old, have.language)
        text = have.kept_text.get(R.H_EARLIER, "")
        if note not in text:
            have.kept_text[R.H_EARLIER] = R.join_text(text, note)
        added = True
    if old.checks:
        if not have.checks:
            have.checks, have.checks_model = list(old.checks), old.checks_model
            added = True
        elif not all(any(l.same_statement(h) for h in have.checks) for l in old.checks):
            left = True
    if old.coverage:
        if not have.coverage:
            have.coverage, have.cover_range = dict(old.coverage), dict(old.cover_range)
            have.cover_model = old.cover_model
            added = True
        elif have.coverage != old.coverage:
            left = True
    for o in overlays:
        to = sam / f"{OVERLAY_RE.match(o.name)['n']}.jpg"
        if not to.exists():
            sam.mkdir(parents=True, exist_ok=True)
            shutil.copy2(o, to)
            added = True
        elif not filecmp.cmp(o, to, shallow=False):  # 前に写した同じ絵なら、入っている
            left = True
    rec = {(l.key, l.text) for l in have.record}
    more = [l for l in old.record if (l.key, l.text) not in rec]
    if more:
        have.record = have.record + more
        added = True
    return added, left


# ---------------------------------------------------------------- 提案、名詞、草の読み


PROPOSAL_KEYS = {
    "cut": {"summary": "cut", "where": "cut", "height": "cut", "leave": "cut", "method": "cut",
            "basis": "basis", "watch": "next_to_observe", "caution": "uncertain"},
    "cover_crop": {"summary": "cover", "mix": "mix", "sowing": "sow", "watch": "next_to_observe",
                   "caution": "uncertain"},
}  # fmt: skip


def merge_proposals(folder: R.Folder, paths: list[Path], language: str) -> None:
    if not paths:
        return
    plan = R.Plan.read(folder.plan) if folder.plan.exists() else None
    for path in sorted(paths):
        front, body = R.split_front(path.read_text(encoding="utf-8"))
        kind = str(front.get("kind") or path.stem.split("-")[-1])
        keys = PROPOSAL_KEYS.get(kind, {})
        lines: list[R.Line] = []
        model = front.get("model")
        for title, block in R.split_sections(body):
            _name, arg = R.heading_arg(title)
            model = model or arg
            for l in R.parse_lines(block):
                lines.append(R.Line(keys.get(l.key, "basis"), l.text, l.confidence, l.verdict, l.reason))
        if plan is None:
            plan = R.Plan.new(language, today=str(front.get("date") or dt.date.today()))
        have = {(l.key, l.text) for l in plan.reading}
        plan.reading = R.sort_reading(
            plan.reading + [l for l in lines if (l.key, l.text) not in have], R.PLAN_KEYS
        )
        plan.model = plan.model or (str(model) if model else None)
    if plan is not None:
        plan.write(folder.plan)


def _parcel(rec: Path) -> dict | None:
    """lookup/parcel_jp.json の筆の形（GeoJSON の geometry）。無ければ None。"""
    p = rec / "lookup" / "parcel_jp.json"
    try:
        hit = json.loads(p.read_text(encoding="utf-8")).get("parcel") if p.exists() else None
    except ValueError:
        return None
    return hit.get("geometry") if isinstance(hit, dict) and isinstance(hit.get("geometry"), dict) else None


def _copy_tree(src: Path, dest: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    elif src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _differs(src: Path, dest: Path) -> bool:
    """dest に、src と同じ名で中身の違う物が一つでも在るか。"""
    if not dest.exists():
        return False
    if src.is_file():
        return dest.is_file() and dest.read_bytes() != src.read_bytes()
    for p in src.rglob("*"):
        q = dest / p.relative_to(src)
        if p.is_file() and q.is_file() and q.read_bytes() != p.read_bytes():
            return True
    return False


# ---------------------------------------------------------------- 全体


def import_farm(
    src: Path, folders: dict[str, R.Folder], language: str = "en", today: str | None = None
) -> Report:
    """src（fieldnotes の農場のフォルダー）を、畑の名 → Folder（init 済み）へ移す。"""
    src = Path(src).expanduser()
    today = today or dt.date.today().isoformat()
    rec = src / "records"
    rep = Report(fields=sorted(folders))
    site = read_site(src, language, today)
    parcel = _parcel(rec)
    for name, folder in folders.items():
        write_place(folder, site)
        if parcel and not (folder.root / walk.PARCEL_FILE).exists():
            walk.save_parcel(folder.root, parcel)
        rep.hypotheses += write_hypotheses(folder, site, rec / "_checks" / name / "expect.md", language)
        # 写真と一日の観察
        days = set()
        ph = src / "photos" / name
        days |= (
            {d.name for d in ph.iterdir() if d.is_dir() and R.DATE_RE.match(d.name)} if ph.is_dir() else set()
        )
        rd = rec / name
        days |= {p.stem for p in rd.glob("*.md") if R.DATE_RE.match(p.stem)} if rd.is_dir() else set()
        for day in sorted(days):
            got = _copy_day_photos(ph / day, folder, day) if (ph / day).is_dir() else DayPhotos()
            rep.photos += got.photos
            rep.voices += got.voices
            rep.photos_there += got.already
            day_md = rd / f"{day}.md"
            if not day_md.exists():
                continue
            obs = convert_day(day_md.read_text(encoding="utf-8"), got.moved, _location(got.points), language)
            target = folder.observation_path(obs)
            overlays = sorted(rd.glob(f"{day}-overlay-*.jpg"))
            sam = folder.observations / (Path(obs.filename).stem + ".sam")
            if target.exists():  # 在る観察は書き換えず、足りない物だけ足す。本人が seed で付けた物を消さない
                have = R.Observation.read(target)
                added, left = merge_into(have, obs, overlays, sam)
                if added:
                    have.write(target)
                    rep.merged += 1
                if left:  # 入れられない物がある日は、元の一日をそのまま残す
                    kept = (folder.project or folder.root) / "notes" / "fieldnotes" / "records" / name
                    kept.mkdir(parents=True, exist_ok=True)
                    for p in [day_md, *overlays]:
                        shutil.copy2(p, kept / p.name)
                    if f"records/{name}" not in rep.kept:
                        rep.kept.append(f"records/{name}")
                continue
            folder.observations.mkdir(parents=True, exist_ok=True)
            obs.write(target)
            rep.observations += 1
            if overlays:
                sam.mkdir(exist_ok=True)
                for o in overlays:
                    shutil.copy2(o, sam / f"{OVERLAY_RE.match(o.name)['n']}.jpg")
        # 名詞、草の読み、提案
        _copy_tree(rec / "_concepts" / f"{name}.md", folder.root / "concepts.md")
        if (rec / "_plants").is_dir():
            _copy_tree(rec / "_plants", folder.root / "plants")
        merge_proposals(folder, list((rec / "_proposals" / name).glob("*.md")), language)
    # 当てられない物は捨てずに写す。農場全体の物なので、プロジェクトの根に一度だけ
    first = next(iter(folders.values()), None)
    if first is not None:
        kept = (first.project or first.root) / "notes" / "fieldnotes"
        parts = [(rec / p, p) for p in ("documents", "_compare", "surroundings", "lookup")]
        parts.append((src / "photos" / "_around", "around"))
        for there, part in parts:
            if not there.exists() or (part == "around" and not there.is_dir()):
                continue
            # 別の農場の同じ名で中身の違う物が在れば、上書きせず農場の名の下へ
            to = part if not _differs(there, kept / part) else f"{src.resolve().name}/{part}"
            _copy_tree(there, kept / to)
            rep.kept.append(to)
    return rep
