@echo off
cd /d "D:\AI论文阅读助手\ai-paper-reader\backend"
start "AI Paper Reader - Backend" ".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000
timeout /t 4 >nul
start "" "D:\AI论文阅读助手\ai-paper-reader\frontend\index.html"
echo.
echo Backend started. Browser will open the app.
echo To stop: close the "AI Paper Reader - Backend" window or press Ctrl+C there.