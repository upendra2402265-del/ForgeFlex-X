from __future__ import annotations
import pandas as pd

def apply_scenario(df: pd.DataFrame, name: str) -> pd.DataFrame:
    out = df.copy()
    if name == "Cloudy Day":
        out["pv_generation_kw"] *= 0.60
    elif name == "High Production":
        out["factory_load_kw"] *= 1.25
        out["production_index"] *= 1.25
    elif name == "High Tariff":
        out["tariff_rs_per_kwh"] *= 1.60
    elif name == "Low Solar":
        out["pv_generation_kw"] *= 0.70
    elif name == "Battery Degraded":
        pass  # Battery parameter is adjusted in the caller.
    return out
