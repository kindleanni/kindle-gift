#!/usr/bin/env python3
"""Generate a 1072x1448 grayscale anniversary dashboard for Kindle PW3.

Run while the Kindle is mounted. The script only writes inside this project
folder and, after the ScreenSavers Hack is installed, its linkss/screensavers
folder. It never changes Kindle firmware or system files.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote as urlquote
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1072, 1448
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out" / "anniversary-dashboard.png"
DISPLAY_FONT = ROOT / "assets" / "fonts" / "UnifrakturCook-Bold.ttf"

# A restrained grayscale palette: enough tonal separation for card hierarchy,
# without faint shadows or gradients that turn muddy on an e-ink panel.
PAPER, CARD, CARD_LIGHT = 248, 242, 252
INK, SECONDARY, BORDER, DIVIDER = 18, 75, 165, 190
MARGIN, RADIUS = 72, 26

PET_STATES = ["学习中", "运动中", "打游戏中", "睡觉中", "做饭中", "逛街中", "洗澡中", "游泳中"]
PET_ART_FILES = {
    "学习中": "studying.png", "运动中": "exercising.png", "打游戏中": "gaming.png", "睡觉中": "sleeping.png",
    "做饭中": "cooking.png", "逛街中": "shopping.png", "洗澡中": "bathing.png", "游泳中": "swimming.png",
}
JOKES = [
    "今天的快乐很简单：见到你，或者想起你。",
    "我问时间为什么过得这么快，它说：因为你在身边。",
    "今日宜：牵手、拥抱、一起吃点好吃的。",
    "小鸡报告：恋爱电量已充满，请继续贴贴。",
    "世界那么大，最想去的地方还是你身边。",
]
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/Deng.ttf",
    "C:/Windows/Fonts/simhei.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


@dataclass(frozen=True)
class QuoteSpec:
    """One compact index shown on the dashboard."""

    code: str
    yahoo_symbol: str
    label: str


@dataclass(frozen=True)
class MarketQuote:
    label: str
    price: float
    change_percent: float


# Tencent's batch endpoint keeps the hourly update to one request.  Yahoo's
# chart endpoint and Eastmoney's existing A-share endpoint below are fallbacks,
# so a transient provider failure only affects the corresponding row.
MARKET_GROUPS: dict[str, tuple[QuoteSpec, ...]] = {
    "a": (
        QuoteSpec("sh000001", "000001.SS", "上证"),
        QuoteSpec("sz399001", "399001.SZ", "深成"),
    ),
    "hk": (
        QuoteSpec("hkHSI", "^HSI", "恒生"),
        QuoteSpec("hkHSTECH", "^HSTECH", "恒生科技"),
    ),
    "us": (
        QuoteSpec("usINX", "^GSPC", "标普 500"),
        QuoteSpec("usIXIC", "^IXIC", "纳斯达克"),
    ),
    # International commodity futures use the latest available settlement when
    # their market is closed, so they remain useful over the weekend too.
    "futures": (
        QuoteSpec("hf_GC", "GC=F", "黄金"),
        QuoteSpec("hf_CL", "CL=F", "WTI 原油"),
    ),
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/Dengb.ttf"] if bold else []) + FONT_CANDIDATES
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def display_font(size: int) -> ImageFont.FreeTypeFont:
    """Load the bundled Fraktur face for the two Latin display lines only."""
    # Bundling the font keeps Windows and GitHub's Ubuntu renderer identical.
    # The Windows face is only a local fallback for an incomplete checkout;
    # body text always stays in the Chinese-capable system font.
    for candidate in (DISPLAY_FONT, Path("C:/Windows/Fonts/swgothe.ttf")):
        try:
            if candidate.is_file():
                return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    return font(size, True)


def fetch_bytes(url: str, extra_headers: dict[str, str] | None = None) -> bytes:
    """Fetch a small public response with one short retry for flaky endpoints."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Kindle anniversary dashboard; +https://github.com/)",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    }
    if extra_headers:
        headers.update(extra_headers)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=12) as response:
                return response.read()
        except (HTTPError, URLError, OSError, TimeoutError) as error:
            last_error = error
            if attempt == 0:
                time.sleep(0.4)
    assert last_error is not None
    raise last_error


def fetch_json(url: str) -> dict:
    """Fetch a JSON document from a public data provider."""
    return json.loads(fetch_bytes(url).decode("utf-8"))


def fetch_text(url: str, *, encoding: str = "utf-8", extra_headers: dict[str, str] | None = None) -> str:
    return fetch_bytes(url, extra_headers).decode(encoding, errors="replace")


