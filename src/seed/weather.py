# SPDX-License-Identifier: AGPL-3.0-or-later
"""気象の記録 weather/<YYYY-MM>.md（docs/記録の形.md §17）。

畑の座標の日ごとの気象（最高・最低気温、降水、日照）を Open-Meteo の過去データから引き、
出典付きの Data の行として残す。網に繋ぐのは fetch だけ。座標は小数 2 桁に丸めて送る。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from .records import EMPTY, Folder, Observation, split_sections

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_URL = "https://open-meteo.com/"
JMA_URL = "https://www.data.jma.go.jp/stats/etrn/"
DAILY = ("temperature_2m_max", "temperature_2m_min", "precipitation_sum", "sunshine_duration")
TIMEZONE = "Asia/Tokyo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAILY = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
)
H_DATA = "Data"
DAY_LINE_RE = re.compile(r"^- (?P<date>\d{4}-\d{2}-\d{2}): ")
COORD_RE = re.compile(r"(-?\d{1,3}(?:\.\d+)?)\s*[,、]\s*(-?\d{1,3}(?:\.\d+)?)")

TEXTS = {
    "ja": {
        "line": "- {date}: 最高 {tmax} ℃、最低 {tmin} ℃、降水 {rain} mm、日照 {sun} h"
        "（出典: Open-Meteo 過去データ {url} 、確認日 {checked}）",
        "jma": "見比べる一次資料: 気象庁 過去の気象データ検索 {url}",
        "none": "—",
    },
    "en": {
        "line": "- {date}: max {tmax} °C, min {tmin} °C, precipitation {rain} mm, sunshine {sun} h"
        " (source: Open-Meteo historical weather {url} , checked {checked})",
        "jma": "Primary source to compare: JMA historical weather data {url}",
        "none": "—",
    },
}


class WeatherError(Exception):
    """本人に一行で返す誤り。word は strings.py の語。"""

    def __init__(self, word: str, detail: str = ""):
        super().__init__(word)
        self.word = word
        self.detail = detail


@dataclass
class Day:
    date: str
    tmax: float | None
    tmin: float | None
    rain: float | None
    sun_h: float | None

    @property
    def empty(self) -> bool:
        return all(v is None for v in (self.tmax, self.tmin, self.rain, self.sun_h))

    def render(self, language: str, checked: str) -> str:
        t = TEXTS.get(language, TEXTS["en"])

        def f(v: float | None) -> str:
            return t["none"] if v is None else f"{v:.1f}"

        return t["line"].format(
            date=self.date,
            tmax=f(self.tmax),
            tmin=f(self.tmin),
            rain=f(self.rain),
            sun=f(self.sun_h),
            url=OPEN_METEO_URL,
            checked=checked,
        )


def rounded(lat: float, lon: float) -> tuple[float, float]:
    """送る座標。小数 2 桁（約 1 km の格子）。"""
    return round(float(lat), 2), round(float(lon), 2)


def place_center(folder: Folder) -> tuple[float, float] | None:
    """畑の座標。place.md の center の行（`- center: 34.05, 134.25`）、無ければ座標のある一番新しい観察。"""
    for line in folder.place_data() + folder.place_record():
        if line.key == "center":
            m = COORD_RE.search(line.text)
            if m:
                return float(m[1]), float(m[2])
    for path in reversed(folder.list_observations()):
        try:
            obs = Observation.read(path)
        except (ValueError, OSError):
            continue
        if obs.location and obs.location.get("center"):
            lat, lon = obs.location["center"]
            return float(lat), float(lon)
    return None


def check_range(start: str, end: str, today: dt.date | None = None) -> tuple[dt.date, dt.date]:
    try:
        a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    except ValueError:
        raise WeatherError("field_bad_date", f"{start} {end}") from None
    today = today or dt.date.today()
    if a > b or b > today:
        raise WeatherError("weather_bad_range", f"{start} {end}")
    return a, b


def parse_daily(data: dict) -> list[Day]:
    """Open-Meteo の daily を日ごとに。形が違えば WeatherError。"""
    try:
        daily = data["daily"]
        dates = daily["time"]
        cols = [daily[k] for k in DAILY]
        if any(len(c) != len(dates) for c in cols):
            raise ValueError("lengths")
    except (KeyError, TypeError, ValueError) as e:
        raise WeatherError("weather_bad_answer", str(e)) from None
    out = []
    for i, date in enumerate(dates):
        tmax, tmin, rain, sun_s = (c[i] for c in cols)
        sun_h = None if sun_s is None else float(sun_s) / 3600
        out.append(
            Day(
                str(date),
                None if tmax is None else float(tmax),
                None if tmin is None else float(tmin),
                None if rain is None else float(rain),
                sun_h,
            )
        )
    return out


def fetch(
    lat: float,
    lon: float,
    start: dt.date,
    end: dt.date,
    transport=None,
    timeout: float = 30.0,
) -> list[Day]:
    """Open-Meteo の過去データを取る。座標はここで 2 桁に丸める。失敗は WeatherError。"""
    import httpx

    lat, lon = rounded(lat, lon)
    params = {
        "latitude": f"{lat:.2f}",
        "longitude": f"{lon:.2f}",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY),
        "timezone": TIMEZONE,
    }
    try:
        with httpx.Client(transport=transport, timeout=timeout) as http:
            r = http.get(ARCHIVE_URL, params=params)
    except httpx.HTTPError as e:
        raise WeatherError("weather_unreachable", type(e).__name__) from None
    if r.status_code != 200:
        reason = ""
        try:
            reason = str(r.json().get("reason") or "")
        except ValueError:
            pass
        raise WeatherError("weather_http", f"HTTP {r.status_code}{' ' + reason if reason else ''}")
    try:
        data = r.json()
    except ValueError:
        raise WeatherError("weather_bad_answer", "not JSON") from None
    return parse_daily(data)


@dataclass
class Forecast:
    date: str
    code: int
    tmax: float | None
    tmin: float | None
    rain: float | None
    rain_prob: int | None


def parse_forecast(data: dict) -> list[Forecast]:
    """Open-Meteo の予報の daily を日ごとに。形が違えば WeatherError。"""
    try:
        daily = data["daily"]
        dates = daily["time"]
        cols = [daily[k] for k in FORECAST_DAILY]
        if any(len(c) != len(dates) for c in cols):
            raise ValueError("lengths")
    except (KeyError, TypeError, ValueError) as e:
        raise WeatherError("weather_bad_answer", str(e)) from None

    def num(v, kind):
        return None if v is None else kind(v)

    out = []
    for i, date in enumerate(dates):
        code, tmax, tmin, rain, prob = (c[i] for c in cols)
        out.append(
            Forecast(
                str(date),
                num(code, int) or 0,
                num(tmax, float),
                num(tmin, float),
                num(rain, float),
                num(prob, int),
            )
        )
    return out


def fetch_forecast(lat: float, lon: float, days: int = 7, get=None) -> list[Forecast]:
    """Open-Meteo の予報を取る。座標は 2 桁に丸める。get は差し替え用（既定は httpx.get）。失敗は WeatherError。"""
    import httpx

    lat, lon = rounded(lat, lon)
    params = {
        "latitude": f"{lat:.2f}",
        "longitude": f"{lon:.2f}",
        "daily": ",".join(FORECAST_DAILY),
        "forecast_days": days,
        "timezone": TIMEZONE,
    }
    get = get or httpx.get
    try:
        r = get(FORECAST_URL, params=params, timeout=10.0)
    except httpx.HTTPError as e:
        raise WeatherError("weather_unreachable", type(e).__name__) from None
    if r.status_code != 200:
        raise WeatherError("weather_http", f"HTTP {r.status_code}")
    try:
        data = r.json()
    except ValueError:
        raise WeatherError("weather_bad_answer", "not JSON") from None
    return parse_forecast(data)


# WMO の天気の符号 → 短い語（上から合う物）
WORDS = (
    ({0}, ("快晴", "Clear")),
    ({1, 2}, ("晴れ", "Sunny")),
    ({3}, ("くもり", "Cloudy")),
    ({45, 48}, ("霧", "Fog")),
    ({51, 53, 55, 56, 57}, ("霧雨", "Drizzle")),
    ({61, 63, 65, 66, 67}, ("雨", "Rain")),
    ({71, 73, 75, 77}, ("雪", "Snow")),
    ({80, 81, 82}, ("にわか雨", "Showers")),
    ({85, 86}, ("にわか雪", "Snow showers")),
    ({95, 96, 99}, ("雷雨", "Thunder")),
)


def weather_word(code: int, language: str) -> str:
    for codes, (ja, en) in WORDS:
        if code in codes:
            return ja if language == "ja" else en
    return "—"


def month_path(root: Path, month: str) -> Path:
    return Path(root) / "weather" / f"{month}.md"


def write_days(root: Path, days: list[Day], language: str, checked: str | None = None) -> list[Path]:
    """月ごとのファイルに足す。同じ日は置き換え、日の順に並べる。ほかの行と見出しは残す。"""
    checked = checked or dt.date.today().isoformat()
    t = TEXTS.get(language, TEXTS["en"])
    by_month: dict[str, list[Day]] = {}
    for d in days:
        if not d.empty:
            by_month.setdefault(d.date[:7], []).append(d)
    written = []
    for month, new in sorted(by_month.items()):
        path = month_path(root, month)
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        sections = split_sections(old)
        dated: dict[str, str] = {}
        other: list[str] = []  # Data の下の、日の行でない文（本人が足した物）
        rest: list[tuple[str, str]] = []
        for title, block in sections:
            if title == H_DATA:
                for raw in block.splitlines():
                    m = DAY_LINE_RE.match(raw)
                    if m:
                        dated[m["date"]] = raw
                    elif raw.strip() and raw.strip() != EMPTY:
                        other.append(raw)
            else:
                rest.append((title, block))
        for d in new:
            dated[d.date] = d.render(language, checked)
        body = [dated[k] for k in sorted(dated)] + other
        parts = [t["jma"].format(url=JMA_URL), "", f"## {H_DATA}", "", *body, ""]
        for title, block in rest:
            parts += [f"## {title}", "", block.strip("\n") or EMPTY, ""]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(parts), encoding="utf-8")
        written.append(path)
    return written


def show(root: Path, month: str) -> str | None:
    path = month_path(root, month)
    return path.read_text(encoding="utf-8") if path.exists() else None


def day_lines(root: Path, month: str) -> list[str]:
    """その月の日の行（観察に Data として引くときに使う）。"""
    text = show(root, month) or ""
    return [raw for raw in text.splitlines() if DAY_LINE_RE.match(raw)]
