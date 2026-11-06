# SPDX-License-Identifier: AGPL-3.0-or-later
"""話す /。畑について Claude とやり取りする（Claude Code の画面のように、上から下へ、新しい物が下）。

作者 2026-11-06「Claude Code のようにチャット形式にすればいい」「Form 形式はすべてなくせ」
「記録と観察をできるだけ楽しくできるソフトでないとダメでしょう」「まちがいの指摘も基本はチャットでやる」。

やり取りは記録のファイルから組む。観察一件が一往復: 人の側は撮った写真と本人の言葉、Claude の側は今日の一枚、
見つけた事（読みの行）、問い、次の一枚。文字を打てる所は、一番下の一行だけ。

送った時の分かれ道（send）:
- 写真あり → 新しい観察にし、読む（読み方は設定。既定は手元の Claude が在ればそれ、無ければサーバー）
- 言葉だけ、手元の Claude あり → Claude Code に渡す（間違いの指摘、計画、公開などの細かい作業）
- 言葉だけ、手元の Claude なし → 一番新しい観察に本人の言葉として足し、サーバーで読み直す
- サーバーが要るのに招待コードが無い → 「招待コードを貼ってください」。次の一行は招待コードとして保存し、やり取りに残さない
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from seed import album, land, local, photos
from seed import highlights as H
from seed.app import capture, cards, photo, theme
from seed.app.strings import error_text
from seed.cli import read_local, read_on_server
from seed.client import ClientError
from seed.records import Folder, Line, Observation

if TYPE_CHECKING:
    from seed.app.main import App

FOUND_SHOWN = 3  # 見つけた事の、頭に見せる行の数（残りは「続きを読む」）
BIG_W = 560  # 今日の一枚の幅の上限


# ---------------------------------------------------------------- やり取りを記録から組む（Flet に依らない）


@dataclass
class Found:
    """見つけた事の一行と、その行が名で指す写真（相対の道）。"""

    line: Line
    photos: list[str] = field(default_factory=list)


@dataclass
class Turn:
    """観察一件 = 一往復。"""

    name: str  # 観察のファイル名の幹（日-時刻）
    obs: Observation
    words: list[str]  # 本人の言葉
    today: str | None  # 今日の一枚（相対の道）
    today_words: str
    found: list[Found]
    question: str | None
    answer: str | None  # 問いへの本人の答え
    next_shot: str | None

    @property
    def read(self) -> bool:
        return bool(self.obs.reading)


def turn_of(name: str, obs: Observation) -> Turn:
    pick, words = H.today(obs) if obs.photos or obs.reading else (None, "")
    if not obs.reading:
        words = ""
    found = [
        Found(l, H.photos_of(l.text, obs))
        for l in obs.reading
        if not H.marked(l) and l.text.strip() != (words or "").strip()
    ]
    q = H.question(obs)
    return Turn(
        name=name,
        obs=obs,
        words=[l.text for l in obs.record if not H.marked(l)],
        today=pick,
        today_words=words,
        found=found,
        question=q,
        answer=H.answered(obs, q) if q else None,
        next_shot=H.next_shot(obs),
    )


def turns(folder: Folder) -> list[Turn]:
    """観察を古い順に一往復ずつ。読めないファイルは飛ばす。"""
    out = []
    for path in folder.list_observations():
        try:
            out.append(turn_of(path.stem, Observation.read(path)))
        except (ValueError, TypeError, OSError):
            continue
    return out


def changed_lines(before: list[Line], after: list[Line]) -> list[Line]:
    """読み直して変わった行（新しく出た文）。直した所として先に見せる。"""
    return [n for n in after if not any(o.same_statement(n) for o in before)]


def readings(folder: Folder) -> dict[str, list[Line]]:
    out = {}
    for path in folder.list_observations():
        try:
            out[path.stem] = list(Observation.read(path).reading)
        except (ValueError, TypeError, OSError):
            continue
    return out


# ---------------------------------------------------------------- やり取りに足す物（この窓の間だけ）
#
# state["talk"] の一件は dict: who（"me" / "claude"）、after（どの観察の後に出すか。無ければ頭）、
# text、fixed（直した行）、obs（どの観察の話か）、card（押した印の札）。記録に残る物はファイルから組む。


def talk_state(app: App) -> list[dict]:
    return app.state.setdefault("talk", [])


def last_name(app: App) -> str | None:
    paths = app.folder.list_observations()
    return paths[-1].stem if paths else None


def add(app: App, **item) -> None:
    item.setdefault("after", last_name(app))
    talk_state(app).append(item)


def say(app: App, text: str, **kw) -> None:
    add(app, who="claude", text=text, **kw)


# ---------------------------------------------------------------- 送る


def read_via(app: App) -> str:
    """読み方。手元の Claude が無ければサーバー。在れば設定の通り（無ければ手元の Claude）。"""
    if local.available() is None:
        return "server"
    return app.settings.read if app.settings.read in ("local", "server") else "local"


def can_talk_local(app: App) -> bool:
    return local.available() is not None


def ask_invite(app: App) -> None:
    app.state["await_invite"] = True
    say(app, app.t("talk_invite_ask"))


async def read_obs(app: App, obs: Observation) -> bool:
    """観察を読む（読み方は設定の通り）。読めたら True。招待コードが要れば頼む。

    サーバーの Claude を呼ぶのは、写真を送って読み取る時だけ（作者の鍵の費用。言葉だけでは呼ばない）。
    """
    via = read_via(app)
    if via == "server" and not app.settings.invite:
        ask_invite(app)
        return False
    try:
        if via == "local":
            await asyncio.to_thread(read_local, app.settings, app.folder, obs)
        else:
            await asyncio.to_thread(read_on_server, app.settings, app.folder, obs)
    except (ClientError, photos.PhotoError) as ex:
        say(app, error_text(ex, app.lang, server=app.settings.server))
        return False
    obs.write(app.folder.observation_path(obs))
    return True


async def send_photos(app: App, paths: list[Path], text: str) -> None:
    try:
        rel = await asyncio.to_thread(photos.import_photos, app.folder, paths, app.settings.keep)
        obs = await asyncio.to_thread(photos.observation_for, app.folder, rel, app.lang)
    except photos.PhotoError as ex:
        say(app, error_text(ex, app.lang))
        return
    except (OSError, TimeoutError) as ex:
        say(app, str(ex))
        return
    obs.kind = app.state.get("kind", "own")
    obs.ask = list(dict.fromkeys([*obs.ask, *LAND_ASKS]))  # 土と歴史はいつも聞く（流れの中で選ばせない）
    if text:
        obs.say("said", text.replace("\n", " "))
    obs.write(app.folder.observation_path(obs))
    await read_obs(app, obs)
    if obs.location and not app.folder.place_data():
        await place_data(app, quiet=True)  # 初めての位置の入った写真: 土地の成り立ちを調べておく（AI 無し）


async def send_words(app: App, text: str) -> None:
    """言葉だけ。手元の Claude が在れば Claude Code に渡す（直す、計画、公開などの細かい作業）。

    無い端末（電話）は、一番新しい観察に本人の言葉として足すだけ（AI は呼ばない）。次に写真を送った時の
    読み取りが、前の観察の本人の言葉を「本人が直した事」として先に読む。
    """
    if can_talk_local(app):
        before = readings(app.folder)
        try:
            reply, session = await asyncio.to_thread(
                local.talk, app.folder, text, app.lang, app.state.get("claude_session")
            )
        except ClientError as ex:
            say(app, error_text(ex, app.lang))
            return
        app.state["claude_session"] = session
        after = readings(app.folder)
        fixed = [l for n, lines in after.items() if before.get(n) for l in changed_lines(before[n], lines)]
        add(app, who="claude", text=reply or app.t("talk_done"), fixed=fixed, reply=True)
        return
    name = last_name(app)
    if name is None:
        say(app, app.t("talk_first_photo"))
        return
    path = app.folder.observations / f"{name}.md"
    obs = Observation.read(path)
    q = H.question(obs)
    line = H.answer_line(q, text, app.lang) if q and not H.answered(obs, q) else Line("said", text)
    obs.record.append(Line(line.key, line.text.replace("\n", " ")))
    obs.write(path)
    say(app, app.t("talk_noted"))


async def take_invite(app: App, code: str) -> None:
    """招待コードを保存する。その一行はやり取りに残さない。まだ読めていない観察があれば読む。"""
    app.state["await_invite"] = False
    app.settings.invite = code.strip()
    app.settings.save()
    say(app, app.t("talk_invite_set"))
    app.page.run_task(app.load_scopes)
    name = last_name(app)
    if name is None:
        return
    obs = Observation.read(app.folder.observations / f"{name}.md")
    if obs.reading or not obs.photos:
        return
    app.state["pending"] = {"text": "", "photos": []}
    app.refresh()
    try:
        await read_obs(app, obs)
    finally:
        app.state.pop("pending", None)
        app.refresh()


async def add_photos(app: App, text: str) -> None:
    """写真を足す: 電話は撮る画面（画面の確かめ用のブラウザでも）、PC は写真を選ぶ。"""
    if capture.available(app.page):
        app.state["capture"] = capture.Session()
        app.state["capture_text"] = text
        app.refresh()
        return
    try:
        paths = await app.pick_photos()
    except (OSError, TimeoutError) as ex:
        say(app, str(ex))
        app.refresh()
        return
    if paths:
        await send(app, text, paths)


async def send(app: App, text: str, paths: list[Path] | None = None, as_example: bool = True) -> None:
    """一番下の入力から送った物。待つ間は app.state["pending"] に置き、画面は読める。"""
    text = (text or "").strip()
    paths = list(paths or [])
    if not text and not paths:
        return
    if app.state.get("await_invite") and text and not paths:
        await take_invite(app, text)
        return
    to = app.state.pop("talk_to", None)
    if to and text and not paths:
        await cards.send_word(app, to, text)
        return
    if as_example and not paths:
        key = example_of(app, text)
        if key is not None:
            await run_example(app, key)
            return
    if not paths:
        add(app, who="me", text=text)  # 言葉はすぐ下に出す（待つ間も読める）
    app.state["pending"] = {"text": text if paths else "", "photos": paths}
    app.refresh()
    try:
        if paths:
            await send_photos(app, paths, text)
        else:
            await send_words(app, text)
    finally:
        app.state.pop("pending", None)
        app.refresh()


# ---------------------------------------------------------------- 見た目


def width(app: App) -> float:
    return theme.fit_width(getattr(app.page, "width", None)) - 32


def me_bubble(app: App, controls: list[ft.Control]) -> ft.Control:
    return ft.Row(
        [
            ft.Container(
                ft.Column(controls, spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.END),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                padding=12,
                border_radius=16,
            )
        ],
        alignment=ft.MainAxisAlignment.END,
        wrap=True,
    )


def claude_side(controls: list[ft.Control]) -> ft.Control:
    return ft.Container(ft.Column(controls, spacing=10, tight=True), padding=ft.Padding.only(right=24))


def words_text(text: str) -> ft.Text:
    return ft.Text(text, size=theme.BODY_SIZE, selectable=True)


def verdict_mark(app: App, line: Line) -> ft.Control | None:
    if not line.verdict:
        return None
    word = app.t("right") if line.verdict == "right" else app.t("wrong")
    return theme.muted(f"→ {word}" + (f"（{line.reason}）" if line.reason else ""))


def found_row(app: App, turn: Turn, f: Found) -> ft.Control:
    shots = photo.shots_of(turn.obs)
    pics = []
    for rel in f.photos[:2]:
        i = turn.obs.photos.index(rel)
        t = photo.tile(app, shots, i, photo.TINY / 1.5)
        if t is not None:
            pics.append(t)
    body: list[ft.Control] = [words_text(f.line.text)]
    mark = verdict_mark(app, f.line)
    if mark is not None:
        body.append(mark)
    return ft.Row(
        [*pics, ft.Column(body, spacing=2, expand=True)],
        vertical_alignment=ft.CrossAxisAlignment.START,
        spacing=10,
    )


def question_card(app: App, text: str, answer: str | None) -> ft.Control:
    rows: list[ft.Control] = [
        ft.Row(
            [
                ft.Icon(ft.Icons.HELP_OUTLINE, color=ft.Colors.ON_TERTIARY_CONTAINER),
                theme.subheading(app.t("talk_question")),
            ],
            spacing=8,
        ),
        ft.Text(text, size=theme.BODY_SIZE, color=ft.Colors.ON_TERTIARY_CONTAINER, selectable=True),
    ]
    if answer:
        rows.append(theme.muted(app.t("talk_answered", answer=answer)))
    return ft.Container(
        ft.Column(rows, spacing=6, tight=True),
        bgcolor=ft.Colors.TERTIARY_CONTAINER,
        padding=14,
        border_radius=16,
    )


def next_card(app: App, text: str) -> ft.Control:
    return ft.Container(
        ft.Row(
            [
                ft.Icon(ft.Icons.PHOTO_CAMERA_OUTLINED, color=ft.Colors.PRIMARY),
                ft.Column(
                    [theme.muted(app.t("talk_next_shot")), words_text(text)],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        padding=12,
        border_radius=16,
    )


def turn_controls(app: App, turn: Turn, hide: set[str]) -> list[ft.Control]:
    """一往復。hide は、この窓で送った言葉（下に別に出ている物）。"""
    t = app.t
    out: list[ft.Control] = []
    me: list[ft.Control] = []
    if turn.obs.photos:
        me.append(photo.strip(app, photo.shots_of(turn.obs), photo.SMALL * 0.75))
    for w in turn.words:
        if w not in hide:
            me.append(words_text(w))
    when = f"{turn.obs.date} {turn.obs.time[:5]}"
    me.append(theme.muted(f"{when} · {t('candidate')}" if turn.obs.kind == "candidate" else when))
    out.append(me_bubble(app, me))
    if not turn.read:
        return out
    side: list[ft.Control] = []
    if turn.today:
        shots = photo.shots_of(turn.obs)
        i = turn.obs.photos.index(turn.today)
        w = min(BIG_W, width(app) - 24)

        def open_big(e, shots=shots, i=i) -> None:
            photo.open_viewer(app, shots, i)

        pic = photo.picture(app, app.folder.root / turn.today, photo.BIG, w, w * 1.2, on_click=open_big)
        if pic is not None:
            side.append(pic)
    if turn.today_words:
        side.append(ft.Text(turn.today_words, size=18, weight=ft.FontWeight.W_500, selectable=True))
    opened: set[str] = app.state.setdefault("talk_open", set())
    seen = [f for f in turn.found if not is_land_line(f)]
    about = [f for f in turn.found if is_land_line(f)]
    shown = seen if turn.name in opened else seen[:FOUND_SHOWN]
    side += [found_row(app, turn, f) for f in shown]
    if len(seen) > len(shown):

        def more(e, name=turn.name) -> None:
            opened.add(name)
            app.refresh()

        side.append(ft.TextButton(t("talk_more", n=len(seen) - len(shown)), on_click=more))
    if about:  # 土や歴史に触れた行は、写真の行に埋もれないように分けて
        side.append(theme.muted(t("land_from_data")))
        side += [found_row(app, turn, f) for f in about]
    if turn.question:
        side.append(question_card(app, turn.question, turn.answer))
    if turn.next_shot:
        side.append(next_card(app, turn.next_shot))
    out.append(claude_side(side))
    return out


def item_controls(app: App, item: dict) -> list[ft.Control]:
    if item.get("card"):
        return [claude_side([cards.card(app, item["card"])])]
    if item["who"] == "me":
        return [me_bubble(app, [words_text(item["text"])])]
    side: list[ft.Control] = []
    fixed: list[Line] = item.get("fixed") or []
    if fixed:  # 直した行を先に
        side.append(theme.subheading(app.t("talk_fixed")))
        for l in fixed:
            row = ft.Row(
                [ft.Icon(ft.Icons.EDIT_NOTE, size=18), ft.Container(words_text(l.text), expand=True)],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            side.append(row)
    if item.get("text"):
        side += reply_controls(app, item["text"]) if item.get("reply") else [words_text(item["text"])]
    if item.get("photos"):
        side.append(photos_strip(app, item["photos"], photo_index(app.folder), photo.SMALL))
    if item.get("land"):
        side += land_controls(app, item["land"])
    if item.get("places"):
        side += places_controls(app)
    if item.get("examples"):
        side.append(example_chips(app, item["examples"]))
    return [claude_side(side)]


def pending_controls(app: App, pending: dict) -> list[ft.Control]:
    out: list[ft.Control] = []
    me: list[ft.Control] = []
    w = min(BIG_W, width(app) - 40)
    for p in pending.get("photos") or []:
        pic = photo.picture(app, Path(p), photo.BIG, w, w)
        if pic is not None:
            me.append(pic)
    if pending.get("text"):
        me.append(words_text(pending["text"]))
    if me:
        out.append(me_bubble(app, me))
    word = pending.get("word") or (
        "talk_reading" if pending.get("photos") or not can_talk_local(app) else "talk_thinking"
    )
    out.append(
        claude_side(
            [ft.Row([ft.ProgressRing(width=18, height=18, stroke_width=2), theme.muted(app.t(word))])]
        )
    )
    return out


def conversation(app: App) -> list[ft.Control]:
    """やり取りの全部（古い順）。"""
    t = app.t
    items = talk_state(app)
    hide = {i["text"] for i in items if i.get("who") == "me" and i.get("text")}
    out: list[ft.Control] = []
    all_turns = turns(app.folder)
    if not all_turns:
        out.append(claude_side([words_text(t("talk_hello")), words_text(t("talk_first_photo"))]))
    if app.folder.place_data() or land.frames(
        app.folder
    ):  # 一番上に、この土地の成り立ち（昔 → 今 → 自分の観察）
        out.append(claude_side(land_controls(app, "top")))
    for it in items:
        if it.get("after") is None:
            out += item_controls(app, it)
    for turn in all_turns:
        out += turn_controls(app, turn, hide)
        for it in items:
            if it.get("after") == turn.name:
                out += item_controls(app, it)
    pending = app.state.get("pending")
    if pending:
        out += pending_controls(app, pending)
    return out


# ---------------------------------------------------------------- 「こういう事ができます」の例
#
# 入力の上に、人が言いそうな言葉で例を出す。押すとその言葉を送った物として扱い、答えを下に出す。
# AI 無しでアプリが答えられる物は、どの端末でもその場で。手元の Claude が要る物は、無い端末では PC での
# やり方を一言添えて返す。


@dataclass(frozen=True)
class Example:
    key: str
    needs_claude: bool = False  # 手元の Claude（Claude Code）が要る


EXAMPLES = {
    e.key: e
    for e in (
        Example("first"),
        Example("by_place"),
        Example("landform"),
        Example("soil_q"),
        Example("past"),
        Example("track", needs_claude=True),
        Example("name_it"),
        Example("wrong"),
        Example("plan_make", needs_claude=True),
        Example("plan_show"),
        Example("publish", needs_claude=True),
        Example("published"),
        Example("others"),
        Example("plants"),
        Example("settings"),
        Example("more"),
    )
}
EXAMPLES_SHOWN = 5  # 一度に出す数（と「ほかに何ができますか」）
CARD_OF = {
    "plan_show": "plan",
    "published": "published",
    "others": "others",
    "plants": "plants",
    "settings": "settings",
}


def examples(app: App, everything: bool = False) -> list[str]:
    """今の場面に合う例の鍵。観察が無い時は「まず一枚」だけ。手元の Claude が無い端末は、AI 無しの物を先に。"""
    if not app.folder.list_observations():
        return ["first"]
    plan = "plan_show" if app.folder.plan.exists() else "plan_make"
    keys = [
        "landform",
        "by_place",
        "name_it",
        "wrong",
        "past",
        "soil_q",
        "track",
        plan,
        "publish",
        "others",
        "plants",
        "published",
        "settings",
    ]
    if any(app.folder.public.glob("*.md")) if app.folder.public.exists() else False:
        keys.remove("published")
        keys.insert(2, "published")
    if not can_talk_local(app):
        keys.sort(key=lambda k: EXAMPLES[k].needs_claude)
    if everything:
        return keys
    return [*keys[:EXAMPLES_SHOWN], "more"]


def example_of(app: App, text: str) -> str | None:
    """打った言葉が例の言葉そのままなら、その鍵。"""
    from seed.app.strings import STRINGS

    t = text.strip()
    for key in EXAMPLES:
        if key in ("first", "more"):
            continue
        if any(STRINGS[lg].get(f"ex_{key}") == t for lg in STRINGS):
            return key
    return None


async def run_example(app: App, key: str) -> None:
    """例を押した、か、例の言葉を打った。人の言葉として出し、答えを下に出す。"""
    ex = EXAMPLES[key]
    if key == "first":
        await add_photos(app, "")
        return
    phrase = app.t(f"ex_{key}")
    if ex.needs_claude and can_talk_local(app):
        await send(app, phrase, as_example=False)
        return
    add(app, who="me", text=phrase)
    if ex.needs_claude:
        say(app, app.t("ex_on_pc", phrase=phrase))
    elif key in CARD_OF:
        add(app, card=CARD_OF[key])
    elif key == "by_place":
        add(app, who="claude", places=True)
    elif key == "wrong":
        say(app, app.t("ex_wrong_how"))
    elif key == "more":
        add(app, who="claude", text=app.t("ex_more_intro"), examples=examples(app, everything=True))
    elif key == "name_it":
        await name_latest(app)
    elif key in ("landform", "soil_q"):
        if await place_data(app):
            add(app, who="claude", land="all" if key == "landform" else "soil")
    elif key == "past":
        await past(app)
    app.refresh()


async def name_latest(app: App) -> None:
    """一番新しい観察の今日の一枚の草の名を、Pl@ntNet で確かめる（AI の読みではない）。"""
    from seed import identify
    from seed.cli import identify_photos

    name = last_name(app)
    obs = Observation.read(app.folder.observations / f"{name}.md") if name else None
    rel = H.today(obs)[0] if obs else None
    if obs is None or rel is None:
        say(app, app.t("talk_first_photo"))
        return
    via = "local" if identify.available() else "server"
    if via == "server" and not app.settings.invite:
        ask_invite(app)
        return
    app.state["pending"] = {"text": "", "photos": []}
    app.refresh()
    try:
        added = await asyncio.to_thread(identify_photos, app.settings, app.folder, obs, [H.stem(rel)], via)
        obs.write(app.folder.observation_path(obs))
        names = [n[1] for n in (H.plant_name(l) for l in added) if n]
        text = app.t("ex_name_result", names="、".join(names)) if names else app.t("identify_none")
        add(app, who="claude", text=text, photos=[rel])
    except (ClientError, photos.PhotoError) as ex:
        say(app, error_text(ex, app.lang, server=app.settings.server))
    finally:
        app.state.pop("pending", None)


EXAMPLE_ICONS = {"first": ft.Icons.PHOTO_CAMERA_OUTLINED, "more": ft.Icons.MORE_HORIZ}


def example_chips(app: App, keys: list[str], one_line: bool = False) -> ft.Control:
    """例の並び。入力の上では一行で横に送る（狭い電話でもやり取りの場所を取らない）。返事の中では折り返す。"""

    def press(key: str):
        async def h(e) -> None:
            if app.state.get("pending"):
                return
            await run_example(app, key)

        return h

    chips = []
    for k in keys:
        icon = EXAMPLE_ICONS.get(k)
        chips.append(ft.OutlinedButton(app.t(f"ex_{k}"), icon=icon, on_click=press(k)))
    if one_line:
        return ft.ListView(chips, horizontal=True, spacing=6, height=40)
    return ft.Row(chips, wrap=True, spacing=6, run_spacing=6)


# ---------------------------------------------------------------- 返事の中の写真


IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
MIN_STEM = 4  # これより短い名（1、2 など）は、文の中の数と取り違えるので写真の名として探さない


def photo_index(folder: Folder) -> dict[str, Observation]:
    """写真の相対の道 → それを持つ観察。"""
    out: dict[str, Observation] = {}
    for path in folder.list_observations():
        try:
            obs = Observation.read(path)
        except (ValueError, TypeError, OSError):
            continue
        for rel in obs.photos:
            out.setdefault(rel, obs)
    return out


def safe_rel(folder: Folder, ref: str, known: dict[str, Observation]) -> str | None:
    """返事の中の絵の道を、記録の写真の相対の道に。フォルダーの外、知らない写真は None。"""
    if not ref or ref.startswith(("/", "\\")) or "://" in ref:
        return None
    try:
        target = (folder.root / ref).resolve()
        rel = target.relative_to(folder.root.resolve()).as_posix()
    except (OSError, ValueError):
        return None
    return rel if rel in known else None


def reply_parts(text: str, folder: Folder, known: dict[str, Observation]) -> list[tuple[str, object]]:
    """返事を、文の塊と写真の並びに分ける。写真は `![一言](photos/…)` と、写真の名（ファイルの名の幹）。"""
    stems = {Path(r).stem: r for r in known if len(Path(r).stem) >= MIN_STEM}
    parts: list[tuple[str, object]] = []
    buf: list[str] = []

    def flush() -> None:
        if any(x.strip() for x in buf):
            parts.append(("text", "\n".join(buf).strip("\n")))
        buf.clear()

    for line in text.splitlines():
        rels = [r for r in (safe_rel(folder, m.group(2), known) for m in IMG_RE.finditer(line)) if r]
        # 絵の書き方は全部外す（出せない物は一言だけ残す。フォルダーの外の道を Markdown に渡さない）
        rest = IMG_RE.sub(lambda m: "" if safe_rel(folder, m.group(2), known) else m.group(1), line)
        rels += [stems[n] for n in H.names_in(rest, list(stems)) if stems[n] not in rels]
        if rest.strip() or not rels:
            buf.append(rest)
        if rels:
            flush()
            if parts and parts[-1][0] == "photos":
                parts[-1][1].extend(r for r in rels if r not in parts[-1][1])  # type: ignore[union-attr]
            else:
                parts.append(("photos", list(dict.fromkeys(rels))))
    flush()
    return parts


def photos_strip(app: App, rels: list[str], known: dict[str, Observation], size: float) -> ft.Control:
    shots = [photo.Shot(known[r], r) for r in rels if r in known]
    return photo.strip(app, shots, size)


def reply_controls(app: App, text: str) -> list[ft.Control]:
    known = photo_index(app.folder)
    out: list[ft.Control] = []
    for kind, val in reply_parts(text, app.folder, known):
        if kind == "text":
            out.append(ft.Markdown(str(val), selectable=True))
        else:
            out.append(photos_strip(app, list(val), known, photo.SMALL * 0.75))  # type: ignore[arg-type]
    return out


def places_controls(app: App) -> list[ft.Control]:
    """写真を場所ごとに、時の順に（album.by_place。AI は使わない）。"""
    known = photo_index(app.folder)
    spots = album.by_place(app.folder)
    if not spots:
        return [words_text(app.t("photos_none_cli"))]
    out: list[ft.Control] = []
    for sp in spots:
        out.append(theme.subheading(album.spot_heading(sp, app.lang)))
        for day, group in album.days(sp):
            out.append(theme.muted(day))
            out.append(photos_strip(app, [s.rel for s in group], known, photo.TINY))
    return out


def composer(app: App) -> ft.Control:
    """一番下の入力。写真を足すボタン、一行の欄、送るボタン。アプリで文字を打てる所はここだけ。"""
    t = app.t
    busy = bool(app.state.get("pending"))
    to = app.state.get("talk_to")
    if app.state.get("await_invite"):
        hint = t("talk_hint_invite")
    elif to:
        hint = t("talk_hint_to", to=to)
    else:
        hint = t("talk_hint")
    box = ft.TextField(
        hint_text=hint,
        expand=True,
        border_radius=24,
        dense=True,
        autocorrect=not app.state.get("await_invite"),
        shift_enter=True,
        min_lines=1,
        max_lines=4,
    )

    def take() -> str:
        text = box.value or ""
        box.value = ""
        return text

    async def go(e=None) -> None:
        if not app.state.get("pending"):
            await send(app, take())

    async def photos_button(e) -> None:
        if not app.state.get("pending"):
            await add_photos(app, take())

    box.on_submit = go
    shoot = capture.available(app.page)
    row: list[ft.Control] = [
        ft.IconButton(
            ft.Icons.PHOTO_CAMERA_OUTLINED if shoot else ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
            tooltip=t("capture_shoot") if shoot else t("choose_photos"),
            on_click=photos_button,
            disabled=busy,
        ),
        box,
        ft.IconButton(ft.Icons.SEND, tooltip=t("talk_send"), on_click=go, disabled=busy),
    ]
    if to:

        def cancel_to(e) -> None:
            app.state.pop("talk_to", None)
            app.refresh()

        row.insert(1, ft.IconButton(ft.Icons.CLOSE, tooltip=t("talk_to_cancel"), on_click=cancel_to))
    return ft.Row(row, spacing=4, vertical_alignment=ft.CrossAxisAlignment.END)


def view(app: App) -> ft.View:
    if app.state.get("capture") is not None:  # 撮っている間は、撮る画面だけ
        done = end_capture(app)
        return app.view("/", capture.view(app, done, done))
    # 新しい物が下。reverse で下から積み、開いた時から一番新しい所が見える
    lines = ft.ListView(
        list(reversed(conversation(app))),
        spacing=16,
        expand=True,
        reverse=True,
        padding=ft.Padding.only(bottom=8),
    )
    body = ft.Column(
        [lines, example_chips(app, examples(app), one_line=True), composer(app)], spacing=10, expand=True
    )
    return app.frame("/", body)


def end_capture(app: App):
    async def done(paths: list | None = None) -> None:
        sess = app.state.pop("capture", None)
        app.state.pop("capture_parts", None)
        text = app.state.pop("capture_text", "")
        if paths:
            await send(app, text, paths)  # 取り込みが済んでから、一時の場所を消す
        else:
            app.refresh()
        if sess is not None:
            sess.close()

    return done


# ---------------------------------------------------------------- この土地の成り立ち（AI 無し。land.py）

LAND_ASKS = ("soil", "history")
LAND_WORDS = (
    "土壌", "地質", "地形", "標高", "洪水", "浸水", "土砂", "断層", "歴史", "地名", "史跡", "昔",
    "soil", "geolog", "landform", "elevation", "flood", "hazard", "history", "historic",
)  # fmt: skip


def is_land_line(f: Found) -> bool:
    """写真を名で指さず、土・地形・水の区域・歴史に触れた行（土地の資料から分かる事）。"""
    low = f.line.text.lower()
    return not f.photos and any(w in low for w in LAND_WORDS)


async def place_data(app: App, quiet: bool = False) -> bool:
    """place.md に土地の資料の行（照会）が在るか。無ければ照会する（手元の照会、無ければサーバーの照会）。"""
    if app.folder.place_data():
        return True
    c = land.center(app.folder)
    if c is None:
        if not quiet:
            say(app, app.t("land_need_photo"))
        return False
    from seed.server import lookup as L

    if not L.available() and not app.settings.invite:
        if not quiet:
            ask_invite(app)
        return False
    try:
        if L.available():
            lines = await asyncio.to_thread(L.data_lines, c[0], c[1], app.lang)
        else:
            lines = await app.call("lookup", c[0], c[1])
    except ClientError as ex:
        if not quiet:
            say(app, error_text(ex, app.lang, server=app.settings.server))
        return False
    if lines:
        app.folder.add_place_data(lines)
    elif not quiet:
        say(app, app.t("land_none"))
    return bool(lines)


async def past(app: App) -> None:
    """昔の地図と空中写真。まだ無ければ作る（seed origin の絵だけ。動画は作らない）。"""
    if not land.frames(app.folder):
        if land.center(app.folder) is None:
            say(app, app.t("land_need_photo"))
            return
        app.state["pending"] = {"text": "", "photos": [], "word": "land_fetching"}
        app.refresh()
        try:
            await asyncio.to_thread(land.make_frames, app.folder, app.lang)
        except Exception as ex:  # noqa: BLE001 — 地図の元に届かない、Pillow が無い、など。一文で見せる
            say(app, app.t("land_past_failed", detail=type(ex).__name__))
            return
        finally:
            app.state.pop("pending", None)
    if land.frames(app.folder):
        add(app, who="claude", land="past")
    else:
        say(app, app.t("land_past_none"))


def frame_items(frames: list[land.Frame]) -> list[tuple[Path, str]]:
    return [(f.path, f.title) for f in frames]


def land_controls(app: App, mode: str) -> list[ft.Control]:
    """この土地の成り立ち。mode: top（やり取りの一番上）、all、soil、past。"""
    t = app.t
    groups = land.summary(app.folder, app.lang)
    frames = land.frames(app.folder)
    out: list[ft.Control] = []
    if mode == "past":
        out.append(theme.subheading(t("land_past")))
        out.append(photo.plain_tiles(app, frame_items(frames)))
        return out
    if mode == "soil":
        groups = [g for g in groups if g.key == "soil"]
        frames = [f for f in frames if f.name == "soil"]
    else:
        out.append(theme.subheading(t("land_title")))
    opened: set[str] = app.state.setdefault("talk_open", set())
    full = mode != "top" or "land" in opened
    hidden = 0
    for g in groups:
        out.append(ft.Text(t(f"land_{g.key}"), weight=ft.FontWeight.W_600, size=theme.BODY_SIZE))
        shown = g.facts if full else g.facts[:1]
        hidden += len(g.facts) - len(shown)
        for f in shown:
            out.append(words_text(f.body))
            if f.source:
                out.append(theme.muted(f.source))
    if not groups:
        out.append(words_text(t("land_none")))
    if hidden:

        def more(e) -> None:
            opened.add("land")
            app.refresh()

        out.append(ft.TextButton(t("talk_more", n=hidden), on_click=more))
    if frames:
        if mode != "soil":
            out.append(theme.muted(t("land_past")))
        out.append(photo.plain_tiles(app, frame_items(frames), photo.SMALL * 0.9))
    return out