def weather() -> str:
    codes = {0: "晴", 1: "大致晴", 2: "多云", 3: "阴", 45: "雾", 48: "雾凇", 51: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪", 75: "大雪", 80: "阵雨", 95: "雷雨"}
    try:
        data = fetch_json("https://api.open-meteo.com/v1/forecast?latitude=39.9042&longitude=116.4074&current=temperature_2m,apparent_temperature,weather_code&timezone=Asia%2FShanghai")
        current = data["current"]
        label = codes.get(current["weather_code"], "天气多变")
        return f"{label}  {current['temperature_2m']:.0f}°C（体感 {current['apparent_temperature']:.0f}°C）"
    except Exception:
        # Independent fallback; wttr.in returns its condition text in JSON.
        try:
            current = fetch_json("https://wttr.in/Beijing?format=j1")["current_condition"][0]
            condition = current["weatherDesc"][0]["value"]
            return f"{condition}  {current['temp_C']}°C（体感 {current['FeelsLikeC']}°C）"
        except Exception:
            return "天气服务暂不可达"


def number(value: object) -> float | None:
    """Turn a provider value into a safe finite number."""
    try:
        result = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def make_quote(spec: QuoteSpec, price: object, previous_close: object) -> MarketQuote | None:
    current, previous = number(price), number(previous_close)
    if current is None or previous in (None, 0):
        return None
    return MarketQuote(spec.label, current, (current - previous) / previous * 100)


def make_percent_quote(spec: QuoteSpec, price: object, change_percent: object) -> MarketQuote | None:
    """Build a quote when a provider already returns percentage change."""
    current, change = number(price), number(change_percent)
    if current is None or change is None:
        return None
    return MarketQuote(spec.label, current, change)


def fetch_tencent_quotes(specs: tuple[QuoteSpec, ...]) -> dict[str, MarketQuote]:
    """Fetch A/HK/US index quotes in one request from Tencent Finance."""
    if not specs:
        return {}
    by_code = {spec.code: spec for spec in specs}
    raw = fetch_text(
        "https://qt.gtimg.cn/q=" + ",".join(by_code),
        encoding="gb18030",
        extra_headers={"Referer": "https://gu.qq.com/"},
    )
    quotes: dict[str, MarketQuote] = {}
    for code, payload in re.findall(r'v_([^=]+)="([^"]*)";', raw):
        spec = by_code.get(code)
        if not spec:
            continue
        if code.startswith("hf_"):
            # Commodity futures use a comma-delimited payload: 0 = price,
            # 1 = already-calculated percentage change.
            fields = payload.split(",")
            quote = make_percent_quote(spec, fields[0], fields[1]) if len(fields) > 1 else None
        else:
            fields = payload.split("~")
            quote = make_quote(spec, fields[3], fields[4]) if len(fields) > 4 else None
        if quote:
            quotes[code] = quote
    return quotes


def fetch_yahoo_quote(spec: QuoteSpec) -> MarketQuote | None:
    """Independent no-key fallback; only used for a quote Tencent did not return."""
    symbol = urlquote(spec.yahoo_symbol, safe="")
    data = fetch_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d")
    result = data.get("chart", {}).get("result", [])
    if not result:
        return None
    chart = result[0]
    meta = chart.get("meta", {})
    close_values = [number(value) for value in chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])]
    close_values = [value for value in close_values if value is not None]
    price = number(meta.get("regularMarketPrice")) or (close_values[-1] if close_values else None)
    previous = number(meta.get("chartPreviousClose")) or number(meta.get("previousClose"))
    if previous is None and len(close_values) >= 2:
        previous = close_values[-2]
    return make_quote(spec, price, previous)


def fetch_yahoo_quotes(specs: tuple[QuoteSpec, ...]) -> dict[str, MarketQuote]:
    """Limit fallback concurrency to avoid slowing an hourly render too much."""
    if not specs:
        return {}
    quotes: dict[str, MarketQuote] = {}
    with ThreadPoolExecutor(max_workers=min(3, len(specs))) as pool:
        futures = {pool.submit(fetch_yahoo_quote, spec): spec for spec in specs}
        for future in as_completed(futures):
            try:
                quote = future.result()
            except Exception:
                continue
            if quote:
                quotes[futures[future].code] = quote
    return quotes


