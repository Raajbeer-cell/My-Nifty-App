import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP & PAGE CONFIG ---
st.set_page_config(page_title="Nifty Sniper Pro", page_icon="📈", layout="wide")

# Custom CSS for Dark Theme and Cards
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

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=30)
def get_nifty_data(symbol):
    try:
        # Increase period to ensure 200 EMA can be calculated
        df = yf.download(symbol, period="60d", interval="15m", progress=False)
        
        if df.empty or len(df) < 200:
            return None

        # FIX: Handle yfinance MultiIndex columns (The most common cause of ValueErrors recently)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Indicators
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # Support & Resistance (Pivot Logic)
        last_h = df['High'].iloc[-20:].max()
        last_l = df['Low'].iloc[-20:].min()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Logic: OI/Volume Build Up
        price_chg = last['Close'] - prev['Close']
        vol_chg = last['Volume'] - prev['Volume']
        
        buildup = "NEUTRAL"
        if price_chg > 0 and vol_chg > 0: buildup = "LONG BUILDUP 🟢"
        elif price_chg < 0 and vol_chg > 0: buildup = "SHORT BUILDUP 🔴"
        elif price_chg > 0 and vol_chg < 0: buildup = "SHORT COVERING 🔵"
        elif price_chg < 0 and vol_chg < 0: buildup = "LONG UNWINDING 🟠"
        
        # Target/SL Logic
        action = "WAIT"
        color = "#888888"
        if last['Close'] > last['EMA200'] and last['RSI'] > 55:
            action = "BUY / CALL"
            color = "#10b981"
        elif last['Close'] < last['EMA200'] and last['RSI'] < 45:
            action = "SELL / PUT"
            color = "#ef4444"
            
        atr_val = last['ATR'] if not pd.isna(last['ATR']) else 10
        
        return {
            "price": float(last['Close']),
            "action": action,
            "color": color,
            "buildup": buildup,
            "support": float(last_l),
            "resist": float(last_h),
            "sl": float(last['Close'] - (atr_val * 1.5)) if "BUY" in action else float(last['Close'] + (atr_val * 1.5)),
            "target": float(last['Close'] + (atr_val * 3)) if "BUY" in action else float(last['Close'] - (atr_val * 3))
        }
    except Exception as e:
        st.error(f"Error processing {symbol}: {e}")
        return None

# --- 3. DASHBOARD UI ---
st.title("🇮🇳 Nifty & BankNifty Sniper Pro")
st_autorefresh(interval=30000, key="datarefresh") 

col1, col2 = st.columns(2)

indices = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK"
}

for i, (name, ticker) in enumerate(indices.items()):
    data = get_nifty_data(ticker)
    
    with (col1 if i % 2 == 0 else col2):
        if data:
            # Combined all HTML into one block to prevent rendering errors
            card_html = f"""
            <div class="metric-card" style="border-left: 5px solid {data['color']};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h2 style="margin:0;">{name}</h2>
                    <span style="background:#374151; padding:4px 10px; border-radius:5px; font-size:0.75rem;">{data['buildup']}</span>
                </div>
                <h1 style="margin:10px 0; font-size:2.8rem;">{data['price']:,.2f}</h1>
                <p style="color:{data['color']}; font-size:1.3rem; font-weight:bold; margin-bottom:15px;">Signal: {data['action']}</p>
                
                <hr style="border:0; border-top:1px solid #374151; margin:15px 0;">
                
                <div style="display:flex; justify-content:space-between; text-align:center;">
                    <div>
                        <small style="color:#9ca3af; display:block;">Support</small>
                        <b style="font-size:1.1rem;">{data['support']:,.0f}</b>
                    </div>
                    <div>
                        <small style="color:#9ca3af; display:block;">Resistance</small>
                        <b style="font-size:1.1rem;">{data['resist']:,.0f}</b>
                    </div>
                </div>
                
                <div style="margin-top:20px; background:#111827; padding:12px; border-radius:8px; display:flex; justify-content:space-between;">
                    <span class="bullish">🎯 TGT: {data['target']:,.0f}</span>
                    <span class="bearish">🛑 SL: {data['sl']:,.0f}</span>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.warning(f"⏳ Data for {name} currently unavailable. The market might be closed or the ticker is incorrect.")

st.info("ℹ️ **Status:** System Active. Data updates automatically every 30 seconds.")
