@echo off
echo Starting AViiD Data Pipeline...

:: 1. Start Backend (Port 8123)
start "AViiD Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\activate && cd backend && python main.py"

:: 2. Start Frontend (Port 5123)
start "AViiD Frontend" cmd /k "cd /d %~dp0 && cd client && npm run dev"

echo.
echo Servers are starting...
echo Backend: http://localhost:8123/docs
echo Frontend: http://localhost:5123
echo.
pause
