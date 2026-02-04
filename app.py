import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- 1. Page Configuration (App ko Fancy Look dena) ---
st.set_page_config(page_title="Bull vs Bear: Pro Trader", page_icon="🐂", layout="wide")

# Custom CSS for a Dark Gold/Black Trading Theme
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stHeader { color: #f63366; }
    div[data-testid="stMetricValue"] { color: #00ff00; font-size: 24px; }
    .status-box { padding: 20px; border-radius: 15px; border: 2px solid #333; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🐂 BULL vs BEAR 🐻: Pro Dashboard")
st.markdown("---")

# --- 2. Levels Calculator Function ---
def calc_levels(df):
    h, l, c = df['High'].iloc[-1], df['Low'].iloc[-1], df['Close'].iloc[-1]
    p = (h + l + c) / 3
    r1, s1 = (2 * p) - l, (2 * p) - h
    r2, s2 = p + (h - l), p - (h - l)
    return {"P": p, "R1": r1, "S1": s1, "R2": r2, "S2": s2}

# --- 3. NIFTY DECODER SECTION ---
st.header("📊 NIFTY 50 - Market Sentiment")
nifty_data = yf.Ticker("^NSEI").history(period="1mo", interval="1d")

if not nifty_data.empty:
    lvl = calc_levels(nifty_data)
    curr = nifty_data['Close'].iloc[-1]
    rsi = nifty_data.ta.rsi(length=14).iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if curr > lvl['P']:
            st.success(f"### 🐂 BULLISH MOOD\n**Price:** {curr:.2f}")
            st.write("**Analysis:** Short Covering / Long Buildup")
        else:
            st.error(f"### 🐻 BEARISH MOOD\n**Price:** {curr:.2f}")
            st.write("**Analysis:** Long Unwinding / Short Buildup")
            
    with col2:
        st.info("🎯 **Target Levels (Order Blocks)**")
        st.write(f"🛑 **Strong Resistance (R2):** {lvl['R2']:.2f}")
        st.write(f"🚧 **Target 1 (R1):** {lvl['R1']:.2f}")
        st.write(f"🟢 **Support Zone (S1):** {lvl['S1']:.2f}")
        st.write(f"🩸 **Danger Zone (S2):** {lvl['S2']:.2f}")

    with col3:
        st.metric("PCR Proxy (Sentiment)", f"{rsi/50:.2f}")
        if rsi > 70: st.warning("⚠️ Market is Overbought")
        elif rsi < 30: st.success("✅ Market is Oversold")

st.markdown("---")

# --- 4. METAL & COMMODITY LEVELS SECTION ---
st.header("🪙 METAL TRADING LEVELS (Intraday)")
metals = {
    "GOLD 🟡": "GC=F",
    "SILVER ⚪": "SI=F",
    "COPPER 🟠": "HG=F"
}

m_cols = st.columns(3)
for i, (name, sym) in enumerate(metals.items()):
    m_data = yf.Ticker(sym).history(period="5d")
    if not m_data.empty:
        m_lvl = calc_levels(m_data)
        m_curr = m_data['Close'].iloc[-1]
        
        with m_cols[i]:
            st.subheader(name)
            st.metric("Live Price", f"${m_curr:.2f}")
            
            # Logic for Buy/Sell
            if m_curr > m_lvl['R1']:
                st.write("🔥 **Status:** Super Bullish (Buy)")
            elif m_curr < m_lvl['S1']:
                st.write("🧊 **Status:** Bearish (Sell)")
            else:
                st.write("⚖️ **Status:** Range Bound")
            
            # Levels Table
            st.table(pd.DataFrame({
                "Level Type": ["Resistance 1", "Pivot", "Support 1"],
                "Value": [f"{m_lvl['R1']:.2f}", f"{m_lvl['P']:.2f}", f"{m_lvl['S1']:.2f}"]
            }))

st.markdown("---")

# --- 5. ROCKET STOCKS SECTION ---
st.header("🚀 ROCKET STOCKS (Intraday Momentum)")
stocks = ["RELIANCE.NS", "TATAMOTORS.NS", "ADANIENT.NS", "HDFCBANK.NS"]
s_cols = st.columns(4)

for i, ticker in enumerate(stocks):
    s_data = yf.Ticker(ticker).history(period="2d", interval="15m")
    if not s_data.empty:
        s_curr = s_data['Close'].iloc[-1]
        chg = ((s_curr - s_data['Open'].iloc[-1]) / s_data['Open'].iloc[-1]) * 100
        with s_cols[i]:
            st.write(f"**{ticker.split('.')[0]}**")
            st.write(f"Price: {s_curr:.1f}")
            if chg > 0.5: st.write("🟢 **STRONG BUY**")
            elif chg < -0.5: st.write("🔴 **STRONG SELL**")
            else: st.write("⚪ NEUTRAL")

if st.button('🔄 Update Live Data'):
    st.rerun()
