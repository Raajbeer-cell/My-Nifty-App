import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import time
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- SETUP ---
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

st.set_page_config(page_title="MC Pro Trader AI", page_icon="📈", layout="wide")

# --- AUTO UPDATE LOGIC ---
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Sidebar me Auto-Refresh Control
with st.sidebar:
    st.title("⚙️ Control Panel")
    auto_refresh = st.checkbox("🟢 Enable Auto-Refresh (Live Mode)", value=True)
    refresh_rate = st.slider("Refresh Rate (Seconds)", 10, 300, 60)
    
    st.markdown("---")
    st.info("Market Data: Real-time (approx)")

# Auto Refresh Mechanism
if auto_refresh:
    if time.time() - st.session_state.last_refresh > refresh_rate:
        st.session_state.last_refresh = time.time()
        st.rerun()

# --- MONEYCONTROL STYLE THEME (CSS) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #121212; color: #e0e0e0; }
    
    /* Headers - Moneycontrol Blue */
    h1, h2, h3 { color: #00b8e6 !important; font-family: 'Roboto', sans-serif; }
    
    /* Card Design */
    .mc-card {
        background-color: #1e1e1e;
        border-left: 4px solid #333;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.5);
    }
    
    /* Bullish/Bearish Styles */
    .bull-card { border-left: 4px solid #00d09c; }
    .bear-card { border-left: 4px solid #ff4d4d; }
    
    .price-text { font-size: 24px; font-weight: bold; color: #ffffff; }
    .label-text { font-size: 12px; color: #aaaaaa; }
    
    /* Strength Meter */
    .meter-box {
        background-color: #333;
        height: 8px;
        border-radius: 4px;
        margin-top: 5px;
        overflow: hidden;
    }
    .meter-fill { height: 100%; border-radius: 4px; }
    
    /* Positive Indicator Count */
    .ind-count { font-size: 13px; font-weight: bold; margin-top: 5px; }
    .bull-text { color: #00d09c; }
    .bear-text { color: #ff4d4d; }
    
</style>
""", unsafe_allow_html=True)

st.title("📈 MC PRO TRADER: Live Signals & AI")

# --- ASSETS CONFIGURATION ---
# Silver ke liye hum Global data lenge aur calculate karenge
ASSETS = {
    "⭐ FAVORITES": {
        "SILVER (MCX SIM)": "SI=F",  # Special handling niche code me hai
        "GOLD (GLOBAL)": "GC=F",
        "BANK NIFTY": "^NSEBANK"
    },
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD"}
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

# --- ADVANCED ANALYSIS FUNCTIONS ---

@st.cache_data(ttl=refresh_rate) # Cache data for the refresh duration
def fetch_data(tickers, period, interval):
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    return data

def analyze_market(df, ticker_symbol):
    if df.empty or len(df) < 50: return None
    
    # 1. Indicators Calculation
    df['EMA_20'] = df.ta.ema(length=20)
    df['EMA_50'] = df.ta.ema(length=50)
    df['EMA_200'] = df.ta.ema(length=200)
    df['RSI'] = df.ta.rsi(length=14)
    df['ATR'] = df.ta.atr(length=14)
    df['ADX'] = df.ta.adx(length=14)['ADX_14']
    
    # Supertrend
    st_data = df.ta.supertrend(length=10, multiplier=3)
    st_dir_col = [c for c in st_data.columns if "SUPERTd_" in c][0]
    df['Trend'] = st_data[st_dir_col] # 1 = Up, -1 = Down

    # MACD
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_SIGNAL'] = macd['MACDs_12_26_9']

    # --- CURRENT VALUES ---
    close = df['Close'].iloc[-1]
    ema20 = df['EMA_20'].iloc[-1]
    ema50 = df['EMA_50'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    trend = df['Trend'].iloc[-1]
    adx = df['ADX'].iloc[-1]
    macd_val = df['MACD'].iloc[-1]
    macd_sig = df['MACD_SIGNAL'].iloc[-1]

    # --- SPECIAL PRICE ADJUSTMENT FOR SILVER (Simulating 3kg/Lot MCX Value) ---
    display_price = close
    if "SI=F" in ticker_symbol:
        # Global Silver ($30 approx) * USDINR (87) * Factor (approx 100 for kg or 300 for lot)
        # Assuming the user sees ~2,85,000. 
        # Standard 1kg ~ 90,000 INR. So 2,85,000 is approx 3kg (Micro Lot x Qty).
        # Calculation: Price($) * 87 * 100
        display_price = close * 87 * 100 # Adjust this factor to match your specific chart view
        
    # --- SCORING SYSTEM (1 to 10) ---
    score = 0
    pos_count = 0
    total_indicators = 5
    
    # Logic for BULLISH Score
    if trend == 1: score += 2; pos_count += 1      # Supertrend Up
    if close > ema50: score += 2; pos_count += 1   # Above EMA 50
    if rsi > 50: score += 2; pos_count += 1        # RSI Bullish
    if macd_val > macd_sig: score += 2; pos_count += 1 # MACD Crossover
    if adx > 25: score += 2; pos_count += 1        # Strong Trend
    
    # Logic for BEARISH Score (Invert score if trend is down)
    is_bearish = False
    if trend == -1:
        is_bearish = True
        # Recalculate for Sell
        score = 0
        pos_count = 0
        if trend == -1: score += 2; pos_count += 1
        if close < ema50: score += 2; pos_count += 1
        if rsi < 50: score += 2; pos_count += 1
        if macd_val < macd_sig: score += 2; pos_count += 1
        if adx > 25: score += 2; pos_count += 1

    # --- ACTION DECISION ---
    action = "WAIT ✋"
    color = "#888888" # Grey
    card_class = "mc-card"
    
    if score >= 6:
        if not is_bearish:
            action = "BUY / CALL 🟢"
            color = "#00d09c" # Moneycontrol Green
            card_class = "mc-card bull-card"
        else:
            action = "SELL / PUT 🔴"
            color = "#ff4d4d" # Moneycontrol Red
            card_class = "mc-card bear-card"
    
    # Targets
    atr = df['ATR'].iloc[-1]
    if "SI=F" in ticker_symbol: atr = atr * 87 * 100 # Adjust ATR for silver too
        
    if not is_bearish:
        sl = display_price - (atr * 1.5)
        tgt = display_price + (atr * 3)
    else:
        sl = display_price + (atr * 1.5)
        tgt = display_price - (atr * 3)

    return {
        "price": display_price,
        "action": action,
        "color": color,
        "score": score,
        "pos_count": pos_count,
        "sl": sl,
        "tgt": tgt,
        "card_class": card_class,
        "is_bearish": is_bearish
    }

# --- UI LAYOUT ---

# Timeframe Selector
col1, col2 = st.columns([6, 1])
with col1:
    st.caption(f"Last Updated: {time.strftime('%H:%M:%S')}")
with col2:
    if st.button("🔄 Now"):
        st.cache_data.clear()
        st.rerun()

timeframe = "15m" # Fixed for scalping as per request
tf_map = "5d"

# Fetch Data
with st.spinner("Analyzing Market Data..."):
    raw_data = fetch_data(ALL_TICKERS, period=tf_map, interval=timeframe)

# --- DISPLAY CARDS ---
if raw_data is not None:
    for cat_name, tickers in ASSETS.items():
        st.subheader(f"{cat_name}")
        cols = st.columns(3)
        idx = 0
        
        for name, symbol in tickers.items():
            try:
                if len(ALL_TICKERS) > 1: df = raw_data[symbol].dropna()
                else: df = raw_data.dropna()
                
                sig = analyze_market(df, symbol)
                
                if sig:
                    with cols[idx % 3]:
                        # Create Progress Bar Color
                        bar_color = "#00d09c" if not sig['is_bearish'] else "#ff4d4d"
                        
                        st.markdown(f"""
                        <div class="{sig['card_class']}">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:16px; font-weight:bold; color:#00b8e6;">{name}</span>
                                <span style="background-color:{sig['color']}20; color:{sig['color']}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:12px;">{sig['action']}</span>
                            </div>
                            
                            <div class="price-text">₹ {sig['price']:,.0f}</div>
                            
                            <div class="label-text">TREND STRENGTH ({sig['score']}/10)</div>
                            <div class="meter-box">
                                <div class="meter-fill" style="width:{sig['score']*10}%; background-color:{bar_color};"></div>
                            </div>
                            
                            <div class="ind-count" style="color:{bar_color};">
                                {'✅' if sig['score'] >=5 else '⚠️'} {sig['pos_count']}/5 Indicators { 'Bearish' if sig['is_bearish'] else 'Bullish' }
                            </div>
                            
                            <hr style="border-color:#333; margin:10px 0;">
                            
                            <div style="display:flex; justify-content:space-between; font-size:13px;">
                                <span style="color:#ff4d4d;">🛑 SL: {sig['sl']:,.0f}</span>
                                <span style="color:#00d09c;">🎯 TGT: {sig['tgt']:,.0f}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    idx += 1
            except Exception as e:
                pass
        st.markdown("---")

# --- NEWS SECTION (Simple & Fast) ---
st.subheader("📰 Market Insights (Live)")
news_cols = st.columns(2)

with news_cols[0]:
    st.markdown("##### 🇮🇳 Indian Economy")
    feed = feedparser.parse("https://www.moneycontrol.com/rss/economy.xml")
    for entry in feed.entries[:3]:
        sent = sia.polarity_scores(entry.title)['compound']
        color = "#00d09c" if sent > 0 else "#ff4d4d" if sent < 0 else "#888"
        st.markdown(f"<div style='border-left:3px solid {color}; padding-left:10px; margin-bottom:10px;'><a href='{entry.link}' style='color:#ccc; text-decoration:none;'>{entry.title}</a></div>", unsafe_allow_html=True)

with news_cols[1]:
    st.markdown("##### 🪙 Crypto & Global")
    feed = feedparser.parse("https://cointelegraph.com/rss")
    for entry in feed.entries[:3]:
        st.markdown(f"<div style='margin-bottom:10px; font-size:14px; color:#aaa;'>• {entry.title}</div>", unsafe_allow_html=True)

