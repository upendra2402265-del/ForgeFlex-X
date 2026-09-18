from __future__ import annotations

import pandas as pd

def _baseline_flex_schedule(forecast: pd.DataFrame, flex_loads: pd.DataFrame) -> pd.Series:
    base = pd.Series(0.0, index=forecast.index)
    for _, row in flex_loads.iterrows():
        valid = [i for i, hour in enumerate(forecast["timestamp"].dt.hour)
                 if int(row["start_h"]) <= hour < int(row["end_h"])]
        chosen = valid[: int(row["duration_h"])]
        for i in chosen:
            base.iloc[i] += float(row["power_kw"])
    return base

def calculate_kpis(forecast: pd.DataFrame, optimized: pd.DataFrame, flex_loads: pd.DataFrame | None = None) -> dict[str, float]:
    flex_loads = flex_loads if flex_loads is not None else pd.DataFrame(columns=["start_h", "end_h", "duration_h", "power_kw"])
    load = float(forecast["load_forecast_kw"].sum() + _baseline_flex_schedule(forecast, flex_loads).sum())
    pv = float(forecast["pv_forecast_kw"].sum())
    grid = float(optimized["grid_kw"].sum())
    curtailed = float(optimized["curtailment_kw"].sum())
    cost = float((optimized["grid_kw"] * optimized["tariff_rs_per_kwh"]).sum())
    baseline_flex = _baseline_flex_schedule(forecast, flex_loads)
    baseline_grid = (forecast["load_forecast_kw"] + baseline_flex - forecast["pv_forecast_kw"]).clip(lower=0)
    baseline_cost = float((baseline_grid * optimized["tariff_rs_per_kwh"]).sum())
    return {
        "optimized_cost_rs": cost,
        "baseline_cost_rs": baseline_cost,
        "cost_reduction_pct": 100 * (baseline_cost - cost) / max(baseline_cost, 1),
        "grid_peak_kw": float(optimized["grid_kw"].max()),
        "baseline_peak_kw": float(baseline_grid.max()),
        "peak_reduction_pct": 100 * (baseline_grid.max() - optimized["grid_kw"].max()) / max(baseline_grid.max(), 1),
        "renewable_utilization_pct": 100 * (pv - curtailed) / max(pv, 1),
        "curtailment_pct": 100 * curtailed / max(pv, 1),
        "grid_energy_kwh": grid,
        "pv_energy_kwh": pv,
        "curtailed_kwh": curtailed,
        "load_energy_kwh": load,
    }
