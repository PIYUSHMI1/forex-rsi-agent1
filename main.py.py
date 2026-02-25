from flask import Flask, jsonify
import requests
import time
import os
import logging
from datetime import datetime
import threading

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ForexRSIAgent:
    def __init__(self):
        # Major Forex Pairs
        self.fx_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD']
        
        # RSI Settings (aap apne hisaab se change kar sakte ho)
        self.rsi_settings = {
            'EURUSD': {'oversold': 30, 'overbought': 70},
            'GBPUSD': {'oversold': 25, 'overbought': 75},
            'USDJPY': {'oversold': 30, 'overbought': 70},
            'USDCHF': {'oversold': 30, 'overbought': 70},
            'AUDUSD': {'oversold': 28, 'overbought': 72},
            'USDCAD': {'oversold': 30, 'overbought': 70}
        }
        
        # API Keys (Render Dashboard se set karna)
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_KEY', 'demo')
        
        # Alert history (duplicate alerts rokne ke liye)
        self.alert_history = {}
        
    def get_rsi_value(self, pair):
        """Alpha Vantage API se RSI fetch karo"""
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'RSI',
                'symbol': pair,
                'interval': '60min',
                'time_period': 14,
                'series_type': 'close',
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'Technical Analysis: RSI' in data:
                latest = list(data['Technical Analysis: RSI'].values())[0]
                rsi = float(latest['RSI'])
                return rsi
            else:
                logger.warning(f"RSI data not found for {pair}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching RSI for {pair}: {e}")
            return None
    
    def check_pair(self, pair):
        """Ek pair check karo aur alert bhejo agar condition meet ho"""
        rsi = self.get_rsi_value(pair)
        
        if rsi is None:
            return None
            
        settings = self.rsi_settings.get(pair, {'oversold': 30, 'overbought': 70})
        
        # Check oversold
        if rsi <= settings['oversold']:
            alert_key = f"{pair}_OVERSOLD"
            current_time = time.time()
            
            # Duplicate check (1 hour cooldown)
            if alert_key not in self.alert_history or \
               (current_time - self.alert_history[alert_key]) > 3600:
                
                self.alert_history[alert_key] = current_time
                return {
                    'pair': pair,
                    'rsi': round(rsi, 2),
                    'signal': 'OVERSOLD',
                    'action': 'BUY',
                    'threshold': settings['oversold'],
                    'time': datetime.now().isoformat()
                }
        
        # Check overbought
        elif rsi >= settings['overbought']:
            alert_key = f"{pair}_OVERBOUGHT"
            current_time = time.time()
            
            if alert_key not in self.alert_history or \
               (current_time - self.alert_history[alert_key]) > 3600:
                
                self.alert_history[alert_key] = current_time
                return {
                    'pair': pair,
                    'rsi': round(rsi, 2),
                    'signal': 'OVERBOUGHT',
                    'action': 'SELL',
                    'threshold': settings['overbought'],
                    'time': datetime.now().isoformat()
                }
        
        return None
    
    def send_telegram_alert(self, alert):
        """Telegram par alert bhejo"""
        if not self.telegram_token or not self.chat_id:
            logger.warning("Telegram credentials not set")
            return
        
        try:
            # Alert message banayo
            if alert['signal'] == 'OVERSOLD':
                emoji = "🔴"
                message = f"""
{emoji} <b>FOREX RSI ALERT</b> {emoji}

<b>Pair:</b> {alert['pair']}
<b>Signal:</b> OVERSOLD (BUY)
<b>RSI Value:</b> {alert['rsi']}
<b>Threshold:</b> {alert['threshold']}
<b>Time:</b> {alert['time']}

💡 <i>Oversold - Potential Buy Signal</i>
                """
            else:
                emoji = "🟢"
                message = f"""
{emoji} <b>FOREX RSI ALERT</b> {emoji}

<b>Pair:</b> {alert['pair']}
<b>Signal:</b> OVERBOUGHT (SELL)
<b>RSI Value:</b> {alert['rsi']}
<b>Threshold:</b> {alert['threshold']}
<b>Time:</b> {alert['time']}

💡 <i>Overbought - Potential Sell Signal</i>
                """
            
            # Send to Telegram
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Alert sent for {alert['pair']}")
            else:
                logger.error(f"Telegram error: {response.text}")
                
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    def monitor_all_pairs(self):
        """Sab pairs ko monitor karo"""
        alerts_found = []
        
        for pair in self.fx_pairs:
            logger.info(f"Checking {pair}...")
            alert = self.check_pair(pair)
            
            if alert:
                alerts_found.append(alert)
                self.send_telegram_alert(alert)
            
            # API rate limit ke liye delay
            time.sleep(12)  # Alpha Vantage allows 5 calls per minute
        
        return alerts_found

# Initialize agent
agent = ForexRSIAgent()

def background_monitor():
    """Background mein monitoring loop"""
    logger.info("🚀 Forex RSI Agent Started!")
    
    while True:
        try:
            logger.info("Starting monitoring cycle...")
            alerts = agent.monitor_all_pairs()
            
            if alerts:
                logger.info(f"Found {len(alerts)} alerts")
            else:
                logger.info("No alerts found")
            
            # 5 minutes wait
            logger.info("Waiting 5 minutes for next check...")
            time.sleep(300)  # 5 minutes
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            time.sleep(60)  # Error ke baad 1 minute wait

# Routes
@app.route('/')
def home():
    return jsonify({
        'status': 'active',
        'agent': 'Forex RSI Monitor',
        'pairs': agent.fx_pairs,
        'check_interval': '5 minutes',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

@app.route('/check-now')
def check_now():
    """Manual trigger for testing"""
    alerts = agent.monitor_all_pairs()
    return jsonify({
        'alerts': alerts,
        'count': len(alerts),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/status')
def status():
    """Agent status"""
    return jsonify({
        'pairs_monitored': agent.fx_pairs,
        'alert_history_count': len(agent.alert_history),
        'telegram_configured': bool(agent.telegram_token and agent.chat_id),
        'api_key_configured': agent.alpha_vantage_key != 'demo'
    })

# Start background thread
thread = threading.Thread(target=background_monitor)
thread.daemon = True
thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)