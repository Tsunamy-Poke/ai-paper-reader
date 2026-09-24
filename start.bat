@echo off
chcp 65001 >nul
cd /d "D:\AI论文阅读助手\ai-paper-reader\backend"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] 虚拟环境不存在，请先运行: cd backend ^&^& python -m venv .venv
  pause
  exit /b 1
)
start "AI Paper Reader - Backend" "D:\AI论文阅读助手\ai-paper-reader\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
timeout /t 4 >nul
start "" "http://127.0.0.1:8000/"
echo.
echo ============================================
echo  AI 论文阅读助手已启动
echo  浏览器将自动打开 http://127.0.0.1:8000/
echo  停止服务: 关闭 "AI Paper Reader - Backend" 窗口
echo ============================================
pause