@echo off
REM Double-click to launch the Chillispark Lead Launcher.
REM Runs the local server with email-automation's venv Python (it has openpyxl),
REM then opens the button page in your browser.

setlocal
set "HERE=%~dp0"
set "PY=%HERE%..\email-automation\.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo Could not find Python venv at:
  echo   %PY%
  echo Make sure email-automation\.venv exists, then run again.
  pause
  exit /b 1
)

cd /d "%HERE%"
"%PY%" server.py

echo.
echo Server stopped.
pause
