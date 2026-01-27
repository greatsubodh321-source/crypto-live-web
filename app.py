import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh
import numpy as np
from sklearn.linear_model import LinearRegression

# Page Configuration
st.set_page_config(page_title="Live Crypto Tracker", layout="wide")

# Initialize session state for navigation
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'dashboard'
if 'selected_coin' not in st.session_state:
    st.session_state.selected_coin = None
if 'pause_refresh' not in st.session_state:
    st.session_state.pause_refresh = False

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

# ============================================================================
# 2. PRICE PREDICTION FUNCTION (Linear Regression for 12-hour forecast)
# ============================================================================
def generate_price_prediction(current_price, hours=12, volatility_factor=0.02):
    """
    Generate a price prediction for the next 12 hours using Linear Regression
    
    Args:
        current_price: Current price of the coin
        hours: Number of hours to predict (default 12)
        volatility_factor: Controls how much variance in predictions (0.02 = 2%)
    
    Returns:
        DataFrame with historical and predicted prices
    """
    # Create simulated historical data (last 24 hours)
    historical_hours = 24
    X = np.arange(historical_hours).reshape(-1, 1)
    
    # Generate realistic historical price data with slight variation
    np.random.seed(42)
    trend = np.linspace(0, volatility_factor * current_price, historical_hours)
    noise = np.random.normal(0, volatility_factor * current_price * 0.5, historical_hours)
    y = current_price + trend + noise
    
    # Train Linear Regression model
    model = LinearRegression()
    model.fit(X, y)
    
    # Generate predictions for next 12 hours
    future_hours = np.arange(historical_hours, historical_hours + hours).reshape(-1, 1)
    predictions = model.predict(future_hours)
    
    # Create time series
    now = datetime.now()
    historical_times = [now - timedelta(hours=h) for h in range(historical_hours, 0, -1)]
    prediction_times = [now + timedelta(hours=h) for h in range(1, hours + 1)]
    
    # Combine historical and prediction data
    all_times = historical_times + prediction_times
    all_prices = np.concatenate([y, predictions])
    
    return {
        'times': all_times,
        'prices': all_prices,
        'historical_count': historical_hours,
        'prediction_count': hours,
        'model': model
    }

# ============================================================================
# 3. NEWS FEED FUNCTION (Placeholder with realistic headlines)
# ============================================================================
def get_crypto_news(coin_name, coin_symbol):
    """
    Fetch crypto news. Using placeholder data for now.
    Can be replaced with real API (e.g., NewsAPI, CoinTelegraph API)
    """
    # Placeholder news data
    news_data = {
        'Bitcoin': [
            {'title': 'Bitcoin reaches new milestone above $45,000', 'source': 'CoinDesk', 'date': 'Today'},
            {'title': 'Institutional investment in BTC increases by 25%', 'source': 'Crypto News', 'date': 'Yesterday'},
            {'title': 'Bitcoin mining difficulty adjustment announced', 'source': 'Bitcoin.org', 'date': '2 days ago'},
        ],
        'Ethereum': [
            {'title': 'Ethereum network upgrade improves scalability', 'source': 'EthHub', 'date': 'Today'},
            {'title': 'ETH staking rewards hit record high', 'source': 'The Block', 'date': 'Yesterday'},
            {'title': 'Layer 2 solutions see 50% increase in usage', 'source': 'DeFi Pulse', 'date': '2 days ago'},
        ],
        'Default': [
            {'title': f'{coin_name} trading volume surges', 'source': 'Crypto News', 'date': 'Today'},
            {'title': f'{coin_symbol} shows strong momentum', 'source': 'Market Watch', 'date': 'Yesterday'},
            {'title': f'Analyst bullish on {coin_name}', 'source': 'Crypto Analytics', 'date': '2 days ago'},
        ]
    }
    
    return news_data.get(coin_name, news_data['Default'])

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

