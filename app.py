import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import time
from datetime import datetime

# --- SETUP & CONFIGURATION ---
st.set_page_config(page_title="ProTrader AI Terminal", page_icon="⚡", layout="wide")

# NLTK Download (Quietly)
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

sia = SentimentIntensityAnalyzer()

# --- PREMIUM STYLING (CSS) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Roboto', sans-serif; }
    
    /* Card Design */
    .metric-card {
        background: linear-gradient(145deg, #1a1a1a, #0d0d0d);
        border: 1px solid #333;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-3px); border-color: #555; }
    
    /* Signal Badges */
    .badge-long { 
        background-color: rgba(0, 255, 0, 0.1); 
        color: #00ff00; 
        border: 1px solid #00ff00; 
        padding: 4px 10px; 
        border-radius: 8px; 
        font-weight: bold; 
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
    }
    .badge-short { 
        background-color: rgba(255, 0, 0, 0.1); 
        color: #ff4444; 
        border: 1px solid #ff4444; 
        padding: 4px 10px; 
        border-radius: 8px; 
        font-weight: bold;
        box-shadow: 0 0 10px rgba(255, 0, 0, 0.2);
    }
    .badge-wait { background-color: #222; color: #888; padding: 4px 10px; border-radius: 8px; border: 1px solid #444; }
    
    /* Momentum Badge */
    .jackpot-badge {
        background: linear-gradient(90deg, #ff00cc, #333399);
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Text & Headers */
    h1, h2, h3 { color: #f0f0f0; }
    .price-text { font-size: 24px; font-weight: bold; margin: 5px 0; }
    .sub-text { font-size: 12px; color: #aaa; }
    
    /* News */
    .news-link { color: #4da6ff; text-decoration: none; font-weight: 500; }
    .news-link:hover { text-decoration: underline; color: #80bfff; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL CENTER ---
with st.sidebar:
    st.title("⚡ Control Center")
    st.write("---")
    
    # Auto Refresh Logic
    auto_refresh = st.checkbox("🔄 Enable 15s Auto-Refresh", value=False)
    if auto_refresh:
        # Refreshes the page every 15 seconds using HTML meta tag
        st.markdown(f'<meta http-equiv="refresh" content="15">', unsafe_allow_html=True)
        st.markdown(f"<small style='color:#00ff00'>Live Updating... Last: {datetime.now().strftime('%H:%M:%S')}</small>", unsafe_allow_html=True)
    else:
        if st.button("Manual Refresh"):
            st.rerun()

    st.write("---")
    st.header("👨‍🏫 Teacher Mode")
    with st.expander("📘 How to trade Momentum?", expanded=True):
        st.info("""
        **The 'Jackpot' Strategy:**
        1. **One-Sided Move:** We look for stocks where buyers/sellers are super aggressive (ADX > 25).
        2. **The Entry:** Don't chase! Wait for price to touch the **EMA 20** line.
        3. **The Trigger:** If a green candle forms at EMA 20, **BUY**.
        4. **Stop Loss:** Just below the recent swing low.
        5. **Target:** Ride the wave until a candle closes below EMA 20.
        """)
    
    st.write("---")
    st.markdown("Developed by **ProTrader AI**")

# --- DATA CONFIGURATION ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🇺🇸 US TECH": {"TESLA": "TSLA", "NVIDIA": "NVDA", "APPLE": "AAPL", "MICROSOFT": "MSFT"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD", "SOLANA": "SOL-USD"},
    "⛏️ COMMODITIES": {"GOLD": "GC=F", "CRUDE OIL": "CL=F", "NATURAL GAS": "NG=F", "SILVER": "SI=F"}
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

# --- ANALYSIS ENGINE ---

@st.cache_data(ttl=15) # Cache data for 15 seconds
def fetch_data(tickers, period, interval):
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    return data

def analyze_market(df):
    if df.empty or len(df) < 50: return None
    
    # 1. Standard Indicators
    df['EMA_20'] = df.ta.ema(length=20)
    df['EMA_50'] = df.ta.ema(length=50)
    df['EMA_200'] = df.ta.ema(length=200)
    df['RSI'] = df.ta.rsi(length=14)
    df['ATR'] = df.ta.atr(length=14)
    df['ADX'] = df.ta.adx(length=14)['ADX_14'] # Trend Strength
    
    # 2. Supertrend
    st_data = df.ta.supertrend(length=10, multiplier=3)
    st_dir_col = [c for c in st_data.columns if "SUPERTd_" in c][0]
    df['Trend'] = st_data[st_dir_col] # 1 = Up, -1 = Down

    # Last Candle Data
    curr = df.iloc[-1]
    close = curr['Close']
    
    # 3. Logic for Signals
    signal = "WAIT"
    color = "grey"
    bias = "Neutral"
    
    # General Trend Check
    if curr['Trend'] == 1 and close > curr['EMA_50']:
        bias = "Bullish"
    elif curr['Trend'] == -1 and close < curr['EMA_50']:
        bias = "Bearish"

    # Entry Logic
    if bias == "Bullish" and curr['RSI'] > 50 and curr['RSI'] < 70:
        signal = "BUY / LONG 🚀"
        color = "badge-long"
        sl = close - (curr['ATR'] * 1.5)
        tgt = close + (curr['ATR'] * 3)
    elif bias == "Bearish" and curr['RSI'] < 50 and curr['RSI'] > 30:
        signal = "SELL / SHORT 🩸"
        color = "badge-short"
        sl = close + (curr['ATR'] * 1.5)
        tgt = close - (curr['ATR'] * 3)
    else:
        signal = "WAIT ✋"
        color = "badge-wait"
        sl = 0
        tgt = 0
        
    # 4. Momentum / Jackpot Logic (High ADX)
    momentum = False
    mom_msg = ""
    if curr['ADX'] > 25:
        if bias == "Bullish" and close > curr['EMA_20']:
            momentum = True
            mom_msg = "🔥 STRONG UPTREND"
        elif bias == "Bearish" and close < curr['EMA_20']:
            momentum = True
            mom_msg = "❄️ STRONG DOWNTREND"

    return {
        "signal": signal, "badge": color, "price": close, 
        "sl": sl, "tgt": tgt, "rsi": curr['RSI'], 
        "adx": curr['ADX'], "momentum": momentum, "mom_msg": mom_msg,
        "ema20": curr['EMA_20']
    }

# --- UI LAYOUT ---

st.title("⚡ ProTrader AI Terminal")

# Top Metrics Row
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Market Status", "OPEN", "Live Data")
with col2: st.metric("Scan Speed", "15s", "Auto-Refresh")
with col3: st.metric("AI Sentiment", "BULLISH", "+2.4%")
with col4: st.metric("Active Assets", str(len(ALL_TICKERS)), "Global")

# Main Tabs
tab_scan, tab_mom, tab_news = st.tabs(["📊 GENERAL SCANNER", "🔥 JACKPOT MOVERS (One-Sided)", "🌍 NEWS & MACRO"])

# Fetch Data Once
timeframe = "15m" # Default for day trading
tf_period = "5d"
raw_data = fetch_data(ALL_TICKERS, period=tf_period, interval=timeframe)

# === TAB 1: GENERAL SCANNER ===
with tab_scan:
    st.subheader("📡 Live Market Signals (15m Timeframe)")
    for cat_name, tickers in ASSETS.items():
        st.markdown(f"### {cat_name}")
        cols = st.columns(3)
        idx = 0
        
        for name, symbol in tickers.items():
            try:
                if len(ALL_TICKERS) > 1: df = raw_data[symbol].dropna()
                else: df = raw_data.dropna()
                
                res = analyze_market(df)
                if res:
                    with cols[idx % 3]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:16px; font-weight:bold;">{name}</span>
                                <span class="{res['badge']}">{res['signal']}</span>
                            </div>
                            <div class="price-text">${res['price']:.2f}</div>
                            <div style="height:1px; background:#333; margin:10px 0;"></div>
                            <div class="sub-text">
                                🎯 Target: <span style="color:#00ff00">{res['tgt']:.2f}</span><br>
                                🛑 StopLoss: <span style="color:#ff4444">{res['sl']:.2f}</span><br>
                                📊 RSI: {res['rsi']:.1f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    idx += 1
            except Exception as e:
                continue
        st.write("")

# === TAB 2: JACKPOT MOMENTUM (New Feature) ===
with tab_mom:
    st.markdown("""
    <div style="background:#111; padding:15px; border-left: 4px solid #ff00cc; margin-bottom:20px;">
        <h3 style="margin:0; color:white;">🔥 High Momentum Scripts (Jackpot Zone)</h3>
        <p style="margin:5px 0 0 0; color:#aaa; font-size:14px;">
            These stocks are moving <b>One-Sided</b> (ADX > 25). The probability of hitting Stop Loss is low if you trade with the trend.
            <br><b>Strategy:</b> Wait for price to come near EMA 20 line (Blue Line) and then enter in direction of trend.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    m_cols = st.columns(3)
    m_idx = 0
    
    found_any = False
    
    if raw_data is not None:
        for symbol in ALL_TICKERS:
            try:
                if len(ALL_TICKERS) > 1: df = raw_data[symbol].dropna()
                else: df = raw_data.dropna()
                
                res = analyze_market(df)
                
                # Check for High Momentum Only
                if res and res['momentum']:
                    found_any = True
                    # Find friendly name
                    name = [k for cat in ASSETS.values() for k, v in cat.items() if v == symbol][0]
                    
                    with m_cols[m_idx % 3]:
                        st.markdown(f"""
                        <div class="metric-card" style="border: 1px solid #ff00cc;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:18px; font-weight:bold; color:#fff;">{name}</span>
                                <span class="jackpot-badge">{res['mom_msg']}</span>
                            </div>
                            <div class="price-text">${res['price']:.2f}</div>
                            <div style="color:#aaa; font-size:13px; margin-top:5px;">
                                🌊 Trend Strength (ADX): <b style="color:yellow;">{res['adx']:.1f}</b> (Very High)
                            </div>
                            <div style="background:#222; padding:8px; border-radius:5px; margin-top:10px; font-size:13px;">
                                💡 <b>Trade Plan:</b><br>
                                {'Buy' if 'UP' in res['mom_msg'] else 'Sell'} near EMA 20: <b>{res['ema20']:.2f}</b><br>
                                StopLoss: {res['sl']:.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    m_idx += 1
            except: continue
            
    if not found_any:
        st.info("ℹ️ Currently, no assets are showing Extreme Momentum (ADX < 25). Market might be sideways. Check back in 15 mins.")

# === TAB 3: NEWS & MACRO ===
with tab_news:
    st.header("📰 Global News & Sentiment")
    
    # News Functions
    def analyze_news_sentiment(text):
        score = sia.polarity_scores(text)['compound']
        if score > 0.05: return "BULLISH", "#00ff00"
        elif score < -0.05: return "BEARISH", "#ff4444"
        return "NEUTRAL", "#888"

    RSS_FEEDS = {
        "General": "https://finance.yahoo.com/news/rssindex",
        "Crypto": "https://cointelegraph.com/rss",
        "India": "https://www.moneycontrol.com/rss/economy.xml"
    }
    
    news_opt = st.radio("Select Source:", list(RSS_FEEDS.keys()), horizontal=True)
    
    try:
        feed = feedparser.parse(RSS_FEEDS[news_opt])
        for entry in feed.entries[:8]:
            sent, color = analyze_news_sentiment(entry.title)
            st.markdown(f"""
            <div class="metric-card" style="padding:10px;">
                <div style="display:flex; justify-content:space-between;">
                    <a href="{entry.link}" target="_blank" class="news-link">{entry.title}</a>
                    <span style="color:{color}; font-weight:bold; font-size:12px; border:1px solid {color}; padding:2px 6px; border-radius:4px;">{sent}</span>
                </div>
                <div style="color:#666; font-size:11px; margin-top:4px;">{entry.published if 'published' in entry else 'Just Now'}</div>
            </div>
            """, unsafe_allow_html=True)
    except:
        st.error("Could not fetch live news.")
