from pathlib import Path
import pandas as pd
from forgeflex.models.forecasting import ForecastModels
from forgeflex.optimization.optimizer_v2 import BatteryParamsV2, optimize_day_v2
from forgeflex.simulation.digital_twin import TwinConfig, simulate_day

ROOT = Path(__file__).resolve().parents[1]


def make_case():
    hist = pd.read_csv(ROOT / 'data' / 'historical_energy.csv', parse_dates=['timestamp'])
    flex = pd.read_csv(ROOT / 'data' / 'flexible_loads.csv')
    models = ForecastModels()
    models.fit(hist)
    day = hist.tail(24).copy().reset_index(drop=True)
    future = day[['timestamp','hour','day_of_week','temperature_c','cloud_factor','tariff_rs_per_kwh','grid_carbon_kg_per_kwh']].copy()
    forecast = models.predict(future)
    return forecast, flex


def test_optimizer_and_twin_pass():
    forecast, flex = make_case()
    battery = BatteryParamsV2()
    optimized = optimize_day_v2(forecast, flex, battery=battery, grid_limit_kw=900)
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
            grid_limit_kw=900,
        ),
    )
    assert len(optimized) == 24
    assert validation['validation_pass']
    assert validation['max_balance_residual_kw'] < 1e-5
