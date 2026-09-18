# ForgeFlex X — GitHub Submission Checklist

## Include

- `app.py` — final Review 2 control-room dashboard
- `forgeflex/` — forecasting, MILP and digital-twin implementation
- `data/` — hackathon demonstration dataset
- `review2_outputs/` — reproducible Review 2 outputs and Simulink handoff MAT file
- `matlab/` — Simulink builder / showcase scripts
- `docs/` — architecture, demo, QA and final review guidance
- `.github/workflows/test.yml` — automated test workflow
- `requirements.txt`
- `LICENSE`

## Do not include

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.vscode/`
- temporary files or editor caches

## Recommended README screenshots

Use one screenshot of the final Command Center and one of the Simulink validation scope if the GitHub submission form benefits from visual evidence.

## Reproducibility commands

```powershell
python -m pip install -r requirements.txt
python scripts/run_review2.py
python -m pytest -q
python -m streamlit run app.py
```
