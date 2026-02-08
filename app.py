import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# 1. AUTO REFRESH (Har 60 seconds mein page refresh hoga)
st_autorefresh(interval=60 * 1000, key="datarefresh")

# 2. PAGE CONFIG
st.set_page_config(page_title="Ultimate Trader Pro", layout="wide")

# 3. ADVANCED STYLING
st.markdown("""
<style>
    .stApp { background: #0a0e14; color: #e1e1e1; }
    .trade-card { 
        background: #161b22; padding: 20px; border-radius: 15px; 
        border-left: 5px solid #58a6ff; margin-bottom: 20px;
    }
    .metric-title { font-size: 18px; font-weight: bold; color: #8b949e; }
    .price-val { font-size: 32px; font-weight: 900; color: #ffffff; }
    .impact-box { background: #21262d; padding: 10px; border-radius: 8px; font-size: 13px; }
    .buy-signal { color: #3fb950; }
    .sell-signal { color: #f85149; }
</style>
""", unsafe_allow_html=True)

# 4. ASSETS & DATA FETCHING
ASSETS = {
    "🇮🇳 INDIAN INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD"},
    "💎 COMMODITIES": {"GOLD": "GC=F", "SILVER": "SI=F"}
}

@st.cache_data(ttl=60)
def get_data(symbol):
    df = yf.download(symbol, period="5d", interval="15m", progress=False)
    return df

# 5. BRAIN OF THE APP (Signal & Impact Logic)
def analyze_asset(df, name):
    df['EMA200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    adx = ta.adx(df['High'], df['Low'], df['Close'])
    curr_adx = adx['ADX_14'].iloc[-1]
    
    # Support & Resistance
    res = df['High'].tail(20).max()
    sup = df['Low'].tail(20).min()
    
    close = df['Close'].iloc[-1]
    ema = df['EMA200'].iloc[-1]
    
    # Trend Logic
    if curr_adx < 20: trend = "SIDEWAYS (No Entry)"
    elif close > ema: trend = "UPTREND (Trending)"
    else: trend = "DOWNTREND (Trending)"
    
    return {
        "price": close,
        "trend": trend,
        "sup": sup, "res": res,
        "rsi": df['RSI'].iloc[-1],
        "adx": curr_adx
    }

# 6. UI LAYOUT
st.title("🎯 ULTIMATE TRADER PRO (Advanced)")

tab1, tab2, tab3 = st.tabs(["📊 LIVE SCANNER", "📰 NEWS IMPACT", "🚀 HOT STOCKS"])

with tab1:
    for cat, tickers in ASSETS.items():
        st.subheader(cat)
        cols = st.columns(len(tickers))
        for i, (name, sym) in enumerate(tickers.items()):
            df = get_data(sym)
            if not df.empty:
                analysis = analyze_asset(df, name)
                with cols[i]:
                    color = "#3fb950" if "UPTREND" in analysis['trend'] else "#f85149" if "DOWNTREND" in analysis['trend'] else "#8b949e"
                    st.markdown(f"""
                    <div class="trade-card" style="border-left-color: {color}">
                        <div class="metric-title">{name}</div>
                        <div class="price-val">${analysis['price']:.2f}</div>
                        <div style="color:{color}; font-weight:bold;">{analysis['trend']}</div>
                        <hr style="opacity:0.1">
                        <div style="font-size:14px;">
                            <b>Entry:</b> Above {analysis['res']:.2f}<br>
                            <b>Target:</b> {analysis['res']*1.02:.2f}<br>
                            <b>StopLoss:</b> {analysis['sup']:.2f}
                        </div>
                        <div style="margin-top:10px; font-size:12px; color:#8b949e;">
                            S: {analysis['sup']:.2f} | R: {analysis['res']:.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

with tab2:
    st.subheader("Why Market is Moving?")
    news_data = [
        {"title": "US Inflation Data Release", "impact": "High", "reason": "Interest rates hike fear causes Sell-off in Gold & Tech stocks."},
        {"title": "RBI Policy Update", "impact": "Moderate", "reason": "Steady rates keeping BankNifty in Sideways zone."},
    ]
    for n in news_data:
        st.markdown(f"""
        <div class="trade-card">
            <h4>{n['title']} (Impact: {n['impact']})</h4>
            <p class="impact-box"><b>Reason:</b> {n['reason']}</p>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.subheader("Best Stocks to Hold (Expected Return)")
    stocks = [
        {"name": "RELIANCE", "return": "12-15%", "time": "3 Months", "view": "Bullish - Expansion in Green Energy."},
        {"name": "TATA MOTORS", "return": "20%", "time": "6 Months", "view": "Strong EV Sales growth."},
    ]
    st.table(stocks)
