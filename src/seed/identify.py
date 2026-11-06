# SPDX-License-Identifier: AGPL-3.0-or-later
"""草の名を確かめる: Pl@ntNet（設計書 §17）。

はじめて作物を作る人は、雑草か作物かが分からない（作者 11-04）。写真の種（species）の見分けは、専用の識別器が
汎用の AI より当たるので、Pl@ntNet の API に写真を送って候補を取り、Claude の読みとは**別の行**として観察に足す。
Pl@ntNet の答えは「モデルの読み」で、出典付きの data 行ではない。決めるのは本人（合う／違う）。

鍵は環境変数 PLANTNET_API_KEY（本人の PC では本人の鍵。サーバーではサーバーの環境ファイル）。リポジトリ、会話、
ログに入れない。鍵が無ければ送らず、Claude だけで読む。送るのは写真だけで、座標は送らない（縮めた JPEG は EXIF 無し）。
"""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .client import ClientError
from .records import Line

ENV_KEY = "PLANTNET_API_KEY"
API = "https://my-api.plantnet.org/v2/identify/all"
MAX_IMAGES = 5  # 一回に送れる枚数（同じ個体）
MAX_PER_OBSERVATION = 10  # 一つの観察で送る写真の上限（一日 500 回の枠を守る）
NB_RESULTS = 5
MIN_SCORE = 0.05  # これより低い候補は行に書かない
TIMEOUT = httpx.Timeout(60.0, connect=15.0)
ORGANS = ("leaf", "flower", "fruit", "bark", "auto")
PREFIX = "Pl@ntNet"  # 行の文の頭。読みを置き換えてもこの行は残す（cli.keep_model_lines）

# Pl@ntNet の commonNames に和名が無いときの補い。手引きの plants/ にある物と、作者の畑で出た物だけ
JA_NAMES = {
    "Miscanthus sacchariflorus": "オギ",
    "Miscanthus sinensis": "ススキ",
    "Solidago altissima": "セイタカアワダチソウ",
    "Solidago canadensis": "カナダアキノキリンソウ",
    "Bidens pilosa": "コセンダングサ",
    "Bidens frondosa": "アメリカセンダングサ",
    "Artemisia indica": "ヨモギ",
    "Equisetum arvense": "スギナ",
    "Houttuynia cordata": "ドクダミ",
    "Farfugium japonicum": "ツワブキ",
    "Setaria viridis": "エノコログサ",
    "Lycium chinense": "クコ",
    "Rumex japonicus": "ギシギシ",
    "Rumex obtusifolius": "エゾノギシギシ",
    "Ipomoea triloba": "ホシアサガオ",
    "Ipomoea lacunosa": "マメアサガオ",
    "Cucurbita moschata": "カボチャ（ニホンカボチャ）",
    "Brassica rapa": "アブラナ（カブ・コマツナの仲間）",
    "Triticum aestivum": "コムギ",
    "Secale cereale": "ライムギ",
    "Avena sativa": "エンバク",
    "Vicia sativa": "カラスノエンドウ",
    "Trifolium repens": "シロツメクサ",
    "Stellaria media": "コハコベ",
    "Digitaria ciliaris": "メヒシバ",
    "Oplismenus undulatifolius": "チヂミザサ",
}


class IdentifyError(ClientError):
    """Pl@ntNet に送れなかった、答えを使えなかった。word は strings の鍵。"""


@dataclass
class Candidate:
    scientific: str  # 学名（著者無し）
    score: float
    family: str = ""
    genus: str = ""
    common: list[str] = field(default_factory=list)  # lang の言語の普通名（無いこともある）
    gbif: str | None = None

    def name(self, language: str) -> str:
        """表示の名。和名が分かれば和名 + 学名、無ければ普通名 + 学名、無ければ学名だけ。"""
        ja = JA_NAMES.get(self.scientific)
        if language == "ja" and ja:
            return f"{ja} {self.scientific}"
        if self.common:
            return f"{self.common[0]} {self.scientific}"
        return self.scientific


@dataclass
class Identification:
    candidates: list[Candidate]
    remaining: int | None = None  # 今日の残りの回数（Pl@ntNet が返す）
    raw: dict = field(default_factory=dict)

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None


def key_from_env() -> str | None:
    return os.environ.get(ENV_KEY, "").strip() or None


def available() -> bool:
    return key_from_env() is not None


