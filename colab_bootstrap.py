# Paste into a Google Colab notebook after uploading the forgeflex_x folder or cloning the GitHub repo.
# This script creates the experimental environment and runs the first forecast validation.

!pip -q install numpy pandas scipy scikit-learn plotly openpyxl joblib ortools

import sys
from pathlib import Path
sys.path.append('/content/forgeflex_x')

from forgeflex.core.data_generator import save_demo_data
a, b = save_demo_data('/content/forgeflex_x/data', days=90)
print(a, b)

import pandas as pd
from forgeflex.models.forecasting import ForecastModels
hist = pd.read_csv('/content/forgeflex_x/data/historical_energy.csv', parse_dates=['timestamp'])
model = ForecastModels()
metrics = model.fit(hist)
metrics