def fetch_eastmoney_a_quotes(specs: tuple[QuoteSpec, ...]) -> dict[str, MarketQuote]:
    """Keep the former provider as a final A-share-only fallback."""
    if not specs:
        return {}
    by_symbol = {spec.code[2:]: spec for spec in specs}
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f12,f2,f3&secids=1.000001,0.399001,0.399006"
    try:
        data = fetch_json(url)
        rows = data.get("data", {}).get("diff", [])
        if isinstance(rows, dict):
            rows = list(rows.values())
        quotes: dict[str, MarketQuote] = {}
        for row in rows:
            spec = by_symbol.get(str(row.get("f12", "")))
            price, change = number(row.get("f2")), number(row.get("f3"))
            if spec and price is not None and change is not None:
                quotes[spec.code] = MarketQuote(spec.label, price, change)
        return quotes
    except Exception:
        return {}


def market_snapshot(now: dt.datetime) -> dict[str, tuple[MarketQuote | None, ...]]:
    """Return A/HK/US/futures data; mainland rows intentionally rest on weekends."""
    weekend = now.weekday() >= 5
    groups = ("hk", "us", "futures") if weekend else ("a", "hk", "us", "futures")
    specs = tuple(spec for group in groups for spec in MARKET_GROUPS[group])
    try:
        quotes = fetch_tencent_quotes(specs)
    except Exception:
        quotes = {}

    # Yahoo's commodity symbols can point at a different contract month.  Use
    # the fallback only for index quotes so an outage cannot create a misleading
    # futures price jump by silently mixing contracts.
    missing = tuple(spec for spec in specs if spec.code not in quotes and not spec.code.startswith("hf_"))
    if missing:
        quotes.update(fetch_yahoo_quotes(missing))

    if not weekend:
        missing_a = tuple(spec for spec in MARKET_GROUPS["a"] if spec.code not in quotes)
        if missing_a:
            quotes.update(fetch_eastmoney_a_quotes(missing_a))

    return {
        group: tuple(quotes.get(spec.code) for spec in MARKET_GROUPS[group])
        for group in groups
    }


def wrap(draw: ImageDraw.ImageDraw, value: str, fnt, max_width: int) -> list[str]:
    lines, line = [], ""
    for char in value:
        test = line + char
        if draw.textlength(test, font=fnt) > max_width and line:
            lines.append(line)
            line = char
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def draw_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, fill: int = CARD) -> None:
    draw.rounded_rectangle(box, radius=RADIUS, fill=fill, outline=BORDER, width=2)


def draw_eyebrow(draw: ImageDraw.ImageDraw, x: int, y: int, value: str) -> None:
    draw.text((x, y), value, font=font(22, True), fill=SECONDARY)


def draw_weekday_reminder(draw: ImageDraw.ImageDraw, x: int, y: int, weekday: int) -> None:
    """A quiet inline weekday/reminder line, without the former black badge."""
    weekday_font = font(29, True)
    reminder_font = font(23)
    weekday_text = "星期" + "一二三四五六日"[weekday]
    reminder = "请多喝水、按时吃饭、注意保暖、不要久坐：）"
    draw.text((x, y), weekday_text, font=weekday_font, fill=INK)
    cursor = x + math.ceil(draw.textlength(weekday_text, font=weekday_font)) + 16
    draw.text((cursor, y + 4), "·", font=font(21, True), fill=BORDER)
    draw.text((cursor + 23, y + 5), reminder, font=reminder_font, fill=SECONDARY)


