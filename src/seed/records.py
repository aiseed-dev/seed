# SPDX-License-Identifier: AGPL-3.0-or-later
"""記録の読み書き。仕様は docs/記録の形.md で、コードはそれに合わせる。

一行の文法は fieldnotes-farm（同じ作者の別の包み。照会だけに使い、PyPI の 0.2.0 に固定）と仕様で揃えてあり
（fieldnotes の docs/records.md）、コードは共有しない。
ここにあるのは、行（Line）、一回の観察（Observation）、栽培計画（Plan）、判定の付いた行（Mark）、
公開ファイル（Public）、本人のフォルダー（Folder）の読み書きだけ。ネットも AI も呼ばない。
"""

from __future__ import annotations

import datetime as dt
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ---------------------------------------------------------------- 行

# docs/記録の形.md §2 の正規表現そのまま
LINE_RE = re.compile(
    r"^- (?P<key>[a-z][a-z0-9_]*): (?P<text>.*?)"
    r"(?:\s+→ farmer: (?P<verdict>right|wrong)(?: \((?P<reason>.*)\))?)?$"
)
CONFIDENCE_RE = re.compile(r"\s*\[(?P<c>\d(?:\.\d{1,2})?)\]$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
VERDICTS = ("right", "wrong")
EMPTY = "(none)"

# 判定の行は書かない（§3）。見つけたら uncertain に落とす。日本語と英語の形
DIRECTIVE_RE = re.compile(
    r"(べき|しなさい|なさい|してください|して下さい|しましょう|せよ|必要があります"
    r"|\b(?:you )?(?:should|must|need to|have to|ought to)\b)",
    re.IGNORECASE,
)

# 読みのキーと順（§3）
READING_KEYS = (
    "overall",
    "soil_surface",
    "plants",
    "crops",
    "water",
    "access",  # 道、通える距離。候補地で特に
    "sun_slope",  # 日当たり、傾斜
    "surroundings",  # 周りの畑、獣の痕
    "change",  # 同じ場所の前の観察からの変化。前の観察が渡されたときだけ
    "basis",
    "uncertain",
    "next_to_observe",
)
RECORD_KEYS = ("did", "saw", "said", "note", "ask")  # ask は本人が知りたいこと（自由な言葉）
# 本人が知りたいこと（前書きの ask）。典型の物を選べる。語は英語のまま、表示と依頼の文は ASK_WORDS
ASKS = ("grow", "soil", "plants", "history", "access", "sow", "next", "names")
ASK_WORDS = {
    "ja": {
        "grow": "この土地で何が育つか",
        "soil": "土と地質と水はけ",
        "plants": "草から今の土を読む",
        "history": "この土地の歴史と地名の由来",
        "access": "借りられるか、買えるか、手続き",
        "sow": "今の時期に何を播くか",
        "next": "売る、加工の候補",
        "names": "写真に写っている植物の名前",
    },
    "en": {
        "grow": "What can grow on this land",
        "soil": "Soil, geology and drainage",
        "plants": "What the weeds say about the soil now",
        "history": "The history of this land and the origin of its place names",
        "access": "Whether it can be rented or bought, and the paperwork",
        "sow": "What to sow in this season",
        "next": "What could be sold or processed",
        "names": "The names of the plants in the photos",
    },
}


def ask_word(key: str, language: str) -> str:
    """ask の語を本人の言語で。無い言語は en。知らない key はそのまま。"""
    return ASK_WORDS.get(language, {}).get(key) or ASK_WORDS["en"].get(key) or key


def parse_asks(text: str | None) -> list[str]:
    """ "grow,soil" のような文字列を ask の列に。知らない語は ValueError。"""
    out: list[str] = []
    for w in (text or "").replace(";", ",").split(","):
        w = w.strip()
        if not w:
            continue
        if w not in ASKS:
            raise ValueError(f"ask は {ASKS}: {w!r}")
        if w not in out:
            out.append(w)
    return out


# 栽培計画 plan.md の ## Plan のキーと順（記録の形 §10）。mix は混植
PLAN_KEYS = ("ground", "sow", "host", "mix", "cover", "no_input", "basis", "uncertain", "next_to_observe")
PLAN_RECORD_KEYS = ("decided", "did")
H_PLAN = "Plan"


@dataclass
class Line:
    """一行。confidence が付いていれば AI の行、無ければ本人の行。"""

    key: str
    text: str
    confidence: float | None = None
    verdict: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not KEY_RE.match(self.key):
            raise ValueError(f"key は [a-z][a-z0-9_]*: {self.key!r}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence は 0〜1: {self.confidence!r}")
        if self.verdict is not None and self.verdict not in VERDICTS:
            raise ValueError(f"verdict は right か wrong: {self.verdict!r}")

    @property
    def by_ai(self) -> bool:
        return self.confidence is not None

    @property
    def judged(self) -> bool:
        return self.verdict is not None

    @property
    def directive(self) -> bool:
        """判定の行（「刈るべき」の形）か。"""
        return bool(DIRECTIVE_RE.search(self.text))

    @classmethod
    def parse(cls, s: str) -> Line | None:
        """一行を読む。行の形でなければ None。"""
        m = LINE_RE.match(s.rstrip("\n"))
        if not m:
            return None
        text = m["text"]
        conf = None
        cm = CONFIDENCE_RE.search(text)
        if cm:
            conf = float(cm["c"])
            text = text[: cm.start()]
        return cls(m["key"], text, conf, m["verdict"], m["reason"])

    def render(self) -> str:
        s = f"- {self.key}: {self.text}"
        if self.confidence is not None:
            s += f" [{self.confidence:.2f}]"
        if self.verdict:
            s += f"  → farmer: {self.verdict}"
            if self.reason:
                s += f" ({self.reason})"
        return s

    def marked(self, verdict: str, reason: str | None = None) -> Line:
        return Line(self.key, self.text, self.confidence, verdict, reason)

    def same_statement(self, other: Line) -> bool:
        """key と text が同じか。判定を引き継ぐ条件。"""
        return self.key == other.key and self.text == other.text


def parse_lines(block: str) -> list[Line]:
    """見出しの下の文から行だけを取る。行の形でない文と (なし) は読み飛ばす。"""
    out = []
    for raw in block.splitlines():
        line = Line.parse(raw)
        if line:
            out.append(line)
    return out


def render_lines(lines: list[Line]) -> str:
    return "\n".join(l.render() for l in lines) if lines else EMPTY


def demote_directives(lines: list[Line]) -> list[Line]:
    """判定の形の文を uncertain に落とす（設計書 §10）。本人の行には触らない。"""
    out = []
    for l in lines:
        if l.by_ai and l.directive and l.key != "uncertain":
            out.append(
                Line(
                    "uncertain",
                    f"（読みでなく判定の形だった: {l.key}）{l.text}",
                    l.confidence,
                    l.verdict,
                    l.reason,
                )
            )
        else:
            out.append(l)
    return out


def sort_reading(lines: list[Line], keys: tuple[str, ...] = READING_KEYS) -> list[Line]:
    """手引きの key の順に並べる（同じ key は元の順）。知らない key は後ろ。"""
    rank = {k: i for i, k in enumerate(keys)}
    return sorted(lines, key=lambda l: rank.get(l.key, len(keys)))


# ---------------------------------------------------------------- 前書きと見出し

FRONT_RE = re.compile(r"\A---\n(?P<front>.*?)\n---\n?(?P<body>.*)\Z", re.DOTALL)
HEADING_RE = re.compile(r"^## (?P<title>.+?)\s*$", re.MULTILINE)
MODEL_IN_HEADING_RE = re.compile(r"^(?P<name>.+?) \((?P<arg>[^()]+)\)$")


def _plain(v):
    """YAML の日付や入れ子を文字と素の型に。日付は 'YYYY-MM-DD' の文字で持つ。"""
    if isinstance(v, (dt.date, dt.datetime)):
        return (
            v.isoformat()
            if isinstance(v, dt.date) and not isinstance(v, dt.datetime)
            else v.isoformat(sep=" ")
        )
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_plain(x) for x in v]
    return v


