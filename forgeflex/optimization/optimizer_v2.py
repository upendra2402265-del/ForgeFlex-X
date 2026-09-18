from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


@dataclass(frozen=True)
class BatteryParamsV2:
    capacity_kwh: float = 500.0
    power_kw: float = 250.0
    initial_soc: float = 0.60
    min_soc: float = 0.20
    max_soc: float = 0.95
    charge_eff: float = 0.95
    discharge_eff: float = 0.95
    degradation_rs_per_kwh: float = 0.15


def optimize_day_v2(
    forecast: pd.DataFrame,
    flex_loads: pd.DataFrame,
    battery: BatteryParamsV2 | None = None,
    peak_penalty: float = 3.0,
    curtail_penalty: float = 0.5,
    carbon_weight: float = 0.8,
    final_soc_reserve: bool = True,
    grid_limit_kw: float = 2000.0,
    time_limit_s: float = 20.0,
) -> pd.DataFrame:
    """Solve the 24-hour industrial energy orchestration MILP.

    Decision variables include grid import, battery charge/discharge/SOC,
    renewable curtailment, a peak-import variable, and binary *start* variables
    for flexible processes. Start variables make each flexible process operate
    as one contiguous run of its required duration inside its allowed window.
    """
    if battery is None:
        battery = BatteryParamsV2()

    required = ["timestamp", "pv_forecast_kw", "load_forecast_kw", "tariff_rs_per_kwh"]
    missing = [c for c in required if c not in forecast.columns]
    if missing:
        raise ValueError(f"Forecast missing columns: {missing}")

    T = len(forecast)
    L = len(flex_loads)
    if T == 0:
        raise ValueError("Forecast is empty")
    if grid_limit_kw <= 0:
        raise ValueError("grid_limit_kw must be positive")

    # Variable groups.
    groups = [
        ("grid", T),
        ("charge", T),
        ("discharge", T),
        ("soc", T + 1),
        ("curtail", T),
        ("peak", 1),
        ("flex_start", L * T),
        ("battery_charge_mode", T),
    ]

    offsets: dict[str, np.ndarray] = {}
    cursor = 0
    for name, size in groups:
        offsets[name] = np.arange(cursor, cursor + size)
        cursor += size
    n = cursor

    tariff = forecast["tariff_rs_per_kwh"].to_numpy(float)
    carbon = forecast.get(
        "grid_carbon_kg_per_kwh",
        pd.Series(np.full(T, 0.6), index=forecast.index),
    ).to_numpy(float)
    pv = forecast["pv_forecast_kw"].to_numpy(float)

    # Objective is a weighted sum of economic / operational terms.
    c = np.zeros(n)
    c[offsets["grid"]] = tariff + carbon_weight * carbon
    c[offsets["charge"]] = 0.02
    c[offsets["discharge"]] = battery.degradation_rs_per_kwh
    c[offsets["curtail"]] = curtail_penalty
    c[offsets["peak"]] = peak_penalty

    integrality = np.zeros(n)
    integrality[offsets["flex_start"]] = 1
    integrality[offsets["battery_charge_mode"]] = 1

    lb = np.zeros(n)
    ub = np.full(n, np.inf)
    ub[offsets["grid"]] = grid_limit_kw
    ub[offsets["charge"]] = battery.power_kw
    ub[offsets["discharge"]] = battery.power_kw
    lb[offsets["soc"]] = battery.min_soc * battery.capacity_kwh
    ub[offsets["soc"]] = battery.max_soc * battery.capacity_kwh
    ub[offsets["curtail"]] = pv
    ub[offsets["peak"]] = grid_limit_kw
    ub[offsets["flex_start"]] = 1
    ub[offsets["battery_charge_mode"]] = 1

    # Pre-compute legal contiguous start positions for each flexible process.
    candidate_starts: list[list[int]] = []
    for _, row in flex_loads.iterrows():
        start_h = int(row["start_h"])
        end_h = int(row["end_h"])
        duration = int(row["duration_h"])
        starts = []
        for t_idx, ts in enumerate(forecast["timestamp"]):
            h = int(ts.hour)
            if start_h <= h and h + duration <= end_h and t_idx + duration <= T:
                # Ensure all hours of the contiguous run are in the window.
                hours = [int(forecast.iloc[j]["timestamp"].hour) for j in range(t_idx, t_idx + duration)]
                if all(start_h <= hh < end_h for hh in hours):
                    starts.append(t_idx)
        if not starts:
            raise RuntimeError(
                f"No feasible contiguous start time for flexible process '{row['name']}'."
            )
        candidate_starts.append(starts)

    # Rows:
    # 1) energy balance T
    # 2) initial SOC 1
    # 3) SOC dynamics T
    # 4) grid <= peak T
    # 5) exactly one start per flexible process L
    # 6) battery charge/discharge exclusivity 2T
    # 7) final SOC reserve 1
    rows = T + 1 + T + T + L + 2 * T + (1 if final_soc_reserve else 0)
    A = lil_matrix((rows, n))
    lo = np.full(rows, -np.inf)
    hi = np.full(rows, np.inf)
    r = 0

    # Energy balance:
    # grid + discharge + PV - curtail - charge - fixed - flexible = 0
    for t_idx in range(T):
        A[r, offsets["grid"][t_idx]] = 1
        A[r, offsets["discharge"][t_idx]] = 1
        A[r, offsets["curtail"][t_idx]] = -1
        A[r, offsets["charge"][t_idx]] = -1

        for i, row in flex_loads.iterrows():
            duration = int(row["duration_h"])
            for s in candidate_starts[i]:
                if s <= t_idx < s + duration:
                    A[r, offsets["flex_start"][i * T + s]] = -float(row["power_kw"])

        lo[r] = hi[r] = float(
            forecast.iloc[t_idx]["load_forecast_kw"] - forecast.iloc[t_idx]["pv_forecast_kw"]
        )
        r += 1

    # Initial SOC.
    A[r, offsets["soc"][0]] = 1
    lo[r] = hi[r] = battery.initial_soc * battery.capacity_kwh
    r += 1

    # Battery state transition.
    for t_idx in range(T):
        A[r, offsets["soc"][t_idx + 1]] = 1
        A[r, offsets["soc"][t_idx]] = -1
        A[r, offsets["charge"][t_idx]] = -battery.charge_eff
        A[r, offsets["discharge"][t_idx]] = 1.0 / battery.discharge_eff
        lo[r] = hi[r] = 0
        r += 1

    # Peak demand definition.
    for t_idx in range(T):
        A[r, offsets["grid"][t_idx]] = 1
        A[r, offsets["peak"][0]] = -1
        hi[r] = 0
        r += 1

    # Exactly one contiguous start for each flexible process.
    for i, starts in enumerate(candidate_starts):
        for s in starts:
            A[r, offsets["flex_start"][i * T + s]] = 1
        lo[r] = hi[r] = 1
        r += 1

        # Explicitly disable impossible start variables through bounds.
        for s in range(T):
            if s not in starts:
                ub[offsets["flex_start"][i * T + s]] = 0

    # Charge/discharge exclusivity.
    for t_idx in range(T):
        # Charge <= Pmax * mode
        A[r, offsets["charge"][t_idx]] = 1
        A[r, offsets["battery_charge_mode"][t_idx]] = -battery.power_kw
        hi[r] = 0
        r += 1

        # Discharge <= Pmax * (1 - mode)
        A[r, offsets["discharge"][t_idx]] = 1
        A[r, offsets["battery_charge_mode"][t_idx]] = battery.power_kw
        hi[r] = battery.power_kw
        r += 1

    if final_soc_reserve:
        A[r, offsets["soc"][T]] = 1
        lo[r] = battery.initial_soc * battery.capacity_kwh
        r += 1

    assert r == rows

    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=LinearConstraint(A.tocsr(), lo, hi),
        options={"time_limit": time_limit_s},
    )
    if not result.success:
        raise RuntimeError(f"Review-2 MILP failed: {result.message}")

    x = result.x
    out = forecast[["timestamp", "pv_forecast_kw", "load_forecast_kw", "tariff_rs_per_kwh"]].copy()
    out["grid_kw"] = x[offsets["grid"]]
    out["charge_kw"] = x[offsets["charge"]]
    out["discharge_kw"] = x[offsets["discharge"]]
    out["soc_kwh"] = x[offsets["soc"][1:]]
    out["curtailment_kw"] = x[offsets["curtail"]]

    # Convert start binaries into one contiguous on/off schedule per machine.
    for i, row in flex_loads.iterrows():
        on = np.zeros(T)
        for s in candidate_starts[i]:
            started = x[offsets["flex_start"][i * T + s]]
            if started > 0.5:
                d = int(row["duration_h"])
                on[s:s + d] = 1
        out[f"{row['name']}_on"] = on

    out.attrs["objective_value"] = float(result.fun)
    out.attrs["solver_success"] = bool(result.success)
    out.attrs["solver_message"] = str(result.message)
    out.attrs["grid_limit_kw"] = float(grid_limit_kw)
    return out