def parse(data: dict) -> Identification:
    """Pl@ntNet の答え（JSON）を候補に。形の合わない物は落とす。"""
    out: list[Candidate] = []
    for r in data.get("results") or []:
        sp = r.get("species") or {}
        sci = str(sp.get("scientificNameWithoutAuthor") or sp.get("scientificName") or "").strip()
        try:
            score = float(r.get("score") or 0)
        except (TypeError, ValueError):
            continue
        if not sci or score < MIN_SCORE:
            continue
        gbif = (r.get("gbif") or {}).get("id")
        out.append(
            Candidate(
                scientific=sci,
                score=score,
                family=str((sp.get("family") or {}).get("scientificNameWithoutAuthor") or ""),
                genus=str((sp.get("genus") or {}).get("scientificNameWithoutAuthor") or ""),
                common=[str(x) for x in (sp.get("commonNames") or []) if x],
                gbif=str(gbif) if gbif is not None else None,
            )
        )
    out.sort(key=lambda c: -c.score)
    remaining = data.get("remainingIdentificationRequests")
    return Identification(out[:NB_RESULTS], int(remaining) if isinstance(remaining, int) else None, data)


def identify(
    images: list[bytes],
    key: str | None = None,
    language: str = "ja",
    organs: list[str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> Identification:
    """写真（JPEG、同じ個体、5 枚まで）を Pl@ntNet に送り、候補を返す。植物でなければ候補は空。"""
    key = key or key_from_env()
    if not key:
        raise IdentifyError("identify_no_key", "no Pl@ntNet key")
    if not images:
        raise IdentifyError("identify_no_photos", "no photos")
    images = images[:MAX_IMAGES]
    organs = list(organs or [])[: len(images)] or ["auto"] * len(images)
    if any(o not in ORGANS for o in organs):
        raise IdentifyError("identify_rejected", f"organs は {ORGANS}")
    files = [("images", (f"{i + 1}.jpg", b, "image/jpeg")) for i, b in enumerate(images)]
    data = {"organs": organs}  # 写真ごとに一つ、同じ順
    params = {
        "api-key": key,
        "lang": language or "en",
        "nb-results": str(NB_RESULTS),
        "include-related-images": "false",
    }
    try:
        with httpx.Client(timeout=TIMEOUT, transport=transport) as c:
            r = c.post(API, params=params, files=files, data=data)
    except httpx.TimeoutException as e:
        raise IdentifyError("identify_unreachable", "Pl@ntNet did not answer") from e
    except httpx.TransportError as e:
        raise IdentifyError("identify_unreachable", "cannot reach Pl@ntNet") from e
    if r.status_code == 404:  # 植物でない、候補が無い
        return Identification([], None, _json_or_empty(r))
    if r.status_code == 401:
        raise IdentifyError("identify_rejected", "Pl@ntNet refused the key", "401")
    if r.status_code == 429:
        raise IdentifyError("identify_limit", "Pl@ntNet quota reached", "429")
    if r.status_code >= 400:
        raise IdentifyError("identify_failed", f"Pl@ntNet error {r.status_code}", str(r.status_code))
    return parse(_json_or_empty(r))


def _json_or_empty(r: httpx.Response) -> dict:
    try:
        data = r.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def line_for(
    result: Identification, photo: str, language: str = "ja", today: str | None = None, top: int = 3
) -> Line | None:
    """観察の `plants` の行。「Pl@ntNet（写真）: 名 0.62、名 0.21（モデルの読み、日）[0.62]」。候補が無ければ None。"""
    if not result.candidates:
        return None
    day = today or dt.date.today().isoformat()
    cands = result.candidates[:top]
    sep = "、" if language == "ja" else ", "
    names = sep.join(f"{c.name(language)} {c.score:.2f}" for c in cands)
    tail = f"（モデルの読み、{day}）" if language == "ja" else f" (model reading, {day})"
    return Line("plants", f"{PREFIX}（{photo}）: {names}{tail}", round(cands[0].score, 2))


def is_model_line(line: Line) -> bool:
    return line.key == "plants" and line.text.startswith(PREFIX)


def save_raw(raw_dir: Path | None, photo: str, result: Identification) -> None:
    """keep が research なら、答えをそのまま残す（observations/<id>.raw/plantnet-<写真>.json）。"""
    if raw_dir is None:
        return
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"plantnet-{photo}.json").write_text(
        json.dumps(result.raw, ensure_ascii=False, indent=1), encoding="utf-8"
    )
