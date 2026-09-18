from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from forgeflex.models.forecasting import ForecastModels
from forgeflex.optimization.optimizer_v2 import BatteryParamsV2, optimize_day_v2
from forgeflex.simulation.digital_twin import TwinConfig, simulate_day

st.set_page_config(page_title="ForgeFlex X — Review 2", page_icon="⚡", layout="wide")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

hist = pd.read_csv(DATA / "historical_energy.csv", parse_dates=["timestamp"])
flex = pd.read_csv(DATA / "flexible_loads.csv")

st.title("⚡ ForgeFlex X — Review 2 Engineering Console")
st.caption("AI forecast → FlexDNA → MILP schedule → numerical digital twin → Simulink-ready validation inputs")

scenario = st.sidebar.selectbox("Scenario", ["Normal Day", "Cloudy Day", "High Production", "High Tariff", "Low Solar", "Battery Degraded"])
pv_capacity = st.sidebar.slider("PV capacity (kW)", 300, 1200, 700, 50)
battery_capacity = st.sidebar.slider("Battery capacity (kWh)", 100, 1500, 500, 50)
peak_penalty = st.sidebar.slider("Peak-demand penalty", 0.0, 10.0, 3.0, 0.5)
carbon_weight = st.sidebar.slider("Grid-carbon weight", 0.0, 3.0, 0.8, 0.1)
grid_limit = st.sidebar.slider("Grid limit (kW)", 400, 1200, 900, 50)
run = st.sidebar.button("⚡ EXECUTE REVIEW 2 PIPELINE", use_container_width=True)

models = ForecastModels()
forecast_metrics = models.fit(hist)
base = hist.tail(24).copy().reset_index(drop=True)
if scenario == "Cloudy Day":
    base["pv_generation_kw"] *= 0.60
elif scenario == "High Production":
    base["factory_load_kw"] *= 1.25
elif scenario == "High Tariff":
    base["tariff_rs_per_kwh"] *= 1.60
elif scenario == "Low Solar":
    base["pv_generation_kw"] *= 0.70

base["pv_generation_kw"] *= pv_capacity / 700.0
future = base[["timestamp", "hour", "day_of_week", "temperature_c", "cloud_factor", "tariff_rs_per_kwh", "grid_carbon_kg_per_kwh"]].copy()
forecast = models.predict(future)
forecast["pv_forecast_kw"] = base["pv_generation_kw"].to_numpy()
forecast["load_forecast_kw"] = base["factory_load_kw"].to_numpy()

battery = BatteryParamsV2(
    capacity_kwh=battery_capacity * (0.85 if scenario == "Battery Degraded" else 1.0),
    power_kw=min(250.0, battery_capacity / 2),
    degradation_rs_per_kwh=0.30 if scenario == "Battery Degraded" else 0.15,
)

if run or "optimized" not in st.session_state:
    try:
        st.session_state.optimized = optimize_day_v2(
            forecast,
            flex,
            battery=battery,
            peak_penalty=peak_penalty,
            carbon_weight=carbon_weight,
        )
        st.session_state.run_error = ""
    except Exception as exc:
        st.session_state.optimized = None
        st.session_state.run_error = str(exc)

optimized = st.session_state.optimized

if st.session_state.get("run_error"):
    st.error(st.session_state.run_error)
    st.stop()

if optimized is None:
    st.warning("Run the pipeline from the sidebar.")
    st.stop()

# Final validation with user-selected grid limit.
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
        grid_limit_kw=float(grid_limit),
    ),
)

cols = st.columns(6)
cols[0].metric("Grid peak", f"{validation['grid_peak_kw']:.0f} kW")
cols[1].metric("Final SOC", f"{validation['final_soc_kwh']:.0f} kWh")
cols[2].metric("Renewable use", f"{100*(forecast['pv_forecast_kw'].sum()-optimized['curtailment_kw'].sum())/max(forecast['pv_forecast_kw'].sum(),1):.1f}%")
cols[3].metric("Curtailment", f"{optimized['curtailment_kw'].sum():.0f} kWh")
cols[4].metric("Twin status", "PASS" if validation["validation_pass"] else "CHECK")
cols[5].metric("Violations", str(validation["violation_count"]))

st.subheader("1. Energy orchestration")
fig = go.Figure()
fig.add_trace(go.Scatter(x=forecast["timestamp"], y=forecast["load_forecast_kw"], name="Fixed/Critical Load"))
fig.add_trace(go.Scatter(x=forecast["timestamp"], y=twin["flex_total_kw"], name="Flexible Load"))
fig.add_trace(go.Scatter(x=forecast["timestamp"], y=forecast["pv_forecast_kw"], name="PV"))
fig.add_trace(go.Scatter(x=optimized["timestamp"], y=optimized["grid_kw"], name="Grid"))
fig.add_trace(go.Scatter(x=optimized["timestamp"], y=optimized["charge_kw"], name="Battery Charge"))
fig.add_trace(go.Scatter(x=optimized["timestamp"], y=optimized["discharge_kw"], name="Battery Discharge"))
fig.update_layout(height=470, xaxis_title="Time", yaxis_title="kW", margin=dict(l=10,r=10,t=25,b=10))
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.subheader("2. Battery digital twin")
    st.line_chart(twin.set_index("timestamp")[["soc_twin_kwh"]])
with c2:
    st.subheader("3. Energy balance residual")
    st.line_chart(twin.set_index("timestamp")[["balance_residual_kw"]])

st.subheader("4. FlexDNA schedule")
sched_cols = ["timestamp"] + [c for c in optimized.columns if c.endswith("_on")]
st.dataframe(optimized[sched_cols], use_container_width=True, hide_index=True)

st.subheader("5. Digital-twin validation")
st.json(validation)

st.subheader("6. Forecast validation")
st.json(forecast_metrics)

st.subheader("7. Simulink handoff")
st.info("The pipeline script creates review2_outputs/review2_simulink_inputs.mat. In MATLAB/Simulink, run matlab/build_forgeflex_twin.m to build and execute the engineering validation model from these setpoints.")
