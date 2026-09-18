@echo off
python -m pip install -r requirements.txt
python scripts/run_review2.py
python -m streamlit run app.py
