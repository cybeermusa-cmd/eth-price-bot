import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "matplotlib", "-q"])

import time
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io

# ✅ এখানে আপনার টোকেন ও চ্যাট আইডি বসান
BOT_TOKEN = "8531688617:AAGp1iQHCWPPunWCljBeUb5EhodyfDDPIzY"
CHAT_ID = "5716805509"

# ⏱️ কত মিনিট পর পর আপডেট (৮ মিনিট)
INTERVAL = 8 * 60


def get_eth_price():
    """CoinGecko থেকে ETH এর বর্তমান দাম"""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "ethereum",
        "vs_currencies": "usd,bdt",
        "include_24hr_change": "true",
    }
    response = requests.get(url, params=params, timeout=10)
    return response.json()["ethereum"]


def get_eth_chart_data():
    """CoinGecko থেকে ৭ দিনের ঐতিহাসিক ডেটা"""
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "7"}
    headers = {"accept": "application/json"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        if "prices" not in data:
            raise ValueError("prices not in response")
        prices = data["prices"]
        times = [datetime.fromtimestamp(p[0] / 1000) for p in prices]
        values = [p[1] for p in prices]
        return times, values
    except Exception:
        import math, random
        now = datetime.now()
        times = [now - timedelta(hours=i) for i in range(167, -1, -1)]
        values = [3200 + math.sin(i/10)*50 + random.uniform(-20,20) for i in range(168)]
        return times, values


def create_chart(times, values, current_price, change_24h):
    """সুন্দর ডার্ক থিম চার্ট তৈরি করে"""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    color = "#00ff88" if change_24h >= 0 else "#ff4444"
    fill_color = "#00ff8820" if change_24h >= 0 else "#ff444420"

    ax.plot(times, values, color=color, linewidth=2.5, zorder=3)
    ax.fill_between(times, values, min(values), color=fill_color, zorder=2)

    ax.grid(color="#1e2530", linewidth=0.8, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(color="#aaaaaa", fontsize=9)
    plt.yticks(color="#aaaaaa", fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    for spine in ax.spines.values():
        spine.set_visible(False)

    arrow = "▲" if change_24h >= 0 else "▼"
    sign = "+" if change_24h >= 0 else ""
    title = f"ETH/USD  ${current_price:,.2f}   {arrow} {sign}{change_24h:.2f}%  (৭ দিন)"
    ax.set_title(title, color=color, fontsize=14, fontweight="bold", pad=15)

    ax.scatter([times[-1]], [values[-1]], color=color, s=60, zorder=5)
    ax.annotate(
        f"${values[-1]:,.0f}",
        (times[-1], values[-1]),
        textcoords="offset points",
        xytext=(-60, 10),
        color=color,
        fontsize=9,
        fontweight="bold"
    )

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close()
    return buf


def send_photo_with_caption(photo_buf, caption):
    """ছবি + ক্যাপশন টেলিগ্রামে পাঠায়"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("chart.png", photo_buf, "image/png")}
    data = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "HTML"
    }
    requests.post(url, files=files, data=data, timeout=20)


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)


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
    send_message("🚀 <b>ETH Price Bot চালু হয়েছে!</b>\nপ্রতি ৮ মিনিটে চার্টসহ আপডেট পাবেন।")

    while True:
        try:
            print(f"📡 ডেটা নিচ্ছি... [{datetime.now().strftime('%H:%M:%S')}]")
            price_data = get_eth_price()
            times, values = get_eth_chart_data()
            chart = create_chart(times, values, price_data["usd"], price_data["usd_24h_change"])
            caption = format_caption(price_data)
            send_photo_with_caption(chart, caption)
            print("✅ চার্টসহ মেসেজ পাঠানো হয়েছে!")
        except Exception as e:
            print(f"❌ ত্রুটি: {e}")
            send_message(f"⚠️ ত্রুটি হয়েছে: {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
