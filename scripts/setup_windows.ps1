$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Python launcher 'py' not found. Install an actively supported Python release, then rerun this script."
    exit 1
}
if (-not (Test-Path ".venv")) {
    py -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m forgeflex.core.data_generator
Write-Host "Setup complete. Run: .\.venv\Scripts\python.exe -m streamlit run app.py"
