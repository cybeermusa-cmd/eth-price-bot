import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "matplotlib", "pillow", "-q"])

import time
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import threading

# ✅ শুধু BOT_TOKEN বসান
BOT_TOKEN = "8531688617:AAGp1iQHCWPPunWCljBeUb5EhodyfDDPIzY"

# ⏱️ ২ মিনিট পর পর আপডেট
INTERVAL = 2 * 60

# সব subscriber এর chat_id
subscribers = set()


def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json().get("result", [])
    except:
        return []


def listen_for_users():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            if chat_id and text.startswith("/start"):
                if chat_id not in subscribers:
                    subscribers.add(chat_id)
                    send_message(chat_id,
                        "✅ <b>সাবস্ক্রাইব করা হয়েছে!</b>\n"
                        "প্রতি ২ মিনিটে ETH প্রাইস আপডেট পাবেন। 🚀\n\n"
                        "বন্ধ করতে /stop পাঠান।"
                    )
            elif chat_id and text.startswith("/stop"):
                subscribers.discard(chat_id)
                send_message(chat_id, "❌ আনসাবস্ক্রাইব হয়েছে। আবার পেতে /start পাঠান।")
        time.sleep(1)


def get_eth_price():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "ethereum", "vs_currencies": "usd,bdt", "include_24hr_change": "true"}
    response = requests.get(url, params=params, timeout=10)
    return response.json()["ethereum"]


