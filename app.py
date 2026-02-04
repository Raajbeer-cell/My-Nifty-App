import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
import time
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- SETUP ---
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

st.set_page_config(page_title="Ultimate Pro Trader", page_icon="🚀", layout="wide")

# --- AUTO REFRESH LOGIC ---
if 'last_run' not in st.session_state:
    st.session_state['last_run'] = time.time()

refresh_sec = 60 # Default refresh rate
auto_ref = st.sidebar.checkbox("🟢 Enable Auto-Refresh", value=True)

if auto_ref:
    if time.time() - st.session_state['last_run'] > refresh_sec:
        st.session_state['last_run'] = time.time()
        st.rerun()

# --- UI STYLE (FIXED RENDERING) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .box { 
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #30363d; 
        margin-bottom: 15px; 
    }
    .box-bull { border-left: 5px solid #2ea043 !important; }
    .box-bear { border-left: 5px solid #da3633 !important; }
    .price-big { font-size: 28px; font-weight: bold; margin: 10px 0; font-family: 'Courier New', monospace; }
    .strength-bar-bg { width: 100%; background-color: #21262d; height: 8px; border-radius: 4px; margin-top: 10px; }
    .strength-bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
    .news-title { color: #58a6ff; font-weight: bold; text-decoration: none; font-size: 16px; }
    .badge-bull { background-color: #238636; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
    .badge-bear { background-color: #da3633; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 ULTIMATE TRADER: Pro Terminal")

# --- DATA CONFIG ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD"},
    "⛏️ COMMODITIES": {"SILVER (MCX)": "SI=F", "GOLD": "GC=F"}
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

@st.cache_data(ttl=60)
def fetch_data(tickers):
    return yf.download(" ".join(tickers), period="5d", interval="15m", group_by='ticker', progress=False)

def get_signal(df, name):
    if df.empty or len(df) < 30: return None
    
    # Technical Indicators
    df['EMA_20'] = df.ta.ema(length=20)
    df['EMA_50'] = df.ta.ema(length=50)
    df['RSI'] = df.ta.rsi(length=14)
    df['ADX'] = df.ta.adx(length=14)['ADX_14']
    st_data = df.ta.supertrend(length=10, multiplier=3)
    df['Trend'] = st_data.iloc[:, 1] # 1 for Up, -1 for Down

    # Current Stats
    close = df['Close'].iloc[-1]
    trend = df['Trend'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    adx = df['ADX'].iloc[-1]
    
    # SILVER PRICE MULTIPLIER (To reach ~2,85,000)
    if "SILVER" in name:
        close = close * 91.5 # Adjusted for MCX-like value
        
    # Strength Logic (1-10)
    score = 0
    if trend == 1: score += 2
    if rsi > 55: score += 2
    if close > df['EMA_20'].iloc[-1]: score += 2
    if adx > 25: score += 2
    if close > df['EMA_50'].iloc[-1]: score += 2
    
    if trend == -1: score = 10 - score # Invert for Sell
    
    # Signals
    action = "WAIT"
    color = "#8b949e"
    box_class = "box"
    
    if trend == 1 and score >= 6:
        action = "BUY / CALL 🟢"
        color = "#3fb950"
        box_class = "box box-bull"
    elif trend == -1 and score >= 6:
        action = "SELL / PUT 🔴"
        color = "#f85149"
        box_class = "box box-bear"

    return {
        "price": close, "action": action, "color": color, 
        "score": score, "box_class": box_class, "adx": adx
    }

# --- MAIN RENDER ---
data = fetch_data(ALL_TICKERS)

tab1, tab2 = st.tabs(["📊 LIVE SCANNER", "📰 NEWS AI"])

with tab1:
    for cat_name, tickers in ASSETS.items():
        st.subheader(cat_name)
        cols = st.columns(3)
        for i, (name, sym) in enumerate(tickers.items()):
            try:
                df = data[sym].dropna()
                sig = get_signal(df, name)
                if sig:
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div class="{sig['box_class']}">
                            <div style="display:flex; justify-content:space-between;">
                                <span style="font-weight:bold; color:#8b949e;">{name}</span>
                                <span style="color:{sig['color']}; font-weight:bold;">{sig['action']}</span>
                            </div>
                            <div class="price-big">₹ {sig['price']:,.2f}</div>
                            <div style="font-size:12px; color:#8b949e; margin-bottom:5px;">TREND STRENGTH: {sig['score']}/10</div>
                            <div class="strength-bar-bg">
                                <div class="strength-bar-fill" style="width:{sig['score']*10}%; background-color:{sig['color']};"></div>
                            </div>
                            <div style="margin-top:15px; font-size:13px;">
                                <span style="color:#3fb950;">🎯 Tgt: {sig['price']*1.02:,.0f}</span> | 
                                <span style="color:#f85149;">🛑 SL: {sig['price']*0.99:,.0f}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            except: continue

with tab2:
    st.header("Global News Sentiment")
    feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
    for entry in feed.entries[:8]:
        sent = sia.polarity_scores(entry.title)['compound']
        badge = "badge-bull" if sent > 0 else "badge-bear" if sent < 0 else ""
        st.markdown(f"""
        <div class="box">
            <a href="{entry.link}" class="news-title">{entry.title}</a><br>
            <span class="{badge}">{"Bullish" if sent > 0 else "Bearish" if sent < 0 else "Neutral"}</span>
        </div>
        """, unsafe_allow_html=True)
