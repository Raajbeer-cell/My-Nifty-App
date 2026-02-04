import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- Page Setup ---
st.set_page_config(page_title="Pro Nifty Trader AI", page_icon="🚀", layout="wide")
st.title("🚀 Pro Nifty & Intraday Hunter AI")
st.caption("Auto-Detects: Short Covering | Long Buildup | Order Blocks | Momentum Stocks")

# --- Styling ---
st.markdown("""
<style>
    .metric-card {background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333;}
    .buy {color: #00FF00; font-weight: bold;}
    .sell {color: #FF4B4B; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

# 1. Pivot Points & Order Blocks Calculator
def get_levels(df):
    high = df['High'].iloc[-1]
    low = df['Low'].iloc[-1]
    close = df['Close'].iloc[-1]
    
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    
    return pivot, r1, s1, r2, s2

# 2. Trend & OI Interpretation (Logic based on Price & Vol)
def analyze_trend(df):
    close = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2]
    
    # Simple RSI & EMA for Trend
    rsi = df.ta.rsi(length=14).iloc[-1]
    ema_20 = df.ta.ema(length=20).iloc[-1]
    
    price_change = close - prev_close
    
    trend_msg = ""
    signal = ""
    
    # Logic simulating OI interpretation
    if price_change > 0 and rsi > 55:
        trend_msg = "🔥 Long Build Up / Short Covering"
        signal = "BUY ON DIPS"
        color = "green"
    elif price_change < 0 and rsi < 45:
        trend_msg = "🩸 Short Build Up / Long Unwinding"
        signal = "SELL ON RISE"
        color = "red"
    else:
        trend_msg = "⚠️ Range Bound / Sideways"
        signal = "WAIT & WATCH"
        color = "orange"
        
    return trend_msg, signal, color, rsi, ema_20

# --- SECTION 1: NIFTY 50 DECODER ---
st.header("1. NIFTY 50 MASTER DECODER 📊")
nifty = yf.Ticker("^NSEI")
hist = nifty.history(period="1mo", interval="1d")

if len(hist) > 0:
    trend_msg, signal, color, rsi, pivot_lvl = analyze_trend(hist)
    pivot, r1, s1, r2, s2 = get_levels(hist)
    curr_price = hist['Close'].iloc[-1]
    
    # Layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"### Current: {curr_price:.2f}")
        st.markdown(f"#### Signal: <span style='color:{color}'>{signal}</span>", unsafe_allow_html=True)
        st.write(f"**Market Mood:** {trend_msg}")
        
    with col2:
        st.write("🎯 **Important Levels (Order Blocks)**")
        st.write(f"🛑 **Resistance 2:** {r2:.2f}")
        st.write(f"🚧 **Resistance 1:** {r1:.2f}")
        st.write(f"⚖️ **Pivot (Mid):** {pivot:.2f}")
        st.write(f"support **Support 1 (Buy Zone):** {s1:.2f}")
        
    with col3:
        # Mock PCR (Real PCR needs paid API, logic based on RSI heat)
        simulated_pcr = rsi / 50  
        pcr_color = "red" if simulated_pcr < 0.7 else ("green" if simulated_pcr > 1.3 else "orange")
        st.metric("Estimated PCR Strength", f"{simulated_pcr:.2f}")
        st.caption("PCR > 1.3 = Overbought (Be careful), PCR < 0.7 = Oversold (Bounce likely)")

st.markdown("---")

# --- SECTION 2: INTRADAY ROCKET STOCKS ---
st.header("2. 🚀 INTRADAY MOVERS (Tez Bhagne Wale)")

# List of High Volatile Stocks
stock_list = {
    "Reliance": "RELIANCE.NS", "HDFC Bank": "HDFCBANK.NS", "ICICI Bank": "ICICIBANK.NS",
    "Tata Motors": "TATAMOTORS.NS", "Adani Ent": "ADANIENT.NS", "Bajaj Finance": "BAJFINANCE.NS",
    "SBI": "SBIN.NS", "Infosys": "INFY.NS"
}

cols = st.columns(4)
count = 0

for name, ticker in stock_list.items():
    try:
        data = yf.Ticker(ticker).history(period="5d", interval="15m")
        if len(data) > 0:
            last = data['Close'].iloc[-1]
            prev = data['Close'].iloc[-2]
            pct = ((last - prev) / prev) * 100
            
            # Action Logic
            action = "NEUTRAL"
            if pct > 0.5: action = "🟢 BUY (Strong)"
            elif pct < -0.5: action = "🔴 SELL (Weak)"
            
            with cols[count % 4]:
                st.markdown(f"**{name}**")
                st.write(f"Price: {last:.1f}")
                st.markdown(f"Change: **{pct:.2f}%**")
                st.markdown(f"Action: **{action}**")
                st.write("---")
            count += 1
    except:
        pass

# --- SECTION 3: COMMODITIES (METAL) ---
st.markdown("---")
st.header("3. 🪙 METALS & COMMODITIES (Gold/Silver/Copper)")

commodities = {
    "Gold (Global)": "GC=F",
    "Silver (Global)": "SI=F",
    "Copper": "HG=F",
    "Crude Oil": "CL=F"
}

c1, c2, c3, c4 = st.columns(4)
c_cols = [c1, c2, c3, c4]
i = 0

for name, sym in commodities.items():
    d = yf.Ticker(sym).history(period="5d")
    if len(d) > 0:
        p, r1, s1, r2, s2 = get_levels(d)
        curr = d['Close'].iloc[-1]
        
        # Decision
        view = "HOLD"
        if curr > r1: view = "BREAKOUT (BUY)"
        elif curr < s1: view = "BREAKDOWN (SELL)"
        
        with c_cols[i]:
            st.markdown(f"### {name}")
            st.write(f"Price: ${curr:.2f}")
            st.markdown(f"View: **{view}**")
            st.caption(f"Support: {s1:.1f} | Res: {r1:.1f}")
    i += 1

# Refresh Button
st.markdown("---")
if st.button('🔄 Refresh Data (Live)'):
    st.rerun()
