import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import time
from streamlit_autorefresh import st_autorefresh

# Page Configuration
st.set_page_config(page_title="Live Crypto Tracker", layout="wide")
st.title("🚀 Real-Time Crypto Market Dashboard")

# 1. Fetch Live Data from CoinGecko with Rate Limiting
def get_crypto_data_with_retry(max_retries=3, backoff_factor=2):
    """Fetch data with retry logic and rate limit handling"""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": False
    }
    
    # Add headers to be more respectful of API
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'CryptoDashboard/1.0'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', backoff_factor ** attempt))
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
                else:
                    raise Exception(f"Rate limit exceeded. Please wait {retry_after} seconds before trying again.")
            
            response.raise_for_status()
            return pd.DataFrame(response.json())
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"Failed to fetch data after {max_retries} attempts: {str(e)}")
    
    return pd.DataFrame()

@st.cache_data(ttl=60)  # Cache for 60 seconds to reduce API calls and avoid rate limits
def get_crypto_data():
    try:
        return get_crypto_data_with_retry()
    except Exception as e:
        error_msg = str(e)
        # Store error in session state
        st.session_state.last_error = error_msg
        return pd.DataFrame()

# Initialize session state for cached data
if 'cached_df' not in st.session_state:
    st.session_state.cached_df = pd.DataFrame()
if 'last_error' not in st.session_state:
    st.session_state.last_error = None

# Load Data
df = get_crypto_data()

# Handle errors and use cached data if available
if df.empty:
    if not st.session_state.cached_df.empty:
        st.warning("⚠️ Using cached data. API rate limit may have been reached. Please wait before refreshing.")
        df = st.session_state.cached_df
    else:
        error_msg = st.session_state.last_error or "Unable to load cryptocurrency data."
        st.error(f"❌ {error_msg}")
        if "Rate limit" in error_msg or "429" in error_msg:
            st.info("💡 **Tip:** CoinGecko's free API has rate limits. Try increasing the refresh interval to 60+ seconds or wait a few minutes.")
        st.stop()
else:
    # Update cached data on successful fetch
    st.session_state.cached_df = df.copy()
    st.session_state.last_error = None

# 2. Sidebar for Selection
st.sidebar.header("Settings")

# Auto-refresh settings
st.sidebar.subheader("🔄 Auto-Refresh")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
refresh_interval = st.sidebar.selectbox(
    "Refresh Interval (seconds)",
    options=[30, 60, 120, 300, 600],
    index=1,  # Default to 60 seconds (recommended to avoid rate limits)
    disabled=not auto_refresh,
    help="⚠️ CoinGecko free API: Minimum 30s recommended. 60s+ is safer to avoid rate limits."
)

selected_coin = st.sidebar.selectbox("Select a Coin", df['name'].tolist())

# 3. Main Dashboard - Metrics
col1, col2, col3 = st.columns(3)
coin_info = df[df['name'] == selected_coin].iloc[0]

with col1:
    st.metric("Price", f"${coin_info['current_price']:,}", f"{coin_info['price_change_percentage_24h']:.2f}%")
with col2:
    st.metric("Market Cap", f"${coin_info['market_cap']:,}")
with col3:
    st.metric("24h High", f"${coin_info['high_24h']:,}")

# 4. Graphs/Charts
st.subheader("📊 Market Visualizations")

# Create two columns for graphs
graph_col1, graph_col2 = st.columns(2)

with graph_col1:
    # Market Cap Bar Chart
    fig_market_cap = go.Figure(data=[
        go.Bar(
            x=df['symbol'],
            y=df['market_cap'],
            marker_color=df['price_change_percentage_24h'].apply(lambda x: 'green' if x >= 0 else 'red'),
            text=[f"${val/1e9:.2f}B" for val in df['market_cap']],
            textposition='auto',
        )
    ])
    fig_market_cap.update_layout(
        title="Market Cap Comparison (Top 10)",
        xaxis_title="Cryptocurrency",
        yaxis_title="Market Cap (USD)",
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_market_cap, use_container_width=True)

