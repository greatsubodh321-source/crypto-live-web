@echo off
echo ========================================
echo   Crypto Dashboard - Public Access
echo ========================================
echo.
echo Starting Streamlit app...
start "Streamlit App" cmd /k "streamlit run app.py"
timeout /t 3 /nobreak >nul
echo.
echo ========================================
echo   To make it public, use one of these:
echo ========================================
echo.
echo Option 1: ngrok (if installed)
echo   ngrok http 8501
echo.
echo Option 2: Streamlit Cloud (Recommended)
echo   1. Push code to GitHub
echo   2. Go to share.streamlit.io
echo   3. Deploy!
echo.
echo See DEPLOY.md for detailed instructions
echo.
pause
