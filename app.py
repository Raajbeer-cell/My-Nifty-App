import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# --- SETUP (Ye bas ek baar chalta hai) ---
# NLTK Vader Lexicon download (Sentiment samajhne ke liye)
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

# Page ka naam aur style set karna
st.set_page_config(page_title="Ultimate Pro Trader", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    .box { background-color: #111111; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .badge-bull { background-color: #004d00; color: #00ff00; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-bear { background-color: #4d0000; color: #ff0000; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .badge-wait { background-color: #333; color: #aaa; padding: 3px 8px; border-radius: 5px; }
    .news-title { color: #58a6ff; font-weight: bold; text-decoration: none; font-size: 16px; }
    .impact-msg { color: #d2a8ff; font-size: 13px; margin-top: 5px; border-left: 3px solid #d2a8ff; padding-left: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 ULTIMATE TRADER: Scanner + News AI")

# --- PART 1: DATA CONFIGURATION (Kiska data chahiye) ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD", "SOLANA": "SOL-USD", "XRP": "XRP-USD"},
    "⛏️ MCX/GLOBAL": {"GOLD": "GC=F", "SILVER": "SI=F", "CRUDE OIL": "CL=F", "COPPER": "HG=F"}
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

# --- PART 2: FUNCTIONS (Dimag wala kaam) ---

@st.cache_data(ttl=60)
def fetch_data(tickers, period, interval):
    # Ek saath saara data laata hai (Fast hai)
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    return data

def get_signal(df):
    # Ye function batata hai ki Buy karna hai ya Sell
    if df.empty or len(df) < 50: return None
    
    # Indicators calculate karna
    df['EMA_50'] = df.ta.ema(length=50)
    df['RSI'] = df.ta.rsi(length=14)
    df['ATR'] = df.ta.atr(length=14)
    
    # Supertrend
    st_data = df.ta.supertrend(length=10, multiplier=3)
    # Column names dhoondna (kabhi kabhi change hote hain)
    st_dir_col = [c for c in st_data.columns if "SUPERTd_" in c][0]
    df['Trend'] = st_data[st_dir_col] # 1 = Up, -1 = Down

    close = df['Close'].iloc[-1]
    trend = df['Trend'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    atr = df['ATR'].iloc[-1]
    
    # Order Block (Support/Resistance)
    support = df['Low'].tail(20).min()
    resistance = df['High'].tail(20).max()
    
    # Decision Lena
    action = "WAIT"
    color = "grey"
    
    if trend == 1 and close > df['EMA_50'].iloc[-1] and rsi > 50:
        action = "BUY / LONG 🚀"
        color = "#00ff00"
        sl = close - (atr * 1.5)
        tgt = close + (atr * 3)
    elif trend == -1 and close < df['EMA_50'].iloc[-1] and rsi < 50:
        action = "SELL / SHORT 🩸"
        color = "#ff0000"
        sl = close + (atr * 1.5)
        tgt = close - (atr * 3)
    else:
        sl = 0
        tgt = 0

    return {"action": action, "color": color, "price": close, "sl": sl, "tgt": tgt, "supp": support, "res": resistance}

# --- NEWS FUNCTIONS ---
RSS_FEEDS = {
    "General": "https://finance.yahoo.com/news/rssindex",
    "Crypto": "https://cointelegraph.com/rss",
    "India": "https://www.moneycontrol.com/rss/economy.xml"
}

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
    if "gold" in text: return "⚠️ Impact: GOLD LOAN STOCKS"
    return ""

# --- PART 3: MAIN APP UI (Jo screen pe dikhega) ---

# Tabs banate hain taaki screen saaf rahe
tab1, tab2 = st.tabs(["📊 MARKET SCANNER", "🌍 NEWS & SENTIMENT"])

# === TAB 1: SCANNER ===
with tab1:
    st.header("📈 Live Signals & Order Blocks")
    timeframe = st.selectbox("Timeframe Select Karo:", ["15m", "1h", "4h", "1d"])
    tf_map = {"15m": "5d", "1h": "1mo", "4h": "1mo", "1d": "1y"}
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Data lana
    with st.spinner("Market scan ho raha hai..."):
        raw_data = fetch_data(ALL_TICKERS, period=tf_map[timeframe], interval=timeframe)

    # Cards dikhana
    if raw_data is not None:
        for cat_name, tickers in ASSETS.items():
            st.subheader(cat_name)
            cols = st.columns(3)
            idx = 0
            for name, symbol in tickers.items():
                try:
                    # Data nikalna
                    if len(ALL_TICKERS) > 1: df = raw_data[symbol].dropna()
                    else: df = raw_data.dropna()
                    
                    sig = get_signal(df)
                    if sig:
                        with cols[idx % 3]:
                            st.markdown(f"""
                            <div class="box">
                                <div style="display:flex; justify-content:space-between;">
                                    <b>{name}</b>
                                    <span style="color:{sig['color']}; font-weight:bold;">{sig['action']}</span>
                                </div>
                                <h2 style="margin:5px 0;">{sig['price']:.2f}</h2>
                                <hr style="border-color:#333;">
                                <div style="font-size:14px;">
                                    🎯 Target: <span style="color:#00ff00;">{sig['tgt']:.2f}</span><br>
                                    🛑 StopLoss: <span style="color:#ff0000;">{sig['sl']:.2f}</span><br>
                                    🧱 Resistance: <span style="color:orange;">{sig['res']:.2f}</span><br>
                                    🛏️ Support: <span style="color:skyblue;">{sig['supp']:.2f}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        idx += 1
                except:
                    continue
            st.markdown("---")

# === TAB 2: NEWS & SENTIMENT ===
with tab2:
    st.header("📰 Global News & AI Analysis")
    
    # Macro Data (VIX etc)
    st.subheader("🌍 Global Fear Meter (Macro)")
    m_cols = st.columns(4)
    macro_ticks = ["^INDIAVIX", "^VIX", "DX-Y.NYB", "BZ=F"] # India Vix, US Vix, Dollar, Oil
    macro_names = ["🇮🇳 INDIA VIX", "🇺🇸 US VIX", "💵 DOLLAR (DXY)", "🛢️ BRENT OIL"]
    
    try:
        m_data = yf.download(macro_ticks, period="5d", interval="1d", group_by='ticker', progress=False)
        for i, tick in enumerate(macro_ticks):
            try:
                curr = m_data[tick]['Close'].iloc[-1]
                prev = m_data[tick]['Close'].iloc[-2]
                chg = ((curr - prev)/prev)*100
                colr = "red" if chg > 0 else "green" # VIX badhna market ke liye bura hota hai
                if "BZ" in tick or "DX" in tick: colr = "red" if chg > 0 else "green"
                
                with m_cols[i]:
                    st.markdown(f"""
                    <div class="box" style="text-align:center;">
                        <small>{macro_names[i]}</small><br>
                        <b style="font-size:20px;">{curr:.2f}</b><br>
                        <span style="color:{colr};">{chg:+.2f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
            except: pass
    except: st.error("Macro Data Load Fail")

    st.markdown("---")
    
    # News Feed
    news_opt = st.radio("Select News Source:", ["General", "Crypto", "India"], horizontal=True)
    
    feed = feedparser.parse(RSS_FEEDS[news_opt])
    for entry in feed.entries[:10]:
        sent, badge_cls = analyze_news_sentiment(entry.title)
        impact = get_impact(entry.title)
        
        st.markdown(f"""
        <div class="box">
            <div style="display:flex; justify-content:space-between;">
                <a href="{entry.link}" target="_blank" class="news-title">{entry.title}</a>
                <span class="{badge_cls}">{sent}</span>
            </div>
            <div style="color:#888; font-size:12px; margin-top:5px;">🕒 {entry.published if 'published' in entry else 'Just Now'}</div>
            <div class="impact-msg">{impact}</div>
        </div>
        """, unsafe_allow_html=True)