def draw_shuttlecock(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    """A tiny badminton cue for the weekend note, legible in one color."""
    draw.ellipse((x + 10, y + 25, x + 30, y + 41), fill=PAPER, outline=INK, width=2)
    draw.polygon(((x + 13, y + 27), (x + 3, y + 1), (x + 19, y + 25)), outline=INK)
    draw.polygon(((x + 20, y + 25), (x + 21, y), (x + 31, y + 26)), outline=INK)
    draw.polygon(((x + 27, y + 27), (x + 40, y + 4), (x + 32, y + 31)), outline=INK)


def quote_change_text(quote: MarketQuote) -> str:
    if quote.change_percent > 0.005:
        arrow, prefix = "↑", "+"
    elif quote.change_percent < -0.005:
        arrow, prefix = "↓", ""
    else:
        arrow, prefix = "—", ""
    return f"{arrow}{prefix}{quote.change_percent:.2f}%"


def draw_market_group(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    label: str,
    group_key: str,
    quotes: tuple[MarketQuote | None, ...],
    *,
    divider: bool,
) -> None:
    """Draw two compact metric tiles in one iOS-style market row."""
    draw.text((x, y + 24), label, font=font(29, True), fill=INK)
    specs = MARKET_GROUPS[group_key]
    data_x = x + 122
    data_width = width - 122
    slot_width = data_width / max(1, len(specs))
    for index, (spec, quote) in enumerate(zip(specs, quotes)):
        quote_x = round(data_x + index * slot_width)
        if index:
            draw.line((quote_x - 14, y + 12, quote_x - 14, y + 63), fill=DIVIDER, width=1)
        visible_label = quote.label if quote else spec.label
        if quote:
            price_text = f"{visible_label} {quote.price:,.2f}"
            change_text = quote_change_text(quote)
        else:
            price_text = f"{visible_label} 暂不可达"
            change_text = "下次更新重试"
        price_font = font(22, True)
        if draw.textlength(price_text, font=price_font) > slot_width - 22:
            price_font = font(20, True)
        draw.text((quote_x, y + 10), price_text, font=price_font, fill=SECONDARY)
        draw.text((quote_x, y + 41), change_text, font=font(21, True), fill=INK if quote else SECONDARY)
    if divider:
        draw.line((x, y + 76, x + width, y + 76), fill=DIVIDER, width=1)


def draw_chick(draw: ImageDraw.ImageDraw, x: int, y: int, state: str) -> None:
    """Draw eight distinct cartoon scenes; all shapes survive grayscale e-ink."""
    ink, feather, paper = 20, 225, 248

    def bird(cx: int, cy: int, *, glasses: bool = False, sleepy: bool = False, goggles: bool = False) -> None:
        """A consistently cute little chick; scenes supply the story around it."""
        draw.ellipse((cx - 40, cy - 17, cx + 42, cy + 63), fill=feather, outline=ink, width=4)
        draw.ellipse((cx - 8, cy - 56, cx + 58, cy + 11), fill=paper, outline=ink, width=4)
        draw.ellipse((cx - 31, cy + 9, cx + 4, cy + 43), outline=ink, width=3)  # wing
        for dx in (-2, 10, 22):
            draw.line((cx + dx, cy - 51, cx + dx + 7, cy - 65), fill=ink, width=3)
        # eyes, cheek, smile, beak and feet
        if sleepy:
            draw.arc((cx + 9, cy - 29, cx + 21, cy - 18), 0, 180, fill=ink, width=2)
            draw.arc((cx + 32, cy - 29, cx + 44, cy - 18), 0, 180, fill=ink, width=2)
        else:
            draw.ellipse((cx + 13, cy - 25, cx + 20, cy - 18), fill=ink)
            draw.ellipse((cx + 36, cy - 25, cx + 43, cy - 18), fill=ink)
        if glasses:
            draw.ellipse((cx + 4, cy - 33, cx + 25, cy - 12), outline=ink, width=2)
            draw.ellipse((cx + 30, cy - 33, cx + 51, cy - 12), outline=ink, width=2)
            draw.line((cx + 25, cy - 23, cx + 30, cy - 23), fill=ink, width=2)
        if goggles:
            draw.rounded_rectangle((cx + 2, cy - 34, cx + 52, cy - 12), 8, outline=ink, width=3)
            draw.line((cx - 7, cy - 23, cx + 2, cy - 23), fill=ink, width=2)
        draw.ellipse((cx + 1, cy - 9, cx + 10, cy - 4), fill=140)
        draw.arc((cx + 22, cy - 14, cx + 38, cy), 10, 170, fill=ink, width=2)
        draw.polygon(((cx + 57, cy - 10), (cx + 71, cy - 4), (cx + 57, cy + 2)), outline=ink)
        draw.line((cx - 11, cy + 62, cx - 17, cy + 74), fill=ink, width=3)
        draw.line((cx + 14, cy + 62, cx + 20, cy + 74), fill=ink, width=3)

    # Each branch contains a complete little activity scene, not just a symbol.
    if state == "学习中":
        draw.line((x + 8, y + 141, x + 198, y + 141), fill=ink, width=4)  # desk
        draw.rectangle((x + 22, y + 91, x + 80, y + 129), fill=paper, outline=ink, width=3)
        draw.line((x + 51, y + 91, x + 51, y + 129), fill=ink, width=2)
        draw.line((x + 29, y + 105, x + 44, y + 105), fill=ink, width=2)
        draw.line((x + 58, y + 105, x + 73, y + 105), fill=ink, width=2)
        draw.arc((x + 167, y + 54, x + 193, y + 89), 180, 360, fill=ink, width=3)  # lamp
        draw.line((x + 180, y + 71, x + 180, y + 137), fill=ink, width=3)
        bird(x + 123, y + 81, glasses=True)
    elif state == "运动中":
        for dx in (0, 18, 36):
            draw.arc((x + dx, y + 118, x + dx + 32, y + 138), 180, 360, fill=ink, width=3)
        draw.line((x + 24, y + 58, x + 53, y + 58), fill=ink, width=4)  # dumbbell
        draw.rectangle((x + 11, y + 47, x + 23, y + 69), outline=ink, width=3)
        draw.rectangle((x + 54, y + 47, x + 66, y + 69), outline=ink, width=3)
        bird(x + 118, y + 65)
        draw.line((x + 100, y + 121, x + 80, y + 139), fill=ink, width=4)  # running leg
        draw.arc((x + 167, y + 25, x + 206, y + 64), 200, 80, fill=ink, width=3)
    elif state == "打游戏中":
        draw.rounded_rectangle((x + 15, y + 25, x + 78, y + 74), 5, outline=ink, width=4)  # monitor
        draw.line((x + 47, y + 74, x + 47, y + 91), fill=ink, width=3)
        draw.line((x + 28, y + 91, x + 66, y + 91), fill=ink, width=3)
        draw.line((x + 34, y + 49, x + 58, y + 49), fill=ink, width=3)
        draw.line((x + 46, y + 37, x + 46, y + 61), fill=ink, width=3)
        bird(x + 128, y + 83)
        draw.rounded_rectangle((x + 82, y + 129, x + 124, y + 151), 7, outline=ink, width=3)
        draw.line((x + 91, y + 140, x + 103, y + 140), fill=ink, width=2)
        draw.line((x + 97, y + 134, x + 97, y + 146), fill=ink, width=2)
    elif state == "睡觉中":
        draw.rounded_rectangle((x + 7, y + 96, x + 190, y + 145), 7, fill=paper, outline=ink, width=4)  # bed
        draw.rectangle((x + 13, y + 98, x + 57, y + 122), fill=feather, outline=ink, width=2)
        draw.line((x + 19, y + 145, x + 19, y + 155), fill=ink, width=3)
        draw.line((x + 175, y + 145, x + 175, y + 155), fill=ink, width=3)
        bird(x + 104, y + 77, sleepy=True)
        draw.text((x + 151, y + 21), "Z", font=font(31, True), fill=ink)
        draw.text((x + 177, y + 7), "z", font=font(21, True), fill=80)
    elif state == "做饭中":
        draw.rectangle((x + 3, y + 113, x + 79, y + 142), fill=paper, outline=ink, width=3)  # stove
        draw.ellipse((x + 12, y + 95, x + 67, y + 119), outline=ink, width=4)  # pan
        draw.line((x + 61, y + 106, x + 94, y + 90), fill=ink, width=4)
        draw.arc((x + 23, y + 74, x + 37, y + 99), 170, 350, fill=ink, width=2)
        bird(x + 126, y + 77)
        # chef hat
        draw.ellipse((x + 104, y + 0, x + 141, y + 32), fill=paper, outline=ink, width=3)
        draw.ellipse((x + 130, y - 4, x + 166, y + 32), fill=paper, outline=ink, width=3)
        draw.rectangle((x + 108, y + 25, x + 160, y + 40), fill=paper, outline=ink, width=3)
    elif state == "逛街中":
        bird(x + 77, y + 74)
        draw.rectangle((x + 138, y + 78, x + 188, y + 131), fill=paper, outline=ink, width=3)  # shopping bag
        draw.arc((x + 148, y + 57, x + 178, y + 93), 180, 360, fill=ink, width=3)
        draw.ellipse((x + 151, y + 101, x + 158, y + 108), fill=ink)
        draw.ellipse((x + 170, y + 101, x + 177, y + 108), fill=ink)
        draw.line((x + 5, y + 143, x + 196, y + 143), fill=ink, width=3)
        for sx in (21, 45, 170):
            draw.line((x + sx, y + 25, x + sx, y + 48), fill=ink, width=2)
            draw.line((x + sx - 8, y + 35, x + sx + 8, y + 35), fill=ink, width=2)
    elif state == "洗澡中":
        draw.rounded_rectangle((x + 9, y + 89, x + 190, y + 147), 18, fill=paper, outline=ink, width=4)  # tub
        draw.line((x + 17, y + 110, x + 182, y + 110), fill=ink, width=2)
        bird(x + 106, y + 69, sleepy=True)
        for dx, dy, size in ((13, 28, 13), (42, 11, 18), (157, 30, 15), (178, 5, 9)):
            draw.ellipse((x + dx, y + dy, x + dx + size, y + dy + size), outline=ink, width=2)
    else:  # 游泳中
        for wave_y in (111, 128, 145):
            for wave_x in range(0, 190, 38):
                draw.arc((x + wave_x, y + wave_y, x + wave_x + 38, y + wave_y + 17), 180, 360, fill=ink, width=3)
        bird(x + 96, y + 75, goggles=True)
        draw.line((x + 44, y + 84, x + 62, y + 72), fill=ink, width=3)  # raised swimming wing
        draw.line((x + 62, y + 72, x + 76, y + 83), fill=ink, width=3)


def draw_pet(image: Image.Image, draw: ImageDraw.ImageDraw, x: int, y: int, state: str) -> None:
    """Use a hand-drawn PNG when provided; otherwise draw the built-in cartoon scene."""
    artwork = ROOT / "assets" / "pets" / PET_ART_FILES[state]
    if artwork.is_file():
        try:
            with Image.open(artwork) as raw:
                # The supplied drawings use an opaque white canvas. Convert only the
                # near-white paper to transparency, preserving anti-aliased ink lines.
                luminance = raw.convert("L")
                alpha = luminance.point(lambda pixel: 0 if pixel >= 245 else min(255, (245 - pixel) * 4))
                pet = Image.merge("RGBA", (luminance, luminance, luminance, alpha))
                pet.thumbnail((210, 170), Image.Resampling.LANCZOS)
                left = x + (210 - pet.width) // 2
                top = y + (165 - pet.height) // 2
                image.paste(pet.convert("L"), (left, top), pet.getchannel("A"))
                return
        except OSError:
            # A malformed optional drawing should never prevent an hourly update.
            pass
    draw_chick(draw, x, y, state)


def draw_cake(image: Image.Image, draw: ImageDraw.ImageDraw, x: int, y: int, digits: str) -> None:
    """A three-layer, same-width strawberry naked cake, matching the reference."""
    generated_asset = ROOT / "assets" / "cake" / "strawberry-naked-cake.png"
    if generated_asset.is_file() and len(digits) == 4:
        try:
            with Image.open(generated_asset) as source:
                target_width = 314
                target_height = round(source.height * target_width / source.width)
                cake = source.convert("L").resize((target_width, target_height), Image.Resampling.LANCZOS)
                # Match the dashboard's off-white background instead of leaving a visible white rectangle.
                cake = cake.point(lambda value: 248 if value > 242 else value)
                asset_left, asset_top = x - 50, y - 76
                image.paste(cake, (asset_left, asset_top))

                # The illustration supplies the cake; rewrite only the digits so the day count stays live.
                scale = target_width / source.width
                digit_boxes = ((320, 160, 366, 242), (490, 160, 536, 242), (657, 160, 703, 242), (826, 160, 872, 242))
                digit_font = font(17, True)
                for digit, (left, top, right, bottom) in zip(digits, digit_boxes):
                    box = (asset_left + round(left * scale), asset_top + round(top * scale), asset_left + round(right * scale), asset_top + round(bottom * scale))
                    draw.rectangle(box, fill=248)
                    text_box = draw.textbbox((0, 0), digit, font=digit_font)
                    text_x = box[0] + ((box[2] - box[0]) - (text_box[2] - text_box[0])) / 2
                    text_y = box[1] + 1
                    draw.text((text_x, text_y), digit, font=digit_font, fill=15)
                return
        except OSError:
            # Keep the vector fallback so an absent/corrupt optional image never breaks an update.
            pass

    ink, cream, sponge, berry, paper = 20, 246, 184, 62, 248
    left, right = x - 24, x + 214
    candle_font = font(25, True)

    def whole_strawberry(sx: int, sy: int, size: int) -> None:
        # Round shoulders + pointed tip produce a recognisable berry silhouette.
        draw.ellipse((sx, sy, sx + size, sy + size - 5), fill=berry, outline=ink, width=2)
        draw.polygon(((sx + 3, sy + size // 2), (sx + size - 3, sy + size // 2), (sx + size // 2, sy + size + 6)), fill=berry, outline=ink)
        draw.line((sx + size // 2, sy + 2, sx + size // 2, sy - 6), fill=ink, width=2)
        draw.polygon(((sx + size // 2, sy + 2), (sx + size // 2 - 8, sy - 2), (sx + size // 2 - 2, sy + 7)), outline=ink)
        draw.polygon(((sx + size // 2, sy + 2), (sx + size // 2 + 8, sy - 2), (sx + size // 2 + 2, sy + 7)), outline=ink)
        for dx, dy in ((size // 3, size // 3), (size * 2 // 3, size // 3 + 2), (size // 2, size * 2 // 3)):
            draw.ellipse((sx + dx, sy + dy, sx + dx + 3, sy + dy + 3), fill=cream)

    def strawberry_slice(sx: int, sy: int, size: int = 25) -> None:
        draw.pieslice((sx, sy, sx + size, sy + size), 180, 360, fill=berry, outline=ink)
        draw.line((sx + 1, sy + size // 2, sx + size - 1, sy + size // 2), fill=cream, width=2)
        for dx in (7, 14, 20):
            draw.ellipse((sx + dx, sy + size // 2 + 4, sx + dx + 3, sy + size // 2 + 7), fill=cream)

    # Four deliberately simple slim candles, with no large flames or holders.
    candle_start = x + 18
    for index, digit in enumerate(digits):
        cx = candle_start + index * 48
        draw.rectangle((cx, y + 4, cx + 22, y + 59), fill=paper, outline=ink, width=2)
        draw.line((cx + 11, y, cx + 11, y + 4), fill=ink, width=2)
        draw.text((cx + 3, y + 20), digit, font=candle_font, fill=ink)

    # A small, natural crown of berries rather than a thick blanket of icing.
    for sx, sy, size in ((x + 22, y + 60, 25), (x + 59, y + 48, 31), (x + 101, y + 57, 28), (x + 145, y + 61, 24)):
        whole_strawberry(sx, sy, size)

    # All three sponge layers share exactly the same left and right edge.
    layers = ((y + 96, y + 126), (y + 147, y + 177), (y + 198, y + 228))
    for top, bottom in layers:
        draw.rounded_rectangle((left, top, right, bottom), radius=4, fill=sponge, outline=ink, width=3)
        # a restrained crumb texture
        for crumb_x in range(left + 18, right - 8, 31):
            draw.line((crumb_x, top + 9, crumb_x + 7, top + 9), fill=125, width=1)

    # Thin irregular cream bands are drawn between the aligned sponges.
    for band_y in (y + 126, y + 177):
        draw.rectangle((left, band_y, right, band_y + 21), fill=cream, outline=ink, width=2)
        for dollop_x in range(left + 10, right - 15, 38):
            draw.ellipse((dollop_x, band_y - 5, dollop_x + 31, band_y + 11), fill=cream, outline=ink, width=1)

    # Fruit peeks naturally out of the two thin cream layers.
    for sx in (x - 3, x + 45, x + 94, x + 143):
        strawberry_slice(sx, y + 123)
    for sx in (x + 18, x + 69, x + 120):
        strawberry_slice(sx, y + 174)
    # A lightly whipped top edge, intentionally much less ornate than rosettes.
    draw.line((left + 4, y + 95, right - 4, y + 95), fill=ink, width=2)
    for dollop_x in range(left + 13, right - 18, 42):
        draw.arc((dollop_x, y + 87, dollop_x + 30, y + 104), 180, 360, fill=ink, width=2)
    draw.ellipse((left - 20, y + 229, right + 20, y + 248), fill=paper, outline=ink, width=2)


def render() -> Path:
    # CI servers usually run in UTC; this screen is explicitly for Beijing time.
    now = dt.datetime.now(ZoneInfo("Asia/Shanghai"))
    together_since = dt.date(2023, 8, 21)
    days = (now.date() - together_since).days
    # A given hour always has the same pet state, avoiding changes on each run.
    pet = PET_STATES[(now.date().toordinal() * 24 + now.hour) % len(PET_STATES)]
    weekend = now.weekday() >= 5
    try:
        markets = market_snapshot(now)
    except Exception:
        # Rendering a graceful screen is more important than one provider's outage.
        markets = {"hk": (None, None), "us": (None, None), "futures": (None, None)}
        if not weekend:
            markets["a"] = (None, None)

    image = Image.new("L", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    title, date_font, body = display_font(54), display_font(88), font(34)

    # Header: generous whitespace, one large date, and the cake as the quiet
    # anniversary cue rather than another information card.
    draw.text((MARGIN, 40), "ParaDog's Day", font=title, fill=INK)
    draw.text((MARGIN, 116), now.strftime("%Y.%m.%d"), font=date_font, fill=INK)
    draw_weekday_reminder(draw, MARGIN, 286, now.weekday())
    draw_cake(image, draw, 770, 82, str(days))
    draw.line((MARGIN, 360, WIDTH - MARGIN, 360), fill=DIVIDER, width=2)

    # Weather is a concise, standalone information card.
    weather_top = 386
    draw_card(draw, (MARGIN, weather_top, WIDTH - MARGIN, weather_top + 132))
    draw_eyebrow(draw, MARGIN + 28, weather_top + 20, "BEIJING · WEATHER")
    weather_text = weather()
    weather_font = font(36)
    for index, line in enumerate(wrap(draw, weather_text, weather_font, WIDTH - MARGIN * 2 - 56)[:2]):
        draw.text((MARGIN + 28, weather_top + 58 + index * 39), line, font=weather_font, fill=INK)

    # A grouped market card replaces the former newspaper-like text block.
    market_top, market_bottom = 548, 976
    draw_card(draw, (MARGIN, market_top, WIDTH - MARGIN, market_bottom))
    draw.text((MARGIN + 28, market_top + 20), "市场速览", font=font(39, True), fill=INK)
    hint = "行情可能延迟 · 最近交易日"
    hint_font = font(23)
    hint_width = draw.textlength(hint, font=hint_font)
    draw.text((WIDTH - MARGIN - 28 - hint_width, market_top + 33), hint, font=hint_font, fill=SECONDARY)

    row_x, row_width = MARGIN + 28, WIDTH - MARGIN * 2 - 56
    if weekend:
        banner_top = market_top + 75
        draw.rounded_rectangle((row_x, banner_top, row_x + row_width, banner_top + 58), radius=18, fill=232, outline=BORDER, width=1)
        draw_shuttlecock(draw, row_x + 10, banner_top + 8)
        draw.text(
            (row_x + 59, banner_top + 15),
            "这一周的交易辛苦啦！现在是羽毛球时间枭枭枭",
            font=font(25, True),
            fill=INK,
        )
        draw_market_group(draw, row_x, market_top + 154, row_width, "港股", "hk", markets["hk"], divider=True)
        draw_market_group(draw, row_x, market_top + 232, row_width, "美股", "us", markets["us"], divider=True)
        draw_market_group(draw, row_x, market_top + 310, row_width, "期货", "futures", markets["futures"], divider=False)
    else:
        draw_market_group(draw, row_x, market_top + 76, row_width, "A 股", "a", markets["a"], divider=True)
        draw_market_group(draw, row_x, market_top + 154, row_width, "港股", "hk", markets["hk"], divider=True)
        draw_market_group(draw, row_x, market_top + 232, row_width, "美股", "us", markets["us"], divider=True)
        draw_market_group(draw, row_x, market_top + 310, row_width, "期货", "futures", markets["futures"], divider=False)

    # The joke has its own quiet card, preserving a little breathing room.
    joke_top = 1008
    draw_card(draw, (MARGIN, joke_top, WIDTH - MARGIN, joke_top + 150), fill=CARD_LIGHT)
    draw_eyebrow(draw, MARGIN + 28, joke_top + 20, "TODAY'S LITTLE NOTE")
    y = joke_top + 58
    joke = JOKES[now.date().toordinal() % len(JOKES)]
    for line in wrap(draw, joke, body, WIDTH - MARGIN * 2 - 56)[:2]:
        draw.text((MARGIN + 28, y), line, font=body, fill=INK)
        y += 42

    # The hand-drawn pet remains tactile and personal, with a clean divider
    # separating illustration from its current little life update.
    pet_top = 1190
    draw_card(draw, (MARGIN, pet_top, WIDTH - MARGIN, 1398), fill=CARD_LIGHT)
    draw.line((298, pet_top + 22, 298, 1376), fill=DIVIDER, width=2)
    draw_pet(image, draw, 83, pet_top + 30, pet)
    draw_eyebrow(draw, 328, pet_top + 25, "A LITTLE CHECK-IN")
    draw.text((328, pet_top + 67), f"电子小鸡 · {pet}", font=font(40, True), fill=INK)
    draw.text((328, pet_top + 137), "猜猜接下来我会干嘛？", font=body, fill=SECONDARY)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, "PNG", optimize=True)
    return OUT


def publish(kindle_root: Path, source: Path) -> Path:
    target_dir = kindle_root / "linkss" / "screensavers"
    if not target_dir.exists():
        raise FileNotFoundError("未找到 linkss/screensavers。请先完成越狱并安装 ScreenSavers Hack。")
    # Online Screensaver's stock configuration refreshes this filename.  Keeping
    # a single, stable PNG in linkss/screensavers also prevents linkss cycling
    # between an old USB preview and the cloud-downloaded dashboard.
    target = target_dir / "bg_ss00.png"
    shutil.copy2(source, target)
    # The hack sees this marker after unplugging and performs its safe short reboot.
    (kindle_root / "linkss" / "reboot").touch()
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kindle-root", type=Path, help="e.g. F:\\; publish to linkss/screensavers when installed")
    args = parser.parse_args()
    output = render()
    print(f"Dashboard generated: {output}")
    if args.kindle_root:
        try:
            print(f"Published to: {publish(args.kindle_root, output)}")
        except FileNotFoundError as error:
            print(f"Not published: {error}")
