import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from streamlit_autorefresh import st_autorefresh  # For Real-Time loops

# --- SETUP ---
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

# Page Setup
st.set_page_config(page_title="Pro Market Dashboard", page_icon="📈", layout="wide")

# --- REAL-TIME CONFIG ---
# Refresh every 60 seconds (60000ms) to update prices without hitting API limits
count = st_autorefresh(interval=60000, key="datarefresh")

# --- UI STYLE: MONEYCONTROL THEME (Light Mode) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #f4f5f8; color: #2a2a2a; font-family: 'Roboto', sans-serif; }
    
    /* Card Container */
    .mc-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-top: 4px solid #e0e0e0;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .mc-card:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    
    /* Silver Special Card */
    .silver-card { border-top: 4px solid #a0a0a0; background: linear-gradient(to bottom right, #ffffff, #f0f0f0); }
    
    /* Typography */
    .asset-name { font-size: 18px; font-weight: 700; color: #333; margin-bottom: 5px; }
    .price-big { font-size: 28px; font-weight: 800; color: #222; }
    .price-positive { color: #009933; font-weight: 600; font-size: 14px; }
    .price-negative { color: #cc0000; font-weight: 600; font-size: 14px; }
    
    /* Technical Score Bar */
    .score-container { background-color: #e0e0e0; border-radius: 5px; height: 8px; width: 100%; margin-top: 10px; }
    .score-fill-bull { height: 100%; border-radius: 5px; background-color: #009933; }
    .score-fill-bear { height: 100%; border-radius: 5px; background-color: #cc0000; }
    .score-fill-neutral { height: 100%; border-radius: 5px; background-color: #ffcc00; }
    
    /* Tags */
    .tech-tag {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        background-color: #f0f2f5;
        color: #555;
        border: 1px solid #ddd;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Market Dashboard Pro")
st.caption(f"Last Updated: Real-time Mode Active • Refresh #{count}")

# --- DATA CONFIGURATION ---
# Added USDINR for MCX Conversion logic
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD"},
    "⛏️ COMMODITIES": {"SILVER (Global)": "SI=F", "GOLD": "GC=F", "CRUDE OIL": "CL=F"},
    "💱 FOREX": {"USD/INR": "USDINR=X"} 
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

# --- FUNCTIONS ---

@st.cache_data(ttl=55) # Cache slightly less than refresh rate
def fetch_data(tickers, period, interval):
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    return data

def calculate_technical_score(df):
    """
    Calculates a score out of 10 based on standard technical indicators.
    Returns: Score, Positive Count, Total Checks, Detail Dictionary
    """
    if df.empty or len(df) < 50: return 0, 0, 10, {}
    
    # Calculate Indicators
    df['EMA_50'] = df.ta.ema(length=50)
    df['EMA_200'] = df.ta.ema(length=200)
    df['RSI'] = df.ta.rsi(length=14)
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_SIGNAL'] = macd['MACDs_12_26_9']
    adx = df.ta.adx(length=14)
    df['ADX'] = adx[adx.columns[0]] if adx is not None else 0
    
    # Current values
    curr = df.iloc[-1]
    close = curr['Close']
    
    # --- SCORING LOGIC (10 Checks) ---
    checks = {
        "Price > EMA 50": close > curr['EMA_50'],
        "Price > EMA 200": close > curr['EMA_200'],
        "RSI Bullish (>50)": curr['RSI'] > 50,
        "RSI Not Overbought (<70)": curr['RSI'] < 70,
        "MACD > Signal": curr['MACD'] > curr['MACD_SIGNAL'],
        "MACD > 0": curr['MACD'] > 0,
        "ADX Strong Trend (>20)": curr['ADX'] > 20,
        "Recent Momentum (Close > Open)": close > curr['Open'],
        "Above Yesterday High": close > df.iloc[-2]['High'],
        "Volume Rising": curr['Volume'] > df['Volume'].rolling(5).mean().iloc[-1]
    }
    
    # Logic: If Bearish context, we might invert score, but for "Strength" we usually count Bullish signals
    # Or we calculate "Bull Strength" vs "Bear Strength". 
    # Here we calculate BULLISH STRENGTH (0 to 10).
    
    positive_signals = sum(checks.values())
    total_checks = 10
    score = (positive_signals / total_checks) * 10
    
    return score, positive_signals, total_checks, checks

# --- MAIN APP UI ---

tab1, tab2 = st.tabs(["📊 DASHBOARD", "📰 INTELLIGENCE"])

with tab1:
    # Top Bar Summary
    col_ctrl, col_status = st.columns([4, 1])
    with col_ctrl:
        timeframe = st.selectbox("Market View:", ["15m", "1h", "1d"], index=1)
    
    tf_map = {"15m": "5d", "1h": "1mo", "1d": "1y"}
    
    with st.spinner("Analyzing Market Structure..."):
        raw_data = fetch_data(ALL_TICKERS, period=tf_map[timeframe], interval=timeframe)

    # USDINR for Conversion
    try:
        usdinr = raw_data['USDINR=X']['Close'].iloc[-1]
    except:
        usdinr = 84.0 # Fallback

    # Loop Categories
    if raw_data is not None:
        for cat_name, tickers in ASSETS.items():
            if "FOREX" in cat_name: continue # Hide Forex row, use it for calculation only
            
            st.subheader(cat_name)
            
            # Grid Layout
            cols = st.columns(3)
            idx = 0
            
            for name, symbol in tickers.items():
                try:
                    df = raw_data[symbol].dropna()
                    if df.empty: continue
                    
                    # Score Calculation
                    score, pos_cnt, total, details = calculate_technical_score(df)
                    
                    # Data Points
                    close = df['Close'].iloc[-1]
                    prev_close = df['Close'].iloc[-2]
                    chg = close - prev_close
                    pct_chg = (chg / prev_close) * 100
                    
                    # SILVER SPECIAL LOGIC (MCX Simulation)
                    display_price = close
                    price_prefix = "$"
                    is_silver = "SILVER" in name or "SI=F" in symbol
                    
                    if is_silver:
                        # Convert Global Silver ($/oz) to Approx MCX (INR/kg)
                        # Formula: (Price / 31.1035) * 1000 * USDINR * (Import Duty + Premium ~ 15%)
                        mcx_approx = (close / 31.1035) * 1000 * usdinr * 1.15
                        display_price = mcx_approx
                        price_prefix = "₹"
                        name = "SILVER MIC (MCX Approx)" # Renaming for display
                    elif cat_name == "🇮🇳 INDICES":
                        price_prefix = "₹"
                    
                    # Styling Classes
                    color_cls = "price-positive" if chg > 0 else "price-negative"
                    arrow = "▲" if chg > 0 else "▼"
                    
                    # Bar Color based on score
                    bar_cls = "score-fill-neutral"
                    if score >= 7: bar_cls = "score-fill-bull"
                    if score <= 3: bar_cls = "score-fill-bear"
                    
                    # Special CSS for Silver
                    card_cls = "mc-card silver-card" if is_silver else "mc-card"
                    
                    with cols[idx % 3]:
                        st.markdown(f"""
                        <div class="{card_cls}">
                            <div class="asset-name">{name}</div>
                            <div style="display:flex; align-items:baseline;">
                                <div class="price-big">{price_prefix}{display_price:,.2f}</div>
                                <div class="{color_cls}" style="margin-left:10px;">
                                    {arrow} {pct_chg:.2f}%
                                </div>
                            </div>
                            
                            <div style="margin-top:15px;">
                                <div style="display:flex; justify-content:space-between; font-size:12px; color:#666;">
                                    <span>Technical Strength</span>
                                    <b>{int(score)}/10</b>
                                </div>
                                <div class="score-container">
                                    <div class="{bar_cls}" style="width: {score*10}%;"></div>
                                </div>
                                <div style="margin-top:8px; font-size:11px; color:#888;">
                                    {pos_cnt} of {total} Indicators are Bullish
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Optional: Expandable details
                        with st.expander("View Indicators"):
                            st.write(f"**RSI:** {df['RSI'].iloc[-1]:.2f}")
                            st.write(f"**Trend:** {'Bullish' if score > 5 else 'Bearish'}")
                            
                    idx += 1
                except Exception as e:
                    pass
            st.markdown("<br>", unsafe_allow_html=True)

with tab2:
    st.header("🌍 Market Sentiment News")
    news_opt = st.radio("Source:", ["General", "India", "Crypto"], horizontal=True)
    
    # (Existing News Logic kept same but cleaner UI)
    feed_url = "https://finance.yahoo.com/news/rssindex" # Default
    if news_opt == "India": feed_url = "https://www.moneycontrol.com/rss/economy.xml"
    if news_opt == "Crypto": feed_url = "https://cointelegraph.com/rss"
    
    feed = feedparser.parse(feed_url)
    
    for entry in feed.entries[:8]:
        sent = sia.polarity_scores(entry.title)['compound']
        border_col = "#009933" if sent > 0.05 else ("#cc0000" if sent < -0.05 else "#ddd")
        
        st.markdown(f"""
        <div style="background:#fff; padding:15px; border-left:5px solid {border_col}; margin-bottom:10px; box-shadow:0 2px 4px #eee;">
            <a href="{entry.link}" target="_blank" style="text-decoration:none; color:#333; font-weight:bold; font-size:16px;">
                {entry.title}
            </a>
            <div style="font-size:12px; color:#888; margin-top:5px;">
                Published: {entry.published if 'published' in entry else 'Now'}
            </div>
        </div>
        """, unsafe_allow_html=True)