# Navigation Buttons
st.sidebar.subheader("📍 Navigation")
if st.sidebar.button("📊 Dashboard", use_container_width=True):
    st.session_state.view_mode = 'dashboard'
    st.session_state.pause_refresh = False
    st.rerun()

if st.sidebar.button("🔬 Analysis", use_container_width=True):
    st.session_state.view_mode = 'analysis'
    st.session_state.pause_refresh = True  # Pause auto-refresh on analysis page
    st.rerun()

st.sidebar.divider()

# Auto-refresh settings (only show on dashboard)
if st.session_state.view_mode == 'dashboard':
    st.sidebar.subheader("🔄 Auto-Refresh")
    auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
    refresh_interval = st.sidebar.selectbox(
        "Refresh Interval (seconds)",
        options=[30, 60, 120, 300, 600],
        index=1,  # Default to 60 seconds (recommended to avoid rate limits)
        disabled=not auto_refresh,
        help="⚠️ CoinGecko free API: Minimum 30s recommended. 60s+ is safer to avoid rate limits."
    )
else:
    auto_refresh = False  # Disable auto-refresh on analysis page
    refresh_interval = 60
    st.sidebar.info("⏸️ Auto-refresh paused on Analysis page")

selected_coin = st.sidebar.selectbox("Select a Coin", df['name'].tolist())
st.session_state.selected_coin = selected_coin

# 3. Main Dashboard - Metrics
col1, col2, col3 = st.columns(3)
coin_info = df[df['name'] == selected_coin].iloc[0]

with col1:
    st.metric("Price", f"${coin_info['current_price']:,}", f"{coin_info['price_change_percentage_24h']:.2f}%")
with col2:
    st.metric("Market Cap", f"${coin_info['market_cap']:,}")
with col3:
    st.metric("24h High", f"${coin_info['high_24h']:,}")

# ============================================================================
# VIEW LOGIC: Dashboard vs Analysis
# ============================================================================

if st.session_state.view_mode == 'dashboard':
    # ========== DASHBOARD VIEW ==========
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

elif st.session_state.view_mode == 'analysis':
    # ========== ANALYSIS PAGE VIEW ==========
    st.subheader(f"📈 Detailed Analysis: {selected_coin}")
    
    coin_info = df[df['name'] == selected_coin].iloc[0]
    
    # Create 2 columns: Chart on left, News on right
    chart_col, news_col = st.columns([2, 1])
    
    with chart_col:
        # ===== PRICE PREDICTION CHART =====
        st.markdown("#### 💹 Price Prediction (Next 12 Hours)")
        
        # Generate prediction data
        prediction_data = generate_price_prediction(
            current_price=coin_info['current_price'],
            hours=12,
            volatility_factor=0.02
        )
        
        times = prediction_data['times']
        prices = prediction_data['prices']
        historical_count = prediction_data['historical_count']
        
        # Create figure with both historical and predicted data
        fig_prediction = go.Figure()
        
        # Add historical data (solid line)
        fig_prediction.add_trace(go.Scatter(
            x=times[:historical_count],
            y=prices[:historical_count],
            mode='lines',
            name='Historical Price',
            line=dict(color='blue', width=2, dash='solid'),
            hovertemplate='<b>Historical</b><br>Time: %{x|%H:%M}<br>Price: $%{y:.2f}<extra></extra>'
        ))
        
        # Add prediction data (dashed line)
        # Include last historical point to connect the lines
        fig_prediction.add_trace(go.Scatter(
            x=times[historical_count-1:],
            y=prices[historical_count-1:],
            mode='lines',
            name='Predicted Price',
            line=dict(color='green', width=2, dash='dash'),
            hovertemplate='<b>Predicted</b><br>Time: %{x|%H:%M}<br>Price: $%{y:.2f}<extra></extra>'
        ))
        
        fig_prediction.update_layout(
            title=f"{selected_coin} - 24h Historical + 12h Prediction",
            xaxis_title="Time",
            yaxis_title="Price (USD)",
            height=500,
            hovermode='x unified',
            template='plotly_white',
            legend=dict(yanchor='top', y=0.99, xanchor='left', x=0.01)
        )
        
        st.plotly_chart(fig_prediction, use_container_width=True)
        
        # ===== ADDITIONAL METRICS =====
        st.markdown("#### 📊 Key Metrics")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("Current Price", f"${coin_info['current_price']:,.2f}")
        
        with metric_col2:
            st.metric("24h Change", f"{coin_info['price_change_percentage_24h']:.2f}%",
                     delta_color="inverse" if coin_info['price_change_percentage_24h'] < 0 else "normal")
        
        with metric_col3:
            st.metric("24h Low", f"${coin_info['low_24h']:,.2f}")
        
        with metric_col4:
            st.metric("Market Cap Rank", coin_info['market_cap_rank'])
    
    with news_col:
        # ===== NEWS FEED =====
        st.markdown("#### 📰 Latest News")
        
        news = get_crypto_news(selected_coin, coin_info['symbol'].upper())
        
        for i, article in enumerate(news, 1):
            with st.container(border=True):
                st.markdown(f"**{article['title']}**")
                st.caption(f"📍 {article['source']} • {article['date']}")
                if i < len(news):
                    st.divider()

