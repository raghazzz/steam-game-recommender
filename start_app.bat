@echo off
rem Double-click to start the app on Windows (first run installs everything).
cd /d "%~dp0"
if not exist .venv (
  echo First run: setting up, this takes a few minutes...
  python -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python -m streamlit run app.py
pause