def split_front(text: str) -> tuple[dict, str]:
    m = FRONT_RE.match(text)
    if not m:
        return {}, text
    front = yaml.safe_load(m["front"]) or {}
    if not isinstance(front, dict):
        raise TypeError("前書きは鍵と値の組")
    return _plain(front), m["body"]


def render_front(front: dict) -> str:
    """前書き。上の段は一行に一つの鍵（流れる形にしない）、中の列だけ [a, b] の形。"""
    text = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, default_flow_style=None).rstrip("\n")
    if text.startswith("{"):  # 鍵が全部単純な値だと一行に畳まれるので、段の形で書き直す
        text = yaml.safe_dump(front, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip(
            "\n"
        )
    return "---\n" + text + "\n---\n"


def split_sections(body: str) -> list[tuple[str, str]]:
    """'## 見出し' ごとに (見出し, 下の文) に分ける。最初の見出しより前の文は捨てる。"""
    out = []
    matches = list(HEADING_RE.finditer(body))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out.append((m["title"], body[m.end() : end].strip("\n")))
    return out


def heading_arg(title: str) -> tuple[str, str | None]:
    """'読み (claude-opus-5-5)' → ('読み', 'claude-opus-5-5')。"""
    m = MODEL_IN_HEADING_RE.match(title)
    return (m["name"], m["arg"]) if m else (title, None)


# ---------------------------------------------------------------- 一回の観察

# 見出しは英語のまま（国際対応）。表示は seed.lang が訳す
H_READING = "Reading"
H_EARLIER = "Earlier reading"
H_DATA = "Data"
H_RECORD = "Record"
NEXT_HEADINGS = ("Sell", "Process", "Host or teach", "Paperwork")
MODEL_CLAUDE_CODE = "claude-code"
KINDS = ("own", "candidate")  # 自分の畑か、候補地（自分の畑でない場所）か
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")


class JudgedLines:
    """AI の行（reading）に本人の判定を付け、置き換えても判定を残す。観察と栽培計画で同じ。

    使う側は reading, earlier, record, model を持ち、KEYS（行の順）と RECORD_KEYS（本人の行の key）を決める。
    """

    KEYS: tuple[str, ...] = READING_KEYS
    RECORD_KEYS: tuple[str, ...] = RECORD_KEYS
    reading: list[Line]
    earlier: list[Line]
    record: list[Line]
    model: str | None

    def reread(self, new_reading: list[Line], model: str) -> None:
        """もう一度読ませた結果を入れる。AI の行は置き換え、判定と本人の行は残す。

        key と text が同じ行には前の判定を引き継ぐ。判定が付いていたのに消えた（文が変わった）行は
        「前の読み」に移す。判定の形の文は uncertain に落とす。
        """
        new_reading = sort_reading(demote_directives(new_reading), self.KEYS)
        carried: list[Line] = []
        for n in new_reading:
            old = next((o for o in self.reading if o.same_statement(n)), None)
            carried.append(n if not (old and old.judged) else n.marked(old.verdict, old.reason))
        gone = [o for o in self.reading if o.judged and not any(o.same_statement(n) for n in new_reading)]
        self.earlier = self.earlier + gone
        self.reading = carried
        self.model = model

    def mark(self, key: str, verdict: str, reason: str | None = None, text: str | None = None) -> Line:
        """読みの行に本人の判定を付ける。同じ key が複数なら text で選ぶ。

        text は全文か、その行だけに含まれる一部（長い行を全部打たなくてよい）。
        """
        same_key = [l for l in self.reading if l.key == key]
        hits = [l for l in same_key if text is None or l.text == text]
        if not hits and text:
            hits = [l for l in same_key if text in l.text]
        if not hits:
            raise KeyError(f"読みに無い行: {key!r}")
        if len(hits) > 1:
            raise KeyError(f"{key!r} の行が {len(hits)} つある。text で選ぶ")
        i = self.reading.index(hits[0])
        self.reading[i] = hits[0].marked(verdict, reason)
        return self.reading[i]

    def say(self, key: str, text: str) -> Line:
        """本人の行を足す。"""
        if key not in self.RECORD_KEYS:
            raise ValueError(f"本人の行の key は {self.RECORD_KEYS}: {key!r}")
        line = Line(key, text)
        self.record.append(line)
        return line

    def unjudged(self) -> list[Line]:
        return [l for l in self.reading if not l.judged]


@dataclass
class Observation(JudgedLines):
    """observations/<date>-<time>.md 一つ。"""

    date: str
    time: str
    photos: list[str] = field(default_factory=list)
    location: dict | None = None  # {center: [lat, lon], points: n, extent_m: m}
    lookup: str | None = None
    model: str | None = None
    language: str = "en"
    kind: str = "own"
    ask: list[str] = field(default_factory=list)  # 本人が知りたいこと（ASKS の語）
    reading: list[Line] = field(default_factory=list)
    earlier: list[Line] = field(default_factory=list)
    data: list[Line] = field(default_factory=list)
    record: list[Line] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not DATE_RE.match(self.date):
            raise ValueError(f"date は YYYY-MM-DD: {self.date!r}")
        if not TIME_RE.match(self.time):
            raise ValueError(f"time は HH:MM:SS: {self.time!r}")
        if self.kind not in KINDS:
            raise ValueError(f"kind は {KINDS}: {self.kind!r}")
        bad = [a for a in self.ask if a not in ASKS]
        if bad:
            raise ValueError(f"ask は {ASKS}: {bad!r}")

    @property
    def filename(self) -> str:
        return f"{self.date}-{self.time.replace(':', '')}.md"

    # --- 読み書き
    @classmethod
    def parse(cls, text: str) -> Observation:
        front, body = split_front(text)
        obs = cls(
            date=str(front.get("date", "")),
            time=str(front.get("time", "")),
            photos=list(front.get("photos") or []),
            location=front.get("location"),
            lookup=str(front["lookup"]) if front.get("lookup") else None,
            model=front.get("model"),
            language=str(front.get("language") or "en"),
            kind=str(front.get("kind") or "own"),
            ask=[str(a) for a in (front.get("ask") or [])],
        )
        for title, block in split_sections(body):
            name, arg = heading_arg(title)
            lines = parse_lines(block)
            if name == H_READING:
                obs.reading = lines
                if arg and not obs.model:
                    obs.model = arg
            elif name == H_EARLIER:
                obs.earlier = lines
            elif name == H_DATA:
                obs.data = lines
            elif name == H_RECORD:
                obs.record = lines
            # 知らない見出しは読み飛ばす（読む側は壊れない）
        return obs

    def front(self) -> dict:
        f: dict = {"date": self.date, "time": self.time, "photos": list(self.photos)}
        if self.location:
            f["location"] = self.location
        if self.lookup:
            f["lookup"] = self.lookup
        if self.model:
            f["model"] = self.model
        f["language"] = self.language
        if self.kind != "own":
            f["kind"] = self.kind
        if self.ask:
            f["ask"] = list(self.ask)
        return f

    def render(self) -> str:
        parts = [render_front(self.front())]
        parts.append(f"## {H_READING} ({self.model or 'none'})\n{render_lines(self.reading)}\n")
        if self.earlier:
            parts.append(f"## {H_EARLIER}\n{render_lines(self.earlier)}\n")
        parts.append(f"## {H_DATA}\n{render_lines(self.data)}\n")
        parts.append(f"## {H_RECORD}\n{render_lines(self.record)}\n")
        return "\n".join(parts)

    @classmethod
    def read(cls, path: Path) -> Observation:
        return cls.parse(Path(path).read_text(encoding="utf-8"))

    def write(self, path: Path) -> None:
        Path(path).write_text(self.render(), encoding="utf-8")

    # --- 操作


# ---------------------------------------------------------------- 栽培計画 plan.md（記録の形 §10）

H_PLAN_EARLIER = "Earlier plan"


@dataclass
class Plan(JudgedLines):
    """plan.md 一つ。借りる・買うことができた畑の栽培計画。AI の行は仮説で、決めるのは本人（decided）。"""

    KEYS = PLAN_KEYS
    RECORD_KEYS = PLAN_RECORD_KEYS

    since: str
    season: str = ""
    language: str = "en"
    model: str | None = None
    reading: list[Line] = field(default_factory=list)  # ## Plan
    earlier: list[Line] = field(default_factory=list)
    data: list[Line] = field(default_factory=list)
    record: list[Line] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not DATE_RE.match(self.since):
            raise ValueError(f"since は YYYY-MM-DD: {self.since!r}")

    @classmethod
    def parse(cls, text: str) -> Plan:
        front, body = split_front(text)
        plan = cls(
            since=str(front.get("since", "")),
            season=str(front.get("season") or ""),
            language=str(front.get("language") or "en"),
            model=front.get("model"),
        )
        for title, block in split_sections(body):
            name, arg = heading_arg(title)
            lines = parse_lines(block)
            if name == H_PLAN:
                plan.reading = lines
                if arg and not plan.model:
                    plan.model = arg
            elif name == H_PLAN_EARLIER:
                plan.earlier = lines
            elif name == H_DATA:
                plan.data = lines
            elif name == H_RECORD:
                plan.record = lines
        return plan

    def front(self) -> dict:
        f: dict = {"since": self.since}
        if self.season:
            f["season"] = self.season
        f["language"] = self.language
        if self.model:
            f["model"] = self.model
        return f

    def render(self) -> str:
        parts = [render_front(self.front())]
        parts.append(f"## {H_PLAN} ({self.model or 'none'})\n{render_lines(self.reading)}\n")
        if self.earlier:
            parts.append(f"## {H_PLAN_EARLIER}\n{render_lines(self.earlier)}\n")
        parts.append(f"## {H_DATA}\n{render_lines(self.data)}\n")
        parts.append(f"## {H_RECORD}\n{render_lines(self.record)}\n")
        return "\n".join(parts)

    @classmethod
    def read(cls, path: Path) -> Plan:
        return cls.parse(Path(path).read_text(encoding="utf-8"))

    def write(self, path: Path) -> None:
        Path(path).write_text(self.render(), encoding="utf-8")

    @classmethod
    def new(cls, language: str, season: str = "", today: str | None = None) -> Plan:
        return cls(since=today or dt.date.today().isoformat(), season=season, language=language)


# ---------------------------------------------------------------- 合う／違うの付いた行（seed marks）

MARK_SOURCES = ("observation", "plan")


@dataclass
class Mark:
    """本人の判定が付いた AI の行一つと、それがどこにあったか。seed marks が集める（設計書 §5.4b の検証の環）。

    when は観察なら '2026-11-02 15:34:02'、栽培計画なら 'plan'。earlier は Earlier reading / Earlier plan にあった行
    （読み直しで置き換わった、前の読み）。
    """

    when: str
    key: str
    text: str
    verdict: str
    reason: str | None
    source: str  # MARK_SOURCES
    earlier: bool = False
    confidence: float | None = None

    @property
    def name(self) -> str:
        """seed mark / say に渡す名。観察なら '2026-11-02-153402'、栽培計画なら 'plan'。"""
        if self.source == "plan":
            return "plan"
        return self.when.replace(" ", "-").replace(":", "")

    @classmethod
    def collect(cls, doc: JudgedLines, when: str, source: str) -> list[Mark]:
        """観察か栽培計画一つから、判定の付いた行を、今の読み → 前の読みの順に。"""
        out = []
        for earlier, lines in ((False, doc.reading), (True, doc.earlier)):
            for l in lines:
                if l.judged:
                    out.append(cls(when, l.key, l.text, l.verdict, l.reason, source, earlier, l.confidence))
        return out


# ---------------------------------------------------------------- 公開ファイル

PUBLIC_KEYS = (
    "id",
    "place",
    "coord",
    "since",
    "what",
    "next",
    "name",
    "contact",
    "word",
    "photo",
    "language",
    "observations",
)
PUBLIC_REQUIRED = ("id", "place", "since", "name", "word")
ID_RE = re.compile(r"^[a-z0-9-]+$")
WORD_MAX = 200
# 個人情報の形。公開ファイルの文にあれば止める
PERSONAL_RE = re.compile(r"(\d{2,4}-\d{2,4}-\d{3,4}|[\w.+-]+@[\w-]+\.[\w.]+|〒?\d{3}-\d{4})")
HTML_RE = re.compile(r"<[a-zA-Z/!][^>]*>")


@dataclass
class Public:
    """public/<id>.md 一つ。本人が観察から選んだ行。"""

    id: str
    place: str
    since: str
    name: str
    word: str
    coord: list[float] | None = None
    what: list[str] = field(default_factory=list)
    next: list[str] = field(default_factory=list)
    contact: str | None = None
    photo: str | None = None
    language: str = "en"
    days: dict[str, list[Line]] = field(default_factory=dict)  # 観察の日 → 行

    @property
    def observations(self) -> int:
        return len(self.days)

    def check(self) -> list[str]:
        """仕様に合わない所を文で返す。空なら通る。サーバーも同じ検査をする。"""
        bad = []
        if not ID_RE.match(self.id):
            bad.append("id は [a-z0-9-]+")
        if not DATE_RE.match(self.since):
            bad.append("since は YYYY-MM-DD")
        if not self.place.strip():
            bad.append("place が無い")
        if not self.name.strip():
            bad.append("name が無い")
        if not self.word.strip():
            bad.append("word が無い")
        if len(self.word) > WORD_MAX:
            bad.append(f"word は {WORD_MAX} 字まで")
        if self.coord is not None:
            if len(self.coord) != 2:
                bad.append("coord は [lat, lon]")
            elif any(round(c, 2) != c for c in self.coord):
                bad.append("coord は小数 2 桁まで")
        for d in self.days:
            if not DATE_RE.match(d):
                bad.append(f"本文の見出しは日: {d!r}")
        text = self.render()
        if HTML_RE.search(text):
            bad.append("HTML は書かない")
        if PERSONAL_RE.search(text):
            bad.append("電話、メール、郵便番号の形の文がある")
        return bad

    @classmethod
    def parse(cls, text: str) -> Public:
        front, body = split_front(text)
        unknown = set(front) - set(PUBLIC_KEYS)
        if unknown:
            raise ValueError(f"前書きに知らない鍵: {sorted(unknown)}")
        missing = [k for k in PUBLIC_REQUIRED if k not in front]
        if missing:
            raise ValueError(f"前書きに無い鍵: {missing}")
        pub = cls(
            id=str(front["id"]),
            place=str(front["place"]),
            since=str(front["since"]),
            name=str(front["name"]),
            word=str(front["word"]),
            coord=[float(c) for c in front["coord"]] if front.get("coord") else None,
            what=[str(x) for x in front.get("what") or []],
            next=[str(x) for x in front.get("next") or []],
            contact=front.get("contact"),
            photo=front.get("photo"),
            language=str(front.get("language") or "en"),
        )
        for title, block in split_sections(body):
            pub.days[title.strip()] = parse_lines(block)
        return pub

    def front(self, for_index: bool = False) -> dict:
        f: dict = {"id": self.id, "place": self.place}
        if self.coord is not None:
            f["coord"] = self.coord
        f.update(since=self.since, what=list(self.what), next=list(self.next), name=self.name)
        if self.contact and not for_index:
            f["contact"] = self.contact
        f["word"] = self.word
        if self.photo:
            f["photo"] = self.photo
        f["language"] = self.language
        f["observations"] = self.observations
        return f

    def render(self) -> str:
        parts = [render_front(self.front())]
        for day in sorted(self.days):
            parts.append(f"## {day}\n{render_lines(self.days[day])}\n")
        return "\n".join(parts)

    @classmethod
    def read(cls, path: Path) -> Public:
        return cls.parse(Path(path).read_text(encoding="utf-8"))

    def write(self, path: Path) -> None:
        Path(path).write_text(self.render(), encoding="utf-8")

    def add(self, obs: Observation, lines: list[Line]) -> None:
        """観察から選んだ行を、その日の下に足す。"""
        self.days.setdefault(obs.date, []).extend(lines)


def coarse_coord(center: list[float]) -> list[float]:
    """公開用に小数 2 桁（約 1 km）に丸める。"""
    return [round(float(center[0]), 2), round(float(center[1]), 2)]


# 小数 3 桁以上の緯度と経度の対（例 34.123 134.456、34.1234, 134.5678、34.1234、134.5678）
FINE_COORD_RE = re.compile(
    r"(?<![\d.])(?P<lat>[-+]?\d{1,2}\.\d{3,})\s*[,，、/]?\s*(?P<lon>[-+]?\d{1,3}\.\d{3,})(?![\d.])"
)


def fine_coords(text: str) -> list[str]:
    """文の中の、小数 3 桁以上の緯度経度らしい対（緯度 ±90、経度 ±180 の中の物だけ）。公開に出さない（設計書 §5.2）。"""
    out = []
    for m in FINE_COORD_RE.finditer(text):
        if abs(float(m.group("lat"))) <= 90 and abs(float(m.group("lon"))) <= 180:
            out.append(m.group(0))
    return out


# ---------------------------------------------------------------- 繋がり

CONNECTION_RE = re.compile(r"^- (?P<date>\d{4}-\d{2}-\d{2}) (?P<src>\S+) → (?P<dst>\S+): (?P<word>.*)$")


@dataclass
class Connection:
    date: str
    src: str
    dst: str
    word: str

    def render(self) -> str:
        return f"- {self.date} {self.src} → {self.dst}: {self.word}"

    @classmethod
    def parse(cls, s: str) -> Connection | None:
        m = CONNECTION_RE.match(s.rstrip("\n"))
        return cls(m["date"], m["src"], m["dst"], m["word"]) if m else None


# ---------------------------------------------------------------- 本人のフォルダー


def _distance_m(a: list[float], b: list[float]) -> float:
    """二点の距離（m）。近い所だけなので平面で足りる。"""
    lat = math.radians((a[0] + b[0]) / 2)
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(lat)
    return math.hypot(dx, dy)


@dataclass
class Folder:
    """~/seed/。道を決めるだけで、作る・読む・書くは呼ぶ側が選ぶ。"""

    root: Path
    bulk: Path | None = (
        None  # 重い物（originals/）を置く別の盤。無ければ root の中（keep.py、seed.toml の bulk）
    )

    def __post_init__(self) -> None:
        self.root = Path(self.root).expanduser()
        if self.bulk is not None:
            self.bulk = Path(self.bulk).expanduser()

    @property
    def photos(self) -> Path:
        return self.root / "photos"

    @property
    def observations(self) -> Path:
        return self.root / "observations"

    @property
    def originals(self) -> Path:
        """写真の元（HEIC など）。keep が research のときだけ写す（keep.py）。bulk があればそちらの盤に。"""
        return (self.bulk or self.root) / "originals"

    def raw_dir(self, obs: Observation) -> Path:
        """読みの生の出力の置き場 observations/<id>.raw/。keep が research のときだけ書く。"""
        return self.observations / (Path(obs.filename).stem + ".raw")

    @property
    def place(self) -> Path:
        return self.root / "place.md"

    @property
    def next(self) -> Path:
        return self.root / "next.md"

    @property
    def plan(self) -> Path:
        """栽培計画（記録の形 §10）。借りる・買うことができた後に書く。"""
        return self.root / "plan.md"

    @property
    def public(self) -> Path:
        return self.root / "public"

    @property
    def connections(self) -> Path:
        return self.root / "connections.md"

    @property
    def settings(self) -> Path:
        return self.root / "seed.toml"

    @property
    def skill(self) -> Path:
        """手引きの写し。本人が直す物（記録の形 §9）。写すのは cli の seed init。"""
        return self.root / "skill"

    def init(self) -> None:
        for d in (self.photos, self.observations, self.public):
            d.mkdir(parents=True, exist_ok=True)
        if not self.place.exists():
            self.place.write_text(f"## {H_DATA}\n{EMPTY}\n\n## {H_RECORD}\n{EMPTY}\n", encoding="utf-8")
        if not self.next.exists():
            self.next.write_text(
                "".join(f"## {h}\n{EMPTY}\n\n" for h in NEXT_HEADINGS).rstrip("\n") + "\n", encoding="utf-8"
            )
        if not self.connections.exists():
            self.connections.write_text("", encoding="utf-8")

    def observation_path(self, obs: Observation) -> Path:
        return self.observations / obs.filename

    def list_observations(self) -> list[Path]:
        return sorted(self.observations.glob("*.md")) if self.observations.exists() else []

    def previous_observation(self, before: Observation, within_m: float = 100.0) -> Observation | None:
        """同じ場所の、直前の観察。change を書くために読みに渡す。座標が無ければ直前の観察。"""
        cands = []
        for path in self.list_observations():
            if path.name >= before.filename:
                continue
            obs = Observation.read(path)
            if (
                before.location
                and obs.location
                and _distance_m(before.location["center"], obs.location["center"]) > within_m
            ):
                continue
            cands.append(obs)
        return cands[-1] if cands else None

    def marks(self) -> list[Mark]:
        """観察（古い順）と plan.md から、本人の判定が付いた行を集める。読むだけで、何も書かない。

        一つの観察の中は ## Reading → ## Earlier reading の順、plan.md は最後に ## Plan → ## Earlier plan の順。
        """
        out: list[Mark] = []
        for path in self.list_observations():
            obs = Observation.read(path)
            out += Mark.collect(obs, f"{obs.date} {obs.time}", "observation")
        if self.plan.exists():
            out += Mark.collect(Plan.read(self.plan), "plan", "plan")
        return out

    def _place_sections(self) -> tuple[list[Line], list[Line]]:
        """place.md の (data 行, record 行)。無ければ空。"""
        data: list[Line] = []
        record: list[Line] = []
        if self.place.exists():
            for title, block in split_sections(self.place.read_text(encoding="utf-8")):
                name = heading_arg(title)[0]
                if name == H_DATA:
                    data = parse_lines(block)
                elif name == H_RECORD:
                    record = parse_lines(block)
        return data, record

    def place_data(self) -> list[Line]:
        """place.md の data 行。読みに添える。"""
        return self._place_sections()[0]

    def place_record(self) -> list[Line]:
        """place.md の record 行（場所について本人が確かめたこと）。読みに添える。"""
        return self._place_sections()[1]

    def add_place_data(self, lines: list[Line]) -> int:
        """照会の行を place.md の ## Data に足す（無い物だけ。記録の形 §4）。足した数を返す。"""
        data, record = self._place_sections()
        have = {(l.key, l.text) for l in data}
        new = [l for l in lines if (l.key, l.text) not in have]
        if not new:
            return 0
        data += new
        self.place.write_text(
            f"## {H_DATA}\n{render_lines(data)}\n\n## {H_RECORD}\n{render_lines(record)}\n", encoding="utf-8"
        )
        return len(new)

    def add_connection(self, c: Connection) -> None:
        with self.connections.open("a", encoding="utf-8") as f:
            f.write(c.render() + "\n")

    def list_connections(self) -> list[Connection]:
        if not self.connections.exists():
            return []
        return [
            c for c in map(Connection.parse, self.connections.read_text(encoding="utf-8").splitlines()) if c
        ]
