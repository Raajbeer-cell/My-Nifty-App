import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP & THEME ---
st.set_page_config(page_title="Nifty Sniper Pro", page_icon="📈", layout="wide")

@st.cache_resource
def load_nlp():
    try:
        nltk.download('vader_lexicon')
        return SentimentIntensityAnalyzer()
    except: return None

sia = load_nlp()

# Custom CSS for Institutional Look
st.markdown("""
<style>
    .stApp { background-color: #05070a; color: #e1e1e1; }
    .metric-card {
        background: linear-gradient(145deg, #111827, #030712);
        padding: 20px; border-radius: 12px; border: 1px solid #1f2937;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .buy-signal { color: #10b981; font-weight: bold; font-size: 1.2rem; }
    .sell-signal { color: #ef4444; font-weight: bold; font-size: 1.2rem; }
    .build-up-tag { background: #1e3a8a; color: #60a5fa; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
    .impact-high { border-left: 5px solid #ef4444; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE (INDIAN MARKET FOCUS) ---

def analyze_derivative_build_up(df):
    """Calculates Build-up based on Price and Volume interaction"""
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    price_chg = (last['Close'] - prev['Close']) / prev['Close']
    vol_chg = (last['Volume'] - prev['Volume']) / prev['Volume']
    
    if price_chg > 0 and vol_chg > 0.1: return "LONG BUILD-UP 🟢"
    if price_chg < 0 and vol_chg > 0.1: return "SHORT BUILD-UP 🔴"
    if price_chg > 0 and vol_chg < -0.1: return "SHORT COVERING 🔵"
    if price_chg < 0 and vol_chg < -0.1: return "LONG UNWINDING 🟠"
    return "NEUTRAL ⚪"

@st.cache_data(ttl=60)
def get_nifty_data(symbol):
    df = yf.download(symbol, period="5d", interval="15m", progress=False)
    if df.empty: return None
    
    # Advanced Indicators
    df['EMA200'] = ta.ema(df['Close'], length=200)
    df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    last = df.iloc[-1]
    buildup = analyze_derivative_build_up(df)
    
    # Target & Stoploss Logic
    action = "SCANNING"
    if last['Close'] > last['EMA200'] and last['RSI'] > 55:
        action = "STRONG BUY"
    elif last['Close'] < last['EMA200'] and last['RSI'] < 45:
        action = "STRONG SELL"
        
    return {
        "price": last['Close'], "buildup": buildup, "action": action,
        "rsi": last['RSI'], "vwap": last['VWAP'],
        "sl": last['Close'] - (last['ATR']*2) if "BUY" in action else last['Close'] + (last['ATR']*2),
        "tp": last['Close'] + (last['ATR']*4) if "BUY" in action else last['Close'] - (last['ATR']*4),
        "vol_breakout": last['Volume'] > df['Volume'].mean() * 1.5
    }

# --- 3. NEWS & SENTIMENT ENGINE ---
def get_news_impact():
    feed = feedparser.parse("https://www.moneycontrol.com/rss/economy.xml")
    impact_list = []
    for entry in feed.entries[:5]:
        text = entry.title.lower()
        impact = "Neutral"
        affected = "General Market"
        
        if "bank" in text or "rbi" in text or "hdfc" in text:
            affected = "BANK NIFTY"; impact = "High"
        elif "nifty" in text or "tax" in text or "gdp" in text:
            affected = "NIFTY 50"; impact = "Moderate"
            
        sent = sia.polarity_scores(entry.title)['compound'] if sia else 0
        impact_list.append({"title": entry.title, "affected": affected, "sentiment": sent, "impact": impact})
    return impact_list

# --- 4. UI LAYOUT ---
st.title("📈 NIFTY & BANK NIFTY COMMAND CENTER")
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Live Dashboard", "News Impact AI", "Astro & Wealth Picks"])

# Auto Refresh
st_autorefresh(interval=60000, key="niftyrefresh")

if page == "Live Dashboard":
    # --- ROW 1: NIFTY & BANKNIFTY ---
    st.subheader("🇮🇳 Major Indian Indices")
    indices = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"}
    idx_cols = st.columns(2)
    
    for i, (name, sym) in enumerate(indices.items()):
        data = get_nifty_data(sym)
        if data:
            with idx_cols[i]:
                color = "#10b981" if "BUY" in data['action'] else "#ef4444"
                st.markdown(f"""
                <div class="metric-card" style="border-top: 4px solid {color};">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-size:1.2rem; font-weight:bold;">{name}</span>
                        <span class="build-up-tag">{data['buildup']}</span>
                    </div>
                    <div style="font-size:2.5rem; font-weight:800; margin:15px 0;">{data['price']:,.2f}</div>
                    <div style="color:{color}; font-weight:bold;">SIGNAL: {data['action']}</div>
                    <hr style="opacity:0.1;">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                        <div>🎯 Target: <br><b style="color:#10b981;">{data['tp']:,.1f}</b></div>
                        <div>🛑 Stoploss: <br><b style="color:#ef4444;">{data['sl']:,.1f}</b></div>
                    </div>
                    <div style="margin-top:15px; font-size:0.85rem; color:#9ca3af;">
                        <b>Reason:</b> {'Volume Breakout' if data['vol_breakout'] else 'Regular Volume'} | RSI: {data['rsi']:.1f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # --- ROW 2: COMMODITIES & FOREX ---
    st.markdown("---")
    st.subheader("⚒️ Commodities & Forex (Global Impact)")
    comm_cols = st.columns(3)
    comms = {"SILVER (MCX)": "SI=F", "GOLD": "GC=F", "USD/INR": "USDINR=X"}
    for i, (name, sym) in enumerate(comms.items()):
        res = get_nifty_data(sym)
        if res:
            with comm_cols[i]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="color:#9ca3af; font-size:0.9rem;">{name}</div>
                    <div style="font-size:1.5rem; font-weight:bold;">{res['price']:,.2f}</div>
                    <div style="font-size:0.8rem; color:{res['color']};">{res['action']}</div>
                </div>
                """, unsafe_allow_html=True)

elif page == "News Impact AI":
    st.subheader("🧠 News Reasoning & Market Impact")
    news_data = get_news_impact()
    for n in news_data:
        impact_color = "#ef4444" if n['impact'] == "High" else "#3b82f6"
        st.markdown(f"""
        <div class="metric-card impact-high" style="border-left-color:{impact_color}; margin-bottom:15px;">
            <div style="font-weight:bold; font-size:1.1rem; color:#60a5fa;">{n['title']}</div>
            <div style="margin-top:8px;">
                🎯 <b>Affected:</b> {n['affected']} | 💥 <b>Impact:</b> {n['impact']}
            </div>
            <div style="font-size:0.9rem; color:#9ca3af; margin-top:5px;">
                <b>AI Analysis:</b> News sentiment is {n['sentiment']:.2f}. This news creates 
                {'Panic/Selling' if n['sentiment'] < 0 else 'Optimism/Buying'} specifically in {n['affected']} stocks.
            </div>
        </div>
        """, unsafe_allow_html=True)

elif page == "Astro & Wealth Picks":
    st.header("✨ Astro-Wealth Strategic Picks")
    st.info("Technical + Astro Cycle analysis for long-term holding.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🇮🇳 HDFC BANK</h3>
            <p style="color:#10b981;"><b>REASON:</b> Time cycle breakout. Saturn-Jupiter alignment favors heavyweights.</p>
            <p><b>Entry:</b> 1620-1650 | <b>Target:</b> 1850 | <b>SL:</b> 1580</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>🪙 SILVER (Long Term)</h3>
            <p style="color:#10b981;"><b>REASON:</b> Industrial demand + Moon cycle volatility.</p>
            <p><b>MCX Target:</b> 1,05,000 | <b>Holding:</b> 6 Months</p>
        </div>
        """, unsafe_allow_html=True)
