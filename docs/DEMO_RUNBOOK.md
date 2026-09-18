# ForgeFlex X — Review 2 Demo Runbook

## 3-minute live flow

### 0:00 — Problem

“Renewable generation is variable while industrial production must remain reliable. ForgeFlex coordinates PV, battery, grid and flexible processes instead of treating factory load as one fixed block.”

### 0:20 — Architecture

Point to:

`Forecast → FlexDNA → MILP → Schedule → Digital Twin`

### 0:40 — Normal Day

Click **EXECUTE 24-HOUR OPTIMIZATION**.

Show the dispatch chart and machine-level FlexDNA schedule.

### 1:15 — Cloudy Day

Select **Cloudy Day** and execute.

Say:

> “The renewable forecast changes, so the energy allocation changes. This is a recomputed decision, not a hard-coded animation.”

### 1:40 — High Production

Select **High Production** and execute.

Say:

> “Production demand has increased. The system must accommodate the new load while remaining within the hard operational constraints.”

### 2:00 — Grid Constrained

Select **Grid Constrained**, set a lower grid limit if needed, and execute.

Point to the validation state.

### 2:20 — Digital Twin

Open the **Digital Twin** tab.

Show:

- Battery SOC trajectory
- Energy-balance residual
- Validation matrix

Say:

> “Python generates the operating decision. The digital twin checks whether the energy accounting, battery state and process constraints remain valid.”

### 2:45 — Novelty

> “Our key idea is treating industrial process flexibility as an energy resource. We optimize energy around production, not production around energy.”

## Q&A anchors

**Why MILP?** It handles continuous decisions like grid/battery power plus binary decisions like whether a flexible process starts at a given hour.

**Are machines physically switched?** Not in this prototype. ForgeFlex generates the optimized operating schedule. A real deployment would hand these setpoints to an industrial EMS/PLC/VFD layer.

**What is Simulink doing?** It is the engineering validation layer, not the optimization solver.
