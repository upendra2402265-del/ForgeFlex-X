# ForgeFlex X — Review 2 Engineering Specification

## Problem alignment

SU-01 asks for intelligent energy orchestration across renewable generation, industrial loads, battery storage and grid consumption while considering energy cost, peak demand, renewable curtailment and production constraints.

## Factory model

- PV nominal capacity: 700 kW in the baseline dataset
- BESS: 500 kWh nominal, 250 kW bidirectional power limit
- Initial SOC: 60%
- SOC limits: 20–95%
- Charge efficiency: 95%
- Discharge efficiency: 95%
- Time step: 1 h for the hackathon MVP

## Flexible processes

| Process | Power | Required duration | Operating window |
|---|---:|---:|---|
| Air Compressor | 150 kW | 2 h | 09:00–16:00 |
| Chiller | 110 kW | 3 h | 10:00–17:00 |
| Water Pump | 75 kW | 2 h | 08:00–18:00 |

## MILP formulation

Decision variables:

- Grid import `P_grid[t]`
- Battery charge `P_charge[t]`
- Battery discharge `P_discharge[t]`
- Battery state `SOC[t]`
- Renewable curtailment `P_curtail[t]`
- Grid peak variable `P_peak`
- Flexible-process start binaries `z[i,t]`
- Battery charge/discharge mode binary `y[t]`

The flexible-process binaries represent **contiguous start events**, so a process required for `d` hours runs for one uninterrupted block inside its operating window.

## Objective

A weighted sum of:

- grid energy cost
- grid peak penalty
- optional grid-carbon term
- battery degradation proxy
- battery charge activity penalty
- renewable-curtailment penalty

The weights are tuning parameters.

## Hard constraints

- Energy balance at every hour
- SOC lower/upper bounds
- Battery charge/discharge power limit
- Charge/discharge exclusivity
- Grid import hard limit
- Exactly one start event per flexible process
- Flexible process contiguous run duration
- Flexible process operating window
- Final SOC reserve at least equal to initial SOC

## Digital twin validation

The numerical twin computes:

```text
P_grid + P_discharge + P_PV
- P_curtail - P_charge
- P_fixed - P_flexible
= balance residual
```

It also validates SOC bounds, grid limits, battery power limits, flexible-process duration and operating-window constraints.

## Simulink layer

Python remains the source of truth for the optimized schedule. MATLAB/Simulink consumes the resulting setpoints as a separate engineering validation layer.

## Future technical layers

1. 15-minute rolling MPC
2. Forecast uncertainty
3. Battery degradation model
4. Thermal storage
5. Compressed-air state model
6. Monte-Carlo robustness
7. Pareto frontier
8. Retrofit sizing/payback optimization
