@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 首次运行，正在创建虚拟环境...
  python -m venv .venv
  if errorlevel 1 (
    echo 创建虚拟环境失败，请确认已安装 Python 并加入 PATH。
    pause
    exit /b 1
  )
)

echo [2/3] 检查依赖...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo 已生成 .env，请填入 GITHUB_TOKEN 和 AI_API_KEY 后重新运行。
  pause
  exit /b 0
)

echo [3/3] 启动服务...
echo.
echo   电脑访问:  http://127.0.0.1:8000
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=1" %%b in ("%%a") do echo   手机访问:  http://%%b:8000
)
echo.
echo 按 Ctrl+C 停止服务。
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
