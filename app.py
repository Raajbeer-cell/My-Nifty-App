"""
ULTIMATE TRADER PRO - Premium Trading Dashboard
===============================================
Features:
- Multi-Asset Real-Time Scanner (Indices, Crypto, Commodities, Forex)
- Advanced Technical Analysis (Supertrend, EMA, RSI, MFI, ADX, ATR)
- AI-Powered News Sentiment Analysis
- Browser Notifications for Strong Signals
- Auto-Refresh Every 60 Seconds
- Professional Dark Theme UI
- Order Block Detection
- Trend Strength Meter
- Risk Management (Dynamic SL/TP)
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import streamlit.components.v1 as components
from datetime import datetime

# ============================================================================
# 1. INITIAL SETUP & CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Ultimate Trader Pro", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# NLTK Setup for Sentiment Analysis
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

sia = SentimentIntensityAnalyzer()

# ============================================================================
# 2. CUSTOM CSS STYLING - PROFESSIONAL DARK THEME
# ============================================================================

st.markdown("""
<style>
    /* Main App Styling */
    .stApp { 
        background: linear-gradient(135deg, #0a0e14 0%, #1a1f2e 100%);
        color: #e1e1e1; 
    }
    
    /* Trading Card Design */
    .trade-card { 
        background: linear-gradient(145deg, #161b22, #0d1117);
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #30363d; 
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .trade-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.8);
    }
    
    /* Signal Colors */
    .signal-buy { 
        color: #00ff88; 
        font-weight: bold; 
        text-shadow: 0 0 10px #00ff88;
    }
    
    .signal-sell { 
        color: #ff4b4b; 
        font-weight: bold; 
        text-shadow: 0 0 10px #ff4b4b;
    }
    
    .signal-wait { 
        color: #888; 
        font-weight: bold;
    }
    
    /* Metrics */
    .metric-val { 
        font-size: 28px; 
        font-weight: 900; 
        color: #ffffff;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    /* Status Badges */
    .status-badge { 
        padding: 5px 15px; 
        border-radius: 20px; 
        font-size: 11px; 
        font-weight: bold;
        display: inline-block;
    }
    
    /* Progress Bars */
    .progress-container {
        width: 100%;
        background-color: #1a1a1a;
        border-radius: 10px;
        height: 10px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }
    
    /* News Card */
    .news-card {
        background: #161b22;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #58a6ff;
        margin-bottom: 12px;
        transition: border-color 0.2s;
    }
    
    .news-card:hover {
        border-left-color: #79c0ff;
    }
    
    /* Special Silver Highlight */
    .silver-special {
        border: 2px solid #c0c0c0;
        background: linear-gradient(145deg, #1a1f2e, #0f1419);
        box-shadow: 0 0 20px rgba(192, 192, 192, 0.3);
    }
    
    /* Sidebar Styling */
    .css-1d391kg { background-color: #0d1117; }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 3. BROWSER NOTIFICATION SYSTEM
# ============================================================================

def trigger_browser_notification(title, message):
    """Send browser push notification for strong signals"""
    notification_js = f"""
    <script>
    function notifyMe() {{
        if (!("Notification" in window)) {{
            console.log("Browser doesn't support notifications");
        }} else if (Notification.permission === "granted") {{
            new Notification("{title}", {{ 
                body: "{message}", 
                icon: "https://cdn-icons-png.flaticon.com/512/3159/3159310.png",
                badge: "https://cdn-icons-png.flaticon.com/512/3159/3159310.png"
            }});
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

# Request notification permission on load
components.html("""
<script>
if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
}
</script>
""", height=0)

# ============================================================================
# 4. ASSET CONFIGURATION
# ============================================================================

ASSETS = {
    "🇮🇳 INDIAN INDICES": {
        "NIFTY 50": "^NSEI", 
        "BANK NIFTY": "^NSEBANK", 
        "FIN NIFTY": "NIFTY_FIN_SERVICE.NS"
    },
    "🪙 CRYPTOCURRENCIES": {
        "BITCOIN": "BTC-USD", 
        "ETHEREUM": "ETH-USD", 
        "SOLANA": "SOL-USD",
        "XRP": "XRP-USD"
    },
    "💎 COMMODITIES": {
        "SILVER (MCX)": "SI=F", 
        "GOLD": "GC=F", 
        "CRUDE OIL": "CL=F",
        "COPPER": "HG=F"
    },
    "💱 FOREX": {
        "USD/INR": "USDINR=X", 
        "EUR/USD": "EURUSD=X", 
        "GBP/USD": "GBPUSD=X"
    },
    "🇺🇸 US STOCKS": {
        "NVIDIA": "NVDA", 
        "TESLA": "TSLA", 
        "APPLE": "AAPL"
    }
}

# Flatten all tickers for batch download
ALL_TICKERS = []
for category in ASSETS.values():
    ALL_TICKERS.extend(category.values())

# ============================================================================
# 5. ADVANCED DATA FETCHING & CACHING
# ============================================================================

@st.cache_data(ttl=60)
def fetch_market_data(tickers, period, interval):
    """Fetch data for multiple tickers efficiently"""
    try:
        tickers_str = " ".join(tickers)
        data = yf.download(
            tickers_str, 
            period=period, 
            interval=interval, 
            group_by='ticker', 
            threads=True, 
            progress=False
        )
        return data
    except Exception as e:
        st.error(f"Data fetch error: {str(e)}")
        return None

# ============================================================================
# 6. ADVANCED SIGNAL GENERATION ENGINE
# ============================================================================

def calculate_advanced_signal(df, ticker_name="", ticker_symbol=""):
    """
    Advanced signal generation with multiple confirmations:
    - Supertrend for trend direction
    - EMA 200 for institutional bias
    - MFI for money flow (better than RSI)
    - ADX for trend strength
    - ATR for dynamic SL/TP
    - Order blocks for support/resistance
    """
    
    if df is None or df.empty or len(df) < 200:
        return None
    
    try:
        # Calculate Technical Indicators
        df['EMA_200'] = ta.ema(df['Close'], length=200)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        
        # Supertrend (Trend Direction)
        supertrend = df.ta.supertrend(length=10, multiplier=3)
        trend_col = [col for col in supertrend.columns if 'SUPERTd' in col][0]
        df['Trend'] = supertrend[trend_col]
        
        # MFI (Money Flow Index - Volume-weighted RSI)
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        # RSI (Relative Strength Index)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # ADX (Trend Strength)
        adx_data = df.ta.adx(length=14)
        if adx_data is not None and not adx_data.empty:
            adx_col = [col for col in adx_data.columns if 'ADX' in col][0]
            df['ADX'] = adx_data[adx_col]
        else:
            df['ADX'] = 0
        
        # ATR (Average True Range for volatility)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # VWAP (Volume Weighted Average Price)
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        
        # Get latest values
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        close = current['Close']
        ema200 = current['EMA_200']
        ema50 = current['EMA_50']
        ema20 = current['EMA_20']
        trend = current['Trend']
        mfi = current['MFI']
        rsi = current['RSI']
        adx = current['ADX']
        atr = current['ATR']
        vwap = current['VWAP']
        
        # Order Blocks (Support/Resistance)
        recent_highs = df['High'].tail(50)
        recent_lows = df['Low'].tail(50)
        resistance = recent_highs.max()
        support = recent_lows.min()
        
        # Calculate price change
        price_change = ((close - prev['Close']) / prev['Close']) * 100
        
        # ===== SIGNAL LOGIC =====
        action = "SCANNING..."
        signal_strength = 0
        color = "#888888"
        sl = 0
        tp = 0
        risk_reward = 0
        
        # Special logic for SILVER (High volatility commodity)
        is_silver = "SILVER" in ticker_name.upper() or "SI=F" in ticker_symbol
        
        if is_silver:
            atr_multiplier_sl = 2.5
            atr_multiplier_tp = 5.0
        else:
            atr_multiplier_sl = 2.0
            atr_multiplier_tp = 4.0
        
        # === BUY SIGNAL CONDITIONS ===
        # 1. Price above EMA 200 (Institutional support)
        # 2. Supertrend is bullish (Trend = 1)
        # 3. MFI not overbought (<80)
        # 4. EMA crossover confirmation
        
        if (close > ema200 and 
            trend == 1 and 
            mfi < 80):
            
            # Calculate strength score (0-100)
            strength_factors = []
            
            # Factor 1: EMA alignment
            if ema20 > ema50 > ema200:
                strength_factors.append(25)
            
            # Factor 2: MFI positioning
            if 50 < mfi < 70:
                strength_factors.append(20)
            elif 40 < mfi < 50:
                strength_factors.append(10)
            
            # Factor 3: ADX strength
            if adx > 25:
                strength_factors.append(20)
            if adx > 40:
                strength_factors.append(10)
            
            # Factor 4: Price above VWAP
            if close > vwap:
                strength_factors.append(15)
            
            # Factor 5: Recent momentum
            if price_change > 0:
                strength_factors.append(10)
            
            signal_strength = sum(strength_factors)
            
            if signal_strength >= 70:
                action = "🚀 STRONG BUY"
                color = "#00ff88"
            elif signal_strength >= 50:
                action = "↗️ BUY"
                color = "#90ee90"
            else:
                action = "⚠️ WEAK BUY"
                color = "#ffcc00"
            
            # Calculate Stop Loss & Take Profit
            sl = close - (atr * atr_multiplier_sl)
            tp = close + (atr * atr_multiplier_tp)
            risk_reward = (tp - close) / (close - sl)
        
        # === SELL SIGNAL CONDITIONS ===
        elif (close < ema200 and 
              trend == -1 and 
              mfi > 20):
            
            # Calculate strength score
            strength_factors = []
            
            if ema20 < ema50 < ema200:
                strength_factors.append(25)
            
            if 30 < mfi < 50:
                strength_factors.append(20)
            elif 50 < mfi < 60:
                strength_factors.append(10)
            
            if adx > 25:
                strength_factors.append(20)
            if adx > 40:
                strength_factors.append(10)
            
            if close < vwap:
                strength_factors.append(15)
            
            if price_change < 0:
                strength_factors.append(10)
            
            signal_strength = sum(strength_factors)
            
            if signal_strength >= 70:
                action = "🩸 STRONG SELL"
                color = "#ff4b4b"
            elif signal_strength >= 50:
                action = "↘️ SELL"
                color = "#ff7f7f"
            else:
                action = "⚠️ WEAK SELL"
                color = "#ffcc00"
            
            sl = close + (atr * atr_multiplier_sl)
            tp = close - (atr * atr_multiplier_tp)
            risk_reward = (close - tp) / (sl - close)
        
        # Trend strength description
        trend_desc = "Weak"
        if adx > 25:
            trend_desc = "Strong"
        if adx > 40:
            trend_desc = "Very Strong"
        if adx > 60:
            trend_desc = "Explosive 🔥"
        
        # Exit strategy message
        exit_msg = "Hold Position"
        if "BUY" in action and mfi > 80:
            exit_msg = "🚨 Consider Partial Profit Booking (Overbought)"
        elif "SELL" in action and mfi < 20:
            exit_msg = "🚨 Consider Partial Profit Booking (Oversold)"
        
        return {
            "action": action,
            "price": close,
            "price_change": price_change,
            "signal_strength": int(signal_strength),
            "color": color,
            "sl": sl,
            "tp": tp,
            "risk_reward": risk_reward,
            "support": support,
            "resistance": resistance,
            "mfi": mfi,
            "rsi": rsi,
            "adx": adx,
            "trend_desc": trend_desc,
            "exit_msg": exit_msg,
            "volume": current['Volume'],
            "vwap": vwap
        }
        
    except Exception as e:
        return None

# ============================================================================
# 7. NEWS & SENTIMENT ANALYSIS
# ============================================================================

RSS_FEEDS = {
    "Global Finance": "https://finance.yahoo.com/news/rssindex",
    "Crypto News": "https://cointelegraph.com/rss",
    "India Economy": "https://www.moneycontrol.com/rss/economy.xml"
}

def analyze_sentiment(text):
    """Analyze sentiment using VADER"""
    score = sia.polarity_scores(text)['compound']
    if score > 0.05:
        return "BULLISH 🟢", "badge-bull", score
    elif score < -0.05:
        return "BEARISH 🔴", "badge-bear", score
    return "NEUTRAL ⚪", "badge-neutral", score

def get_market_impact(text):
    """Determine which markets are impacted by the news"""
    text_lower = text.lower()
    impacts = []
    
    if any(word in text_lower for word in ['inflation', 'rate', 'fed', 'rbi']):
        impacts.append("📊 Indices & Banking")
    if any(word in text_lower for word in ['oil', 'crude', 'energy']):
        impacts.append("⛽ Energy Sector")
    if any(word in text_lower for word in ['bitcoin', 'crypto', 'ethereum']):
        impacts.append("🪙 Crypto Markets")
    if any(word in text_lower for word in ['gold', 'silver', 'metal']):
        impacts.append("💎 Precious Metals")
    if any(word in text_lower for word in ['dollar', 'forex', 'currency']):
        impacts.append("💱 Forex Markets")
    
    return " | ".join(impacts) if impacts else "🌐 Global Markets"

# ============================================================================
# 8. SIDEBAR CONTROLS
# ============================================================================

st.sidebar.title("🎯 ULTIMATE TRADER PRO")
st.sidebar.markdown("---")

st.sidebar.info("**Status:** 🟢 Live | Auto-refresh: 60s")
st.sidebar.markdown(f"**Last Update:** {datetime.now().strftime('%H:%M:%S')}")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Settings")

# Timeframe selection
timeframe = st.sidebar.selectbox(
    "📊 Select Timeframe:",
    ["15m", "1h", "4h", "1d"],
    index=1,
    help="Choose your trading timeframe"
)

# Period mapping
period_map = {
    "15m": "5d",
    "1h": "1mo",
    "4h": "2mo",
    "1d": "1y"
}

# Notification toggle
enable_notifications = st.sidebar.checkbox(
    "🔔 Enable Browser Notifications",
    value=True,
    help="Get alerts for strong signals"
)

# Refresh button
if st.sidebar.button("🔄 Force Refresh", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Features:**
- ✅ Multi-Asset Scanning
- ✅ Advanced Technical Analysis
- ✅ AI Sentiment Analysis
- ✅ Real-Time Signals
- ✅ Risk Management
- ✅ Order Block Detection
""")

# ============================================================================
# 9. MAIN APPLICATION LAYOUT
# ============================================================================

st.title("🎯 ULTIMATE TRADER PRO")
st.markdown("*Professional-Grade Multi-Asset Trading Dashboard*")

# Create tabs
tab1, tab2, tab3 = st.tabs([
    "📊 LIVE MARKET SCANNER", 
    "📰 NEWS & SENTIMENT", 
    "🎓 TRADING INSIGHTS"
])

# ============================================================================
# TAB 1: LIVE MARKET SCANNER
# ============================================================================

with tab1:
    st.header("🔍 Live Market Analysis")
    
    # Fetch data
    with st.spinner(f"🔄 Scanning {len(ALL_TICKERS)} assets on {timeframe} timeframe..."):
        market_data = fetch_market_data(
            ALL_TICKERS, 
            period=period_map[timeframe], 
            interval=timeframe
        )
    
    if market_data is not None:
        # Process each category
        for category_name, tickers in ASSETS.items():
            st.subheader(category_name)
            
            # Create columns for cards
            cols = st.columns(3)
            col_idx = 0
            
            for asset_name, symbol in tickers.items():
                try:
                    # Extract data for this symbol
                    if len(ALL_TICKERS) > 1:
                        asset_df = market_data[symbol].copy().dropna()
                    else:
                        asset_df = market_data.copy().dropna()
                    
                    # Generate signal
                    signal = calculate_advanced_signal(asset_df, asset_name, symbol)
                    
                    if signal:
                        # Trigger notification for strong signals
                        if enable_notifications and "STRONG" in signal['action']:
                            trigger_browser_notification(
                                f"🎯 {asset_name}",
                                f"{signal['action']} at {signal['price']:.2f}"
                            )
                        
                        # Determine if this is silver (special styling)
                        card_class = "trade-card silver-special" if "SILVER" in asset_name.upper() else "trade-card"
                        
                        # Currency symbol
                        if "🇮🇳" in category_name:
                            currency = "₹"
                        elif "🪙" in category_name or "🇺🇸" in category_name:
                            currency = "$"
                        else:
                            currency = ""
                        
                        # Create trading card
                        with cols[col_idx % 3]:
                            st.markdown(f"""
                            <div class="{card_class}">
                                <!-- Header -->
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                                    <span style="font-size:16px; font-weight:bold; color:#fff;">{asset_name}</span>
                                    <span class="status-badge" style="background:{signal['color']}22; color:{signal['color']}; border:1px solid {signal['color']};">
                                        Score: {signal['signal_strength']}%
                                    </span>
                                </div>
                                
                                <!-- Price -->
                                <div class="metric-val" style="margin:12px 0;">
                                    {currency}{signal['price']:,.2f}
                                </div>
                                
                                <!-- Price Change -->
                                <div style="color:{'#00ff88' if signal['price_change'] >= 0 else '#ff4b4b'}; font-size:14px; margin-bottom:10px;">
                                    {'▲' if signal['price_change'] >= 0 else '▼'} {abs(signal['price_change']):.2f}%
                                </div>
                                
                                <!-- Signal -->
                                <div style="color:{signal['color']}; font-weight:bold; font-size:16px; margin-bottom:12px; text-align:center; padding:8px; background:{signal['color']}11; border-radius:8px;">
                                    {signal['action']}
                                </div>
                                
                                <!-- Strength Progress Bar -->
                                <div style="margin-bottom:12px;">
                                    <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
                                        <span>Signal Strength</span>
                                        <span>{signal['signal_strength']}%</span>
                                    </div>
                                    <div class="progress-container">
                                        <div class="progress-bar" style="width:{signal['signal_strength']}%; background:{signal['color']};"></div>
                                    </div>
                                </div>
                                
                                <!-- Targets & Levels -->
                                <div style="background:#000; padding:12px; border-radius:8px; font-size:13px; margin-bottom:10px;">
                                    <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                                        <span>🎯 Target:</span>
                                        <span style="color:#00ff88; font-weight:bold;">{currency}{signal['tp']:,.2f}</span>
                                    </div>
                                    <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                                        <span>🛑 Stop Loss:</span>
                                        <span style="color:#ff4b4b; font-weight:bold;">{currency}{signal['sl']:,.2f}</span>
                                    </div>
                                    <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                                        <span>⚖️ Risk:Reward:</span>
                                        <span style="color:#ffcc00; font-weight:bold;">1:{signal['risk_reward']:.2f}</span>
                                    </div>
                                </div>
                                
                                <!-- Technical Metrics -->
                                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:11px; margin-bottom:10px;">
                                    <div style="background:#0a0a0a; padding:6px; border-radius:5px; text-align:center;">
                                        <div style="color:#888;">MFI</div>
                                        <div style="color:#fff; font-weight:bold;">{signal['mfi']:.0f}</div>
                                    </div>
                                    <div style="background:#0a0a0a; padding:6px; border-radius:5px; text-align:center;">
                                        <div style="color:#888;">RSI</div>
                                        <div style="color:#fff; font-weight:bold;">{signal['rsi']:.0f}</div>
                                    </div>
                                    <div style="background:#0a0a0a; padding:6px; border-radius:5px; text-align:center;">
                                        <div style="color:#888;">ADX</div>
                                        <div style="color:#fff; font-weight:bold;">{signal['adx']:.0f}</div>
                                    </div>
                                    <div style="background:#0a0a0a; padding:6px; border-radius:5px; text-align:center;">
                                        <div style="color:#888;">Trend</div>
                                        <div style="color:#fff; font-weight:bold; font-size:9px;">{signal['trend_desc']}</div>
                                    </div>
                                </div>
                                
                                <!-- Exit Strategy -->
                                <div style="font-size:11px; color:#d2a8ff; font-style:italic; text-align:center; padding:8px; background:#d2a8ff11; border-radius:6px;">
                                    {signal['exit_msg']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        col_idx += 1
                        
                except Exception as e:
                    continue
            
            st.markdown("---")
    else:
        st.error("❌ Unable to fetch market data. Please try again.")

# ============================================================================
# TAB 2: NEWS & SENTIMENT
# ============================================================================

with tab2:
    st.header("📰 Market News & AI Sentiment Analysis")
    
    # Market Fear Indicators
    st.subheader("🌍 Global Market Fear Indicators")
    
    fear_cols = st.columns(4)
    fear_tickers = {
        "🇮🇳 INDIA VIX": "^INDIAVIX",
        "🇺🇸 US VIX": "^VIX",
        "💵 DOLLAR INDEX": "DX-Y.NYB",
        "🛢️ BRENT OIL": "BZ=F"
    }
    
    try:
        fear_data = yf.download(
            list(fear_tickers.values()), 
            period="5d", 
            interval="1d", 
            group_by='ticker', 
            progress=False
        )
        
        for idx, (name, symbol) in enumerate(fear_tickers.items()):
            try:
                if len(fear_tickers) > 1:
                    df = fear_data[symbol]
                else:
                    df = fear_data
                
                current_val = df['Close'].iloc[-1]
                prev_val = df['Close'].iloc[-2]
                change = ((current_val - prev_val) / prev_val) * 100
                
                # Color based on VIX logic (higher = more fear)
                if "VIX" in name:
                    color = "#ff4b4b" if change > 0 else "#00ff88"
                else:
                    color = "#00ff88" if change > 0 else "#ff4b4b"
                
                with fear_cols[idx]:
                    st.markdown(f"""
                    <div class="trade-card" style="text-align:center;">
                        <div style="font-size:12px; color:#888; margin-bottom:8px;">{name}</div>
                        <div style="font-size:22px; font-weight:bold; color:#fff; margin-bottom:6px;">
                            {current_val:.2f}
                        </div>
                        <div style="color:{color}; font-weight:bold;">
                            {'▲' if change > 0 else '▼'} {abs(change):.2f}%
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                pass
    except:
        st.warning("Unable to load fear indicators")
    
    st.markdown("---")
    
    # News Feed Selection
    news_source = st.selectbox(
        "Select News Source:",
        list(RSS_FEEDS.keys()),
        index=0
    )
    
    st.subheader(f"Latest from {news_source}")
    
    try:
        feed = feedparser.parse(RSS_FEEDS[news_source])
        
        for entry in feed.entries[:10]:
            sentiment, badge_class, score = analyze_sentiment(entry.title)
            impact = get_market_impact(entry.title)
            
            # Badge color
            if "bull" in badge_class:
                badge_color = "#00ff88"
            elif "bear" in badge_class:
                badge_color = "#ff4b4b"
            else:
                badge_color = "#888888"
            
            st.markdown(f"""
            <div class="news-card">
                <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:10px;">
                    <a href="{entry.link}" target="_blank" style="color:#58a6ff; font-weight:bold; text-decoration:none; flex:1; font-size:15px;">
                        {entry.title}
                    </a>
                    <span class="status-badge" style="background:{badge_color}22; color:{badge_color}; border:1px solid {badge_color}; margin-left:10px;">
                        {sentiment}
                    </span>
                </div>
                <div style="font-size:12px; color:#888; margin-bottom:8px;">
                    🕒 {entry.get('published', 'Just Now')}
                </div>
                <div style="font-size:12px; color:#d2a8ff; border-left:3px solid #d2a8ff; padding-left:10px;">
                    <strong>Impact:</strong> {impact}
                </div>
                <div style="font-size:11px; color:#666; margin-top:6px;">
                    Sentiment Score: {score:.3f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Unable to fetch news: {str(e)}")

# ============================================================================
# TAB 3: TRADING INSIGHTS
# ============================================================================

with tab3:
    st.header("🎓 Trading Insights & Best Practices")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📊 How Signals Work
        
        **Signal Strength Calculation:**
        - **70-100%**: Strong signal with multiple confirmations
        - **50-69%**: Moderate signal, proceed with caution
        - **Below 50%**: Weak signal, wait for better setup
        
        **Key Indicators Used:**
        1. **Supertrend** - Trend direction
        2. **EMA 200** - Institutional bias
        3. **MFI** - Money flow (volume-weighted)
        4. **ADX** - Trend strength
        5. **ATR** - Volatility for SL/TP
        
        **Entry Conditions (BUY):**
        - Price above EMA 200
        - Supertrend bullish
        - MFI below 80 (not overbought)
        - EMA alignment (20>50>200)
        - Strong ADX (>25)
        """)
    
    with col2:
        st.markdown("""
        ### 💡 Risk Management Tips
        
        **Position Sizing:**
        - Never risk more than 2% per trade
        - Calculate: Position Size = (Account * 2%) / (Entry - SL)
        
        **Stop Loss Strategy:**
        - Always use the provided SL
        - ATR-based SL adapts to volatility
        - Never move SL against your position
        
        **Take Profit Strategy:**
        - Book 50% at 2:1 RR
        - Move SL to breakeven
        - Trail remaining 50% with Supertrend
        
        **Exit Signals:**
        - MFI > 80: Consider booking profits (BUY)
        - MFI < 20: Consider booking profits (SELL)
        - Supertrend reversal
        """)
    
    st.markdown("---")
    
    st.subheader("🎯 Featured Setups (Educational)")
    
    setup_col1, setup_col2 = st.columns(2)
    
    with setup_col1:
        st.success("""
        **📈 Momentum Breakout Setup**
        
        **When to Use:** Strong trending markets
        
        **Entry Criteria:**
        - Price breaks above resistance
        - Volume spike (>2x average)
        - ADX > 30
        - MFI 50-70
        
        **Management:**
        - Quick profit targets
        - Tight trailing SL
        - Book 75% at 3:1 RR
        """)
    
    with setup_col2:
        st.info("""
        **📉 Reversal Setup**
        
        **When to Use:** Overbought/Oversold conditions
        
        **Entry Criteria:**
        - MFI extreme (>85 or <15)
        - Divergence on RSI
        - Supertrend reversal
        - Price at order block
        
        **Management:**
        - Wider stop loss
        - Multiple profit targets
        - Patient holding
        """)
    
    st.markdown("---")
    
    st.warning("""
    ⚠️ **Important Disclaimers:**
    - This is an educational tool, not financial advice
    - Past performance doesn't guarantee future results
    - Always do your own research
    - Trade only with money you can afford to lose
    - Consider consulting a financial advisor
    - Signals are based on technical analysis only
    """)

# ============================================================================
# 10. AUTO-REFRESH MECHANISM
# ============================================================================

# Auto-refresh every 60 seconds
try:
    from streamlit_autorefresh import st_autorefresh
    count = st_autorefresh(interval=60000, key="market_refresh")
except:
    st.info("💡 Install `streamlit-autorefresh` for auto-refresh: `pip install streamlit-autorefresh`")

# ============================================================================
# END OF APPLICATION
# ============================================================================
