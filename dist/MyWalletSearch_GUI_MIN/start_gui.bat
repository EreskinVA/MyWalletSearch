@echo off
setlocal
cd /d %~dp0

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.x with tkinter and try again.
  pause
  exit /b 1
)

set PYTHONUTF8=1
python vanity_gui.py