with graph_col2:
    # 24h Price Change Chart
    fig_price_change = go.Figure(data=[
        go.Bar(
            x=df['symbol'],
            y=df['price_change_percentage_24h'],
            marker_color=df['price_change_percentage_24h'].apply(lambda x: 'green' if x >= 0 else 'red'),
            text=[f"{val:.2f}%" for val in df['price_change_percentage_24h']],
            textposition='auto',
        )
    ])
    fig_price_change.update_layout(
        title="24h Price Change %",
        xaxis_title="Cryptocurrency",
        yaxis_title="Price Change (%)",
        height=400,
        showlegend=False,
        yaxis=dict(zeroline=True, zerolinecolor='black')
    )
    st.plotly_chart(fig_price_change, use_container_width=True)

# Price vs Market Cap Scatter Plot
st.subheader("💰 Price vs Market Cap Analysis")
# Calculate normalized sizes for markers
size_values = (df['price_change_percentage_24h'].abs() * 2).clip(lower=5, upper=50)
fig_scatter = go.Figure(data=[
    go.Scatter(
        x=df['market_cap'],
        y=df['current_price'],
        mode='markers+text',
        text=df['symbol'],
        textposition='top center',
        marker=dict(
            size=size_values.tolist(),
            color=df['price_change_percentage_24h'].tolist(),
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="24h Change %"),
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='<b>%{text}</b><br>' +
                      'Market Cap: $%{x:,.0f}<br>' +
                      'Price: $%{y:,.2f}<extra></extra>'
    )
])
fig_scatter.update_layout(
    title="Cryptocurrency Price vs Market Cap",
    xaxis_title="Market Cap (USD)",
    yaxis_title="Current Price (USD)",
    height=500,
    xaxis=dict(type='log'),
    yaxis=dict(type='log')
)
st.plotly_chart(fig_scatter, use_container_width=True)

# 6. Interactive Table
st.subheader("Market Overview (Top 10)")
st.dataframe(df[['name', 'symbol', 'current_price', 'market_cap', 'price_change_percentage_24h']], use_container_width=True)

# 7. Live "Pulse" and Auto-Refresh
current_time = datetime.now().strftime('%H:%M:%S')

# Initialize session state for refresh count
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0

# Display status
status_col1, status_col2 = st.columns([3, 1])
with status_col1:
    if auto_refresh:
        status_msg = f"🔄 Live Mode | Last updated: {current_time} | Auto-refreshing every {refresh_interval} seconds"
        if refresh_interval < 30:
            status_msg += " ⚠️ (May hit rate limits)"
        st.info(status_msg)
    else:
        st.info(f"⏸️ Paused | Last updated: {current_time} | Auto-refresh disabled")
    
    # Show rate limit warning if error occurred
    if st.session_state.last_error and ("Rate limit" in st.session_state.last_error or "429" in st.session_state.last_error):
        st.warning("⚠️ API Rate Limit: Using cached data. Please wait before refreshing.")

with status_col2:
    if st.button('🔄 Refresh Now'):
        # Check if we should wait to avoid rate limits
        if 'last_refresh_time' in st.session_state:
            time_since_refresh = time.time() - st.session_state.last_refresh_time
            if time_since_refresh < 10:
                st.warning("⏳ Please wait a few seconds before refreshing again to avoid rate limits.")
        else:
            st.session_state.last_refresh_time = time.time()
        
        st.cache_data.clear()
        st.session_state.refresh_count += 1
        st.session_state.last_refresh_time = time.time()
        st.rerun()

# Auto-refresh using streamlit-autorefresh
if auto_refresh:
    # Count refreshes
    count = st_autorefresh(interval=refresh_interval * 1000, limit=None, key="crypto_refresh")
    if count > 0:
        # Only clear cache if refresh interval is >= cache TTL to avoid rate limits
        if refresh_interval >= 60:
            st.cache_data.clear()
        st.session_state.refresh_count = count
