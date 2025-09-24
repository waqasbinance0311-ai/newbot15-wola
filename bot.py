import requests
import pandas as pd
import time
from datetime import datetime
import pytz

# ================== CONFIG ==================
API_KEY = "5be1b12e0de6475a850cc5caeea9ac72"  # Twelve Data API key
SYMBOL = "XAU/USD"
INTERVAL = "5min"

TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

RUN_INTERVAL_SECONDS = 60  # check every 1 min

# Pakistan timezone
PKT = pytz.timezone("Asia/Karachi")

# ================== FUNCTIONS ==================
def fetch_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize=100&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        print("❌ Error fetching data:", data)
        return None
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    df["close"] = df["close"].astype(float)
    return df

def calculate_indicators(df):
    df["rsi"] = ta_rsi(df["close"], 14)
    df["atr"] = ta_atr(df, 14)
    return df

def ta_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def ta_atr(df, period=14):
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def in_trading_session():
    now = datetime.now(PKT).time()
    london_start, london_end = datetime.strptime("12:00", "%H:%M").time(), datetime.strptime("16:00", "%H:%M").time()
    ny_start, ny_end = datetime.strptime("17:00", "%H:%M").time(), datetime.strptime("21:00", "%H:%M").time()
    
    return (london_start <= now <= london_end) or (ny_start <= now <= ny_end)

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

def generate_signal(df):
    last = df.iloc[-1]
    rsi = last["rsi"]

    if rsi < 30:
        return f"📉 RSI={rsi:.2f} → BUY XAUUSD (oversold)"
    elif rsi > 70:
        return f"📈 RSI={rsi:.2f} → SELL XAUUSD (overbought)"
    else:
        return None

# ================== MAIN LOOP ==================
def run_bot():
    while True:
        if not in_trading_session():
            print("⏸ Outside trading hours (PKT). No signals.")
            time.sleep(RUN_INTERVAL_SECONDS)
            continue

        df = fetch_data()
        if df is not None:
            df = calculate_indicators(df)
            signal = generate_signal(df)
            if signal:
                send_telegram_message(f"✅ {signal}\n⏰ {datetime.now(PKT).strftime('%Y-%m-%d %H:%M:%S')} PKT")
                print(signal)
            else:
                print("No valid signal at this time.")
        else:
            print("⚠️ Data fetch failed.")

        time.sleep(RUN_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_bot()
