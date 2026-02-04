import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import io
import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Quantum Sniper X", page_icon="⚡", layout="wide")

if 'trades' not in st.session_state:
    st.session_state.trades = []

# --- 2. ADVANCED ANALYSIS ENGINE ---
def get_analysis(symbol):
    try:
        # 1. Multi-Timeframe Logic (Trend Detection)
        # Using 15m for calculation, representing intraday
        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicators
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        price = float(last['Close'])
        atr = float(last['ATR'])
        
        # 2. Dynamic TSL Calculation (ATR Based)
        # Buy Side TSL = Price - (2 * ATR)
        # Sell Side TSL = Price + (2 * ATR)
        buy_sl = price - (atr * 2)
        sell_sl = price + (atr * 2)
        
        # 3. Signal Generation
        bias = "NEUTRAL ⚪"
        color = "#888"
        if price > last['EMA200'] and last['RSI'] > 55:
            bias = "STRONG BUY 🚀"
            color = "#00ffaa"
        elif price < last['EMA200'] and last['RSI'] < 45:
            bias = "STRONG SELL 🩸"
            color = "#ff4b4b"
            
        return {
            "price": price, "bias": bias, "color": color, 
            "buy_sl": buy_sl, "sell_sl": sell_sl, "atr": atr,
            "rsi": last['RSI']
        }
    except Exception as e:
        return None

# --- 3. UI DASHBOARD ---
st.title("⚡ Quantum Sniper X (Auto-Risk Management)")
st_autorefresh(interval=60000, key="auto_x")

indices = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"}
cols = st.columns(2)

for i, (name, sym) in enumerate(indices.items()):
    data = get_analysis(sym)
    if data:
        with cols[i]:
            st.markdown(f"""
            <div style="background:#0d1117; padding:20px; border-radius:15px; border-left:8px solid {data['color']}; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <div style="display:flex; justify-content:space-between;">
                    <h3 style="margin:0; color:#e1e1e1;">{name}</h3>
                    <span style="background:{data['color']}22; color:{data['color']}; padding:2px 8px; border-radius:4px; font-size:0.8rem;">{data['bias']}</span>
                </div>
                <h1 style="margin:10px 0; font-size:3rem; font-weight:800;">{data['price']:,.2f}</h1>
                
                <div style="background:#161b22; padding:10px; border-radius:8px; display:flex; justify-content:space-between; margin-bottom:15px;">
                    <div style="text-align:center;">
                        <span style="color:#aaa; font-size:0.8rem;">VOLATILITY (ATR)</span><br>
                        <span style="color:#fff; font-weight:bold;">{data['atr']:.1f} pts</span>
                    </div>
                    <div style="text-align:center;">
                        <span style="color:#aaa; font-size:0.8rem;">RSI MOMENTUM</span><br>
                        <span style="color:#fff; font-weight:bold;">{data['rsi']:.1f}</span>
                    </div>
                </div>
                
                <div style="font-size:0.85rem; color:#888; font-style:italic;">
                    System Suggested TSL: <b style="color:#00ffaa;">{data['buy_sl']:,.1f} (L)</b> | <b style="color:#ff4b4b;">{data['sell_sl']:,.1f} (S)</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # TRADE EXECUTION BUTTONS
            b1, b2 = st.columns(2)
            if b1.button(f"🚀 BUY {name}", use_container_width=True):
                st.session_state.trades.append({
                    "Time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "Asset": name, "Type": "BUY", 
                    "Entry Price": data['price'], 
                    "Auto TSL": round(data['buy_sl'], 2),  # Saving Calculated TSL
                    "Risk (Pts)": round(data['price'] - data['buy_sl'], 2)
                })
                st.toast(f"Buy Order Punched! TSL set at {data['buy_sl']:.1f}", icon="✅")
                
            if b2.button(f"🩸 SELL {name}", use_container_width=True):
                st.session_state.trades.append({
                    "Time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "Asset": name, "Type": "SELL", 
                    "Entry Price": data['price'], 
                    "Auto TSL": round(data['sell_sl'], 2), # Saving Calculated TSL
                    "Risk (Pts)": round(data['sell_sl'] - data['price'], 2)
                })
                st.toast(f"Sell Order Punched! TSL set at {data['sell_sl']:.1f}", icon="✅")

# --- 4. EXCEL REPORTING ---
st.divider()
st.subheader("📊 Automated Trade Journal")

if st.session_state.trades:
    df = pd.DataFrame(st.session_state.trades)
    
    # Styling the dataframe for better readability
    st.dataframe(
        df.style.applymap(lambda v: 'color: #00ffaa;' if v == 'BUY' else ('color: #ff4b4b;' if v == 'SELL' else ''), subset=['Type'])
          .format({"Entry Price": "{:,.2f}", "Auto TSL": "{:,.2f}", "Risk (Pts)": "{:.2f}"}),
        use_container_width=True
    )
    
    # EXCEL DOWNLOAD LOGIC
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sniper_Trades')
        
        # Auto-Formatting Excel Widths
        workbook = writer.book
        worksheet = writer.sheets['Sniper_Trades']
        format1 = workbook.add_format({'num_format': '0.00'})
        worksheet.set_column('D:F', 18, format1) # Formatting Price Columns
        
    st.download_button(
        label="📥 Download Excel Report (with TSL)",
        data=output.getvalue(),
        file_name=f"Sniper_Journal_{datetime.date.today()}.xlsx",
        mime="application/vnd.ms-excel"
    )
else:
    st.info("Waiting for trade execution... Click BUY/SELL above.")

# --- SIDEBAR: RISK METRICS ---
st.sidebar.header("🛡️ Risk Management")
st.sidebar.info("""
**Auto TSL Formula:**
- **Buy:** Current Price - (2 x ATR)
- **Sell:** Current Price + (2 x ATR)

ATR (Average True Range) volatility ko measure karta hai. Agar market tez move karega, TSL door ho jayega taaki SL hunt na ho.
""")
