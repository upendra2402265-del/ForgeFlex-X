from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURES = ["hour", "day_of_week", "temperature_c", "cloud_factor"]

class ForecastModels:
    def __init__(self) -> None:
        self.pv = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.06, max_depth=6, random_state=42)
        self.load = RandomForestRegressor(n_estimators=250, max_depth=12, random_state=42, n_jobs=-1)
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> dict[str, float]:
        X = df[FEATURES]
        y_pv = df["pv_generation_kw"]
        y_load = df["factory_load_kw"]
        split = int(len(df) * 0.8)
        self.pv.fit(X.iloc[:split], y_pv.iloc[:split])
        self.load.fit(X.iloc[:split], y_load.iloc[:split])
        pv_pred = np.clip(self.pv.predict(X.iloc[split:]), 0, None)
        load_pred = np.clip(self.load.predict(X.iloc[split:]), 0, None)
        self._fitted = True
        return {
            "pv_mae_kw": float(mean_absolute_error(y_pv.iloc[split:], pv_pred)),
            "load_mae_kw": float(mean_absolute_error(y_load.iloc[split:], load_pred)),
            "pv_rmse_kw": float(mean_squared_error(y_pv.iloc[split:], pv_pred) ** 0.5),
            "load_rmse_kw": float(mean_squared_error(y_load.iloc[split:], load_pred) ** 0.5),
        }

    def predict(self, future: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Fit the forecasting models first.")
        out = future.copy()
        out["pv_forecast_kw"] = np.clip(self.pv.predict(out[FEATURES]), 0, None)
        out["load_forecast_kw"] = np.clip(self.load.predict(out[FEATURES]), 0, None)
        return out
