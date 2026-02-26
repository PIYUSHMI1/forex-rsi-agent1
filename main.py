from flask import Flask, jsonify
import requests
import time
import os
import logging
from datetime import datetime
import threading
import sys

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ForexRSIAgent:
    def __init__(self):
        # Major Forex Pairs - EXACT format like Jupiter code
        self.fx_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/SD', 'USD/CAD']
        
        # RSI Settings - exactly like Jupiter code
        self.rsi_settings = {
            'EUR/USD': {'oversold': 30, 'overbought': 70},
            'GBP/USD': {'oversold': 30, 'overbought': 70},
            'USD/JPY': {'oversold': 30, 'overbought': 70},
            'USD/CHF': {'oversold': 30, 'overbought': 70},
            'AUD/USD': {'oversold': 30, 'overbought': 70},
            'USD/CAD': {'oversold': 30, 'overbought': 70}
        }
        
        # API Keys from environment
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.twelve_data_key = os.environ.get('TWELVE_DATA_KEY')
        
        # Alert history (30 minute cooldown like Jupiter code)
        self.alert_history = {}
        
        logger.info("=" * 50)
        logger.info("🚀 FOREX RSI AGENT INITIALIZED")
        logger.info(f"📊 Monitoring: {', '.join(self.fx_pairs)}")
        logger.info(f"📱 Telegram: {'✅' if self.telegram_token and self.chat_id else '❌'}")
        logger.info(f"🔑 Twelve Data: {'✅' if self.twelve_data_key else '❌'}")
        logger.info("=" * 50)
    
    def get_rsi(self, pair):
        """EXACT same as Jupiter code - with direct symbol"""
        url = "https://api.twelvedata.com/rsi"
        
        params = {
            "symbol": pair,  # Direct EUR/USD, no formatting needed!
            "interval": "5min",  # Jupiter code uses 5min
            "time_period": 14,
            "apikey": self.twelve_data_key,
            "outputsize": 1
        }
        
        try:
            logger.info(f"📡 Fetching RSI for {pair}")
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("status") == "error":
                logger.error(f"API Error {pair}: {data.get('message')}")
                return None
            
            if "values" in data and len(data["values"]) > 0:
                rsi = float(data["values"][0]["rsi"])
                logger.info(f"✅ {pair} RSI: {rsi:.2f}")
                return rsi
            
            logger.warning(f"⚠️ No values in response for {pair}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching RSI for {pair}: {e}")
            return None
    
    def send_telegram(self, message):
        """EXACT same as Jupiter code"""
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info("📱 Telegram alert sent")
            else:
                logger.error(f"❌ Telegram error: {response.text}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    def check_pair(self, pair):
        """EXACT same logic as Jupiter code"""
        rsi = self.get_rsi(pair)
        
        if rsi is None:
            return
        
        settings = self.rsi_settings[pair]
        current_time = time.time()
        
        # Oversold - BUY signal
        if rsi <= settings["oversold"]:
            key = f"{pair}_BUY"
            
            # 30 minute cooldown (1800 seconds) like Jupiter code
            if key not in self.alert_history or (current_time - self.alert_history[key]) > 1800:
                self.alert_history[key] = current_time
                
                message = f"""
🔴 <b>RSI OVERSOLD ALERT</b>

Pair: {pair}
RSI: {round(rsi, 2)}
TF: 5min
Signal: BUY
Time: {datetime.now().strftime('%H:%M:%S')}
"""
                self.send_telegram(message)
                logger.info(f"🔴 {pair} BUY alert sent")
        
        # Overbought - SELL signal
        elif rsi >= settings["overbought"]:
            key = f"{pair}_SELL"
            
            if key not in self.alert_history or (current_time - self.alert_history[key]) > 1800:
                self.alert_history[key] = current_time
                
                message = f"""
🟢 <b>RSI OVERBOUGHT ALERT</b>

Pair: {pair}
RSI: {round(rsi, 2)}
TF: 5min
Signal: SELL
Time: {datetime.now().strftime('%H:%M:%S')}
"""
                self.send_telegram(message)
                logger.info(f"🟢 {pair} SELL alert sent")

# Initialize agent
agent = ForexRSIAgent()

def monitoring_loop():
    """Background monitoring thread"""
    logger.info("🔄 Background monitoring thread started")
    
    # Small delay to ensure Flask starts first
    time.sleep(5)
    
    while True:
        try:
            logger.info("=" * 40)
            logger.info("🔄 Starting monitoring cycle")
            
            for pair in agent.fx_pairs:
                logger.info(f"🔍 Checking {pair}...")
                agent.check_pair(pair)
                time.sleep(3)  # 3 second delay between pairs
            
            logger.info("⏳ Waiting 5 minutes for next cycle...")
            logger.info("=" * 40)
            time.sleep(300)  # 5 minutes
            
        except Exception as e:
            logger.error(f"💥 Error in monitoring loop: {e}")
            time.sleep(60)

# Flask Routes
@app.route('/')
def home():
    return jsonify({
        'status': 'active',
        'agent': 'Forex RSI Monitor',
        'pairs': agent.fx_pairs,
        'check_interval': '5 minutes',
        'timeframe': '5min',
        'timestamp': datetime.now().isoformat(),
        'telegram': '✅' if agent.telegram_token and agent.chat_id else '❌',
        'twelve_data': '✅' if agent.twelve_data_key else '❌'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

@app.route('/status')
def status():
    """Agent status"""
    return jsonify({
        'pairs_monitored': agent.fx_pairs,
        'alert_history_count': len(agent.alert_history),
        'telegram_configured': bool(agent.telegram_token and agent.chat_id),
        'twelve_data_configured': bool(agent.twelve_data_key),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/check-now')
def check_now():
    """Manual trigger for testing"""
    logger.info("🔄 Manual check triggered")
    
    results = []
    for pair in agent.fx_pairs:
        rsi = agent.get_rsi(pair)
        results.append({
            'pair': pair,
            'rsi': rsi,
            'time': datetime.now().isoformat()
        })
        time.sleep(3)
    
    return jsonify({
        'results': results,
        'count': len(results),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/test-telegram')
def test_telegram():
    """Test Telegram alert"""
    test_message = """
🧪 <b>TEST ALERT</b>

This is a test message from Render
Time: {}
""".format(datetime.now().strftime('%H:%M:%S'))
    
    agent.send_telegram(test_message)
    return jsonify({'status': 'test message sent'})

# IMPORTANT: Start monitoring thread properly
def start_monitoring():
    """Function to start monitoring in background"""
    if not monitoring_thread.is_alive():
        logger.info("🎯 Starting monitoring thread...")
        monitoring_thread.start()
        logger.info("✅ Monitoring thread started")
    else:
        logger.info("⏩ Monitoring thread already running")

# Create and start thread
monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
monitoring_thread.name = "ForexMonitor"

# Start thread when app starts
with app.app_context():
    start_monitoring()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    # Start Flask with proper configuration
    app.run(host='0.0.0.0', port=port, threaded=True)
