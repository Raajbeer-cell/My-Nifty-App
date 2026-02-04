import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from streamlit_autorefresh import st_autorefresh  # For Real-Time loops

# --- SETUP ---
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

# Page Setup
st.set_page_config(page_title="Pro Market Dashboard", page_icon="📈", layout="wide")

# --- REAL-TIME CONFIG ---
# Refresh every 60 seconds (60000ms) to update prices without hitting API limits
count = st_autorefresh(interval=60000, key="datarefresh")

# --- UI STYLE: MONEYCONTROL THEME (Light Mode) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #f4f5f8; color: #2a2a2a; font-family: 'Roboto', sans-serif; }
    
    /* Card Container */
    .mc-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-top: 4px solid #e0e0e0;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .mc-card:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    
    /* Silver Special Card */
    .silver-card { border-top: 4px solid #a0a0a0; background: linear-gradient(to bottom right, #ffffff, #f0f0f0); }
    
    /* Typography */
    .asset-name { font-size: 18px; font-weight: 700; color: #333; margin-bottom: 5px; }
    .price-big { font-size: 28px; font-weight: 800; color: #222; }
    .price-positive { color: #009933; font-weight: 600; font-size: 14px; }
    .price-negative { color: #cc0000; font-weight: 600; font-size: 14px; }
    
    /* Technical Score Bar */
    .score-container { background-color: #e0e0e0; border-radius: 5px; height: 8px; width: 100%; margin-top: 10px; }
    .score-fill-bull { height: 100%; border-radius: 5px; background-color: #009933; }
    .score-fill-bear { height: 100%; border-radius: 5px; background-color: #cc0000; }
    .score-fill-neutral { height: 100%; border-radius: 5px; background-color: #ffcc00; }
    
    /* Tags */
    .tech-tag {
        font-size: 11px;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    .tag-green { background-color: #e6f9e6; color: #009933; border: 1px solid #009933; }
    .tag-red { background-color: #ffe6e6; color: #cc0000; border: 1px solid #cc0000; }
    .tag-blue { background-color: #e6f2ff; color: #0066cc; border: 1px solid #0066cc; }
    
    /* Call Card Specifics */
    .call-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .call-val { font-size: 15px; font-weight: 600; color: #333; }
</style>
""", unsafe_allow_html=True)

st.title("📈 Market Dashboard Pro")
st.caption(f"Last Updated: Real-time Mode Active • Refresh #{count}")

# --- DATA CONFIGURATION ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD"},
    "⛏️ COMMODITIES": {"SILVER (Global)": "SI=F", "GOLD": "GC=F", "CRUDE OIL": "CL=F"},
    "💱 FOREX": {"USD/INR": "USDINR=X"} 
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

# --- NEW EXPERT DATA (Integrated) ---
EXPERT_DATA = {
  "INDIAN_STOCKS": [
    {
      "script_name": "ADANIPORTS",
      "trend_strength": "Very Strong (ADX: 32.5)",
      "entry_price": 1560,
      "stop_loss": 1490,
      "exit_price_target_1": 1650,
      "exit_price_target_2": 1720,
      "holding_duration": "14-21 Days",
      "expected_returns": "8-10%",
      "logic": "Breakout above 52-week high with high volume; Beneficiary of India-US Trade Deal news.",
      "sector_rank": "1"
    },
    {
      "script_name": "TRENT",
      "trend_strength": "Strong Bullish (ADX: 28.4)",
      "entry_price": 4050,
      "stop_loss": 3880,
      "exit_price_target_1": 4350,
      "exit_price_target_2": 4500,
      "holding_duration": "30-45 Days",
      "expected_returns": "12-15%",
      "logic": "Consistent retail expansion and strong quarterly earnings growth; RSI holding above 60.",
      "sector_rank": "2"
    },
    {
      "script_name": "POWERGRID",
      "trend_strength": "Momentum (ADX: 26.1)",
      "entry_price": 415,
      "stop_loss": 395,
      "exit_price_target_1": 445,
      "exit_price_target_2": 465,
      "holding_duration": "45-60 Days",
      "expected_returns": "10%",
      "logic": "Defensive pick with sustained buying interest; MACD crossover on weekly charts.",
      "sector_rank": "3"
    },
    {
      "script_name": "INFOSYS",
      "trend_strength": "Weak/Bearish (ADX: 18)",
      "entry_price": 1820,
      "stop_loss": 1880,
      "exit_price_target_1": 1750,
      "exit_price_target_2": 1680,
      "holding_duration": "7-10 Days",
      "expected_returns": "5-7% (Short Side)",
      "logic": "Facing resistance at 1850; Tech sector under pressure due to global discretionary spending slowdown.",
      "sector_rank": "Lagging"
    }
  ],
  "METALS": [
    {
      "commodity": "GOLD (MCX)",
      "trend": "BULLISH",
      "current_market_price": 148676,
      "entry_range": "148000 - 148500",
      "stop_loss": 146500,
      "target_1": 152000,
      "target_2": 155000,
      "analysis": "Safe-haven buying amid global volatility. Price sustaining above 20-day EMA."
    },
    {
      "commodity": "SILVER (MCX)",
      "trend": "HIGH MOMENTUM BULLISH",
      "current_market_price": 254005,
      "entry_range": "252000 - 253000",
      "stop_loss": 248000,
      "target_1": 265000,
      "target_2": 275000,
      "analysis": "Industrial demand uptick and breakout from consolidation zone. Silver outperforming Gold in percentage terms."
    },
    {
      "commodity": "COPPER",
      "trend": "NEUTRAL",
      "current_market_price": 865,
      "entry_range": "Wait for dip to 850",
      "stop_loss": 835,
      "target_1": 890,
      "target_2": 910,
      "analysis": "Consolidating in a narrow range. Wait for breakout above 880 for fresh longs."
    }
  ],
  "SCRIPT_SPECIFIC_SIGNALS": [
    {
      "script_name": "NIFTY 50",
      "side": "BUY/LONG",
      "action_zone": "Above 25800",
      "confirmation_logic": "Hourly closing above 25800 indicates continuation of the trend towards 26000. Support established at 25650.",
      "risk_reward": "1:2.5"
    },
    {
      "script_name": "BANK NIFTY",
      "side": "WAIT/WATCH",
      "action_zone": "Range 59800 - 60300",
      "confirmation_logic": "Index is stuck in a consolidation box. Buy only on a clear breakout above 60350 with high volumes.",
      "risk_reward": "1:2"
    },
    {
      "script_name": "BITCOIN",
      "side": "BUY/LONG",
      "action_zone": "Above $110,000",
      "confirmation_logic": "Holding above key support. Altseason delayed—BTC dominance still high.",
      "risk_reward": "1:3"
    },
    {
      "script_name": "CRUDE OIL",
      "side": "SELL/SHORT",
      "action_zone": "Below $72",
      "confirmation_logic": "Bearish bias intact with oversupply concerns. Target $68.",
      "risk_reward": "1:2"
    }
  ],
  "GLOBAL_NEWS_IMPACT": [
    {
      "event": "India-US Trade Deal Finalized",
      "sentiment": "BULLISH",
      "impact_asset": "Indian Equities (Pharma, IT Services, Exports)",
      "reason": "Reduces tariff barriers. Long-term positive."
    },
    {
      "event": "Fed Hints at Rate Cuts in Q2 2026",
      "sentiment": "BULLISH",
      "impact_asset": "Gold, Silver, Global Equities",
      "reason": "Lower rates = weaker USD = boost for commodities and risk-on assets."
    },
    {
      "event": "China GDP Miss (Expected 5.2%, Actual 4.8%)",
      "sentiment": "BEARISH",
      "impact_asset": "Base Metals (Copper), Energy",
      "reason": "Slowing demand from world's largest commodity consumer."
    }
  ]
}

# --- FETCH DATA ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(tickers, period, interval):
    try:
        data = yf.download(tickers, period=period, interval=interval, group_by='ticker', progress=False)
        return data
    except Exception as e:
        st.error(f"Data fetch error: {e}")
        return None

# --- TECHNICAL SCORING ---
def calculate_technical_score(df):
    df_ind = df.copy()
    
    # Calculate indicators
    df_ind['EMA_9'] = ta.ema(df_ind['Close'], length=9)
    df_ind['EMA_21'] = ta.ema(df_ind['Close'], length=21)
    df_ind['RSI'] = ta.rsi(df_ind['Close'], length=14)
    
    macd = ta.macd(df_ind['Close'])
    if macd is not None and not macd.empty:
        df_ind['MACD'] = macd['MACD_12_26_9']
        df_ind['MACD_SIGNAL'] = macd['MACDs_12_26_9']
    else:
        df_ind['MACD'] = 0
        df_ind['MACD_SIGNAL'] = 0
    
    adx_data = ta.adx(df_ind['High'], df_ind['Low'], df_ind['Close'], length=14)
    if adx_data is not None and not adx_data.empty:
        df_ind['ADX'] = adx_data['ADX_14']
    else:
        df_ind['ADX'] = 0
    
    df_ind = df_ind.dropna()
    if df_ind.empty or len(df_ind) < 2:
        return 5.0, 0, 10, {}
    
    curr = df_ind.iloc[-1]
    close = curr['Close']
    
    checks = {
        "Price > EMA 9": close > curr['EMA_9'],
        "Price > EMA 21": close > curr['EMA_21'],
        "EMA 9 > EMA 21": curr['EMA_9'] > curr['EMA_21'],
        "RSI Not Overbought (<70)": curr['RSI'] < 70,
        "MACD > Signal": curr['MACD'] > curr['MACD_SIGNAL'],
        "MACD > 0": curr['MACD'] > 0,
        "ADX Strong Trend (>20)": curr['ADX'] > 20,
        "Recent Momentum (Close > Open)": close > curr['Open'],
        "Above Yesterday High": close > df.iloc[-2]['High'],
        "Volume Rising": curr['Volume'] > df['Volume'].rolling(5).mean().iloc[-1]
    }
    
    positive_signals = sum(checks.values())
    total_checks = 10
    score = (positive_signals / total_checks) * 10
    
    return score, positive_signals, total_checks, checks

# --- MAIN APP UI ---

# Updated to 3 Tabs to include the new Data
tab1, tab2, tab3 = st.tabs(["📊 DASHBOARD", "📰 INTELLIGENCE", "🎯 PRIME SETUPS"])

# --- TAB 1: LIVE DASHBOARD ---
with tab1:
    col_ctrl, col_status = st.columns([4, 1])
    with col_ctrl:
        timeframe = st.selectbox("Market View:", ["15m", "1h", "1d"], index=1)
    
    tf_map = {"15m": "5d", "1h": "1mo", "1d": "1y"}
    
    with st.spinner("Analyzing Market Structure..."):
        raw_data = fetch_data(ALL_TICKERS, period=tf_map[timeframe], interval=timeframe)

    # USDINR for Conversion
    try:
        usdinr = raw_data['USDINR=X']['Close'].iloc[-1]
    except:
        usdinr = 84.0 # Fallback

    if raw_data is not None:
        for cat_name, tickers in ASSETS.items():
            if "FOREX" in cat_name: continue 
            
            st.subheader(cat_name)
            cols = st.columns(3)
            idx = 0
            
            for name, symbol in tickers.items():
                try:
                    df = raw_data[symbol].dropna()
                    if df.empty: continue
                    
                    score, pos_cnt, total, details = calculate_technical_score(df)
                    
                    close = df['Close'].iloc[-1]
                    prev_close = df['Close'].iloc[-2]
                    chg = close - prev_close
                    pct_chg = (chg / prev_close) * 100
                    
                    display_price = close
                    price_prefix = "$"
                    is_silver = "SILVER" in name or "SI=F" in symbol
                    
                    if is_silver:
                        mcx_approx = (close / 31.1035) * 1000 * usdinr * 1.15
                        display_price = mcx_approx
                        price_prefix = "₹"
                        name = "SILVER MIC (MCX Approx)"
                    elif cat_name == "🇮🇳 INDICES":
                        price_prefix = "₹"
                    
                    color_cls = "price-positive" if chg > 0 else "price-negative"
                    arrow = "▲" if chg > 0 else "▼"
                    bar_cls = "score-fill-neutral"
                    if score >= 7: bar_cls = "score-fill-bull"
                    if score <= 3: bar_cls = "score-fill-bear"
                    card_cls = "mc-card silver-card" if is_silver else "mc-card"
                    
                    with cols[idx % 3]:
                        st.markdown(f"""
                        <div class="{card_cls}">
                            <div class="asset-name">{name}</div>
                            <div style="display:flex; align-items:baseline;">
                                <div class="price-big">{price_prefix}{display_price:,.2f}</div>
                                <div class="{color_cls}" style="margin-left:10px;">
                                    {arrow} {pct_chg:.2f}%
                                </div>
                            </div>
                            
                            <div style="margin-top:15px;">
                                <div style="display:flex; justify-content:space-between; font-size:12px; color:#666;">
                                    <span>Technical Strength</span>
                                    <b>{int(score)}/10</b>
                                </div>
                                <div class="score-container">
                                    <div class="{bar_cls}" style="width: {score*10}%;"></div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    idx += 1
                except Exception:
                    pass
            st.markdown("<br>", unsafe_allow_html=True)

# --- TAB 2: NEWS INTELLIGENCE ---
with tab2:
    st.header("🌍 Market Sentiment News")
    news_opt = st.radio("Source:", ["General", "India", "Crypto"], horizontal=True)
    
    feed_url = "https://finance.yahoo.com/news/rssindex" # Default
    if news_opt == "India": feed_url = "https://www.moneycontrol.com/rss/economy.xml"
    if news_opt == "Crypto": feed_url = "https://cointelegraph.com/rss"
    
    feed = feedparser.parse(feed_url)
    
    for entry in feed.entries[:8]:
        sent = sia.polarity_scores(entry.title)['compound']
        border_col = "#009933" if sent > 0.05 else ("#cc0000" if sent < -0.05 else "#ddd")
        
        st.markdown(f"""
        <div style="background:#fff; padding:15px; border-left:5px solid {border_col}; margin-bottom:10px; box-shadow:0 2px 4px #eee;">
            <a href="{entry.link}" target="_blank" style="text-decoration:none; color:#333; font-weight:bold; font-size:16px;">
                {entry.title}
            </a>
            <div style="font-size:12px; color:#888; margin-top:5px;">
                Published: {entry.published if 'published' in entry else 'Now'}
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 3: PRIME SETUPS (NEW ADDITION) ---
with tab3:
    st.markdown("### 🏆 Expert Swing Picks & Analysis")
    
    # 1. Indian Stocks Grid
    st.markdown("#### 🇮🇳 Top Stock Picks")
    cols = st.columns(2)
    for i, stock in enumerate(EXPERT_DATA["INDIAN_STOCKS"]):
        is_long = "Bearish" not in stock["trend_strength"] and "Weak" not in stock["trend_strength"]
        side_tag = "tag-green" if is_long else "tag-red"
        side_text = "BUY/LONG" if is_long else "SELL/SHORT"
        
        with cols[i % 2]:
            st.markdown(f"""
            <div class="mc-card" style="border-top: 4px solid {'#009933' if is_long else '#cc0000'};">
                <div style="display:flex; justify-content:space-between;">
                    <span class="asset-name">{stock['script_name']}</span>
                    <span class="tech-tag {side_tag}">{side_text}</span>
                </div>
                <div style="font-size:13px; color:#555; margin-bottom:10px;">{stock['trend_strength']}</div>
                
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <div><span class="call-label">ENTRY</span><br><span class="call-val">₹{stock['entry_price']}</span></div>
                    <div><span class="call-label">STOP LOSS</span><br><span class="call-val" style="color:#cc0000">₹{stock['stop_loss']}</span></div>
                    <div><span class="call-label">TARGET</span><br><span class="call-val" style="color:#009933">₹{stock['exit_price_target_1']}</span></div>
                </div>
                <hr style="margin:8px 0;">
                <div style="font-size:13px; font-style:italic; color:#444;">"{stock['logic']}"</div>
            </div>
            """, unsafe_allow_html=True)

    # 2. Metals & Signals Row
    st.markdown("---")
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("#### ⚡ Commodity/Metal Calls")
        for metal in EXPERT_DATA["METALS"]:
            trend_col = "#009933" if "BULLISH" in metal["trend"] else ("#cc0000" if "BEARISH" in metal["trend"] else "#ffcc00")
            st.markdown(f"""
            <div style="background:#fff; padding:15px; border-radius:8px; border-left: 5px solid {trend_col}; margin-bottom:10px; box-shadow:0 2px 4px #eee;">
                <div style="font-weight:bold; font-size:16px;">{metal['commodity']} <span style="font-size:12px; color:{trend_col}">({metal['trend']})</span></div>
                <div style="display:flex; gap:15px; margin-top:5px; font-size:14px;">
                    <span>CMP: <b>{metal['current_market_price']}</b></span>
                    <span>TGT: <b>{metal['target_1']}</b></span>
                    <span>SL: <b>{metal['stop_loss']}</b></span>
                </div>
                <div style="font-size:12px; color:#666; margin-top:5px;">{metal['analysis']}</div>
            </div>
            """, unsafe_allow_html=True)
            
    with c2:
        st.markdown("#### 📡 Index & Global Signals")
        for signal in EXPERT_DATA["SCRIPT_SPECIFIC_SIGNALS"]:
             st.info(f"**{signal['script_name']} ({signal['side']})**: {signal['confirmation_logic']} (Zone: {signal['action_zone']})")

    # 3. Global Impact
    st.markdown("#### 🌏 Macro News Impact")
    for news in EXPERT_DATA["GLOBAL_NEWS_IMPACT"]:
        emoji = "🟢" if news['sentiment'] == "BULLISH" else ("🔴" if news['sentiment'] == "BEARISH" else "⚪")
        with st.expander(f"{emoji} {news['event']} (Impact: {news['impact_asset']})"):
            st.write(f"**Reason:** {news['reason']}")
