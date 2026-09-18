from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class FactoryConfig:
    pv_kw: float = 700.0
    battery_kwh: float = 500.0
    battery_power_kw: float = 250.0
    initial_soc: float = 0.60
    min_soc: float = 0.20
    max_soc: float = 0.95
    charge_eff: float = 0.95
    discharge_eff: float = 0.95

FLEX_LOADS = [
    {"name": "Air Compressor", "power_kw": 150, "duration_h": 2, "start_h": 9, "end_h": 16, "critical": 0},
    {"name": "Chiller", "power_kw": 110, "duration_h": 3, "start_h": 10, "end_h": 17, "critical": 0},
    {"name": "Water Pump", "power_kw": 75, "duration_h": 2, "start_h": 8, "end_h": 18, "critical": 0},
]

CRITICAL_PROFILES = [
    {"name": "CNC Line", "power_kw": 240, "start_h": 8, "end_h": 18},
    {"name": "Production Furnace", "power_kw": 300, "start_h": 13, "end_h": 16},
    {"name": "HVAC Base", "power_kw": 90, "start_h": 0, "end_h": 24},
]

def _solar_shape(hour: np.ndarray) -> np.ndarray:
    # Smooth daytime curve, zero overnight.
    x = (hour - 6) / 12 * np.pi
    return np.clip(np.sin(x), 0, None) ** 1.7

def generate_history(days: int = 90, seed: int = 42, config: FactoryConfig | None = None) -> pd.DataFrame:
    config = config or FactoryConfig()
    rng = np.random.default_rng(seed)
    n = days * 24
    ts = pd.date_range("2026-01-01", periods=n, freq="h")
    hour = ts.hour.to_numpy()
    dow = ts.dayofweek.to_numpy()

    cloud = np.clip(rng.normal(0.86, 0.12, n), 0.30, 1.10)
    seasonal = 0.95 + 0.08 * np.sin(2 * np.pi * (ts.dayofyear.to_numpy() - 30) / 365)
    pv = config.pv_kw * _solar_shape(hour) * cloud * seasonal
    temp = 25 + 5 * np.sin(2 * np.pi * (hour - 14) / 24) + rng.normal(0, 1.5, n)

    weekday_factor = np.where(dow < 5, 1.0, 0.55)
    base = 170 + 50 * weekday_factor
    daytime = 230 * np.where((hour >= 8) & (hour < 18), 1.0, 0.25)
    shift = 70 * np.where((hour >= 13) & (hour < 16), 1.0, 0.0)
    load = (base + daytime + shift + 15 * np.sin(2*np.pi*hour/24) + rng.normal(0, 18, n)) * weekday_factor
    production = np.clip((load - 150) / 50 + rng.normal(0, 0.10, n), 0, None)

    tariff = np.full(n, 7.0)
    tariff[(hour >= 6) & (hour < 10)] = 6.2
    tariff[(hour >= 10) & (hour < 18)] = 8.5
    tariff[(hour >= 18) & (hour < 22)] = 13.0
    tariff[(hour >= 22) | (hour < 6)] = 5.5

    carbon = np.where((hour >= 10) & (hour < 16), 0.45, 0.62) + rng.normal(0, 0.03, n)

    df = pd.DataFrame({
        "timestamp": ts,
        "hour": hour,
        "day_of_week": dow,
        "temperature_c": temp,
        "cloud_factor": cloud,
        "pv_generation_kw": np.clip(pv, 0, None),
        "factory_load_kw": np.clip(load, 100, None),
        "production_index": production,
        "tariff_rs_per_kwh": tariff,
        "grid_carbon_kg_per_kwh": np.clip(carbon, 0.25, 0.9),
    })
    return df

def save_demo_data(out_dir: str | Path = "data", days: int = 90, seed: int = 42) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    hist = generate_history(days=days, seed=seed)
    hist_path = out / "historical_energy.csv"
    hist.to_csv(hist_path, index=False)
    flex_path = out / "flexible_loads.csv"
    pd.DataFrame(FLEX_LOADS).to_csv(flex_path, index=False)
    return hist_path, flex_path

if __name__ == "__main__":
    print(save_demo_data())
