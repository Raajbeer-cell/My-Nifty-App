import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
import time  # NEW: Time module add kiya auto-refresh ke liye
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- SETUP ---
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

st.set_page_config(page_title="Ultimate Pro Trader", page_icon="🚀", layout="wide")

# --- 1. NEW FEATURE: AUTO REFRESH LOGIC ---
if 'last_run' not in st.session_state:
    st.session_state['last_run'] = time.time()

# Sidebar me refresh control
refresh_sec = st.sidebar.slider("⏳ Auto-Refresh Rate (Seconds):", 10, 300, 60)
auto_ref = st.sidebar.checkbox("🟢 Enable Auto-Refresh", value=True)

if auto_ref:
    if time.time() - st.session_state['last_run'] > refresh_sec:
        st.session_state['last_run'] = time.time()
        st.rerun()

# --- 2. UI UPGRADE: MONEYCONTROL THEME ---
st.markdown("""
<style>
    /* Dark Background similar to MoneyControl/Terminal */
    .stApp { background-color: #121212; color: #e0e0e0; }
    
    /* Card Style */
    .box { 
        background-color: #1e1e1e; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 5px solid #444; 
        margin-bottom: 15px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Dynamic Borders */
    .box-bull { border-left: 5px solid #00D09C !important; } /* MoneyControl Green */
    .box-bear { border-left: 5px solid #FF4D4D !important; } /* MoneyControl Red */
    .box-silver { border: 1px solid #C0C0C0; background-color: #181818; }

    /* Text Styles */
    .asset-name { font-size: 16px; font-weight: bold; color: #FFFFFF; }
    .price-big { font-size: 26px; font-weight: bold; margin: 5px 0; }
    
    /* Strength Meter Bar */
    .strength-bar-bg { width: 100%; background-color: #333; height: 6px; border-radius: 3px; margin-top: 5px; }
    .strength-bar-fill { height: 100%; border-radius: 3px; }
    
    /* Badges */
    .badge-bull { background-color: rgba(0, 208, 156, 0.2); color: #00D09C; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .badge-bear { background-color: rgba(255, 77, 77, 0.2); color: #FF4D4D; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    
    .news-title { color: #58a6ff; font-weight: bold; text-decoration: none; font-size: 15px; }
    .impact-msg { color: #d2a8ff; font-size: 12px; margin-top: 5px; border-left: 2px solid #d2a8ff; padding-left: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 ULTIMATE TRADER: Live Signals & AI")

# --- ASSETS CONFIGURATION ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD", "SOLANA": "SOL-USD", "XRP": "XRP-USD"},
    "⛏️ COMMODITIES": {"SILVER (MCX SIM)": "SI=F", "GOLD": "GC=F", "CRUDE OIL": "CL=F", "COPPER": "HG=F"}
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

# --- FUNCTIONS ---

@st.cache_data(ttl=refresh_sec) # Cache syncs with auto-refresh
def fetch_data(tickers, period, interval):
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    return data

def get_signal(df, ticker_name=""):
    if df.empty or len(df) < 50: return None
    
    # --- EXISTING CALCULATIONS ---
    df['EMA_50'] = df.ta.ema(length=50)
    df['EMA_20'] = df.ta.ema(length=20)
    df['RSI'] = df.ta.rsi(length=14)
    df['ATR'] = df.ta.atr(length=14)
    df['ADX'] = df.ta.adx(length=14)['ADX_14'] # ADX fix
    
    st_data = df.ta.supertrend(length=10, multiplier=3)
    st_dir_col = [c for c in st_data.columns if "SUPERTd_" in c][0]
    df['Trend'] = st_data[st_dir_col]

    # Z-Score
    df['Z_Score'] = (df['Close'] - df['Close'].rolling(20).mean()) / df['Close'].rolling(20).std()

    # Current Values
    close = df['Close'].iloc[-1]
    trend = df['Trend'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    atr = df['ATR'].iloc[-1]
    ema20 = df['EMA_20'].iloc[-1]
    ema50 = df['EMA_50'].iloc[-1]
    adx = df['ADX'].iloc[-1]
    z_score = df['Z_Score'].iloc[-1]
    
    support = df['Low'].tail(20).min()
    resistance = df['High'].tail(20).max()
    
    # --- 3. NEW FEATURE: SILVER PRICE CONVERSION (To ~285,000) ---
    # Logic: Global Silver ($31 approx) * USDINR (87) * Lot Multiplier (100) = ~2,70,000 - 2,85,000
    display_price = close
    
    if "SILVER" in ticker_name or "SI=F" in ticker_name:
        conversion_factor = 87 * 100 # USD to INR * Lot Size
        display_price = close * conversion_factor
        atr = atr * conversion_factor # ATR ko bhi adjust karo taaki SL/Target sahi dikhe
        support = support * conversion_factor
        resistance = resistance * conversion_factor
        ema20 = ema20 * conversion_factor
        ema50 = ema50 * conversion_factor
    
    # --- 4. NEW FEATURE: STRENGTH METER (1-10) & COUNT ---
    score = 0
    pos_indicators = 0
    
    # Scoring Logic (Max 10)
    if trend == 1: score += 2; pos_indicators += 1             # Supertrend
    if rsi > 50: score += 2; pos_indicators += 1               # RSI
    if display_price > ema50: score += 2; pos_indicators += 1  # EMA Trend
    if adx > 25: score += 2; pos_indicators += 1               # ADX Strength
    if display_price > ema20: score += 2; pos_indicators += 1  # Short term mom
    
    # Bearish Case Adjustment (Agar trend down hai to score bear ke liye count karo)
    is_bearish = False
    if trend == -1:
        is_bearish = True
        score = 0 # Reset
        pos_indicators = 0
        if trend == -1: score += 2; pos_indicators += 1
        if rsi < 50: score += 2; pos_indicators += 1
        if display_price < ema50: score += 2; pos_indicators += 1
        if adx > 25: score += 2; pos_indicators += 1
        if display_price < ema20: score += 2; pos_indicators += 1

    # --- ACTION DECISION (OLD LOGIC KEPT) ---
    action = "WAIT"
    color = "grey"
    box_class = "box"
    
    # Silver Specific Logic
    if "SILVER" in ticker_name or "SI=F" in ticker_name:
        box_class = "box box-silver"
        if trend == 1 and display_price > ema20:
             action = "BUY SILVER 🚀"
             color = "#00D09C"
             box_class = "box box-bull"
             sl = display_price - (atr * 2)
             tgt = display_price + (atr * 4)
        elif trend == -1 and display_price < ema20:
             action = "SELL SILVER 🩸"
             color = "#FF4D4D"
             box_class = "box box-bear"
             sl = display_price + (atr * 2)
             tgt = display_price - (atr * 4)
        else:
             sl=0; tgt=0

    # Normal Asset Logic
    else:
        if trend == 1 and rsi > 50:
            action = "BUY / CALL 🟢"
            color = "#00D09C"
            box_class = "box box-bull"
            sl = display_price - (atr * 1.5)
            tgt = display_price + (atr * 3)
        elif trend == -1 and rsi < 50:
            action = "SELL / PUT 🔴"
            color = "#FF4D4D"
            box_class = "box box-bear"
            sl = display_price + (atr * 1.5)
            tgt = display_price - (atr * 3)
        else:
            sl=0; tgt=0

    return {
        "action": action, "color": color, "price": display_price, 
        "sl": sl, "tgt": tgt, "supp": support, "res": resistance,
        "score": score, "pos_count": pos_indicators, "box_class": box_class,
        "z_score": z_score, "adx": adx
    }

# --- NEWS FUNCTIONS (SAME) ---
RSS_FEEDS = { "General": "https://finance.yahoo.com/news/rssindex", "Crypto": "https://cointelegraph.com/rss", "India": "https://www.moneycontrol.com/rss/economy.xml" }

def analyze_news_sentiment(text):
    score = sia.polarity_scores(text)['compound']
    if score > 0.05: return "BULLISH", "badge-bull"
    elif score < -0.05: return "BEARISH", "badge-bear"
    return "NEUTRAL", "badge-wait"

def get_impact(text):
    text = text.lower()
    if "inflation" in text or "rate" in text: return "⚠️ Impact: BANKNIFTY & LOANS"
    if "oil" in text: return "⚠️ Impact: PAINTS & TYRES"
    if "bitcoin" in text or "crypto" in text: return "⚠️ Impact: CRYPTO MARKET"
    if "gold" in text or "silver" in text: return "⚠️ Impact: PRECIOUS METALS"
    return ""

# --- PART 3: MAIN APP UI ---

tab1, tab2 = st.tabs(["📊 MARKET SCANNER", "🌍 NEWS & SENTIMENT"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("📈 Live Signals (Auto-Updating)")
    with col2:
        timeframe = st.selectbox("Timeframe:", ["15m", "1h", "4h", "1d"])
        
    tf_map = {"15m": "5d", "1h": "1mo", "4h": "1mo", "1d": "1y"}
    
    with st.spinner("Scanning Market..."):
        raw_data = fetch_data(ALL_TICKERS, period=tf_map[timeframe], interval=timeframe)

    if raw_data is not None:
        for cat_name, tickers in ASSETS.items():
            st.subheader(cat_name)
            cols = st.columns(3)
            idx = 0
            for name, symbol in tickers.items():
                try:
                    if len(ALL_TICKERS) > 1: df = raw_data[symbol].dropna()
                    else: df = raw_data.dropna()
                    
                    sig = get_signal(df, name)
                    
                    if sig:
                        # Bar color logic
                        bar_color = "#00D09C" if "BUY" in sig['action'] else "#FF4D4D" if "SELL" in sig['action'] else "#888"
                        
                        with cols[idx % 3]:
                            st.markdown(f"""
                            <div class="{sig['box_class']}">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span class="asset-name">{name}</span>
                                    <span style="color:{sig['color']}; font-weight:bold;">{sig['action']}</span>
                                </div>
                                
                                <div class="price-big" style="color:{sig['color']}">{sig['price']:,.2f}</div>
                                
                                <div style="font-size:12px; color:#aaa; margin-top:5px;">
                                    TREND STRENGTH: <b style="color:{bar_color}">{sig['score']}/10</b>
                                </div>
                                <div class="strength-bar-bg">
                                    <div class="strength-bar-fill" style="width:{sig['score']*10}%; background-color:{bar_color};"></div>
                                </div>
                                
                                <div style="font-size:12px; margin-top:8px;">
                                    ✅ <b>{sig['pos_count']}/5</b> Indicators Positive
                                </div>
                                <div style="font-size:11px; color:#666;">Z-Score: {sig['z_score']:.2f} | ADX: {sig['adx']:.0f}</div>
                                
                                <hr style="border-color:#333; margin:10px 0;">
                                
                                <div style="font-size:13px; display:flex; justify-content:space-between;">
                                    <span>🎯 Tgt: <b style="color:#00D09C;">{sig['tgt']:,.0f}</b></span>
                                    <span>🛑 SL: <b style="color:#FF4D4D;">{sig['sl']:,.0f}</b></span>
                                </div>
                                <div style="font-size:12px; color:#888; margin-top:5px;">
                                    🧱 Res: {sig['res']:,.0f} | 🛏️ Supp: {sig['supp']:,.0f}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        idx += 1
                except Exception as e:
                    continue
            st.markdown("---")

with tab2:
    st.header("📰 Global News & AI Analysis")
    
    st.subheader("🌍 Global Fear Meter (Macro)")
    m_cols = st.columns(4)
    macro_ticks = ["^INDIAVIX", "^VIX", "DX-Y.NYB", "BZ=F"]
    macro_names = ["🇮🇳 INDIA VIX", "🇺🇸 US VIX", "💵 DOLLAR (DXY)", "🛢️ BRENT OIL"]
    
    try:
        m_data = yf.download(macro_ticks, period="5d", interval="1d", group_by='ticker', progress=False)
        for i, tick in enumerate(macro_ticks):
            try:
                curr = m_data[tick]['Close'].iloc[-1]
                prev = m_data[tick]['Close'].iloc[-2]
                chg = ((curr - prev)/prev)*100
                colr = "#FF4D4D" if chg > 0 else "#00D09C"
                if "BZ" in tick or "DX" in tick: colr = "#FF4D4D" if chg > 0 else "#00D09C"
                
                with m_cols[i]:
                    st.markdown(f"""
                    <div class="box" style="text-align:center; padding:10px;">
                        <small style="color:#aaa;">{macro_names[i]}</small><br>
                        <b style="font-size:18px;">{curr:.2f}</b><br>
                        <span style="color:{colr}; font-weight:bold;">{chg:+.2f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
            except: pass
    except: st.error("Macro Data Load Fail")

    st.markdown("---")
    
    news_opt = st.radio("Select News Source:", ["General", "Crypto", "India"], horizontal=True)
    
    feed = feedparser.parse(RSS_FEEDS[news_opt])
    for entry in feed.entries[:10]:
        sent, badge_cls = analyze_news_sentiment(entry.title)
        impact = get_impact(entry.title)
        
        st.markdown(f"""
        <div class="box" style="padding:10px;">
            <div style="display:flex; justify-content:space-between;">
                <a href="{entry.link}" target="_blank" class="news-title">{entry.title}</a>
                <span class="{badge_cls}">{sent}</span>
            </div>
            <div style="color:#666; font-size:11px; margin-top:5px;">🕒 {entry.published if 'published' in entry else 'Just Now'}</div>
            <div class="impact-msg">{impact}</div>
        </div>
        """, unsafe_allow_html=True)
