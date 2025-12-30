import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. APP CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Forex & Economic Dashboard",
    page_icon="💹",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. SECRETS & API CONFIGURATION
# -----------------------------------------------------------------------------
# Try to retrieve the API key from Streamlit secrets
try:
    api_key = st.secrets["RAPIDAPI_KEY"]
except FileNotFoundError:
    st.error("Secrets file not found. Please add your API key to Streamlit secrets.")
    st.stop()
except KeyError:
    st.error("API Key not found in secrets. Please add 'RAPIDAPI_KEY' to your secrets.toml file.")
    st.stop()

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS (CACHED)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def fetch_ultimate_calendar(_headers, start_date, end_date, countries):
    url = "https://ultimate-economic-calendar.p.rapidapi.com/economic-events/tradingview"
    
    # Convert list of countries to CSV string (e.g., "US,DE")
    country_str = ",".join(countries)
    
    querystring = {
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "countries": country_str
    }
    
    # Host specific to this endpoint
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
        "currency": "ALL",
        "event_name": "ALL",
        "timezone": "GMT-06:00 Central Time (US & Canada)",
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

@st.cache_data(ttl=1800) # Cache news for 30 mins
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

# Base Headers
base_headers = {
    "x-rapidapi-key": api_key
}

# -----------------------------------------------------------------------------
# 4. MAIN APP LAYOUT
# -----------------------------------------------------------------------------
st.title("💹 Global Economic Monitor")
st.markdown("Dashboard integrating **Ultimate Economic Calendar** and **Forex Factory Scraper** via RapidAPI.")

tab1, tab2 = st.tabs(["📅 Economic Calendar", "📰 Market News"])

# --- TAB 1: ECONOMIC CALENDAR ---
with tab1:
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Filters")
        # Date Selection
        d_range = st.date_input("Select Date Range", [datetime.now(), datetime.now() + timedelta(days=2)])
        
        # Country Selection
        country_options = ["US", "DE", "GB", "JP", "AU", "CA", "CH", "CN", "EU"]
        selected_countries = st.multiselect("Select Countries", country_options, default=["US", "DE"])
        
        fetch_btn = st.button("Fetch Calendar Data")

    with col2:
        if fetch_btn and len(d_range) == 2:
            start_d, end_d = d_range
            
            # 1. Ultimate Economic Calendar
            st.subheader("🌐 TradingView Economic Events")
            with st.spinner("Fetching Ultimate Economic Calendar..."):
                data_ult = fetch_ultimate_calendar(base_headers, start_d, end_d, selected_countries)
                
                if "error" in data_ult:
                    st.error(f"Error: {data_ult['error']}")
                elif isinstance(data_ult, list) and data_ult:
                    df_ult = pd.DataFrame(data_ult)
                    # Filter and show columns
                    cols_to_show = ["time", "country", "title", "actual", "previous", "forecast", "impact"]
                    cols = [c for c in cols_to_show if c in df_ult.columns]
                    st.dataframe(df_ult[cols], use_container_width=True, hide_index=True)
                else:
                    st.info("No data found for Ultimate Calendar.")

            st.divider()

            # 2. Forex Factory Calendar
            st.subheader("🏭 Forex Factory Real-Time Calendar")
            with st.spinner("Fetching Forex Factory Data..."):
                data_ff = fetch_forex_factory_calendar(base_headers, start_d)
                
                if "error" in data_ff:
                    st.error(f"Error: {data_ff['error']}")
                elif isinstance(data_ff, list) and data_ff:
                    df_ff = pd.DataFrame(data_ff)
                    st.dataframe(df_ff, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No Forex Factory events found for {start_d}.")
        
        elif fetch_btn and len(d_range) != 2:
            st.warning("Please select both a Start and End date.")

# --- TAB 2: MARKET NEWS ---
with tab2:
    st.subheader("Latest Forex News")
    
    news_type = st.radio(
        "Select News Source:",
        ("Latest Hottest News", "Fundamental Analysis", "Breaking News"),
        horizontal=True
    )
    
    endpoint_map = {
        "Latest Hottest News": "latest_hottest_news",
        "Fundamental Analysis": "latest_fundamental_analysis_news",
        "Breaking News": "latest_breaking_news"
    }
    
    if st.button("Refresh News"):
        selected_endpoint = endpoint_map[news_type]
        
        with st.spinner("Fetching news..."):
            news_data = fetch_news(base_headers, selected_endpoint)
            
            if "error" in news_data:
                st.error(f"Error: {news_data['error']}")
            elif isinstance(news_data, list) and news_data:
                df_news = pd.DataFrame(news_data)
                
                # Dynamic column config for clickable links
                column_config = {}
                if "Link" in df_news.columns or "url" in df_news.columns:
                     link_col = "Link" if "Link" in df_news.columns else "url"
                     column_config[link_col] = st.column_config.LinkColumn("Read Article")

                st.dataframe(
                    df_news, 
                    use_container_width=True, 
                    column_config=column_config,
                    hide_index=True
                )
            else:
                st.info("No news items found.")

# -----------------------------------------------------------------------------
# 5. FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption("Data provided by RapidAPI.")
