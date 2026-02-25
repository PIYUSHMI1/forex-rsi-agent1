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
        self.fx_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD']
        
        # RSI Settings
        self.rsi_settings = {
            'EUR/USD': {'oversold': 30, 'overbought': 70},
            'GBP/USD': {'oversold': 25, 'overbought': 75},
            'USD/JPY': {'oversold': 30, 'overbought': 70},
            'USD/CHF': {'oversold': 30, 'overbought': 70},
            'AUD/USD': {'oversold': 28, 'overbought': 72},
            'USD/CAD': {'oversold': 30, 'overbought': 70}
        }
        
        # Environment Variables
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.twelve_data_key = os.environ.get('TWELVE_DATA_KEY')
        
        # Alert history (duplicate alerts prevent)
        self.alert_history = {}
        
    def get_rsi_value(self, pair):
        """Fetch RSI from Twelve Data API"""
        if not self.twelve_data_key:
            logger.error("TWELVE_DATA_KEY not set in environment variables")
            return None

        try:
            url = "https://api.twelvedata.com/rsi"
            params = {
                'symbol': pair,
                'interval': '1h',
                'time_period': 14,
                'apikey': self.twelve_data_key,
                'outputsize': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Handle API error response
            if data.get("status") == "error":
                logger.error(f"TwelveData API Error for {pair}: {data.get('message')}")
                return None
            
            if 'values' in data and len(data['values']) > 0:
                rsi = float(data['values'][0]['rsi'])
                return rsi
            else:
                logger.warning(f"RSI data not found for {pair}: {data}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching RSI for {pair}")
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching RSI for {pair}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching RSI for {pair}: {e}")
        
        return None
    
    def check_pair(self, pair):
        """Check pair and generate alert if condition met"""
        rsi = self.get_rsi_value(pair)
        
        if rsi is None:
            return None
            
        settings = self.rsi_settings.get(pair, {'oversold': 30, 'overbought': 70})
        
        # Check oversold
        if rsi <= settings['oversold']:
            alert_key = f"{pair}_OVERSOLD"
            current_time = time.time()
            
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
        """Send alert to Telegram"""
        if not self.telegram_token or not self.chat_id:
            logger.warning("Telegram credentials not set")
            return
        
        try:
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
        """Monitor all pairs"""
        alerts_found = []
        
        for pair in self.fx_pairs:
            logger.info(f"Checking {pair}...")
            alert = self.check_pair(pair)
            
            if alert:
                alerts_found.append(alert)
                self.send_telegram_alert(alert)
            
            time.sleep(2)  # Small delay to avoid hitting API limits
        
        return alerts_found


# Initialize agent
agent = ForexRSIAgent()

def background_monitor():
    """Background monitoring loop"""
    logger.info("🚀 Forex RSI Agent Started!")
    
    while True:
        try:
            logger.info("Starting monitoring cycle...")
            alerts = agent.monitor_all_pairs()
            
            if alerts:
                logger.info(f"Found {len(alerts)} alerts")
            else:
                logger.info("No alerts found")
            
            logger.info("Waiting 5 minutes for next check...")
            time.sleep(300)
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            time.sleep(60)


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
    alerts = agent.monitor_all_pairs()
    return jsonify({
        'alerts': alerts,
        'count': len(alerts),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/status')
def status():
    return jsonify({
        'pairs_monitored': agent.fx_pairs,
        'alert_history_count': len(agent.alert_history),
        'telegram_configured': bool(agent.telegram_token and agent.chat_id),
        'api_key_configured': bool(agent.twelve_data_key)
    })


# Start background thread
thread = threading.Thread(target=background_monitor)
thread.daemon = True
thread.start()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
