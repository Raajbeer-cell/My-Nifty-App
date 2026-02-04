import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np

# --- 1. Page Configuration & Custom CSS ---
st.set_page_config(page_title="Pro Fast Scanner", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 20px; }
    .box { padding: 15px; border: 1px solid #333; border-radius: 10px; margin-bottom: 10px; background-color: #161b22; }
    .stProgress > div > div > div > div { background-color: #00ff00; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ REAL-TIME PRO MOMENTUM SCANNER")
st.markdown("### 🚀 Ultra-Fast • Accurate • Sideways Filter")
st.markdown("---")

# --- 2. OPTIMIZED DATA FETCHING (The Speed Secret) ---
@st.cache_data(ttl=60)  # Cache data for 60 seconds to prevent lag
def fetch_batch_data(tickers, period, interval):
    """
    Fetches data for ALL stocks in ONE request (Batch Fetching).
    This is 10x faster than looping.
    """
    # Join tickers with space
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
    return data

# --- 3. ADVANCED LOGIC: ACCURATE TREND DETECTION ---
def analyze_stock(df):
    """
    Calculates technical indicators accurately.
    Returns: Status, Details, Color, Vol_Status
    """
    if df.empty or len(df) < 30:
        return "N/A", "Insufficient Data", "grey", "N/A"

    # --- Technical Indicators ---
    # 1. ADX (Trend Strength)
    adx = df.ta.adx(length=14)
    curr_adx = adx['ADX_14'].iloc[-1] if adx is not None else 0

    # 2. Choppiness Index (Sideways Detector)
    df['CHOP'] = df.ta.chop(length=14)
    curr_chop = df['CHOP'].iloc[-1]

    # 3. Moving Averages
    sma_50 = df.ta.sma(length=50).iloc[-1]
    ema_20 = df.ta.ema(length=20).iloc[-1]
    close = df['Close'].iloc[-1]
    
    # 4. Volume Analysis
    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
    curr_vol = df['Volume'].iloc[-1]
    is_high_vol = curr_vol > (avg_vol * 1.5)
    vol_str = "🔥 High Vol" if is_high_vol else "Normal Vol"

    # --- DECISION LOGIC (Strict) ---
    status = ""
    color = ""

    # Rule 1: Kill Sideways Markets First
    if curr_adx < 20:
        status = "💤 SIDEWAYS (Weak ADX)"
        color = "grey"
    elif curr_chop > 60:
        status = "💤 CHOPPY (Consolidation)"
        color = "grey"
    
    # Rule 2: Trend Confirmation
    else:
        if close > ema_20 and close > sma_50:
            if is_high_vol:
                status = "🚀 STRONG UPTREND (Breakout)"
                color = "#00ff00" # Bright Green
            else:
                status = "🟢 UPTREND (Steady)"
                color = "green"
        elif close < ema_20 and close < sma_50:
            if is_high_vol:
                status = "🩸 STRONG DOWNTREND (Breakdown)"
                color = "#ff0000" # Bright Red
            else:
                status = "🔴 DOWNTREND (Weak)"
                color = "red"
        else:
            status = "⚖️ CORRECTION / INDECISION"
            color = "orange"

    details = f"ADX: {curr_adx:.1f} | Chop: {curr_chop:.1f}"
    return status, details, color, vol_str

# --- 4. MAIN DASHBOARD UI ---

# Sidebar
timeframe = st.sidebar.selectbox("⏱️ Timeframe", ["15m", "1h", "1d"], index=0)
period_map = {"15m": "5d", "1h": "1mo", "1d": "1y"}

# Define Tickers
nifty_ticker = ["^NSEI"]
metal_stocks = [
    "TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", 
    "VEDL.NS", "NMDC.NS", "JINDALSTEL.NS", 
    "SAIL.NS", "NATIONALUM.NS"
]

all_tickers = nifty_ticker + metal_stocks

# --- FAST DATA LOADING ---
with st.spinner('⚡ Scanning Market Data...'):
    try:
        raw_data = fetch_batch_data(all_tickers, period=period_map[timeframe], interval=timeframe)
    except Exception as e:
        st.error("Data Fetch Error. Please refresh.")
        st.stop()

# --- SECTION A: NIFTY 50 DECODER ---
st.header("1️⃣ NIFTY 50 SENTIMENT")

# Extract Nifty Data safely
try:
    nifty_df = raw_data["^NSEI"].dropna()
    n_status, n_det, n_col, n_vol = analyze_stock(nifty_df)
    n_price = nifty_df['Close'].iloc[-1]

    st.markdown(f"""
    <div class="box" style="border-left: 8px solid {n_col};">
        <h2 style='margin:0; color:{n_col}'>{n_status}</h2>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <span style='font-size:28px; font-weight:bold;'>{n_price:.2f}</span>
            <span style='font-size:16px; opacity:0.8;'>{n_det}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
except KeyError:
    st.error("Nifty Data Not Available")

st.markdown("---")

# --- SECTION B: METAL SECTOR MATRIX ---
st.header("2️⃣ METAL STOCKS HEATMAP")
st.write("Wait for **'STRONG'** signals with **'High Vol'** for best accuracy.")

results = []

# Process Stocks (Using Local Data - Super Fast)
for ticker in metal_stocks:
    try:
        # Check if we have data for this ticker in the batch
        if ticker in raw_data.columns.levels[0]: 
            df = raw_data[ticker].dropna()
        else:
            # Fallback for flat structure if single ticker (rare)
            df = raw_data 
            
        if not df.empty:
            status, details, color, vol = analyze_stock(df)
            close = df['Close'].iloc[-1]
            opn = df['Open'].iloc[-1]
            change = ((close - opn) / opn) * 100
            
            results.append({
                "Ticker": ticker.replace(".NS", ""),
                "Price": close,
                "Change": change,
                "Status": status,
                "Color": color,
                "Vol": vol
            })
    except Exception as e:
        continue

# Display Logic (Grid System)
cols = st.columns(4) # 4 items per row for compact view

for i, res in enumerate(results):
    with cols[i % 4]:
        c_code = res['Color']
        border_style = "dashed" if "SIDEWAYS" in res['Status'] else "solid"
        
        st.markdown(f"""
        <div class="box" style="border-top: 3px {border_style} {c_code}; text-align:center;">
            <b>{res['Ticker']}</b><br>
            <span style="font-size:22px;">{res['Price']:.2f}</span><br>
            <span style="color:{c_code}; font-weight:bold;">{res['Change']:.2f}%</span><br>
            <small style="color:#bbb;">{res['Status']}</small><br>
            <small style="color:#ffd700; font-weight:bold;">{res['Vol']}</small>
        </div>
        """, unsafe_allow_html=True)

# --- AUTO REFRESH BUTTON ---
if st.button('🔄 FORCE REFRESH (Live)'):
    st.cache_data.clear()
    st.rerun()
