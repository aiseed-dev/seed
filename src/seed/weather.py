# SPDX-License-Identifier: AGPL-3.0-or-later
"""気象の記録 weather/<YYYY-MM>.md（docs/記録の形.md §17）。

畑の座標の日ごとの気象（最高・最低気温、降水、日照）を Open-Meteo の過去データから引き、
出典付きの Data の行として残す。網に繋ぐのは fetch だけ。座標は小数 2 桁に丸めて送る。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, replace
from pathlib import Path

from .records import EMPTY, Folder, Observation, split_sections

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_URL = "https://open-meteo.com/"
JMA_URL = "https://www.data.jma.go.jp/stats/etrn/"
DAILY = ("temperature_2m_max", "temperature_2m_min", "precipitation_sum", "sunshine_duration")
TIMEZONE = "Asia/Tokyo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ECMWF_URL = "https://api.open-meteo.com/v1/ecmwf"
FORECAST_DAILY = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
)
EXTRA_DAILY = (
    "sunshine_duration",
    "et0_fao_evapotranspiration",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
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
    sunshine_h: float | None = None  # 日照（時間）
    et0: float | None = None  # 蒸発散（mm）
    wind: float | None = None  # 最大の風（m/s）
    gust: float | None = None  # 最大の突風（m/s）
    wind_dir: int | None = None  # 主な風向（度）


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
        sun, et0, wind, gust, wdir = (
            (daily.get(k) or [None] * len(dates))[i] if len(daily.get(k) or []) in (0, len(dates)) else None
            for k in EXTRA_DAILY
        )
        out.append(
            Forecast(
                str(date),
                num(code, int) or 0,
                num(tmax, float),
                num(tmin, float),
                num(rain, float),
                num(prob, int),
                None if sun is None else float(sun) / 3600,
                num(et0, float),
                num(wind, float),
                num(gust, float),
                num(wdir, int),
            )
        )
    return out


SOIL_TEMP = {
    "soil_temperature_0cm": "0 cm",
    "soil_temperature_6cm": "6 cm",
    "soil_temperature_18cm": "18 cm",
    "soil_temperature_54cm": "54 cm",
}
SOIL_MOISTURE = {
    "soil_moisture_0_to_1cm": "0-1 cm",
    "soil_moisture_1_to_3cm": "1-3 cm",
    "soil_moisture_3_to_9cm": "3-9 cm",
    "soil_moisture_9_to_27cm": "9-27 cm",
    "soil_moisture_27_to_81cm": "27-81 cm",
}
HOURLY = (*SOIL_TEMP, *SOIL_MOISTURE)
HOURLY_WEATHER = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "precipitation_probability",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
)
JST = dt.timezone(dt.timedelta(hours=9))


@dataclass
class Hour:
    time: str  # 2026-11-08T06:00（Asia/Tokyo）
    code: int | None
    temp: float | None
    humidity: int | None
    dewpoint: float | None
    rain: float | None
    rain_prob: int | None
    wind: float | None
    gust: float | None
    wind_dir: int | None


def parse_hours(data: dict, days: int = 7) -> dict[str, list[Hour]]:
    """hourly を日付ごとの時の並びに（最初の days 日だけ）。無い列は None、hourly が無ければ空。"""
    try:
        hourly = data["hourly"]
        times = hourly["time"]
    except (KeyError, TypeError):
        return {}

    def col(name: str) -> list:
        c = hourly.get(name)
        return c if isinstance(c, list) and len(c) == len(times) else [None] * len(times)

    def num(v, kind):
        return None if v is None else kind(v)

    t, h, d, r, p, c, w, g, wd = (col(k) for k in HOURLY_WEATHER)
    out: dict[str, list[Hour]] = {}
    for i, tm in enumerate(times):
        date = str(tm)[:10]
        if date not in out and len(out) >= days:
            continue
        out.setdefault(date, []).append(
            Hour(
                str(tm),
                num(c[i], int),
                num(t[i], float),
                num(h[i], int),
                num(d[i], float),
                num(r[i], float),
                num(p[i], int),
                num(w[i], float),
                num(g[i], float),
                num(wd[i], int),
            )
        )
    return out


@dataclass
class Soil:
    time: str  # 2026-11-08T14:00（Asia/Tokyo）
    temp: dict[str, float | None]  # 深さ → 地温 ℃
    moisture: dict[str, float | None]  # 深さ → 水分 m³/m³
    surface: tuple[str, float] | None = None  # ECMWF の地表面温度（時, ℃）


def parse_soil(data: dict, now: dt.datetime | None = None) -> Soil | None:
    """hourly から、今（Asia/Tokyo）以前で一番新しい時の土の値。hourly が無い・形が違えば None。"""
    try:
        hourly = data["hourly"]
        times = hourly["time"]
        cols = {k: hourly[k] for k in HOURLY}
        if any(len(c) != len(times) for c in cols.values()):
            return None
        now = now or dt.datetime.now(JST).replace(tzinfo=None)
        best = None
        for i, tm in enumerate(times):
            if dt.datetime.fromisoformat(tm) <= now:
                best = i
    except (KeyError, TypeError, ValueError):
        return None
    if best is None:
        return None

    def pick(names: dict[str, str]) -> dict[str, float | None]:
        return {
            label: (None if cols[k][best] is None else float(cols[k][best])) for k, label in names.items()
        }

    return Soil(times[best], pick(SOIL_TEMP), pick(SOIL_MOISTURE))


def fetch_surface(
    lat: float, lon: float, get=None, now: dt.datetime | None = None
) -> tuple[str, float] | None:
    """ECMWF の地表面温度（今以前で一番新しい時, ℃）。どんな失敗でも None（投げない）。"""
    try:
        import httpx

        lat, lon = rounded(lat, lon)
        params = {
            "latitude": f"{lat:.2f}",
            "longitude": f"{lon:.2f}",
            "hourly": "surface_temperature",
            "timezone": TIMEZONE,
            "forecast_days": 1,
        }
        r = (get or httpx.get)(ECMWF_URL, params=params, timeout=10.0)
        if r.status_code != 200:
            return None
        hourly = r.json()["hourly"]
        now = now or dt.datetime.now(JST).replace(tzinfo=None)
        best = None
        for tm, v in zip(hourly["time"], hourly["surface_temperature"], strict=True):
            if v is not None and dt.datetime.fromisoformat(tm) <= now:
                best = (tm, float(v))
        return best
    except Exception:  # noqa: BLE001
        return None


def fetch_forecast(lat: float, lon: float, days: int = 7, get=None) -> list[Forecast]:
    """予報の日ごとだけ（fetch_week の前半）。"""
    return _week(lat, lon, days, get)[0]


def fetch_week(
    lat: float, lon: float, days: int = 16, get=None
) -> tuple[list[Forecast], Soil | None, dict[str, list[Hour]]]:
    """予報、土の値、時間ごとの値、それに ECMWF の地表面温度（二つ目の問い合わせ。取れなくても他は返す）。"""
    rows, soil, hours = _week(lat, lon, days, get)
    surface = fetch_surface(lat, lon, get)
    if surface:
        soil = replace(soil, surface=surface) if soil else Soil("", {}, {}, surface)
    return rows, soil, hours


def _week(
    lat: float, lon: float, days: int = 7, get=None
) -> tuple[list[Forecast], Soil | None, dict[str, list[Hour]]]:
    """Open-Meteo の予報と今の土の値を取る。座標は 2 桁に丸める。get は差し替え用（既定は httpx.get）。失敗は WeatherError。"""
    import httpx

    lat, lon = rounded(lat, lon)
    params = {
        "latitude": f"{lat:.2f}",
        "longitude": f"{lon:.2f}",
        "daily": ",".join((*FORECAST_DAILY, *EXTRA_DAILY)),
        "wind_speed_unit": "ms",
        "hourly": ",".join((*HOURLY_WEATHER, *HOURLY)),
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
    return parse_forecast(data), parse_soil(data), parse_hours(data)


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


COMPASS = {
    "ja": [
        "北",
        "北北東",
        "北東",
        "東北東",
        "東",
        "東南東",
        "南東",
        "南南東",
        "南",
        "南南西",
        "南西",
        "西南西",
        "西",
        "西北西",
        "北西",
        "北北西",
    ],
    "en": [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ],
}


def wind_name(deg: float, language: str) -> str:
    """風向（度。風の来る向き）を 16 方位の語に。"""
    return COMPASS["ja" if language == "ja" else "en"][int((float(deg) % 360) / 22.5 + 0.5) % 16]


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
