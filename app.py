import streamlit as st
import yfinance as yf
import feedparser
import datetime

# --- 1. Page Setup ---
st.set_page_config(page_title="Nifty AI Trader", page_icon="📈")
st.title("🇮🇳 Nifty Pre-Market AI Analyst")
st.write(f"**Date:** {datetime.date.today().strftime('%d %B, %Y')}")

# --- 2. Function: Global Market Data lana ---
def get_data():
    # Tickers (Inke codes hote hain)
    tickers = {
        "🇺🇸 US Market (S&P 500)": "^GSPC",
        "🇺🇸 Tech Stocks (Nasdaq)": "^IXIC",
        "🇯🇵 Japan (Nikkei)": "^N225",
        "🛢️ Crude Oil": "CL=F",
        "🇮🇳 Nifty 50 (Yesterday)": "^NSEI"
    }
    
    st.header("1. Global Market Dashboard 🌍")
    col1, col2 = st.columns(2)
    
    data_points = {}
    
    for name, symbol in tickers.items():
        try:
            stock = yf.Ticker(symbol)
            # Pichle 2 din ka data
            hist = stock.history(period="5d")
            
            if len(hist) > 0:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change_pct = ((current - prev) / prev) * 100
                data_points[name] = change_pct
                
                color = "green" if change_pct >= 0 else "red"
                with col1 if "US" in name else col2:
                    st.markdown(f"**{name}**")
                    st.markdown(f"<h4 style='color:{color}'>{change_pct:.2f}%</h4>", unsafe_allow_html=True)
            else:
                data_points[name] = 0.0
        except:
            pass
            
    return data_points

# --- 3. Function: Free Google News lana ---
def get_news():
    st.header("2. Latest Market News 📰")
    # Google News RSS Feed for 'Indian Stock Market'
    rss_url = "https://news.google.com/rss/search?q=Sensex+Nifty+Market+India&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    
    for entry in feed.entries[:5]: # Top 5 news
        st.write(f"👉 **{entry.title}**")
        st.caption(f"Source: {entry.source.title}")
        st.write("---")

# --- 4. AI Logic (Simple Brain) ---
def ai_prediction(data):
    st.header("3. AI Final Decision 🤖")
    
    score = 0
    reasons = []
    
    # Logic
    sp500 = data.get("🇺🇸 US Market (S&P 500)", 0)
    nikkei = data.get("🇯🇵 Japan (Nikkei)", 0)
    
    if sp500 > 0.3:
        score += 2
        reasons.append("✅ US Markets kal positive the.")
    elif sp500 < -0.3:
        score -= 2
        reasons.append("❌ US Markets kal gire the.")
        
    if nikkei > 0.5:
        score += 1
        reasons.append("✅ Asian Markets (Japan) aaj subah green hain.")
    elif nikkei < -0.5:
        score -= 1
        reasons.append("❌ Asian Markets (Japan) aaj subah red hain.")
        
    # Result
    if score >= 2:
        st.success("🚀 VIEW: GAP UP / BULLISH")
    elif score <= -2:
        st.error("📉 VIEW: GAP DOWN / BEARISH")
    else:
        st.warning("😐 VIEW: SIDEWAYS / FLAT")
        
    st.write("Reasoning:")
    for r in reasons:
        st.write(r)

# --- RUN APP ---
market_data = get_data()
st.markdown("---")
ai_prediction(market_data)
st.markdown("---")
get_news()

if st.button("Refresh Data 🔄"):
    st.rerun()
