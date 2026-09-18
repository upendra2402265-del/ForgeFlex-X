from __future__ import annotations

from pathlib import Path
import json
import sys
import pandas as pd
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from forgeflex.models.forecasting import ForecastModels
from forgeflex.optimization.optimizer_v2 import BatteryParamsV2, optimize_day_v2
from forgeflex.simulation.digital_twin import TwinConfig, simulate_day
from forgeflex.analytics.metrics import calculate_kpis

DATA = ROOT / "data"
OUT = ROOT / "review2_outputs"
OUT.mkdir(exist_ok=True)


def prepare_day() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    hist = pd.read_csv(DATA / "historical_energy.csv", parse_dates=["timestamp"])
    flex = pd.read_csv(DATA / "flexible_loads.csv")
    models = ForecastModels()
    forecast_metrics = models.fit(hist)
    day = hist.tail(24).copy().reset_index(drop=True)
    future = day[[
        "timestamp", "hour", "day_of_week", "temperature_c", "cloud_factor",
        "tariff_rs_per_kwh", "grid_carbon_kg_per_kwh"
    ]].copy()
    forecast = models.predict(future)
    forecast["pv_forecast_kw"] = day["pv_generation_kw"].to_numpy()
    forecast["load_forecast_kw"] = day["factory_load_kw"].to_numpy()
    return forecast, flex, forecast_metrics


def main() -> None:
    forecast, flex, forecast_metrics = prepare_day()
    battery = BatteryParamsV2(capacity_kwh=500.0, power_kw=250.0)
    optimized = optimize_day_v2(forecast, flex, battery=battery, peak_penalty=3.0, carbon_weight=0.8)

    kpis = calculate_kpis(forecast, optimized, flex)
    twin, validation = simulate_day(
        forecast,
        optimized,
        flex,
        TwinConfig(
            battery_capacity_kwh=battery.capacity_kwh,
            initial_soc=battery.initial_soc,
            min_soc=battery.min_soc,
            max_soc=battery.max_soc,
            charge_eff=battery.charge_eff,
            discharge_eff=battery.discharge_eff,
            battery_power_limit_kw=battery.power_kw,
            grid_limit_kw=2000.0,
        ),
    )

    result = {
        "forecast_metrics": forecast_metrics,
        "kpis": kpis,
        "digital_twin": validation,
        "milp": {
            "solver": "scipy.optimize.milp",
            "battery_charge_discharge_exclusivity": True,
            "time_step_h": 1.0,
        },
    }

    optimized.to_csv(OUT / "optimized_schedule.csv", index=False)
    twin.to_csv(OUT / "digital_twin_validation.csv", index=False)
    (OUT / "review2_result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    # MATLAB/Simulink input file. Time is measured in hours from start.
    t = [float(i) for i in range(len(optimized))]
    def ts(col):
        return [[t[i], float(optimized.iloc[i][col])] for i in range(len(optimized))]

    mat = {
        "time_h": t,
        "pv_kw": ts("pv_forecast_kw"),
        "fixed_load_kw": ts("load_forecast_kw"),
        "flex_load_kw": ts("load_forecast_kw"),  # overwritten below
        "grid_kw": ts("grid_kw"),
        "charge_kw": ts("charge_kw"),
        "discharge_kw": ts("discharge_kw"),
        "curtail_kw": ts("curtailment_kw"),
        "soc_kwh": ts("soc_kwh"),
    }
    flex_total = []
    for i in range(len(optimized)):
        total = 0.0
        for _, row in flex.iterrows():
            total += float(row["power_kw"]) * float(optimized.iloc[i][f"{row['name']}_on"])
        flex_total.append([t[i], total])
    mat["flex_load_kw"] = flex_total
    savemat(OUT / "review2_simulink_inputs.mat", mat)

    print("FORGEFLEX X — REVIEW 2 PIPELINE")
    print("=" * 42)
    print(f"Forecast PV MAE:   {forecast_metrics['pv_mae_kw']:.2f} kW")
    print(f"Forecast Load MAE: {forecast_metrics['load_mae_kw']:.2f} kW")
    print(f"Optimized cost:     Rs {kpis['optimized_cost_rs']:,.2f}")
    print(f"Baseline cost:      Rs {kpis['baseline_cost_rs']:,.2f}")
    print(f"Peak grid:          {kpis['grid_peak_kw']:.2f} kW")
    print(f"Renewable use:      {kpis['renewable_utilization_pct']:.2f}%")
    print(f"Curtailment:        {kpis['curtailment_pct']:.2f}%")
    print(f"Twin validation:    {'PASS' if validation['validation_pass'] else 'CHECK'}")
    print(f"Balance residual:   {validation['max_balance_residual_kw']:.6f} kW")
    print(f"Final SOC:           {validation['final_soc_kwh']:.2f} kWh")
    print("\nOutputs written to:")
    for p in sorted(OUT.glob("*")):
        print(" -", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
