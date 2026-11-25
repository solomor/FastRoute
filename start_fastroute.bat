@echo off
REM FastRoute auto-start (double-click this file)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Creating .venv and installing requirements...
  py -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo Stopping any previous FastRoute / Streamlit processes...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8501 ^| findstr LISTENING') do taskkill /F /PID %%P >nul 2>&1

echo Starting FastRoute at http://localhost:8501 ...
echo Press Ctrl+C in this window to stop the app.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true
pause
