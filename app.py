import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. APP CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="USD High Impact Monitor (Quota Saver)",
    page_icon="🛡️",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. MOCK DATA GENERATORS (Save your quota!)
# -----------------------------------------------------------------------------
def get_mock_ultimate_calendar():
    """Returns fake data structure matching Ultimate Economic Calendar"""
    return [
        {"time": "08:30 AM", "country": "US", "title": "[DEMO] Core PPI m/m", "actual": "0.3%", "previous": "0.2%", "forecast": "0.2%", "impact": "High"},
        {"time": "08:30 AM", "country": "US", "title": "[DEMO] PPI m/m", "actual": "0.1%", "previous": "-0.1%", "forecast": "0.1%", "impact": "High"},
        {"time": "10:00 AM", "country": "US", "title": "[DEMO] Prelim UoM Consumer Sentiment", "actual": "69.5", "previous": "67.4", "forecast": "69.0", "impact": "Medium"},
    ]

def get_mock_forex_factory():
    """Returns fake data structure matching Forex Factory"""
    return [
        {"Currency": "USD", "Impact": "High", "Event": "[DEMO] Unemployment Claims", "Actual": "210K", "Forecast": "215K", "Previous": "208K"},
        {"Currency": "USD", "Impact": "High", "Event": "[DEMO] Philly Fed Mfg Index", "Actual": "15.5", "Forecast": "8.0", "Previous": "12.2"},
        {"Currency": "USD", "Impact": "Medium", "Event": "[DEMO] Natural Gas Storage", "Actual": "85B", "Forecast": "82B", "Previous": "79B"},
    ]

def get_mock_news():
    """Returns fake news data"""
    return [
        {"Title": "[DEMO] Dollar surges as inflation fears return", "Link": "#", "Date": "2 hours ago"},
        {"Title": "[DEMO] Fed Chair signals rate cut delay", "Link": "#", "Date": "4 hours ago"},
        {"Title": "[DEMO] Oil prices drop amid supply concerns", "Link": "#", "Date": "5 hours ago"},
    ]

# -----------------------------------------------------------------------------
# 3. API HANDLING & CACHING
# -----------------------------------------------------------------------------
# Try to get secrets, but don't crash if missing (we can use mock data)
try:
    API_KEY = st.secrets["RAPIDAPI_KEY"]
except (FileNotFoundError, KeyError):
    API_KEY = None

def make_api_request(url, params=None, headers=None):
    """Generic wrapper to handle limits gracefully"""
    if not API_KEY:
        return {"error": "NO_KEY"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 429:
            return {"error": "429_LIMIT"}
        return {"error": str(err)}
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600)
def fetch_ultimate_calendar_live(target_date, countries):
    url = "https://ultimate-economic-calendar.p.rapidapi.com/economic-events/tradingview"
    date_str = target_date.strftime("%Y-%m-%d")
    country_str = ",".join(countries)
    querystring = {"from": date_str, "to": date_str, "countries": country_str}
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "ultimate-economic-calendar.p.rapidapi.com"}
    return make_api_request(url, querystring, headers)

@st.cache_data(ttl=3600)
def fetch_forex_factory_live(date_obj):
    url = "https://forex-factory-scraper1.p.rapidapi.com/get_real_time_calendar_details"
    querystring = {
        "calendar": "Forex", "year": str(date_obj.year), "month": str(date_obj.month), "day": str(date_obj.day),
        "currency": "USD", "event_name": "ALL", "timezone": "GMT-05:00 Eastern Time (US & Canada)", "time_format": "12h"
    }
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "forex-factory-scraper1.p.rapidapi.com"}
    return make_api_request(url, querystring, headers)

@st.cache_data(ttl=1800)
def fetch_news_live(endpoint_suffix):
    base_url = "https://forex-factory-scraper1.p.rapidapi.com/"
    url = f"{base_url}{endpoint_suffix}"
    headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "forex-factory-scraper1.p.rapidapi.com"}
    return make_api_request(url, None, headers)

# -----------------------------------------------------------------------------
# 4. SIDEBAR & CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. The Safety Switch
    use_demo = st.checkbox("🛠️ Use DEMO Data (Save Quota)", value=True, help="Uncheck this to use real API calls. Watch your limit!")
    
    st.divider()
    
    st.subheader("Filters")
    selected_date = st.date_input("Select Date", datetime.now())
    
    st.info(f"**Status:** {'🟢 Demo Mode' if use_demo else '🔴 Live API Mode'}")
    if not use_demo and not API_KEY:
        st.error("⚠️ No API Key found in secrets. Switched to Mock Data.")
        use_demo = True