def create_banner(price_usd, change_24h):
    """রেফারেন্স ছবির মতো সুন্দর banner বানায়"""
    W, H = 1200, 400
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(H):
        ratio = y / H
        r = int(110 + (70 - 110) * ratio)
        g = int(80 + (90 - 80) * ratio)
        b = int(210 + (255 - 210) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Purple left overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for x in range(W // 2):
        alpha = int(60 * (1 - x / (W // 2)))
        ov_draw.line([(x, 0), (x, H)], fill=(140, 60, 255, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Soft blur
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    draw = ImageDraw.Draw(img)

    # Grid dots
    for gx in range(0, W, 45):
        for gy in range(0, H, 45):
            draw.ellipse([gx-1, gy-1, gx+1, gy+1], fill=(255, 255, 255, 25))

    # Left down arrow
    ax, ay = 70, 60
    pts = [(ax+30, ay), (ax, ay+90), (ax+20, ay+90), (ax+20, ay+200), (ax+40, ay+200), (ax+40, ay+90), (ax+60, ay+90)]
    draw.polygon(pts, fill=(100, 210, 255))

    # Right up arrow
    ax2, ay2 = 1070, 110
    pts2 = [(ax2+30, ay2+200), (ax2+60, ay2+110), (ax2+40, ay2+110), (ax2+40, ay2), (ax2+20, ay2), (ax2+20, ay2+110), (ax2, ay2+110)]
    draw.polygon(pts2, fill=(210, 140, 255))

    # ETH coin left
    for cx, cy, sz in [(210, 130, 52), (1010, 265, 46)]:
        draw.ellipse([cx-sz, cy-sz, cx+sz, cy+sz], fill=(160, 160, 185))
        draw.ellipse([cx-sz+5, cy-sz+5, cx+sz-5, cy+sz-5], fill=(200, 200, 220))
        pts_eth = [(cx, cy-28), (cx+16, cy), (cx, cy+12), (cx-16, cy)]
        draw.polygon(pts_eth, fill=(240, 240, 255))

    # Fonts
    try:
        font_big  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_mid  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
        font_sm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_tag  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except:
        font_big = font_mid = font_sm = font_tag = ImageFont.load_default()

    # Price text center
    price_text = f"${price_usd:,.2f}"
    bbox = draw.textbbox((0, 0), price_text, font=font_big)
    tw = bbox[2] - bbox[0]
    px = (W - tw) // 2
    draw.text((px + 4, 124), price_text, font=font_big, fill=(0, 0, 0, 70))  # shadow
    draw.text((px, 120), price_text, font=font_big, fill=(15, 15, 15))

    # Change pill
    arrow_ch = "▲" if change_24h >= 0 else "▼"
    sign = "+" if change_24h >= 0 else ""
    badge_text = f"{arrow_ch} {sign}{change_24h:.2f}%"
    badge_color = (50, 190, 110) if change_24h >= 0 else (210, 70, 70)
    bbox2 = draw.textbbox((0, 0), badge_text, font=font_mid)
    bw = bbox2[2] - bbox2[0] + 40
    bx = (W - bw) // 2
    draw.rounded_rectangle([bx, 258, bx+bw, 300], radius=14, fill=badge_color)
    draw.text((bx+20, 261), badge_text, font=font_mid, fill=(255, 255, 255))

    # Bot handle pill (like reference image)
    handle = " @EthPriiceBot"
    bbox3 = draw.textbbox((0, 0), "✈" + handle, font=font_tag)
    hw = bbox3[2] - bbox3[0] + 50
    hx = (W - hw) // 2
    draw.rounded_rectangle([hx, 315, hx+hw, 360], radius=22, fill=(230, 225, 245))
    draw.rounded_rectangle([hx, 315, hx+hw, 360], radius=22, outline=(200, 195, 225), width=2)
    draw.text((hx+22, 320), "✈" + handle, font=font_tag, fill=(50, 50, 110))

    # ETH PRICE BOT top right
    draw.text((1090, 18), "ETH", font=font_mid, fill=(255, 255, 255))
    draw.text((1068, 52), "PRICE BOT", font=font_sm, fill=(255, 255, 255))

    # Made By bottom left
    draw.text((22, H-52), "Made By", font=font_sm, fill=(210, 210, 240))
    draw.text((22, H-26), "@tmmad1", font=font_tag, fill=(255, 255, 255))

    # Time top center
    time_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    bbox_t = draw.textbbox((0, 0), time_now, font=font_sm)
    tw2 = bbox_t[2] - bbox_t[0]
    draw.text(((W-tw2)//2, 20), time_now, font=font_sm, fill=(240, 240, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)


def send_banner(chat_id, banner_buf, caption):
    banner_buf.seek(0)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("banner.png", banner_buf, "image/png")}
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    requests.post(url, files=files, data=data, timeout=20)


def format_caption(price_data):
    usd = price_data["usd"]
    bdt = price_data["bdt"]
    change_24h = price_data["usd_24h_change"]
    arrow = "🟢 ▲" if change_24h >= 0 else "🔴 ▼"
    time_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    return (
        f"⚡ <b>Ethereum (ETH) Price Update</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💵 USD: <b>${usd:,.2f}</b>\n"
        f"🇧🇩 BDT: <b>৳{bdt:,.0f}</b>\n"
        f"📊 ২৪ঘণ্টার পরিবর্তন: {arrow} {abs(change_24h):.2f}%\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🕐 {time_now}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🛠 Made By @tmmad1"
    )


def main():
    print("✅ ETH Price Bot চালু হয়েছে!")

    t = threading.Thread(target=listen_for_users, daemon=True)
    t.start()

    while True:
        if subscribers:
            try:
                print(f"📡 {len(subscribers)} জনকে পাঠাচ্ছি...")
                price_data = get_eth_price()
                caption = format_caption(price_data)

                for chat_id in list(subscribers):
                    try:
                        banner = create_banner(price_data["usd"], price_data["usd_24h_change"])
                        send_banner(chat_id, banner, caption)
                    except Exception as e:
                        print(f"❌ {chat_id} তে ব্যর্থ: {e}")

                print("✅ সবাইকে পাঠানো হয়েছে!")
            except Exception as e:
                print(f"❌ ত্রুটি: {e}")
        else:
            print("⏳ কোনো subscriber নেই...")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
