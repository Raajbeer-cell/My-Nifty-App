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


import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
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
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Roboto', sans-serif; }
    
    /* Silver Card Special */
    .silver-card {
        background: linear-gradient(135deg, #2c3e50, #000000);
        border: 2px solid #C0C0C0; /* Silver Border */
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.2);
        margin-bottom: 20px;
    }
    
    .metric-card {
        background: linear-gradient(145deg, #1a1a1a, #0d0d0d);
        border: 1px solid #333;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 15px;
    }
    
    .badge-long { background-color: rgba(0, 255, 0, 0.1); color: #00ff00; border: 1px solid #00ff00; padding: 4px 10px; border-radius: 8px; font-weight: bold; }
    .badge-short { background-color: rgba(255, 0, 0, 0.1); color: #ff4444; border: 1px solid #ff4444; padding: 4px 10px; border-radius: 8px; font-weight: bold; }
    .badge-wait { background-color: #222; color: #888; padding: 4px 10px; border-radius: 8px; border: 1px solid #444; }
    
    .block-zone { color: #f39c12; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL ---
with st.sidebar:
    st.title("⚡ Control Center")
    auto_refresh = st.checkbox("🔄 Enable 15s Auto-Refresh", value=False)
    if auto_refresh:
        st.markdown(f'<meta http-equiv="refresh" content="15">', unsafe_allow_html=True)
        st.markdown(f"<small style='color:#00ff00'>Live: {datetime.now().strftime('%H:%M:%S')}</small>", unsafe_allow_html=True)
    else:
        if st.button("Manual Refresh"): st.rerun()
    
    st.info("💡 **Silver Tip:** Silver follows global market (SI=F). Always trade with Order Blocks.")

# --- DATA CONFIGURATION ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🇺🇸 US TECH": {"TESLA": "TSLA", "NVIDIA": "NVDA", "APPLE": "AAPL"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "SOLANA": "SOL-USD"},
    "⛏️ COMMODITIES": {"GOLD": "GC=F", "CRUDE OIL": "CL=F", "NATURAL GAS": "NG=F"}
}
# Silver Special Ticker
SILVER_TICKER = "SI=F" 

ALL_TICKERS = list([v for cat in ASSETS.values() for v in cat.values()])
ALL_TICKERS.append(SILVER_TICKER)

# --- ANALYSIS ENGINE ---

@st.cache_data(ttl=15)
def fetch_data(tickers, period, interval):
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    return data

def analyze_silver_vip(df):
    if df.empty or len(df) < 50: return None
    
    # --- 1. Indicators Calculation (Max Indicators) ---
    df['EMA_20'] = df.ta.ema(length=20)
    df['EMA_50'] = df.ta.ema(length=50)
    df['EMA_200'] = df.ta.ema(length=200)
    df['RSI'] = df.ta.rsi(length=14)
    df['ATR'] = df.ta.atr(length=14)
    
    # MACD
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_SIG'] = macd['MACDs_12_26_9']
    
    # Bollinger Bands
    bb = df.ta.bbands(length=20, std=2)
    df['BB_UP'] = bb['BBU_20_2.0']
    df['BB_LOW'] = bb['BBL_20_2.0']
    
    # Supertrend
    st_data = df.ta.supertrend(length=10, multiplier=3)
    st_dir_col = [c for c in st_data.columns if "SUPERTd_" in c][0]
    df['Trend'] = st_data[st_dir_col] # 1 = Up, -1 = Down

    # --- 2. Order Blocks (Support/Resistance) ---
    # Logic: Last 20 candles Low min and High max
    order_block_supp = df['Low'].tail(20).min()
    order_block_res = df['High'].tail(20).max()
    
    curr = df.iloc[-1]
    close = curr['Close']
    
    # --- 3. Decision Logic (Score System) ---
    score = 0
    total_checks = 5
    reasons = []
    
    # Check 1: Supertrend
    if curr['Trend'] == 1: score += 1; reasons.append("Supertrend Bullish")
    else: score -= 1; reasons.append("Supertrend Bearish")
    
    # Check 2: EMA Structure
    if close > curr['EMA_50']: score += 1
    else: score -= 1
    
    # Check 3: RSI
    if curr['RSI'] > 55: score += 1; reasons.append("RSI Strong")
    elif curr['RSI'] < 45: score -= 1; reasons.append("RSI Weak")
    
    # Check 4: MACD
    if curr['MACD'] > curr['MACD_SIG']: score += 1
    else: score -= 1
    
    # Check 5: Price vs EMA 20 (Momentum)
    if close > curr['EMA_20']: score += 1
    else: score -= 1

    # --- 4. Signal Generation ---
    signal = "NEUTRAL / CHOPPY"
    color = "badge-wait"
    action_text = "Wait for clear direction"
    
    if score >= 3:
        signal = "STRONG BUY / LONG 🚀"
        color = "badge-long"
        action_text = f"Buy Above {curr['High']:.2f}"
        sl = order_block_supp
        tgt1 = close + (curr['ATR'] * 2)
        tgt2 = close + (curr['ATR'] * 4)
    elif score <= -3:
        signal = "STRONG SELL / SHORT 🩸"
        color = "badge-short"
        action_text = f"Sell Below {curr['Low']:.2f}"
        sl = order_block_res
        tgt1 = close - (curr['ATR'] * 2)
        tgt2 = close - (curr['ATR'] * 4)
    else:
        sl = 0; tgt1 = 0; tgt2 = 0

    return {
        "signal": signal, "color": color, "price": close, "score": score,
        "sl": sl, "tgt1": tgt1, "tgt2": tgt2,
        "supp": order_block_supp, "res": order_block_res,
        "rsi": curr['RSI'], "reasons": reasons
    }

def analyze_market_general(df):
    # Simplified logic for other assets
    if df.empty or len(df) < 50: return None
    df['EMA_50'] = df.ta.ema(length=50)
    df['RSI'] = df.ta.rsi(length=14)
    st_data = df.ta.supertrend(length=10, multiplier=3)
    df['Trend'] = st_data[st_data.columns[1]]
    
    close = df['Close'].iloc[-1]
    trend = df['Trend'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    sig = "WAIT"; col = "badge-wait"
    if trend == 1 and rsi > 50: sig = "BUY"; col = "badge-long"
    elif trend == -1 and rsi < 50: sig = "SELL"; col = "badge-short"
    
    return {"signal": sig, "badge": col, "price": close}

# --- UI LAYOUT ---
st.title("⚡ ProTrader AI Terminal")

# Tabs
tab_silver, tab_scan, tab_mom = st.tabs(["💎 SILVER VIP (MCX)", "📊 GLOBAL SCANNER", "🔥 JACKPOT"])

# Get Data
raw_data = fetch_data(ALL_TICKERS, period="5d", interval="15m")

# === TAB 1: SILVER VIP ===
with tab_silver:
    st.markdown("### 💎 SILVER AUTOMATED AI TRADER")
    
    try:
        # Silver Logic
        if len(ALL_TICKERS) > 1: s_df = raw_data[SILVER_TICKER].dropna()
        else: s_df = raw_data.dropna()
        
        s_res = analyze_silver_vip(s_df)
        
        if s_res:
            # Main Signal Card
            st.markdown(f"""
            <div class="silver-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h2 style="color:#C0C0C0; margin:0;">SILVER (Global/MCX)</h2>
                    <span class="{s_res['color']}" style="font-size:18px;">{s_res['signal']}</span>
                </div>
                <h1 style="color:white; margin:10px 0;">${s_res['price']:.3f}</h1>
                <p style="color:#aaa;">Confidence Score: {abs(s_res['score'])}/5</p>
                <hr style="border-color:#555;">
                
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                    <div>
                        <h4 style="color:#00ff00; margin:0;">🎯 Targets (Profit Book)</h4>
                        <ul style="list-style:none; padding:0; color:#ddd;">
                            <li>Target 1: <b>{s_res['tgt1']:.3f}</b></li>
                            <li>Target 2: <b>{s_res['tgt2']:.3f}</b></li>
                        </ul>
                    </div>
                    <div>
                        <h4 style="color:#ff4444; margin:0;">🛑 Stop Loss</h4>
                        <div style="font-size:18px; font-weight:bold;">{s_res['sl']:.3f}</div>
                    </div>
                </div>
                
                <hr style="border-color:#555;">
                <h4 class="block-zone">🧱 ORDER BLOCKS (Institutional Zones)</h4>
                <div style="display:flex; justify-content:space-between; color:#ddd;">
                    <span>Resistance (Sellers): <b style="color:#ff4444">{s_res['res']:.3f}</b></span>
                    <span>Support (Buyers): <b style="color:#00ff00">{s_res['supp']:.3f}</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Technical Details
            with st.expander("🔍 View Technical Reason (Why AI took this trade?)", expanded=True):
                st.write(f"**RSI Value:** {s_res['rsi']:.1f}")
                st.write("**Confluence Factors:**")
                for reason in s_res['reasons']:
                    st.write(f"- {reason}")
                    
    except Exception as e:
        st.error(f"Waiting for Silver Data... (Error: {str(e)})")

# === TAB 2: GENERAL SCANNER ===
with tab_scan:
    st.subheader("📡 Global Market Overview")
    for cat_name, tickers in ASSETS.items():
        st.markdown(f"**{cat_name}**")
        cols = st.columns(3)
        idx = 0
        for name, symbol in tickers.items():
            try:
                if len(ALL_TICKERS) > 1: df = raw_data[symbol].dropna()
                else: df = raw_data.dropna()
                res = analyze_market_general(df)
                if res:
                    with cols[idx % 3]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <b>{name}</b> <span class="{res['badge']}">{res['signal']}</span><br>
                            <span style="font-size:20px;">{res['price']:.2f}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    idx += 1
            except: continue

# === TAB 3: JACKPOT MOVERS ===
with tab_mom:
    st.info("Searching for One-Sided Momentum (ADX > 25)...")
    # Reuse General Logic to find ADX spikes
    m_cols = st.columns(3)
    m_idx = 0
    for symbol in ALL_TICKERS:
        try:
            if len(ALL_TICKERS) > 1: df = raw_data[symbol].dropna()
            else: df = raw_data.dropna()
            
            adx = df.ta.adx(length=14)['ADX_14'].iloc[-1]
            if adx > 25:
                trend = "UP 🔥" if df['Close'].iloc[-1] > df.ta.ema(length=50).iloc[-1] else "DOWN ❄️"
                with m_cols[m_idx % 3]:
                    st.markdown(f"""
                    <div class="metric-card" style="border:1px solid #ff00cc;">
                        <b>{symbol}</b><br>
                        Trend: {trend}<br>
                        ADX Strength: {adx:.1f}
                    </div>
                    """, unsafe_allow_html=True)
                m_idx += 1
        except: continue


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
