# 🚀 Live Crypto Market Dashboard

A real-time cryptocurrency market tracker built with Streamlit.

## Features

- 📊 Real-time cryptocurrency prices from CoinGecko API
- 📈 Interactive charts and visualizations
- 🔄 Auto-refresh functionality
- 💰 Market cap and price analysis
- 📱 Responsive design

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
streamlit run app.py
```

3. Open your browser to `http://localhost:8501`

## Deploy to Web

### Option 1: Streamlit Cloud (Recommended - Free)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select your repository and branch
6. Set main file path to `app.py`
7. Click "Deploy"

Your app will be live at: `https://your-app-name.streamlit.app`

### Option 2: Using ngrok (Quick Testing)

1. Install ngrok: [ngrok.com/download](https://ngrok.com/download)
2. Run your Streamlit app:
```bash
streamlit run app.py
```
3. In another terminal, run:
```bash
ngrok http 8501
```
4. Copy the HTTPS URL from ngrok (e.g., `https://abc123.ngrok.io`)

### Option 3: Other Platforms

- **Heroku**: Use the included `Procfile`
- **AWS/Azure/GCP**: Deploy as a containerized app
- **Railway**: Connect GitHub repo for auto-deploy

## API Rate Limits

CoinGecko's free API has rate limits. The app is configured to:
- Cache data for 60 seconds
- Recommend refresh intervals of 60+ seconds
- Handle rate limit errors gracefully

## License

MIT
