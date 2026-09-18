from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TwinConfig:
    battery_capacity_kwh: float = 500.0
    initial_soc: float = 0.60
    min_soc: float = 0.20
    max_soc: float = 0.95
    charge_eff: float = 0.95
    discharge_eff: float = 0.95
    battery_power_limit_kw: float = 250.0
    grid_limit_kw: float = 2000.0
    balance_tolerance_kw: float = 1e-5


def simulate_day(
    forecast: pd.DataFrame,
    optimized: pd.DataFrame,
    flex_loads: pd.DataFrame,
    config: TwinConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, float | int | bool]]:
    """Numerical digital-twin validation of the optimizer schedule."""
    config = config or TwinConfig()

    T = len(forecast)
    if len(optimized) != T:
        raise ValueError("Forecast and optimized schedule lengths differ")

    base = forecast["load_forecast_kw"].to_numpy(float)
    pv = forecast["pv_forecast_kw"].to_numpy(float)
    grid = optimized["grid_kw"].to_numpy(float)
    charge = optimized["charge_kw"].to_numpy(float)
    discharge = optimized["discharge_kw"].to_numpy(float)
    curtail = optimized["curtailment_kw"].to_numpy(float)

    flex_total = np.zeros(T)
    flex_checks: dict[str, int] = {}
    for _, row in flex_loads.iterrows():
        key = f"{row['name']}_on"
        if key not in optimized.columns:
            raise ValueError(f"Missing flexible schedule column: {key}")
        on = optimized[key].to_numpy(float)
        flex_total += float(row["power_kw"]) * on
        flex_checks[str(row["name"])] = int(round(on.sum()))

    total_load = base + flex_total
    balance_residual = grid + discharge + pv - curtail - charge - total_load

    soc = np.zeros(T + 1)
    soc[0] = config.initial_soc * config.battery_capacity_kwh
    for t in range(T):
        soc[t + 1] = (
            soc[t]
            + config.charge_eff * charge[t]
            - discharge[t] / config.discharge_eff
        )

    violations: list[str] = []
    if np.any(np.abs(balance_residual) > config.balance_tolerance_kw):
        violations.append("energy_balance")
    if np.any(soc[1:] < config.min_soc * config.battery_capacity_kwh - 1e-6):
        violations.append("soc_lower_bound")
    if np.any(soc[1:] > config.max_soc * config.battery_capacity_kwh + 1e-6):
        violations.append("soc_upper_bound")
    if np.any(charge > config.battery_power_limit_kw + 1e-6):
        violations.append("charge_power_limit")
    if np.any(discharge > config.battery_power_limit_kw + 1e-6):
        violations.append("discharge_power_limit")
    if np.any(grid > config.grid_limit_kw + 1e-6):
        violations.append("grid_limit")
    if soc[-1] < soc[0] - 1e-6:
        violations.append("final_soc_reserve")

    for _, row in flex_loads.iterrows():
        name = str(row["name"])
        expected = int(row["duration_h"])
        if flex_checks[name] != expected:
            violations.append(f"flex_duration:{name}")
        on = optimized[f"{row['name']}_on"].to_numpy(float)
        for t, ts in enumerate(forecast["timestamp"]):
            hour = int(ts.hour)
            valid = int(row["start_h"]) <= hour < int(row["end_h"])
            if not valid and on[t] > 1e-6:
                violations.append(f"flex_window:{name}")
                break

    twin = optimized.copy()
    twin["flex_total_kw"] = flex_total
    twin["total_load_kw"] = total_load
    twin["soc_twin_kwh"] = soc[1:]
    twin["balance_residual_kw"] = balance_residual
    twin["grid_limit_margin_kw"] = config.grid_limit_kw - grid

    result = {
        "validation_pass": len(violations) == 0,
        "violation_count": len(violations),
        "violations": ";".join(violations),
        "max_balance_residual_kw": float(np.max(np.abs(balance_residual))),
        "min_soc_kwh": float(np.min(soc)),
        "max_soc_kwh": float(np.max(soc)),
        "final_soc_kwh": float(soc[-1]),
        "grid_peak_kw": float(np.max(grid)),
        "total_grid_kwh": float(np.sum(grid)),
        "total_curtailment_kwh": float(np.sum(curtail)),
        "production_constraint_violations": 0 if len(violations) == 0 else 1,
    }
    return twin, result