# -----------------------------------------------------------------------------
# 5. MAIN LAYOUT
# -----------------------------------------------------------------------------
st.title("🇺🇸 USD High Impact Monitor")
st.markdown("Dashboard for **High Impact USD** events.")

if use_demo:
    st.warning("👀 Viewing **MOCK DATA**. Real API quota is being preserved.")

# --- SECTION 1: TRADINGVIEW EVENTS ---
st.subheader("🌐 TradingView Events (USD High Impact)")

if use_demo:
    data_ult = get_mock_ultimate_calendar()
    source = "Mock Data"
else:
    with st.spinner("Fetching Live Ultimate Calendar..."):
        data_ult = fetch_ultimate_calendar_live(selected_date, ["US"])
        source = "Live API"

# Process Ultimate Data
if isinstance(data_ult, dict) and "error" in data_ult:
    error_code = data_ult["error"]
    if error_code == "429_LIMIT":
        st.error("🚫 API Quota Exceeded (429). Switching to Mock Data for display.")
        data_ult = get_mock_ultimate_calendar() # Fallback
    elif error_code == "NO_KEY":
        st.error("🚫 No API Key. Using Mock Data.")
        data_ult = get_mock_ultimate_calendar()
    else:
        st.error(f"API Error: {error_code}")
        data_ult = []

if isinstance(data_ult, list) and data_ult:
    df_ult = pd.DataFrame(data_ult)
    # Filter for High Impact if column exists
    if 'impact' in df_ult.columns:
        df_ult = df_ult[df_ult['impact'].astype(str).str.contains("High", case=False, na=False)]
    
    if not df_ult.empty:
        # Dynamic column selection
        cols = [c for c in ["time", "title", "actual", "previous", "forecast", "impact"] if c in df_ult.columns]
        st.dataframe(df_ult[cols], use_container_width=True, hide_index=True)
    else:
        st.info("No High Impact events found.")
else:
    st.info("No data available.")

st.divider()

# --- SECTION 2: FOREX FACTORY ---
st.subheader("🏭 Forex Factory Events (USD High Impact)")

if use_demo:
    data_ff = get_mock_forex_factory()
else:
    with st.spinner("Fetching Live Forex Factory..."):
        data_ff = fetch_forex_factory_live(selected_date)

# Process FF Data
if isinstance(data_ff, dict) and "error" in data_ff:
    if data_ff["error"] == "429_LIMIT":
        st.error("🚫 API Quota Exceeded (429). Switching to Mock Data.")
        data_ff = get_mock_forex_factory()
    else:
        st.error(f"API Error: {data_ff['error']}")
        data_ff = []

if isinstance(data_ff, list) and data_ff:
    df_ff = pd.DataFrame(data_ff)
    
    # Filter USD & High
    if 'Currency' in df_ff.columns:
        df_ff = df_ff[df_ff['Currency'] == 'USD']
    if 'Impact' in df_ff.columns:
        df_ff = df_ff[df_ff['Impact'].astype(str).str.contains("High", case=False, na=False)]
        
    if not df_ff.empty:
        st.dataframe(df_ff, use_container_width=True, hide_index=True)
    else:
        st.info("No High Impact USD events found.")
else:
    st.info("No data available.")

st.divider()

# --- SECTION 3: NEWS ---
st.subheader("📰 Latest Market News")

if use_demo:
    news_data = get_mock_news()
else:
    if st.button("Refresh News (Uses Quota)"):
        with st.spinner("Fetching Live News..."):
            news_data = fetch_news_live("latest_hottest_news")
    else:
        news_data = []
        st.caption("Click button to load news (saves 1 request).")

# Process News
if isinstance(news_data, dict) and "error" in news_data:
    if news_data["error"] == "429_LIMIT":
        st.error("🚫 API Quota Exceeded. Showing Mock News.")
        news_data = get_mock_news()
    else:
        st.error(f"News Error: {news_data['error']}")
        news_data = []

if isinstance(news_data, list) and news_data:
    df_news = pd.DataFrame(news_data)
    
    # Link Config
    column_config = {}
    link_col = next((c for c in ["Link", "url"] if c in df_news.columns), None)
    if link_col:
        column_config[link_col] = st.column_config.LinkColumn("Read Article")

    st.dataframe(df_news, use_container_width=True, column_config=column_config, hide_index=True)
