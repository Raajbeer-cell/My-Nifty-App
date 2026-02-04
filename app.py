import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import feedparser
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from streamlit_autorefresh import st_autorefresh

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="Pro Market Dashboard", page_icon="📈", layout="wide")

# NLTK Fix for Cloud (Ye error rokne ke liye hai)
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

sia = SentimentIntensityAnalyzer()

# --- 2. CSS STYLING (Ye Design ko Sunder Banayega) ---
# Maine yahan ensure kiya hai ki HTML sahi se kaam kare
st.markdown("""
<style>
    /* Pure App ka background */
    .stApp { background-color: #f0f2f6; }
    
    /* Card ka design */
    .metric-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
    }
    
    /* Text styles */
    .stock-name { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 5px; }
    .stock-price { font-size: 22px; font-weight: 800; color: #000; }
    
    /* Green aur Red colors */
    .positive { color: #009933; font-weight: bold; }
    .negative { color: #cc0000; font-weight: bold; }
    
    /* Progress Bar container */
    .score-bg { width: 100%; background-color: #eee; height: 8px; border-radius: 4px; margin-top: 8px; }
    .score-fill { height: 100%; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS (Kaam Karne Wale Tools) ---

# Data Download karne wala function
@st.cache_data(ttl=60)
def get_data(tickers, period="5d", interval="15m"):
    try:
        # yfinance ka data download
        data = yf.download(tickers, period=period, interval=interval, group_by='ticker', progress=False)
        return data
    except Exception as e:
        return None

# Technical Score Calculator
def get_tech_score(df):
    if df.empty or len(df) < 15:
        return 5, 0 # Data kam hai to default score
        
    # Indicators calculate karna
    df['EMA_9'] = ta.ema(df['Close'], length=9)
    df['EMA_21'] = ta.ema(df['Close'], length=21)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # Latest candle (Abhi ka data)
    curr = df.iloc[-1]
    
    score = 0
    total = 5
    
    # Simple logic check
    if curr['Close'] > curr['EMA_9']: score += 1
    if curr['EMA_9'] > curr['EMA_21']: score += 1
    if curr['RSI'] < 70 and curr['RSI'] > 40: score += 1
    if curr['Close'] > df.iloc[-2]['High']: score += 1 # Kal se upar
    if curr['Volume'] > df['Volume'].mean(): score += 1 # Volume acha hai
    
    final_score = (score / total) * 10
    return final_score, score

# --- 4. DATA LISTS ---
ASSETS = {
    "🇮🇳 INDICES": {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK"},
    "🪙 CRYPTO": {"BITCOIN": "BTC-USD", "ETHEREUM": "ETH-USD"},
    "💱 COMMODITY": {"GOLD": "GC=F", "SILVER": "SI=F", "OIL": "CL=F"}
}

ALL_TICKERS = []
for cat in ASSETS.values():
    ALL_TICKERS.extend(cat.values())

# --- 5. MAIN APP LAYOUT ---

st.title("📈 Market Dashboard Pro")
st.caption("Live Market Analysis • Auto-Refreshes every 60s")

# Auto Refresh (Page ko reload karega)
count = st_autorefresh(interval=60000, key="datarefresh")

# Tabs banana
tab1, tab2, tab3 = st.tabs(["📊 LIVE MARKET", "📰 NEWS", "🎯 EXPERT PICKS"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.write("Market Loading...")
    
    # Data fetch karna
    data = get_data(ALL_TICKERS, period="5d", interval="15m")
    
    if data is not None:
        for category, tickers in ASSETS.items():
            st.subheader(category)
            cols = st.columns(3) # 3 Card ek line mein
            i = 0
            
            for name, symbol in tickers.items():
                try:
                    # Specific symbol ka data nikala
                    stock_df = data[symbol].copy().dropna()
                    
                    if not stock_df.empty:
                        # Price aur Score nikala
                        latest_price = stock_df['Close'].iloc[-1]
                        prev_price = stock_df['Close'].iloc[-2]
                        change = latest_price - prev_price
                        pct_change = (change / prev_price) * 100
                        
                        tech_score, raw_score = get_tech_score(stock_df)
                        
                        # Color logic
                        color_class = "positive" if change >= 0 else "negative"
                        arrow = "▲" if change >= 0 else "▼"
                        bar_color = "#009933" if tech_score >= 7 else ("#cc0000" if tech_score <= 3 else "#ffcc00")
                        
                        # Currency Symbol
                        currency = "₹" if "INDICES" in category else "$"
                        
                        # HTML Card create karna (Ye wala part screen par dikhega)
                        html_code = f"""
                        <div class="metric-card">
                            <div class="stock-name">{name}</div>
                            <div class="stock-price">{currency}{latest_price:,.2f}</div>
                            <div class="{color_class}" style="font-size:14px;">
                                {arrow} {pct_change:.2f}%
                            </div>
                            <hr style="margin: 10px 0; opacity: 0.2;">
                            <div style="font-size:12px; display:flex; justify-content:space-between;">
                                <span>Strength Score</span>
                                <b>{int(tech_score)}/10</b>
                            </div>
                            <div class="score-bg">
                                <div class="score-fill" style="width:{tech_score*10}%; background-color:{bar_color};"></div>
                            </div>
                        </div>
                        """
                        
                        with cols[i % 3]:
                            st.markdown(html_code, unsafe_allow_html=True)
                        
                        i += 1
                except Exception as e:
                    pass # Agar koi error aaye to ignore karein
            st.write("---")

# --- TAB 2: NEWS ---
with tab2:
    st.header("Latest Market News")
    try:
        # Moneycontrol RSS Feed
        feed = feedparser.parse("https://www.moneycontrol.com/rss/economy.xml")
        for entry in feed.entries[:5]:
            sentiment = sia.polarity_scores(entry.title)['compound']
            color = "green" if sentiment > 0 else ("red" if sentiment < 0 else "gray")
            
            st.markdown(f"**[{entry.title}]({entry.link})**")
            st.caption(f"Sentiment: :{color}[{sentiment}] • Published: {entry.published}")
            st.write("---")
    except:
        st.error("News load nahi ho payi.")

# --- TAB 3: EXPERT PICKS (Static Data) ---
with tab3:
    st.header("🏆 Swing Trading Setups")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### 🟢 BUY: TRENT")
        st.write("**Entry:** 4050 | **Target:** 4350 | **SL:** 3880")
        st.write("*Logic: Strong retail expansion and volume breakout.*")
        
    with col2:
        st.error("### 🔴 SELL: INFOSYS")
        st.write("**Entry:** 1820 | **Target:** 1750 | **SL:** 1880")
        st.write("*Logic: IT Sector under pressure, facing resistance.*")
