@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher ^(py^) not found. Install an actively supported Python release and rerun.
  pause
  exit /b 1
)
if not exist .venv py -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m forgeflex.core.data_generator
.venv\Scripts\python.exe -m streamlit run app.py
endlocal
