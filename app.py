import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(page_title="Nifty Sniper Pro", page_icon="📈", layout="wide")

# Custom CSS for Dark Theme
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e1e1e1; }
    .metric-card {
        background: #1f2937; padding: 20px; border-radius: 10px;
        border: 1px solid #374151; margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .bullish { color: #10b981; font-weight: bold; }
    .bearish { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE (BUG FIXED) ---
@st.cache_data(ttl=60)
def get_nifty_data(symbol):
    try:
        # FIX 1: Period increased to '1mo' for EMA 200 calculation
        df = yf.download(symbol, period="1mo", interval="15m", progress=False)
        
        if df.empty:
            return None

        # FIX 2: Handle MultiIndex Columns (Crucial Fix for yfinance update)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Ensure we have enough data
        if len(df) < 200:
            return None

        # Indicators
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # Support & Resistance (Pivot Logic)
        last_h = df['High'].iloc[-20:].max()
        last_l = df['Low'].iloc[-20:].min()
        
        last = df.iloc[-1]
        
        # Logic: OI/Volume Build Up (Simulated)
        price_chg = (df['Close'].iloc[-1] - df['Close'].iloc[-2])
        vol_chg = (df['Volume'].iloc[-1] - df['Volume'].iloc[-2])
        
        buildup = "NEUTRAL"
        if price_chg > 0 and vol_chg > 0: buildup = "LONG BUILDUP 🟢"
        elif price_chg < 0 and vol_chg > 0: buildup = "SHORT BUILDUP 🔴"
        elif price_chg > 0 and vol_chg < 0: buildup = "SHORT COVERING 🔵"
        elif price_chg < 0 and vol_chg < 0: buildup = "LONG UNWINDING 🟠"
        
        # Target/SL Logic
        action = "WAIT"
        color = "#888"
        if last['Close'] > last['EMA200'] and last['RSI'] > 55:
            action = "BUY / CALL"
            color = "#10b981"
        elif last['Close'] < last['EMA200'] and last['RSI'] < 45:
            action = "SELL / PUT"
            color = "#ef4444"
            
        atr_val = last['ATR'] if not pd.isna(last['ATR']) else 0
        
        return {
            "price": last['Close'],
            "action": action,
            "color": color,
            "buildup": buildup,
            "support": last_l,
            "resist": last_h,
            "sl": last['Close'] - (atr_val * 2) if "BUY" in action else last['Close'] + (atr_val * 2),
            "target": last['Close'] + (atr_val * 3) if "BUY" in action else last['Close'] - (atr_val * 3)
        }
        
    except Exception as e:
        # FIX 3: Catch generic errors to prevent app crash
        print(f"Error fetching {symbol}: {e}")
        return None

# --- 3. DASHBOARD UI ---
st.title("🇮🇳 Nifty & BankNifty Sniper Pro")
st_autorefresh(interval=30000, key="datarefresh") # Auto refresh every 30 secs

col1, col2 = st.columns(2)

# List of Indices
indices = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK"
}

for i, (name, ticker) in enumerate(indices.items()):
    data = get_nifty_data(ticker)
    
    # Choose column (Left or Right)
    with (col1 if i % 2 == 0 else col2):
        if data:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid {data['color']};">
                <div style="display:flex; justify-content:space-between;">
                    <h3>{name}</h3>
                    <span style="background:#374151; padding:2px 8px; border-radius:5px; font-size:0.8rem;">{data['buildup']}</span>
                </div>
                <h1 style="margin:0; font-size:2.5rem;">{data['price']:,.2f}</h1>
                <p style="color:{data['color']}; font-size:1.2rem; font-weight:bold;">Signal: {data['action']}</p>
                
                <hr style="border-color:#374151;">
                
                <div style="display:flex; justify-content:space-between; text-align:center;">
                    <div>
                        <small style="color:#9ca3af;">Support</small><br>
                        <b>{data['support']:,.0f}</b>
                    </div>
                    <div>
                        <small style="color:#9ca3af;">Resistance</small><br>
                        <b>{data['resist']:,.0f}</b>
                    </div>
                </div>
                
                <div style="margin-top:15px; background:#111827; padding:10px; border-radius:8px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span class="bullish">🎯 TGT: {data['target']:,.0f}</span>
                        <span class="bearish">🛑 SL: {data['sl']:,.0f}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"⏳ Fetching data for {name}... (Wait or Check Internet)")

st.info("ℹ️ **Status:** System Active. Data updates automatically every 30 seconds.")
