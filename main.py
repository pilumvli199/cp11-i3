import os, asyncio, aiohttp, json, pyotp, time
from datetime import datetime
from dotenv import load_dotenv
from SmartApi import SmartConnect
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
from tempfile import NamedTemporaryFile

load_dotenv()

# ---------------- CONFIG ----------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SMARTAPI_CLIENT_ID = os.getenv("SMARTAPI_CLIENT_ID")
SMARTAPI_API_KEY = os.getenv("SMARTAPI_API_KEY")
SMARTAPI_API_SECRET = os.getenv("SMARTAPI_API_SECRET")
SMARTAPI_PASSWORD = os.getenv("SMARTAPI_PASSWORD")
SMARTAPI_TOTP_SECRET = os.getenv("SMARTAPI_TOTP_SECRET")
SMARTAPI_MPIN = os.getenv("SMARTAPI_MPIN")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 300))
SIGNAL_CONF_THRESHOLD = float(os.getenv("SIGNAL_CONF_THRESHOLD", 70.0))

# ---------------- TELEGRAM ----------------
async def send_text(session, text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    await session.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

async def send_photo(session, caption, path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(path, "rb") as f:
        data = aiohttp.FormData()
        data.add_field("chat_id", str(TELEGRAM_CHAT_ID))
        data.add_field("caption", caption)
        data.add_field("photo", f, filename="chart.png", content_type="image/png")
        await session.post(url, data=data)

# ---------------- SMARTAPI LOGIN ----------------
def smartapi_login():
    obj = SmartConnect(api_key=SMARTAPI_API_KEY)

    if SMARTAPI_MPIN:  
        # ✅ MPIN LOGIN
        print("[SmartAPI] Trying MPIN login...")
        data = obj.generateSessionV4(clientcode=SMARTAPI_CLIENT_ID, mpin=SMARTAPI_MPIN)
    else:
        # ✅ PASSWORD + TOTP LOGIN
        if not SMARTAPI_PASSWORD or not SMARTAPI_TOTP_SECRET:
            raise Exception("Password+TOTP or MPIN required!")
        totp = pyotp.TOTP(SMARTAPI_TOTP_SECRET).now()
        print(f"[SmartAPI] Trying Password+TOTP login (OTP={totp})...")
        data = obj.generateSession(clientcode=SMARTAPI_CLIENT_ID,
                                   password=SMARTAPI_PASSWORD,
                                   totp=totp)
    if not data.get("status"):
        raise Exception(f"SmartAPI login failed: {data}")
    print("[SmartAPI] Login success ✅")
    return obj

# ---------------- CHART PLOT ----------------
def plot_chart(candles, symbol):
    times = [datetime.strptime(c[0], "%Y-%m-%d %H:%M") for c in candles]
    opens = [float(c[1]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]

    x = date2num(times)
    fig, ax = plt.subplots(figsize=(8,4), dpi=100)

    for xi, o, h, l, c in zip(x, opens, highs, lows, closes):
        color = "green" if c >= o else "red"
        ax.vlines(xi, l, h, color=color, linewidth=1)
        ax.add_patch(plt.Rectangle((xi-0.2, min(o, c)), 0.4, abs(c-o), facecolor=color))

    ax.set_title(f"{symbol} Candlestick Chart")
    fig.autofmt_xdate()
    tmp = NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(tmp.name, bbox_inches="tight"); plt.close(fig)
    return tmp.name

# ---------------- MAIN LOOP ----------------
async def loop():
    async with aiohttp.ClientSession() as session:
        await send_text(session, "📊 Indian Market Bot Started (SmartAPI)")

        smart = smartapi_login()

        while True:
            try:
                # Example: Fetch NIFTY 5min candles
                params = {
                    "exchange": "NSE",
                    "symboltoken": "99926000",  # NIFTY
                    "interval": "FIVE_MINUTE",
                    "fromdate": "2025-09-16 09:15",
                    "todate": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                data = smart.getCandleData(params)
                candles = data.get("data", [])

                if candles:
                    chart = plot_chart(candles[-50:], "NIFTY")
                    await send_photo(session, "📊 NIFTY Analysis", chart)

            except Exception as e:
                print("Loop error:", e)

            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(loop())