# 7. Live "Pulse" and Auto-Refresh
current_time = datetime.now().strftime('%H:%M:%S')

# Initialize session state for refresh count
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0

# Display status
status_col1, status_col2 = st.columns([3, 1])
with status_col1:
    if st.session_state.view_mode == 'dashboard':
        if auto_refresh:
            status_msg = f"🔄 Live Mode | Last updated: {current_time} | Auto-refreshing every {refresh_interval} seconds"
            if refresh_interval < 30:
                status_msg += " ⚠️ (May hit rate limits)"
            st.info(status_msg)
        else:
            st.info(f"⏸️ Paused | Last updated: {current_time} | Auto-refresh disabled")
    else:
        st.info(f"🔬 Analysis Mode | Last updated: {current_time} | Auto-refresh paused")
    
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

# Auto-refresh using streamlit-autorefresh (only on dashboard view)
if auto_refresh and st.session_state.view_mode == 'dashboard':
    # Count refreshes
    count = st_autorefresh(interval=refresh_interval * 1000, limit=None, key="crypto_refresh")
    if count > 0:
        # Only clear cache if refresh interval is >= cache TTL to avoid rate limits
        if refresh_interval >= 60:
            st.cache_data.clear()
        st.session_state.refresh_count = count
 import streamlit as st
import base64

def apply_integrated_premium_style(image_path="crypto_bg.png"):
    # Function to convert local image to base64 for CSS injection
    def get_base64(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()

    bin_str = get_base64(image_path)

    st.markdown(
        f"""
        <style>
        /* 1. Main Page Background with local image */
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
                        url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* 2. Glassmorphism for Property Parameters & Results Cards */
        [data-testid="stSidebar"], .stMetric, .stVerticalBlock > div {{
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(15px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        /* 3. Smooth Fade-In/Slide-Up Animation for content */
        @keyframes slideUpFade {{
            0% {{ opacity: 0; transform: translateY(30px); }}
            100% {{ opacity: 1; transform: translateY(0); }}
        }}

        .main .block-container {{
            animation: slideUpFade 1.2s ease-out;
        }}

        /* 4. Highlighted 'Get Estimated Price' Button */
        div.stButton > button:first-child {{
            background: linear-gradient(45deg, #FF4B4B, #FF7E7E);
            color: white;
            border: none;
            padding: 0.5rem 2rem;
            transition: transform 0.3s ease;
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
        }}

        div.stButton > button:first-child:hover {{
            transform: scale(1.05);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# 2. Call the function before any other Streamlit commands
# Ensure 'crypto_bg.png' is in your project folder
apply_integrated_premium_style("crypto_bg.png")