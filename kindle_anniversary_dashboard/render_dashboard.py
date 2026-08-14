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
import shutil
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1072, 1448
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out" / "anniversary-dashboard.png"

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


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/Dengb.ttf"] if bold else []) + FONT_CANDIDATES
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def fetch_json(url: str) -> dict:
    """Fetch JSON using headers accepted by both public data providers."""
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Kindle anniversary dashboard; +https://github.com/)",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    })
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


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


def market_news() -> str:
    """A compact real-time A-share briefing from Eastmoney's index quote API."""
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f12,f14,f2,f3,f4,f6&secids=1.000001,0.399001,0.399006"
    try:
        data = fetch_json(url)
        quotes = data.get("data", {}).get("diff", [])
        if isinstance(quotes, dict):
            quotes = list(quotes.values())
        parts = []
        for quote in quotes:
            name = quote.get("f14") or quote.get("f12")
            price, change = quote.get("f2"), quote.get("f3")
            if name and price is not None and change is not None:
                prefix = "+" if float(change) > 0 else ""
                parts.append(f"{name} {float(price):,.2f} {prefix}{float(change):.2f}%")
        if parts:
            return " · ".join(parts)
    except Exception:
        pass
    return "行情服务暂不可达（下次更新将自动重试）"


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


def draw_rule(draw, y: int) -> None:
    draw.line((72, y, WIDTH - 72, y), fill=70, width=2)


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
    image = Image.new("L", (WIDTH, HEIGHT), 248)
    draw = ImageDraw.Draw(image)
    title, date_font, body, small = font(42, True), font(98, True), font(35), font(28)

    draw.text((72, 66), "ParaDog's Day", font=title, fill=25)
    draw.text((72, 150), now.strftime("%Y.%m.%d"), font=date_font, fill=0)
    draw.text((76, 294), "星期" + "一二三四五六日"[now.weekday()], font=body, fill=45)
    draw_cake(image, draw, 790, 82, str(days))
    draw_rule(draw, 362)

    draw.text((72, 418), "北京天气  ·  " + weather(), font=body, fill=20)
    draw_rule(draw, 495)

    draw.text((72, 540), "今日 A 股", font=title, fill=20)
    y = 602
    for line in wrap(draw, market_news(), body, WIDTH - 144)[:3]:
        draw.text((72, y), line, font=body, fill=45)
        y += 49
    draw_rule(draw, 778)

    draw.text((72, 821), "今日笑话", font=title, fill=20)
    y = 882
    joke = JOKES[now.date().toordinal() % len(JOKES)]
    for line in wrap(draw, joke, body, WIDTH - 144)[:2]:
        draw.text((72, y), line, font=body, fill=45)
        y += 49

    draw.rounded_rectangle((72, 1160, WIDTH - 72, 1370), radius=26, outline=45, width=2)
    draw_pet(image, draw, 83, 1196, pet)
    draw.text((310, 1208), f"电子小鸡 · {pet}", font=title, fill=25)
    draw.text((310, 1280), "猜猜接下来我会干嘛？", font=body, fill=50)

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
