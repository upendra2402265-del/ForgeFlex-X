# ⚡ ForgeFlex X

## Production-Aware Industrial Energy Orchestration for SU-01

ForgeFlex X is an engineering prototype for renewable-energy + industrial-load orchestration. It forecasts renewable generation and factory demand, models flexible production processes, solves a constrained mixed-integer linear program (MILP), validates the resulting schedule with a numerical digital twin, and prepares the same setpoints for MATLAB/Simulink engineering validation.

> **We optimize energy around production, not production around energy.**

## Core architecture

```text
Historical factory + renewable data
                │
                ▼
        AI forecast engine
          PV + factory load
                │
                ▼
             FlexDNA
     power + duration + window
                │
                ▼
          MILP optimizer
      grid + battery + flexible loads
                │
                ▼
          24-hour schedule
                │
        ┌───────┴────────┐
        ▼                ▼
 Numerical digital    MATLAB/Simulink
      twin              engineering twin
        │                │
        └───────┬────────┘
                ▼
        Review 2 command center
```


## Team

**Technoblade**  
Lead: **Upendra P**  
Team member: **Vishnu A R**

## Review 2 technical stack

| Layer | Implementation |
|---|---|
| Forecasting | HistGradientBoostingRegressor for PV; RandomForestRegressor for factory demand |
| Optimization | `scipy.optimize.milp` |
| Decision variables | grid, charge, discharge, SOC, curtailment, peak import, flexible-process start binaries, charge/discharge mode binaries |
| FlexDNA | contiguous machine runs inside legal operating windows |
| Battery | SOC bounds, power limit, charge/discharge efficiency, final SOC reserve |
| Numerical digital twin | energy balance, SOC, grid limit, battery power, flexible duration/window checks |
| Dashboard | Streamlit + Plotly |
| Engineering handoff | MATLAB `.mat` setpoint export + Simulink builder |

## Flexible industrial processes

- Air Compressor — 150 kW, 2 h, allowed 09:00–16:00
- Chiller — 110 kW, 3 h, allowed 10:00–17:00
- Water Pump — 75 kW, 2 h, allowed 08:00–18:00

## Run locally

```powershell
python -m pip install -r requirements.txt
python scripts/run_review2.py
python -m pytest -q
python -m streamlit run app.py
```

The final Review 2 dashboard is in `app.py`.

## Review 2 demonstration

1. Run **Normal Day**.
2. Show the 24-hour dispatch curve.
3. Open **FlexDNA** and show process timing.
4. Switch to **Cloudy Day** and execute again.
5. Switch to **High Production** and execute again.
6. Demonstrate **Grid Constrained** with a lower grid limit.
7. Open **Digital Twin** and show SOC, residual and validation checks.
8. Open MATLAB/Simulink and show the engineering validation scope.

See `docs/FINAL_REVIEW2_DEMO.md` for the exact speaking flow.

## Current prototype scope

The demonstration uses a synthetic hackathon dataset and a 1-hour Review 2 MVP time step. The dashboard reports model outputs, not measured factory savings. Physical machine actuation through PLC/EMS/VFD hardware is not implemented in the prototype.

## Engineering roadmap

- 15-minute rolling MPC
- Forecast uncertainty bands
- Battery degradation model
- Thermal / compressed-air state models
- Monte-Carlo robustness analysis
- Cost / CO2 / peak Pareto analysis
- Retrofit sizing and payback optimization
