# GitHub Submission Checklist

## Commit these

- `app.py`
- `requirements.txt`
- `ENGINEERING_SPEC.md`
- `README.md`
- `data/historical_energy.csv`
- `data/flexible_loads.csv`
- `forgeflex/` source modules
- `scripts/run_review2.py`
- `matlab/` builder/documentation
- `review2_outputs/` generated Review 2 artifacts
- `docs/`
- `.github/workflows/test.yml`

## Do not commit

- `.venv/`
- `__pycache__/`
- editor caches
- personal files
- downloaded installers
- credentials/tokens

## Local commands

```powershell
python -m pip install -r requirements.txt
python scripts/run_review2.py
python -m streamlit run app.py
```

## Suggested commit sequence

```bash
git add .
git commit -m "feat: add Review 2 forecasting MILP and digital twin"
git add app.py docs/ matlab/
git commit -m "feat: add engineering command center and Simulink handoff"
git add .github/workflows README.md ENGINEERING_SPEC.md
git commit -m "docs: prepare reproducible GitHub submission"
```
