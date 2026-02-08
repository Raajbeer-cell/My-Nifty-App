import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import streamlit.components.v1 as components
from datetime import datetime
import time

# ============================================================================
# 1. INITIAL SETUP
# ============================================================================

st.set_page_config(
    page_title="Ultimate Trader Pro", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if 'notified_assets' not in st.session_state:
    st.session_state.notified_assets = set()

# NLTK Setup
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

sia = SentimentIntensityAnalyzer()

# ============================================================================
# 2. DESIGN & STYLING (CSS)
# ============================================================================

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0a0e14 0%, #1a1f2e 100%); color: #e1e1e1; }
    .trade-card { 
        background: linear-gradient(145deg, #161b22, #0d1117);
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #30363d; 
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
    }
    .metric-val { font-size: 28px; font-weight: 900; color: #ffffff; }
    .status-badge { padding: 5px 15px; border-radius: 20px; font-size: 11px; font-weight: bold; display: inline-block; }
    .silver-special { border: 2px solid #c0c0c0; box-shadow: 0 0 20px rgba(192, 192, 192, 0.3); }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 3. NOTIFICATION SYSTEM
# ============================================================================

def trigger_browser_notification(title, message, unique_id):
    if unique_id in st.session_state.notified_assets:
        return
    js_code = f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("{title}", {{ body: "{message}" }});
    }} else if (Notification.permission !== "denied") {{
        Notification.requestPermission().then(permission => {{
            if (permission === "granted") {{ new Notification("{title}", {{ body: "{message}" }}); }}
        }});
    }}
    </script>
    """
    components.html(js_code, height=0)
    st.session_state.notified_assets.add(unique_id)

# ============================================================================
# 4. ASSET LIST
# ============================================================================

ASSETS = {
    "🇮🇳 INDIAN INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD", "SOLANA": "SOL-USD"},
    "💎 COMMODITIES": {"GOLD": "GC=F", "SILVER": "SI=F", "CRUDE OIL": "CL=F"},
    "🇺🇸 STOCKS": {"NVIDIA": "NVDA", "TESLA": "TSLA", "APPLE": "AAPL"}
}

ALL_TICKERS = [symbol for cat in ASSETS.values() for symbol in cat.values()]

# ============================================================================
# 5. DATA FETCHING
# ============================================================================

@st.cache_data(ttl=60)
def fetch_market_data(tickers, period, interval):
    try:
        data = yf.download(tickers, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
        return data
    except:
        return None

# ============================================================================
# 6. SIGNAL CALCULATION
# ============================================================================

def calculate_advanced_signal(df, ticker_name=""):
    if df is None or df.empty or len(df) < 50: return None
    try:
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df = df.ffill().bfill()
        
        curr = df.iloc[-1]
        close = curr['Close']
        ema200 = curr['EMA_200']
        rsi = curr['RSI']
        atr = curr['ATR']
        
        change = ((close - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
        
        action = "NEUTRAL"
        color = "#888888"
        
        if close > ema200 and rsi < 70:
            action = "BUY"
            color = "#00ff88"
        elif close < ema200 and rsi > 30:
            action = "SELL"
            color = "#ff4b4b"
            
        return {
            "action": action, "price": close, "change": change,
            "color": color, "rsi": rsi, "sl": close - (atr*2), "tp": close + (atr*4)
        }
    except: return None

# ============================================================================
# 7. MAIN APP UI
# ============================================================================

st.sidebar.title("🎯 TRADER PRO")
timeframe = st.sidebar.selectbox("Select Timeframe", ["15m", "1h", "1d"], index=1)
period_map = {"15m": "5d", "1h": "1mo", "1d": "1y"}

st.title("🎯 ULTIMATE TRADER PRO")

market_data = fetch_market_data(ALL_TICKERS, period_map[timeframe], timeframe)

if market_data is not None:
    for category, tickers in ASSETS.items():
        st.subheader(category)
        cols = st.columns(3)
        idx = 0
        
        for name, symbol in tickers.items():
            try:
                df = market_data[symbol] if len(ALL_TICKERS) > 1 else market_data
                df = df.dropna()
                signal = calculate_advanced_signal(df, name)
                
                if signal:
                    with cols[idx % 3]:
                        # YAHAN HAI MAGIC - HTML Rendering
                        html_code = f"""
                        <div class="trade-card" style="border-left: 5px solid {signal['color']}">
                            <div style="display:flex; justify-content:space-between;">
                                <span style="font-size:20px; font-weight:bold;">{name}</span>
                                <span class="status-badge" style="background:{signal['color']}20; color:{signal['color']}">{signal['action']}</span>
                            </div>
                            <div class="metric-val">${signal['price']:.2f}</div>
                            <div style="color:{'#00ff88' if signal['change']>0 else '#ff4b4b'}">
                                {signal['change']:+.2f}%
                            </div>
                            <div style="margin-top:10px; font-size:12px; color:#aaa;">
                                🛑 SL: {signal['sl']:.2f} | 🎯 TP: {signal['tp']:.2f}
                            </div>
                        </div>
                        """
                        st.markdown(html_code, unsafe_allow_html=True)
                    idx += 1
            except Exception as e:
                continue
else:
    st.error("Market Data load nahi ho raha. Refresh karein.")
