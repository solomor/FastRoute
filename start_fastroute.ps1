# FastRoute auto-start (Windows PowerShell)
# Double-click or run:  powershell -ExecutionPolicy Bypass -File .\start_fastroute.ps1

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host 'Virtual environment not found. Creating .venv and installing requirements...'
    py -m venv .venv
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
}

Write-Host 'Starting FastRoute at http://localhost:8501 ...'
Write-Host 'Press Ctrl+C in this window to stop the app.'
& $python -m streamlit run app.py
