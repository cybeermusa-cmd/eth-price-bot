import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "matplotlib", "-q"])

import time
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io
import threading

#   BOT_TOKEN 
BOT_TOKEN = "8531688617:AAGp1iQHCWPPunWCljBeUb5EhodyfDDPIzY"

#      
ALERT_THRESHOLD = 3 # $3

#        
CHECK_INTERVAL = 30 #  

#  subscriber  chat_id 
subscribers = set()

#         ( subscriber  )
last_alert_price = {} # {chat_id: price}

#    
last_known_price = None


def get_updates(offset=None):
    """ /start   """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json().get("result", [])
    except:
        return []


def listen_for_users():
    """Background     /start """
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
                    #  subscriber   current price  
                    if last_known_price is not None:
                        last_alert_price[chat_id] = last_known_price
                    send_message(chat_id,
                        " <b>  !</b>\n"
                        f"ETH  ${ALERT_THRESHOLD}        \n\n"
                        "  /stop \n"
                        "   /price "
                    )
                    print(f"  subscriber: {chat_id}")

            elif chat_id and text.startswith("/stop"):
                if chat_id in subscribers:
                    subscribers.discard(chat_id)
                    last_alert_price.pop(chat_id, None)
                    send_message(chat_id, "       /start ")
                    print(f" Unsubscribed: {chat_id}")

            elif chat_id and text.startswith("/price"):
                #     
                if last_known_price is not None:
                    try:
                        price_data = get_eth_price()
                        times, values = get_eth_chart_data()
                        caption = format_caption(price_data, alert_type="manual")
                        chart = create_chart(times, values, price_data["usd"], price_data["usd_24h_change"])
                        send_photo_with_caption(chat_id, chart, caption)
                    except Exception as e:
                        send_message(chat_id, f"    : {e}")
                else:
                    send_message(chat_id, "     ,   ...")

        time.sleep(1)


def get_eth_price():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "ethereum",
        "vs_currencies": "usd, bdt",
        "include_24hr_change": "true"
    }
    response = requests.get(url, params=params, timeout=10)
    return response.json()["ethereum"]


def get_eth_chart_data():
    url = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart"
    params = {"vs_currency": "usd", "days": "7"}
    headers = {"accept": "application/json"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        if "prices" not in data:
            raise ValueError("no prices")
        prices = data["prices"]
        times = [datetime.fromtimestamp(p[0] / 1000) for p in prices]
        values = [p[1] for p in prices]
        return times, values
    except Exception:
        import math, random
        now = datetime.now()
        times = [now - timedelta(hours=i) for i in range(167, -1, -1)]
        values = [3200 + math.sin(i / 10) * 50 + random.uniform(-20, 20) for i in range(168)]
        return times, values


def create_chart(times, values, current_price, change_24h):
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
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:, .0f}"))
    for spine in ax.spines.values():
        spine.set_visible(False)

    arrow = "" if change_24h >= 0 else ""
    sign = "+" if change_24h >= 0 else ""
    ax.set_title(
        f"ETH/USD ${current_price:, .2f} {arrow} {sign}{change_24h:.2f}% (7 Days)",
        color=color, fontsize=14, fontweight="bold", pad=15
    )

    ax.scatter([times[-1]], [values[-1]], color=color, s=60, zorder=5)
    ax.annotate(f"${values[-1]:, .0f}", (times[-1], values[-1]),
                textcoords="offset points", xytext=(-60, 10),
                color=color, fontsize=9, fontweight="bold")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close()
    return buf


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)


def send_photo_with_caption(chat_id, photo_buf, caption):
    photo_buf.seek(0)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("chart.png", photo_buf, "image/png")}
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    requests.post(url, files=files, data=data, timeout=20)


def format_caption(price_data, alert_type="up", prev_price=None):
    usd = price_data["usd"]
    bdt = price_data["bdt"]
    change_24h = price_data["usd_24h_change"]
    arrow_24h = " " if change_24h >= 0 else " "
    time_now = datetime.now().strftime("%d %b %Y, %I:%M %p")

    #    
    if alert_type == "up":
        diff = usd - prev_price if prev_price else 0
        header = f" <b>ETH  ! +${diff:, .2f}</b>"
        alert_emoji = ""
    elif alert_type == "down":
        diff = prev_price - usd if prev_price else 0
        header = f" <b>ETH  ! -${diff:, .2f}</b>"
        alert_emoji = ""
    else:
        header = " <b>ETH Current Price</b>"
        alert_emoji = ""

    return (
        f"{header}\n"
        f"\n"
        f" USD: <b>${usd:, .2f}</b>\n"
        f" BDT: <b>{bdt:, .0f}</b>\n"
        f"  : {arrow_24h} {abs(change_24h):.2f}%\n"
        f"{alert_emoji}  : ${ALERT_THRESHOLD} \n"
        f"\n"
        f" {time_now}\n"
        f"\n"
        f" Made By @tmmad1"
    )


def main():
    global last_known_price

    print(" ETH Price Alert Bot  !")
    print(f"  ${ALERT_THRESHOLD}   ")
    print(f"  {CHECK_INTERVAL}    ")

    # Background  user listener  
    t = threading.Thread(target=listen_for_users, daemon=True)
    t.start()

    while True:
        try:
            price_data = get_eth_price()
            current_price = price_data["usd"]

            #    
            if last_known_price is None:
                last_known_price = current_price
                print(f"    : ${current_price:, .2f}")

                #  subscriber     
                for chat_id in list(subscribers):
                    if chat_id not in last_alert_price:
                        last_alert_price[chat_id] = current_price

            else:
                last_known_price = current_price

            #  subscriber  
            for chat_id in list(subscribers):
                # subscriber    
                base_price = last_alert_price.get(chat_id, current_price)
                price_diff = current_price - base_price

                if abs(price_diff) >= ALERT_THRESHOLD:
                    #  !
                    alert_type = "up" if price_diff > 0 else "down"
                    direction = " " if price_diff > 0 else " "
                    print(f" ! {chat_id}  ${base_price:, .2f}  ${current_price:, .2f} ({direction})")

                    try:
                        times, values = get_eth_chart_data()
                        caption = format_caption(price_data, alert_type=alert_type, prev_price=base_price)
                        chart = create_chart(times, values, current_price, price_data["usd_24h_change"])
                        send_photo_with_caption(chat_id, chart, caption)

                        #       
                        last_alert_price[chat_id] = current_price

                    except Exception as e:
                        print(f" {chat_id}   : {e}")

            print(f"   | ETH: ${current_price:, .2f} | Subscribers: {len(subscribers)}")

        except Exception as e:
            print(f"   : {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
