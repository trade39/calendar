import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. APP CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="USD High Impact Monitor",
    page_icon="🇺🇸",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. SECRETS & API CONFIGURATION
# -----------------------------------------------------------------------------
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
except (FileNotFoundError, KeyError):
    st.error("API Key not found. Please add 'RAPIDAPI_KEY' to your secrets.toml file.")
    st.stop()

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS (CACHED)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_ultimate_calendar(_headers, target_date, countries):
    url = "https://ultimate-economic-calendar.p.rapidapi.com/economic-events/tradingview"
    
    # For single day focus, "from" and "to" are the same
    date_str = target_date.strftime("%Y-%m-%d")
    country_str = ",".join(countries)
    
    querystring = {
        "from": date_str,
        "to": date_str,
        "countries": country_str
    }
    
    headers = _headers.copy()
    headers["x-rapidapi-host"] = "ultimate-economic-calendar.p.rapidapi.com"

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=3600)
def fetch_forex_factory_calendar(_headers, date_obj):
    url = "https://forex-factory-scraper1.p.rapidapi.com/get_real_time_calendar_details"
    
    querystring = {
        "calendar": "Forex",
        "year": str(date_obj.year),
        "month": str(date_obj.month),
        "day": str(date_obj.day),
        "currency": "USD", # Requesting ALL to filter later ensures we catch everything, but user requested focus
        "event_name": "ALL",
        "timezone": "GMT-05:00 Eastern Time (US & Canada)", # Aligning with NY time
        "time_format": "12h"
    }

    headers = _headers.copy()
    headers["x-rapidapi-host"] = "forex-factory-scraper1.p.rapidapi.com"

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(ttl=1800)
def fetch_news(_headers, endpoint_suffix):
    base_url = "https://forex-factory-scraper1.p.rapidapi.com/"
    url = f"{base_url}{endpoint_suffix}"
    headers = _headers.copy()
    headers["x-rapidapi-host"] = "forex-factory-scraper1.p.rapidapi.com"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

base_headers = {"x-rapidapi-key": api_key}

# -----------------------------------------------------------------------------
# 4. MAIN APP LAYOUT
# -----------------------------------------------------------------------------
st.title("🇺🇸 USD High Impact Monitor")
st.markdown("Focused dashboard for **High Impact USD** events happening **Today**.")

# Filter Settings (Sidebar for minimal distraction)
with st.sidebar:
    st.header("Filters")
    selected_date = st.date_input("Select Date", datetime.now())
    
    # Locked settings to ensure user focus
    st.caption("🔒 Filters applied automatically:")
    st.info("- Currency: **USD**\n- Impact: **High**")
    
    refresh = st.button("Refresh Data")

# --- DATA PROCESSING & DISPLAY ---

# 1. ULTIMATE ECONOMIC CALENDAR
st.subheader("🌐 TradingView Events (USD High Impact)")

with st.spinner("Fetching Ultimate Economic Calendar..."):
    # Fetch only US data
    data_ult = fetch_ultimate_calendar(base_headers, selected_date, ["US"])
    
    if "error" in data_ult:
        st.error(f"Error: {data_ult['error']}")
    elif isinstance(data_ult, list) and data_ult:
        df_ult = pd.DataFrame(data_ult)
        
        # FILTER: Keep only High Impact
        # Note: APIs vary on capitalization, so we normalize to title case or check string presence
        if 'impact' in df_ult.columns:
            # Filter where impact contains "High" (case insensitive)
            df_ult = df_ult[df_ult['impact'].astype(str).str.contains("High", case=False, na=False)]
        
        if not df_ult.empty:
            cols_to_show = ["time", "title", "actual", "previous", "forecast", "impact"]
            cols = [c for c in cols_to_show if c in df_ult.columns]
            st.dataframe(df_ult[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No High Impact USD events found for this date in Ultimate Calendar.")
    else:
        st.info("No events returned from API.")

st.divider()

# 2. FOREX FACTORY CALENDAR
st.subheader("🏭 Forex Factory Events (USD High Impact)")

with st.spinner("Fetching Forex Factory Data..."):
    data_ff = fetch_forex_factory_calendar(base_headers, selected_date)
    
    if "error" in data_ff:
        st.error(f"Error: {data_ff['error']}")
    elif isinstance(data_ff, list) and data_ff:
        df_ff = pd.DataFrame(data_ff)
        
        # FILTER: Currency == USD
        if 'Currency' in df_ff.columns:
            df_ff = df_ff[df_ff['Currency'] == 'USD']
            
        # FILTER: Impact == High
        # Forex Factory often uses "High", "Medium", "Low" strings
        if 'Impact' in df_ff.columns:
             df_ff = df_ff[df_ff['Impact'].astype(str).str.contains("High", case=False, na=False)]

        if not df_ff.empty:
            st.dataframe(df_ff, use_container_width=True, hide_index=True)
        else:
            st.info("No High Impact USD events found for this date in Forex Factory.")
    else:
        st.info(f"No events found for {selected_date}.")

st.divider()

# 3. NEWS (Optional: Filtered by relevance if possible, or kept generic)
st.subheader("📰 Latest Market News")
news_expander = st.expander("Show Latest Hottest News", expanded=False)
with news_expander:
    with st.spinner("Fetching news..."):
        news_data = fetch_news(base_headers, "latest_hottest_news")
        if isinstance(news_data, list) and news_data:
            df_news = pd.DataFrame(news_data)
            column_config = {}
            if "Link" in df_news.columns or "url" in df_news.columns:
                 link_col = "Link" if "Link" in df_news.columns else "url"
                 column_config[link_col] = st.column_config.LinkColumn("Read Article")
            
            st.dataframe(df_news, use_container_width=True, column_config=column_config, hide_index=True)
