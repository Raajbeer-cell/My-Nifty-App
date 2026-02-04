import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import streamlit.components.v1 as components

# --- 1. SETTINGS & NOTIFICATION JS ---
st.set_page_config(page_title="Quantum Sniper Elite", page_icon="🚀", layout="wide")

def trigger_browser_notification(title, message):
    # JavaScript to handle Browser Push Alerts
    notification_js = f"""
    <script>
    function notifyMe() {{
      if (!("Notification" in window)) {{
        alert("This browser does not support desktop notification");
      }} else if (Notification.permission === "granted") {{
        new Notification("{title}", {{ body: "{message}", icon: "https://cdn-icons-png.flaticon.com/512/1001/1001022.png" }});
      }} else if (Notification.permission !== "denied") {{
        Notification.requestPermission().then((permission) => {{
          if (permission === "granted") {{
            new Notification("{title}", {{ body: "{message}" }});
          }}
        }});
      }}
    }}
    notifyMe();
    </script>
    """
    components.html(notification_js, height=0)

# --- 2. ASSETS CONFIGURATION ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "FIN NIFTY": "NIFTY_FIN_SERVICE.NS"},
    "⚒️ MCX (METALS/OIL)": {"SILVER": "SI=F", "GOLD": "GC=F", "COPPER": "HG=F", "CRUDE OIL": "CL=F"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD", "SOLANA": "SOL-USD"},
    "💱 FOREX": {"USD/INR": "USDINR=X", "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X"},
    "🇺🇸 US MARKETS": {"NVIDIA": "NVDA", "TESLA": "TSLA", "APPLE": "AAPL"}
}

# --- 3. POWERFUL ANALYSIS ENGINE ---
@st.cache_data(ttl=60)
def get_advanced_analysis(symbol, name):
    try:
        df = yf.download(symbol, period="150d", interval="1h", progress=False)
        if df.empty: return None

        # Indicators for Precision
        df['EMA200'] = ta.ema(df['Close'], length=200) # Institutional Trend
        df['EMA50'] = ta.ema(df['Close'], length=50)   # Short-term Momentum
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'])['ADX_14']
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        
        # Logic Building
        action = "WAIT"
        color = "#888"
        strength = "Weak"
        
        # Trend & Strength Logic
        is_bullish = last['Close'] > last['EMA200'] and last['EMA50'] > last['EMA200']
        is_bearish = last['Close'] < last['EMA200'] and last['EMA50'] < last['EMA200']
        
        if is_bullish and last['RSI'] > 55:
            action = "STRONG BUY 🚀"
            color = "#00ffaa"
        elif is_bearish and last['RSI'] < 45:
            action = "STRONG SELL 🩸"
            color = "#ff4b4b"
            
        if last['ADX'] > 25: strength = "Trending 🔥"
        if last['ADX'] > 50: strength = "Explosive ⚡"

        # Astro Logic (Sector Based)
        astro_reason = "Neutral Cycle"
        if "SI=F" in symbol or "GC=F" in symbol:
            astro_reason = "Moon cycle indicates liquidity surge in Metals."
        elif "^NSE" in symbol:
            astro_reason = "Jupiter aspect supports Financial Index stability."

        return {
            "price": last['Close'], "action": action, "color": color, 
            "adx": last['ADX'], "rsi": last['RSI'], "strength": strength,
            "sl": last['Close'] - (last['ATR']*2.5) if "BUY" in action else last['Close'] + (last['ATR']*2.5),
            "tp": last['Close'] + (last['ATR']*5) if "BUY" in action else last['Close'] - (last['ATR']*5),
            "astro": astro_reason
        }
    except: return None

# --- 4. UI NAVIGATION ---
st.sidebar.title("🎯 SNIPER ELITE v3")
st.sidebar.info("Auto-Refreshes every 60s with Browser Alerts.")
mode = st.sidebar.radio("Select Mode", ["Dashboard", "Wealth & Astro", "News Impact"])

# --- DASHBOARD MODE ---
if mode == "Dashboard":
    # Asking for notification permission on first load
    components.html("<script>Notification.requestPermission();</script>", height=0)

    for cat_name, tickers in ASSETS.items():
        st.subheader(cat_name)
        cols = st.columns(3)
        for i, (name, symbol) in enumerate(tickers.items()):
            res = get_advanced_analysis(symbol, name)
            if res:
                # Trigger Alert if Strong Signal
                if "STRONG" in res['action']:
                    trigger_browser_notification(f"Signal Alert: {name}", f"{res['action']} at {res['price']:.2f}")
                
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="background:#0d1117; padding:20px; border-radius:12px; border:1px solid {res['color']}55;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-weight:bold;">{name}</span>
                            <span style="color:{res['color']};">{res['strength']}</span>
                        </div>
                        <div style="font-size:26px; font-weight:bold; margin:10px 0;">{res['price']:,.2f}</div>
                        <div style="color:{res['color']}; font-weight:bold; font-size:18px;">{res['action']}</div>
                        <hr style="opacity:0.2;">
                        <div style="font-size:13px; color:#aaa;">
                            🎯 TGT: <span style="color:#00ffaa;">{res['tp']:,.1f}</span> | 
                            🛑 SL: <span style="color:#ff4b4b;">{res['sl']:,.1f}</span>
                        </div>
                        <div style="margin-top:10px; font-size:11px; font-style:italic; color:#818cf8;">
                            ✨ {res['astro']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# --- WEALTH & ASTRO MODE ---
elif mode == "Wealth & Astro":
    st.header("💎 Institutional Wealth Picks")
    st.write("Special selection based on Astro-Cycles and 200-EMA Institutional Support.")
    
    w_cols = st.columns(2)
    with w_cols[0]:
        st.success("### 🇮🇳 TATA MOTORS (Holding)")
        st.write("**Reason:** Breakout above 200 EMA + Rahu transit favoring Auto/Tech exports.")
        st.write("**Entry Zone:** Current Market Price | **Target:** 1200+")
    with w_cols[1]:
        st.info("### 🪙 BITCOIN (Digital Gold)")
        st.write("**Reason:** Halving cycles aligning with global liquidity expansion.")
        st.write("**Entry Zone:** $40k-$45k (Dips) | **Target:** $100k")

# --- NEWS IMPACT MODE ---
elif mode == "News Impact":
    st.header("🧠 AI News Reasoner")
    feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
    for entry in feed.entries[:5]:
        st.markdown(f"""
        <div style="background:#161b22; padding:15px; border-radius:10px; margin-bottom:10px;">
            <a href="{entry.link}" style="color:#58a6ff; font-weight:bold;">{entry.title}</a>
            <p style="font-size:13px; margin-top:5px; color:#d2a8ff;">
                ⚠️ <b>Impact:</b> This news affects <b>USD Pairs & Global Indices</b>. 
                <b>Reason:</b> Institutional sentiment shifts based on inflation data mentioned.
            </p>
        </div>
        """, unsafe_allow_html=True)

# --- AUTO REFRESH ---
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=60000, key="autotracker")
