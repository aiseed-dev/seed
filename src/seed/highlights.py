# SPDX-License-Identifier: AGPL-3.0-or-later
"""読みの中の、決まった書き出しの行（今日の一枚、問い、次の一枚）と、行が名で指す写真。

行はただの文のまま（記録の形は変えない）。Claude に頼む書き出しは三つ:

- `overall` の最初の行を「今日の一枚: <写真の名>。<一言>」
- `uncertain` に一つ「問い: …」（本人しか知らない事、次に畑で確かめられる事）
- `next_to_observe` に一つ「次の一枚: …」（次に撮ると分かる事が増える物）

写真の名は、ファイルの名の幹（`photos/2026-11-02/153402.jpg` なら `153402`）。本人が選び直した今日の一枚は、
本人の行（`note: 今日の一枚: <写真の名>`）に残す。この書き出しが無い古い読みでも、下の関数は崩れずに答える。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .records import TAG_STATES, Line, Observation

LABELS = {
    "today": {"ja": "今日の一枚", "en": "Photo of the day"},
    "question": {"ja": "問い", "en": "Question"},
    "next_shot": {"ja": "次の一枚", "en": "Next photo"},
}
CHOSEN_KEY = "note"  # 本人が選び直した今日の一枚の行の key（本人の行の中で一番無理の無い物）
NAME_CHARS = "0-9A-Za-z_-"


def label(kind: str, language: str) -> str:
    return LABELS[kind].get(language) or LABELS[kind]["en"]


def stem(rel: str) -> str:
    return Path(rel).stem


def _after_label(text: str, kind: str) -> str | None:
    """書き出しが kind の物なら、その後ろの文。違えば None。"""
    for lab in LABELS[kind].values():
        m = re.match(rf"\s*{re.escape(lab)}\s*[:：]\s*(.*)\Z", text, re.DOTALL)
        if m:
            return m.group(1).strip()
    return None


def marked(line: Line) -> bool:
    """決まった書き出しの行か（画面では、別の所に出す）。"""
    return any(_after_label(line.text, k) is not None for k in LABELS)


def names_in(text: str, names: list[str]) -> list[str]:
    """文が名で指す写真の名（names の順）。173445 は 1734451 や 173445-1 の中では数えない。"""
    return [
        n
        for n in names
        if n and re.search(rf"(?<![{NAME_CHARS}]){re.escape(n)}(?![{NAME_CHARS}])", text) is not None
    ]


def photos_of(text: str, obs: Observation) -> list[str]:
    """行が指す写真（観察の前書きの相対の道）。"""
    by_name = {stem(r): r for r in obs.photos}
    return [by_name[n] for n in names_in(text, list(by_name))]


def _named_head(rest: str, names: list[str]) -> tuple[str, str] | None:
    """「<名>。<一言>」→ (名, 一言)。名が写真に無ければ None。"""
    m = re.match(rf"([{NAME_CHARS}]+)\s*[。.、,]?\s*(.*)\Z", rest, re.DOTALL)
    if m and m.group(1) in names:
        return m.group(1), m.group(2).strip()
    return None


def plain(text: str) -> str:
    """「今日の一枚: 173445。一言」→「一言」。書き出しが無ければそのまま。"""
    rest = _after_label(text, "today")
    if rest is None:
        return text
    m = re.match(rf"[{NAME_CHARS}]+\s*[。.、,]?\s*(.*)\Z", rest, re.DOTALL)
    return (m.group(1) if m else rest).strip()


def _picked(obs: Observation, names: list[str]) -> tuple[str | None, str | None]:
    """選ばれた今日の一枚の名と一言。本人の行（新しい物）→ 読みの最初の行。どちらにも無ければ (None, None)。"""
    for line in reversed(obs.record):
        rest = _after_label(line.text, "today")
        head = _named_head(rest, names) if rest is not None else None
        if head:
            return head[0], None
    if obs.reading:
        rest = _after_label(obs.reading[0].text, "today")
        head = _named_head(rest, names) if rest is not None else None
        if head:
            return head[0], head[1] or None
    return None, None


def today(obs: Observation) -> tuple[str | None, str]:
    """今日の一枚（相対の道）と、その写真についての一言。

    見る順: 本人の行（今日の一枚: 名。新しい物）→ 読みの最初の行（今日の一枚: 名。一言）→ 読みの行で
    一番多く名が出る写真 → 最初の写真。一言は、その写真の名が出る最初の行（無ければ読みの最初の行）。
    """
    by_name = {stem(r): r for r in obs.photos}
    names = list(by_name)
    reading = obs.reading
    pick, words = _picked(obs, names)
    if pick is None:
        counts = {n: sum(1 for l in reading if n in names_in(l.text, [n])) for n in names}
        best = max(counts.values(), default=0)
        if best > 0:
            pick = next(n for n in names if counts[n] == best)
    if pick is None and names:
        pick = names[0]
    if words is None and pick is not None:
        words = next((plain(l.text) for l in reading if names_in(l.text, [pick])), None)
    if words is None:
        words = plain(reading[0].text) if reading else ""
    return (by_name[pick] if pick else None), words


def chosen_line(name: str, language: str) -> Line:
    """本人が今日の一枚を選び直した時の、本人の行。"""
    return Line(CHOSEN_KEY, f"{label('today', language)}: {name}")


def question(obs: Observation) -> str | None:
    """Claude からの問い（一つ目）。無ければ None。"""
    return next((r for r in (_after_label(l.text, "question") for l in obs.reading) if r), None)


def next_shot(obs: Observation) -> str | None:
    """次の一枚（一つ目）。無ければ None。"""
    return next((r for r in (_after_label(l.text, "next_shot") for l in obs.reading) if r), None)


def answer_line(question_text: str, answer: str, language: str) -> Line:
    """問いへの答え。本人の言った事（said）として、問いを添えて残す。"""
    q = question_text.replace("\n", " ")
    a = answer.strip().replace("\n", " ")
    return Line(
        "said",
        f"{a}（{label('question', language)}: {q}）"
        if language in ("ja", "zh")
        else f"{a} ({label('question', language)}: {q})",
    )


def answered(obs: Observation, question_text: str) -> str | None:
    """問いに答えた本人の行の文（答えの部分）。まだなら None。"""
    q = question_text.replace("\n", " ")
    for line in obs.record:
        for lab in LABELS["question"].values():
            for tail in (f"（{lab}: {q}）", f" ({lab}: {q})"):
                if line.text.endswith(tail):
                    return line.text[: -len(tail)]
    return None


# ---------------------------------------------------------------- 草の名（Pl@ntNet の行から）

PLANT_RE = re.compile(
    r"\APl@ntNet（(?P<name>[^）]+)）[:：]\s*(?P<cands>.+?)\s*(?:（モデルの読み|\(model reading).*\Z"
)


@dataclass
class Plant:
    name: str
    photos: list[tuple[str, str]] = field(default_factory=list)  # (観察のファイル名の幹, 写真の相対の道)

    @property
    def count(self) -> int:
        return len(self.photos)


def plant_name(line: Line) -> tuple[str, str] | None:
    """Pl@ntNet の行 → (写真の名, 一番の候補の名)。違うと付いた行と、形の違う行は None。"""
    if line.key != "plants" or line.verdict == "wrong":
        return None
    m = PLANT_RE.match(line.text)
    if not m:
        return None
    first = re.split(r"、|, ", m.group("cands"))[0].strip()
    name = re.sub(r"\s+[0-9.]+\Z", "", first).strip()
    return (m.group("name"), name) if name else None


def plants(observations: list[tuple[str, Observation]]) -> list[Plant]:
    """記録に在る草の名を集める（多い順）。observations は (観察の名, 観察)。"""
    found: dict[str, Plant] = {}
    for oid, obs in observations:
        by_name = {stem(r): r for r in obs.photos}
        for line in obs.reading:
            got = plant_name(line)
            if not got:
                continue
            photo, name = got
            p = found.setdefault(name, Plant(name))
            if photo in by_name:
                p.photos.append((oid, by_name[photo]))
            else:
                p.photos.append((oid, ""))
    return sorted(found.values(), key=lambda p: (-p.count, p.name))


# ---------------------------------------------------------------- 写真のタグ（tags の行から）

TAG_RE = re.compile(r"\A(?P<stem>[^\s:：,、]+)\s*[:：]\s*(?P<words>.+)\Z")


def tags_of(obs: Observation) -> dict[str, list[str]]:
    """写真の名（幹）→ 語の並び。違うと付いた行、形の違う行、この観察に無い写真の行は飛ばす。"""
    stems = {stem(r) for r in obs.photos}
    out: dict[str, list[str]] = {}
    for line in obs.reading:
        if line.key != "tags" or line.verdict == "wrong":
            continue
        m = TAG_RE.match(line.text.strip())
        if not m or m.group("stem") not in stems:
            continue
        words = out.setdefault(m.group("stem"), [])
        for w in re.split(r",|、", m.group("words")):
            w = w.strip()
            if w and w not in words:
                words.append(w)
    return {k: v for k, v in out.items() if v}


def all_tags(observations: list[tuple[str, Observation]]) -> list[tuple[str, int]]:
    """語と、その語が付いた写真の数（多い順、同じなら語の順）。observations は (観察の名, 観察)。"""
    count: dict[str, int] = {}
    for _, obs in observations:
        for words in tags_of(obs).values():
            for w in words:
                count[w] = count.get(w, 0) + 1
    return sorted(count.items(), key=lambda x: (-x[1], x[0]))


# ---------------------------------------------------------------- 読みの指示に足す文（サーバーと手元で同じ）


def prompt_rules(language: str) -> str:
    """読みの指示に足す、決まった書き出しの頼み。行はただの文のまま。key は手引きの順のまま。"""
    t, q, n = (label(k, language) for k in ("today", "question", "next_shot"))
    states = "、".join(TAG_STATES.get(language, TAG_STATES["en"]))
    return (
        "読みの行に、決まった書き出しの行を三つ入れます（行はただの文。key は手引きの順のまま）:\n"
        f"- `overall` の最初の行を「{t}: <写真の名>。<なぜその一枚か、何が写っているかを一言>」にします。"
        "本人に一番見せたい一枚を選びます。\n"
        f"- 本人への問いを一つ、`uncertain` の行で「{q}: …」と書きます。本人しか知らない事か、次に畑で確かめられる事を。\n"
        f"- 次に撮ると分かる事が増える物を一つ、`next_to_observe` の行で「{n}: …」と書きます。どこを、どう撮るか。\n"
        "ある写真に基づく行には、その写真の名（ファイルの名の幹。例 173445）を書きます。\n"
        f"- 写真一枚ごとに `tags` の行を一つ: 「<写真の名>: <植物の名>, <状態>, …」。状態の語は {states} から。"
        "植物の名は分かる物だけ（本人が直した名が先。分からなければ上の括り）。"
    )
