import requests
import time
from datetime import datetime

# ==============================
# CONFIGURATION
# ==============================

TWELVE_DATA_KEY = "fc1ae29d28fb4bbfa07d9b7fa1f90e36"
TELEGRAM_TOKEN = "8630059141:AAEHZJmV0iGcdXqniKX7PD1cL83nbdkGPwo"
CHAT_ID = "862548607"

FX_PAIRS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD']

RSI_SETTINGS = {
    'EUR/USD': {'oversold': 30, 'overbought': 70},
    'GBP/USD': {'oversold': 30, 'overbought': 70},
    'USD/JPY': {'oversold': 30, 'overbought': 70},
    'USD/CHF': {'oversold': 30, 'overbought': 70},
    'AUD/USD': {'oversold': 30, 'overbought': 70},
    'USD/CAD': {'oversold': 30, 'overbought': 70}
}

alert_history = {}

# ==============================
# FUNCTIONS
# ==============================

def get_rsi(pair):
    url = "https://api.twelvedata.com/rsi"
    
    params = {
        "symbol": pair,
        "interval": "1min",
        "time_period": 14,
        "apikey": TWELVE_DATA_KEY,
        "outputsize": 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "error":
            print(f"API Error {pair}: {data.get('message')}")
            return None
        
        if "values" in data:
            return float(data["values"][0]["rsi"])
        
    except Exception as e:
        print(f"Error fetching RSI for {pair}: {e}")
    
    return None


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, json=payload)
    except:
        pass


def check_pair(pair):
    rsi = get_rsi(pair)
    
    if rsi is None:
        return
    
    settings = RSI_SETTINGS[pair]
    current_time = time.time()
    
    # Oversold
    if rsi <= settings["oversold"]:
        key = f"{pair}_BUY"
        
        if key not in alert_history or current_time - alert_history[key] > 1800:
            alert_history[key] = current_time
            
            message = f"""
🔴 <b>RSI OVERSOLD ALERT</b>

Pair: {pair}
RSI: {round(rsi,2)}
TF: 1min
Signal: BUY
Time: {datetime.now().strftime('%H:%M:%S')}
"""
            send_telegram(message)
            print(f"{pair} BUY alert sent")
    
    # Overbought
    elif rsi >= settings["overbought"]:
        key = f"{pair}_SELL"
        
        if key not in alert_history or current_time - alert_history[key] > 1800:
            alert_history[key] = current_time
            
            message = f"""
🟢 <b>RSI OVERBOUGHT ALERT</b>

Pair: {pair}
RSI: {round(rsi,2)}
TF: 1min
Signal: SELL
Time: {datetime.now().strftime('%H:%M:%S')}
"""
            send_telegram(message)
            print(f"{pair} SELL alert sent")


# ==============================
# MAIN LOOP
# ==============================

print("🚀 Forex RSI 1min Bot Started...")

while True:
    try:
        for pair in FX_PAIRS:
            print(f"Checking {pair}...")
            check_pair(pair)
            time.sleep(3)  # avoid API limit
        
        print("Waiting 1 minutes...\n")
        time.sleep(300)  # 1 min wait
        
    except KeyboardInterrupt:
        print("Stopped manually")
        break
