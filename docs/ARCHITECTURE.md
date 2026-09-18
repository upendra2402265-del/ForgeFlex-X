# ForgeFlex X — Architecture

## Decision loop

```text
           HISTORICAL DATA
                  |
                  v
          ┌───────────────┐
          │ AI FORECAST   │
          │ PV + LOAD     │
          └───────┬───────┘
                  |
                  v
          ┌───────────────┐
          │    FlexDNA    │
          │ Power / time  │
          │ window / type │
          └───────┬───────┘
                  |
                  v
          ┌───────────────┐
          │     MILP      │
          │ Grid / BESS / │
          │ flexible load │
          └───────┬───────┘
                  |
                  v
            24-HOUR PLAN
                  |
          ┌───────┴─────────┐
          v                 v
 NUMERICAL DIGITAL      MATLAB/SIMULINK
      TWIN                 TWIN
          |                 |
          └───────┬─────────┘
                  v
             VALIDATION
                  |
                  v
          COMMAND CENTER
```

## Separation of responsibilities

**Forecast layer:** predicts renewable generation and factory demand from weather/time features.

**Optimization layer:** decides the grid import, battery charge/discharge, curtailment and start times of flexible processes.

**Digital twin:** independently recomputes energy balance, battery SOC and constraint checks from the chosen schedule.

**Dashboard:** visualizes decisions and validation, rather than being the source of truth.

## MILP flexibility logic

Each flexible process has a binary start decision. Exactly one legal start is selected and the required duration is converted into a contiguous ON interval. This is stronger than allowing fragmented one-hour ON selections.

## Energy balance

```text
Grid + Battery Discharge + PV
- Curtailment - Battery Charge
- Fixed Load - Flexible Load = 0
```
