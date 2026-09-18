from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

@dataclass(frozen=True)
class BatteryParams:
    capacity_kwh: float = 500.0
    power_kw: float = 250.0
    initial_soc: float = 0.60
    min_soc: float = 0.20
    max_soc: float = 0.95
    charge_eff: float = 0.95
    discharge_eff: float = 0.95
    degradation_rs_per_kwh: float = 0.15


def optimize_day(forecast: pd.DataFrame, flex_loads: pd.DataFrame, battery: BatteryParams | None = None,
                 peak_penalty: float = 3.0, curtail_penalty: float = 0.5,
                 carbon_weight: float = 0.8) -> pd.DataFrame:
    battery = battery or BatteryParams()
    T = len(forecast)
    L = len(flex_loads)

    # Variable groups: grid(T), charge(T), discharge(T), soc(T+1), curtail(T), peak(1), flex_binary(L*T)
    offsets = {}
    cursor = 0
    for name, size in [
        ("grid", T), ("charge", T), ("discharge", T), ("soc", T + 1), ("curtail", T), ("peak", 1), ("flex", L*T)
    ]:
        offsets[name] = np.arange(cursor, cursor + size)
        cursor += size
    n = cursor

    c = np.zeros(n)
    tariff = forecast["tariff_rs_per_kwh"].to_numpy(float)
    carbon = forecast.get("grid_carbon_kg_per_kwh", pd.Series(np.full(T, 0.6))).to_numpy(float)
    c[offsets["grid"]] = tariff + carbon_weight * carbon
    c[offsets["charge"]] = 0.02
    c[offsets["discharge"]] = battery.degradation_rs_per_kwh
    c[offsets["curtail"]] = curtail_penalty
    c[offsets["peak"]] = peak_penalty

    integrality = np.zeros(n)
    integrality[offsets["flex"]] = 1

    lb = np.zeros(n)
    ub = np.full(n, np.inf)
    ub[offsets["grid"]] = 2000
    ub[offsets["charge"]] = battery.power_kw
    ub[offsets["discharge"]] = battery.power_kw
    ub[offsets["soc"]] = battery.max_soc * battery.capacity_kwh
    lb[offsets["soc"]] = battery.min_soc * battery.capacity_kwh
    ub[offsets["curtail"]] = forecast["pv_forecast_kw"].to_numpy(float)
    ub[offsets["peak"]] = 2000
    ub[offsets["flex"]] = 1

    A = lil_matrix((2*T + 1 + T + 1 + L, n))
    lower = np.full(2*T + 1 + T + 1 + L, -np.inf)
    upper = np.full(2*T + 1 + T + 1 + L, np.inf)
    row = 0

    # Energy balance: grid + discharge + PV - curtail = base load + flex + charge
    for t in range(T):
        A[row, offsets["grid"][t]] = 1
        A[row, offsets["discharge"][t]] = 1
        A[row, offsets["curtail"][t]] = -1
        A[row, offsets["charge"][t]] = -1
        for i in range(L):
            A[row, offsets["flex"][i*T + t]] = -flex_loads.iloc[i]["power_kw"]
        rhs = forecast.iloc[t]["load_forecast_kw"] - forecast.iloc[t]["pv_forecast_kw"]
        lower[row] = upper[row] = rhs
        row += 1

    # SOC dynamics in energy units.
    A[row, offsets["soc"][0]] = 1
    lower[row] = upper[row] = battery.initial_soc * battery.capacity_kwh
    row += 1
    for t in range(T):
        A[row, offsets["soc"][t+1]] = 1
        A[row, offsets["soc"][t]] = -1
        A[row, offsets["charge"][t]] = -battery.charge_eff
        A[row, offsets["discharge"][t]] = 1.0 / battery.discharge_eff
        lower[row] = upper[row] = 0
        row += 1

    # Grid <= peak
    for t in range(T):
        A[row, offsets["grid"][t]] = 1
        A[row, offsets["peak"][0]] = -1
        upper[row] = 0
        row += 1

    # Each flexible load runs exactly duration hours inside its window.
    for i in range(L):
        valid = [t for t in range(T) if int(flex_loads.iloc[i]["start_h"]) <= t < int(flex_loads.iloc[i]["end_h"])]
        for t in range(T):
            if t not in valid:
                ub[offsets["flex"][i*T + t]] = 0
        for t in valid:
            A[row, offsets["flex"][i*T+t]] = 1
        lower[row] = upper[row] = float(flex_loads.iloc[i]["duration_h"])
        row += 1

    # Final SOC not below initial SOC reserve.
    A[row, offsets["soc"][T]] = 1
    lower[row] = battery.initial_soc * battery.capacity_kwh
    row += 1

    result = milp(c=c, integrality=integrality, bounds=Bounds(lb, ub),
                  constraints=LinearConstraint(A.tocsr(), lower, upper),
                  options={"time_limit": 20})
    if not result.success:
        raise RuntimeError(f"Optimization failed: {result.message}")

    x = result.x
    out = forecast[["timestamp", "pv_forecast_kw", "load_forecast_kw", "tariff_rs_per_kwh"]].copy()
    out["grid_kw"] = x[offsets["grid"]]
    out["charge_kw"] = x[offsets["charge"]]
    out["discharge_kw"] = x[offsets["discharge"]]
    out["soc_kwh"] = x[offsets["soc"][1:]]
    out["curtailment_kw"] = x[offsets["curtail"]]
    for i, row_data in flex_loads.iterrows():
        out[f"{row_data['name']}_on"] = x[offsets["flex"][i*T:(i+1)*T]]
    return out
