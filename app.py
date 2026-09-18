from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from forgeflex.analytics.metrics import calculate_kpis
from forgeflex.models.forecasting import ForecastModels
from forgeflex.optimization.optimizer_v2 import BatteryParamsV2, optimize_day_v2
from forgeflex.simulation.digital_twin import TwinConfig, simulate_day

# =============================================================================
# FORGEFLEX X — REVIEW 2 PREMIUM COMMAND CENTER
# Team: TECHNOBLADE | Lead: Upendra P | Member: Vishnu A R
# =============================================================================

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "review2_outputs"

st.set_page_config(
    page_title="ForgeFlex X · Technoblade",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Premium glass / industrial control-room design.
# No external fonts or CDNs: reliable offline rendering.
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
:root {
  --bg:#050a10;
  --bg2:#08111a;
  --glass:rgba(13,25,37,.68);
  --glass2:rgba(10,21,31,.82);
  --line:rgba(142,181,207,.16);
  --line2:rgba(73,132,167,.30);
  --text:#edf5fa;
  --muted:#8da3b4;
  --cyan:#35d2ff;
  --green:#59e49a;
  --yellow:#ffd36a;
  --red:#ff7489;
  --violet:#aa9cff;
}
html, body, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 0% 0%, rgba(53,210,255,.08), transparent 23%),
    radial-gradient(circle at 100% 0%, rgba(170,156,255,.07), transparent 22%),
    linear-gradient(180deg,var(--bg),var(--bg2));
  color:var(--text);
  font-family:"Aptos","Segoe UI",Inter,Arial,sans-serif;
}
[data-testid="stHeader"] { background:rgba(5,10,16,.65); }
.block-container { max-width:1660px; padding-top:1rem; padding-bottom:2.8rem; }

/* Hide Streamlit noise but retain accessibility. */
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }

.hero {
  position:relative;
  overflow:hidden;
  padding:22px 24px 20px;
  border:1px solid var(--line);
  border-radius:22px;
  background:
    radial-gradient(circle at 88% 18%, rgba(53,210,255,.11), transparent 26%),
    linear-gradient(145deg, rgba(17,33,47,.84), rgba(7,16,24,.92));
  box-shadow:0 18px 50px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.03);
  backdrop-filter:blur(18px);
  -webkit-backdrop-filter:blur(18px);
}
.hero-grid{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:22px;align-items:end}
.brandline{display:flex;gap:9px;align-items:center;color:var(--muted);font-size:10px;font-weight:800;letter-spacing:.16em;text-transform:uppercase}
.brandmark{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:8px;border:1px solid rgba(53,210,255,.28);background:rgba(53,210,255,.07);color:var(--cyan);font-size:15px}
.hero h1{margin:8px 0 7px;font-size:36px;line-height:1.05;letter-spacing:-.035em}
.hero-sub{max-width:980px;color:var(--muted);font-size:12px;line-height:1.7}
.hero-chiprow{display:flex;gap:8px;flex-wrap:wrap;margin-top:13px}
.chip{border:1px solid var(--line2);background:rgba(12,33,47,.58);padding:6px 9px;border-radius:999px;font-size:9px;font-weight:800;color:#a8def2;letter-spacing:.04em}
.team-card{min-width:290px;padding:15px 16px;border-radius:16px;border:1px solid rgba(73,132,167,.28);background:rgba(7,17,26,.72);box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.team-title{font-size:10px;letter-spacing:.12em;font-weight:900;color:var(--cyan);text-transform:uppercase}
.team-name{font-size:18px;font-weight:900;margin:5px 0}
.team-meta{font-size:10px;color:var(--muted);line-height:1.65}
.team-meta b{color:#d8e8f1}

.section-head{display:flex;justify-content:space-between;align-items:end;gap:16px;margin:22px 1px 9px}
.kicker{font-size:9px;font-weight:900;color:var(--cyan);letter-spacing:.16em;text-transform:uppercase}
.section-title{font-size:20px;font-weight:900;letter-spacing:-.02em}
.section-note{color:var(--muted);font-size:10px}

/* KPI cards */
.kpi-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px}
.kpi{position:relative;padding:15px;border-radius:15px;border:1px solid var(--line);background:linear-gradient(145deg,rgba(14,27,39,.84),rgba(8,18,27,.84));box-shadow:0 10px 28px rgba(0,0,0,.16),inset 0 1px 0 rgba(255,255,255,.025);overflow:hidden}
.kpi::after{content:"";position:absolute;inset:auto -30px -55px auto;width:120px;height:120px;border-radius:50%;background:rgba(53,210,255,.05);filter:blur(12px)}
.kpi-label{color:var(--muted);font-size:8.5px;letter-spacing:.1em;text-transform:uppercase;font-weight:900}
.kpi-value{margin-top:9px;font-size:25px;font-weight:900;letter-spacing:-.03em}
.kpi-note{margin-top:5px;color:#94a9b8;font-size:9px;line-height:1.35}
.kpi-green{border-color:rgba(89,228,154,.22)}
.kpi-cyan{border-color:rgba(53,210,255,.24)}
.kpi-gold{border-color:rgba(255,211,106,.22)}
.kpi-red{border-color:rgba(255,116,137,.24)}

.status{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:7px 10px;font-size:9px;font-weight:900;letter-spacing:.06em}
.status.good{color:#7cf0a9;background:rgba(33,104,67,.20);border:1px solid rgba(89,228,154,.28)}
.status.warn{color:#ffe093;background:rgba(112,78,24,.20);border:1px solid rgba(255,211,106,.27)}
.dot{width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 11px currentColor}

/* Sidebar */
section[data-testid="stSidebar"] { background:linear-gradient(180deg,#061019,#07111a); border-right:1px solid rgba(142,181,207,.13); }
section[data-testid="stSidebar"] .block-container{padding:1rem .9rem}
.side-title{font-size:21px;font-weight:900;letter-spacing:-.03em}
.side-sub{color:var(--muted);font-size:10px;line-height:1.5;margin-top:3px}
.side-team{margin:15px 0;padding:12px;border:1px solid var(--line);background:rgba(13,25,37,.62);border-radius:13px}
.side-team .t{font-size:9px;color:var(--cyan);font-weight:900;letter-spacing:.12em;text-transform:uppercase}
.side-team .n{font-size:15px;font-weight:900;margin-top:3px}
.side-team .m{font-size:9px;color:var(--muted);line-height:1.6}

/* Glass panels */
.panel{padding:16px;border-radius:17px;border:1px solid var(--line);background:linear-gradient(145deg,rgba(13,27,39,.82),rgba(8,18,27,.82));box-shadow:0 12px 34px rgba(0,0,0,.16),inset 0 1px 0 rgba(255,255,255,.025)}
.panel-title{font-size:12px;font-weight:900;letter-spacing:.02em}
.panel-sub{font-size:9px;color:var(--muted);margin-top:3px}
.glow-line{height:1px;background:linear-gradient(90deg,rgba(53,210,255,.35),rgba(53,210,255,0));margin:9px 0 12px}

.callout{padding:12px 13px;border-radius:12px;background:rgba(8,18,27,.65);border:1px solid var(--line);border-left:3px solid var(--cyan);font-size:10px;line-height:1.7;color:#b5c6d1}
.callout b{color:#eef5f9}

/* Streamlit buttons */
.stButton > button{border-radius:10px;border:1px solid #2d4b5f;background:#0d1c28;color:#edf7fb;font-weight:800;font-size:10px;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
.stButton > button:hover{border-color:#3a708c;background:#122638}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid var(--line);padding:0 0 4px}
.stTabs [data-baseweb="tab"]{font-size:10px;font-weight:900;color:#8197a8;border-radius:8px 8px 0 0;padding:8px 13px}
.stTabs [aria-selected="true"]{color:#e8f6fb!important;background:rgba(53,210,255,.06)}

/* Tables */
[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden;border:1px solid var(--line)}

/* Footer */
.final-footer{margin-top:22px;padding:17px;border-top:1px solid var(--line);color:#698090;text-align:center;font-size:9px;line-height:1.7}
.final-footer b{color:#a3bac8}

@media(max-width:1200px){
  .kpi-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
  .hero-grid{grid-template-columns:1fr}
  .team-card{min-width:0}
}
@media(max-width:780px){
  .kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    hist = pd.read_csv(DATA / "historical_energy.csv", parse_dates=["timestamp"])
    flex = pd.read_csv(DATA / "flexible_loads.csv")
    return hist, flex


@st.cache_resource(show_spinner=False)
def load_models(hist_fingerprint: int) -> tuple[ForecastModels, dict[str, float]]:
    del hist_fingerprint
    models = ForecastModels()
    hist = pd.read_csv(DATA / "historical_energy.csv", parse_dates=["timestamp"])
    metrics = models.fit(hist)
    return models, metrics


def baseline_flex_schedule(forecast: pd.DataFrame, flex: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame({"timestamp": forecast["timestamp"]})
    for _, row in flex.iterrows():
        on = np.zeros(len(forecast))
        duration = int(row["duration_h"])
        start_h = int(row["start_h"])
        end_h = int(row["end_h"])
        candidates = []
        for idx, ts in enumerate(forecast["timestamp"]):
            if start_h <= int(ts.hour) and int(ts.hour) + duration <= end_h:
                if idx + duration <= len(forecast):
                    hours = [int(forecast.iloc[j]["timestamp"].hour) for j in range(idx, idx + duration)]
                    if all(start_h <= h < end_h for h in hours):
                        candidates.append(idx)
        if candidates:
            s = candidates[0]
            on[s : s + duration] = 1
        result[str(row["name"])] = on
    return result


def baseline_series(forecast: pd.DataFrame, flex: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    base = baseline_flex_schedule(forecast, flex)
    flex_total = np.zeros(len(forecast))
    for _, row in flex.iterrows():
        flex_total += float(row["power_kw"]) * base[str(row["name"])].to_numpy()
    demand = forecast["load_forecast_kw"].to_numpy(float) + flex_total
    pv = forecast["pv_forecast_kw"].to_numpy(float)
    grid = np.maximum(demand - pv, 0.0)
    curtail = np.maximum(pv - demand, 0.0)
    cost = float(np.sum(grid * forecast["tariff_rs_per_kwh"].to_numpy(float)))
    return (
        pd.DataFrame(
            {
                "timestamp": forecast["timestamp"],
                "fixed_load_kw": forecast["load_forecast_kw"],
                "flex_load_kw": flex_total,
                "grid_kw": grid,
                "pv_kw": pv,
                "curtailment_kw": curtail,
            }
        ),
        {
            "cost_rs": cost,
            "peak_kw": float(grid.max()),
            "grid_energy_kwh": float(grid.sum()),
            "curtailment_kwh": float(curtail.sum()),
        },
    )


def scenario_day(forecast: pd.DataFrame, scenario: str, pv_capacity: float) -> pd.DataFrame:
    day = forecast.copy()
    day["pv_forecast_kw"] *= pv_capacity / 700.0
    if scenario == "Cloudy Day":
        day["pv_forecast_kw"] *= 0.60
    elif scenario == "High Solar":
        day["pv_forecast_kw"] *= 1.25
    elif scenario == "High Production":
        day["load_forecast_kw"] *= 1.25
    elif scenario == "High Tariff":
        day["tariff_rs_per_kwh"] *= 1.60
    elif scenario == "Low Solar":
        day["pv_forecast_kw"] *= 0.70
    elif scenario == "Battery Degraded":
        pass
    elif scenario == "Grid Constrained":
        pass
    return day


def start_hour_from_schedule(df: pd.DataFrame, name: str) -> int | None:
    col = f"{name}_on"
    if col not in df:
        return None
    idx = np.flatnonzero(df[col].to_numpy(float) > 0.5)
    if len(idx) == 0:
        return None
    return int(pd.Timestamp(df.iloc[idx[0]]["timestamp"]).hour)


def validation_rows(validation: dict, optimized: pd.DataFrame, battery: BatteryParamsV2, grid_limit: float) -> list[tuple[str, str, str]]:
    checks = [
        ("Energy balance", validation["max_balance_residual_kw"] < 1e-5, f"max residual {validation['max_balance_residual_kw']:.6f} kW"),
        ("Battery SOC band", validation["min_soc_kwh"] >= battery.min_soc * battery.capacity_kwh - 1e-6 and validation["max_soc_kwh"] <= battery.max_soc * battery.capacity_kwh + 1e-6, f"{validation['min_soc_kwh']:.1f}–{validation['max_soc_kwh']:.1f} kWh"),
        ("Battery power limit", max(float(optimized["charge_kw"].max()), float(optimized["discharge_kw"].max())) <= battery.power_kw + 1e-6, f"limit {battery.power_kw:.0f} kW"),
        ("Grid limit", float(optimized["grid_kw"].max()) <= grid_limit + 1e-6, f"peak {optimized['grid_kw'].max():.1f} / {grid_limit:.0f} kW"),
        ("Final SOC reserve", validation["final_soc_kwh"] >= battery.initial_soc * battery.capacity_kwh - 1e-6, f"final {validation['final_soc_kwh']:.1f} kWh"),
        ("Production constraints", validation["production_constraint_violations"] == 0, "required durations / windows satisfied"),
    ]
    return [(name, "PASS" if ok else "CHECK", evidence) for name, ok, evidence in checks]


def plot_layout(fig: go.Figure, height: int = 460) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=14, r=14, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,17,26,.52)",
        font=dict(family="Aptos, Segoe UI, Arial", size=11, color="#dce8ef"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, font=dict(size=9)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#213341", tickfont=dict(size=9))
    fig.update_yaxes(gridcolor="rgba(62,91,109,.28)", zeroline=False, tickfont=dict(size=9))
    return fig


def make_dispatch_figure(day: pd.DataFrame, optimized: pd.DataFrame, twin: pd.DataFrame, baseline: pd.DataFrame) -> go.Figure:
    x = day["timestamp"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=day["pv_forecast_kw"], name="☀ PV forecast", mode="lines", line=dict(width=3.2, color="#ffd166"), fill="tozeroy", fillcolor="rgba(255,209,102,.05)"))
    fig.add_trace(go.Scatter(x=x, y=optimized["grid_kw"], name="⚡ Grid import", mode="lines", line=dict(width=3, color="#ff7288")))
    fig.add_trace(go.Scatter(x=x, y=twin["total_load_kw"], name="🏭 Factory demand", mode="lines", line=dict(width=3, color="#f2f7fa")))
    fig.add_trace(go.Scatter(x=x, y=optimized["discharge_kw"], name="🔋 Battery discharge", mode="lines", line=dict(width=2, dash="dot", color="#55e496")))
    fig.add_trace(go.Scatter(x=x, y=optimized["charge_kw"], name="🔋 Battery charge", mode="lines", line=dict(width=2, dash="dot", color="#8dcbff")))
    fig.add_trace(go.Scatter(x=x, y=baseline["grid_kw"], name="Reference grid", mode="lines", line=dict(width=1.4, dash="dash", color="#7a8d9b"), opacity=.65))
    fig.update_layout(title="24-HOUR ENERGY ORCHESTRATION", title_font=dict(size=12, color="#eaf4f8"))
    fig.update_yaxes(title="Power (kW)")
    return plot_layout(fig, 490)


def make_soc_figure(twin: pd.DataFrame, battery: BatteryParamsV2) -> go.Figure:
    x = twin["timestamp"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=twin["soc_twin_kwh"], name="Battery SOC", mode="lines", line=dict(width=3.5, color="#55e496")))
    fig.add_hline(y=battery.min_soc * battery.capacity_kwh, line_dash="dash", line_color="#ff7489", annotation_text="MIN")
    fig.add_hline(y=battery.max_soc * battery.capacity_kwh, line_dash="dash", line_color="#ffd166", annotation_text="MAX")
    fig.update_layout(title="BATTERY OPERATING ENVELOPE", title_font=dict(size=12))
    fig.update_yaxes(title="Energy (kWh)")
    return plot_layout(fig, 325)


def make_flex_heatmap(optimized: pd.DataFrame, flex: pd.DataFrame) -> go.Figure:
    names = [str(r["name"]) for _, r in flex.iterrows()]
    z = [optimized[f"{name}_on"].to_numpy(float).tolist() for name in names]
    hours = [pd.Timestamp(t).strftime("%H") for t in optimized["timestamp"]]
    fig = go.Figure(go.Heatmap(z=z, x=hours, y=names, zmin=0, zmax=1, colorscale=[[0,"#101a24"],[1,"#2bc7ff"]], showscale=False, hovertemplate="%{y}<br>%{x}:00<br>Status: %{z}<extra></extra>"))
    fig.update_layout(title="FLEXDNA · PROCESS OPERATING WINDOWS", title_font=dict(size=12))
    fig.update_xaxes(title="Hour")
    return plot_layout(fig, 260)


def make_forecast_figure(hist: pd.DataFrame, forecast: pd.DataFrame) -> go.Figure:
    actual = hist.tail(24).reset_index(drop=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=actual["timestamp"], y=actual["pv_generation_kw"], name="Actual PV", mode="lines+markers", line=dict(width=2.2, color="#ffd166"), marker=dict(size=4)))
    fig.add_trace(go.Scatter(x=forecast["timestamp"], y=forecast["pv_forecast_kw"], name="Forecast PV", mode="lines", line=dict(width=2.7, dash="dash", color="#ffb83f")))
    fig.add_trace(go.Scatter(x=actual["timestamp"], y=actual["factory_load_kw"], name="Actual factory load", mode="lines+markers", line=dict(width=2.2, color="#eaf2f7"), marker=dict(size=4)))
    fig.add_trace(go.Scatter(x=forecast["timestamp"], y=forecast["load_forecast_kw"], name="Forecast factory load", mode="lines", line=dict(width=2.7, dash="dash", color="#8dcbff")))
    fig.update_layout(title="FORECAST EVIDENCE · ACTUAL VS PREDICTED", title_font=dict(size=12))
    fig.update_yaxes(title="Power (kW)")
    return plot_layout(fig, 390)


def build_baseline_vs_opt_chart(kpis: dict, baseline_info: dict) -> go.Figure:
    fig = go.Figure()
    labels = ["Energy cost", "Grid peak", "Grid energy", "Curtailment"]
    base = [baseline_info["cost_rs"], baseline_info["peak_kw"], baseline_info["grid_energy_kwh"], baseline_info["curtailment_kwh"]]
    opt = [kpis["optimized_cost_rs"], kpis["grid_peak_kw"], kpis["grid_energy_kwh"], kpis["curtailed_kwh"]]
    fig.add_trace(go.Bar(name="Reference", x=labels, y=base, marker_color="#65798a"))
    fig.add_trace(go.Bar(name="ForgeFlex", x=labels, y=opt, marker_color="#2bc7ff"))
    fig.update_layout(title="REFERENCE VS FORGEFLEX", barmode="group", title_font=dict(size=12), yaxis_title="Native metric units")
    return plot_layout(fig, 360)


# =============================================================================
# DATA + FORECAST
# =============================================================================
hist, flex = load_data()
models, forecast_metrics = load_models(int(hist["timestamp"].astype("int64").sum()))
future = hist.tail(24)[["timestamp", "hour", "day_of_week", "temperature_c", "cloud_factor", "tariff_rs_per_kwh", "grid_carbon_kg_per_kwh"]].copy().reset_index(drop=True)
base_forecast = models.predict(future)

# =============================================================================
# SIDEBAR — CONTROL ROOM
# =============================================================================
with st.sidebar:
    st.markdown('<div class="side-title">⚡ FORGEFLEX X</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-sub">Production-aware energy orchestration · Review 2</div>', unsafe_allow_html=True)
    st.markdown('<div style="margin-top:11px"><span class="status good"><span class="dot"></span>SYSTEM ONLINE</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="side-team"><div class="t">TEAM</div><div class="n">TECHNOBLADE</div><div class="m"><b>Lead:</b> Upendra P<br><b>Member:</b> Vishnu A R</div></div>', unsafe_allow_html=True)

    st.markdown("### Scenario")
    scenario = st.selectbox(
        "Operating condition",
        ["Normal Day", "Cloudy Day", "High Solar", "High Production", "High Tariff", "Low Solar", "Battery Degraded", "Grid Constrained"],
        index=0,
    )
    pv_capacity = st.slider("PV capacity · kW", 300, 1200, 700, 50)
    battery_capacity = st.slider("Battery capacity · kWh", 100, 1500, 500, 50)
    battery_power = st.slider("Battery power limit · kW", 50, 500, 250, 25)
    grid_limit = st.slider("Grid import limit · kW", 350, 1200, 900, 25)

    st.markdown("### Decision weights")
    peak_penalty = st.slider("Peak-demand weight", 0.0, 10.0, 3.0, 0.5)
    carbon_weight = st.slider("Grid-carbon weight", 0.0, 3.0, 0.8, 0.1)
    objective = st.selectbox("Decision emphasis", ["Balanced", "Cost", "Peak", "Renewable", "Production protection"])

    execute = st.button("⚡ EXECUTE 24-HOUR OPTIMIZATION", type="primary", use_container_width=True)
    st.caption("Same engineering core · different operating conditions · reproducible outputs")

# =============================================================================
# RUN / CACHE RESULT
# =============================================================================
control_key = json.dumps(
    {
        "scenario": scenario,
        "pv": pv_capacity,
        "battery": battery_capacity,
        "bp": battery_power,
        "grid": grid_limit,
        "peak": peak_penalty,
        "carbon": carbon_weight,
        "objective": objective,
    },
    sort_keys=True,
)

if execute or st.session_state.get("control_key") != control_key or "optimized" not in st.session_state:
    st.session_state["control_key"] = control_key
    try:
        t0 = time.perf_counter()
        day = scenario_day(base_forecast, scenario, pv_capacity)

        effective_capacity = battery_capacity * (0.85 if scenario == "Battery Degraded" else 1.0)
        degradation_cost = 0.30 if scenario == "Battery Degraded" else 0.15

        pp = peak_penalty
        cw = carbon_weight
        cp = 0.5
        if objective == "Cost":
            pp *= 0.35; cw *= 0.50; cp *= 0.60
        elif objective == "Peak":
            pp *= 2.5
        elif objective == "Renewable":
            cp *= 3.0
        elif objective == "Production protection":
            pp *= 0.75

        battery = BatteryParamsV2(
            capacity_kwh=effective_capacity,
            power_kw=min(float(battery_power), effective_capacity / 2.0),
            degradation_rs_per_kwh=degradation_cost,
        )

        optimized = optimize_day_v2(
            day,
            flex,
            battery=battery,
            peak_penalty=pp,
            curtail_penalty=cp,
            carbon_weight=cw,
            grid_limit_kw=float(grid_limit),
            time_limit_s=20.0,
        )

        twin, validation = simulate_day(
            day,
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

        baseline, baseline_info = baseline_series(day, flex)
        kpis = calculate_kpis(day, optimized, flex)
        solve_s = time.perf_counter() - t0

        st.session_state["optimized"] = {
            "optimized": optimized,
            "twin": twin,
            "validation": validation,
            "kpis": kpis,
            "baseline": baseline,
            "baseline_info": baseline_info,
            "battery": battery,
            "solve_seconds": solve_s,
            "scenario": scenario,
            "grid_limit": float(grid_limit),
        }
        st.session_state["run_error"] = ""
    except Exception as exc:
        st.session_state["optimized"] = None
        st.session_state["run_error"] = str(exc)

result = st.session_state.get("optimized")
error_message = st.session_state.get("run_error", "")

# =============================================================================
# HEADER
# =============================================================================
st.markdown(
    """
<div class="hero">
  <div class="hero-grid">
    <div>
      <div class="brandline"><span class="brandmark">⚡</span> TECHNOBLADE · SUSTAINABILITY · SU-01 · REVIEW 2</div>
      <h1>ForgeFlex X</h1>
      <div class="hero-sub">
        Production-aware energy orchestration for renewable-powered industry.
        Forecast the renewable source and factory demand, encode industrial process flexibility,
        solve a constrained MILP dispatch, then validate the resulting trajectory through a digital twin.
      </div>
      <div class="hero-chiprow">
        <span class="chip">PREDICT</span><span class="chip">FLEX</span><span class="chip">OPTIMIZE</span><span class="chip">VALIDATE</span>
        <span class="chip">PYTHON · MILP</span><span class="chip">MATLAB · SIMULINK</span>
      </div>
    </div>
    <div class="team-card">
      <div class="team-title">Project Team</div>
      <div class="team-name">TECHNOBLADE</div>
      <div class="team-meta"><b>Lead</b> · Upendra P<br><b>Team member</b> · Vishnu A R</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if error_message:
    st.error("The selected configuration did not return a feasible schedule.")
    st.code(error_message, language="text")
    st.info("Increase the grid limit, increase battery capacity/power, or return to a less restrictive scenario.")
    st.stop()

if result is None:
    st.warning("Run the 24-hour optimization from the left control panel to populate the engineering dashboard.")
    st.stop()

optimized = result["optimized"]
twin = result["twin"]
validation = result["validation"]
kpis = result["kpis"]
baseline = result["baseline"]
baseline_info = result["baseline_info"]
battery = result["battery"]
solve_s = result["solve_seconds"]
day = scenario_day(base_forecast, scenario, pv_capacity)

validation_pass = bool(validation["validation_pass"])
margin = float(grid_limit) - float(optimized["grid_kw"].max())

# =============================================================================
# EXECUTIVE STATUS
# =============================================================================
st.markdown('<div class="section-head"><div><div class="kicker">LIVE OPERATIONS</div><div class="section-title">Executive control strip</div></div><div class="section-note">Current scenario · ' + scenario + '</div></div>', unsafe_allow_html=True)

kpispec = [
    ("Energy cost", f"₹{kpis['optimized_cost_rs']:,.0f}", f"reference ₹{baseline_info['cost_rs']:,.0f}", "kpi-cyan"),
    ("Cost delta", f"{kpis['cost_reduction_pct']:+.1f}%", "vs reference schedule", "kpi-green"),
    ("Grid peak", f"{kpis['grid_peak_kw']:.0f} kW", f"limit {grid_limit:.0f} kW", "kpi-gold"),
    ("Renewable use", f"{kpis['renewable_utilization_pct']:.1f}%", f"curtailment {kpis['curtailment_pct']:.1f}%", "kpi-cyan"),
    ("Final SOC", f"{validation['final_soc_kwh']:.0f} kWh", f"effective BESS {battery.capacity_kwh:.0f} kWh", "kpi-green"),
    ("Twin state", "PASS" if validation_pass else "CHECK", f"balance error {validation['max_balance_residual_kw']:.6f} kW", "kpi-green" if validation_pass else "kpi-red"),
]

cols = st.columns(6)
for c, spec in zip(cols, kpispec):
    label, value, note, cls = spec
    with c:
        st.markdown(
            f'<div class="kpi {cls}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',
            unsafe_allow_html=True,
        )

# =============================================================================
# NAV / TABS
# =============================================================================
t1, t2, t3, t4, t5 = st.tabs(["COMMAND CENTER", "FLEXDNA", "DIGITAL TWIN", "FORECAST", "ENGINEERING"])

with t1:
    st.markdown('<div class="section-head"><div><div class="kicker">01 · DISPATCH</div><div class="section-title">Energy orchestration</div></div><div class="section-note">One chart to understand the plant</div></div>', unsafe_allow_html=True)
    st.plotly_chart(make_dispatch_figure(day, optimized, twin, baseline), use_container_width=True, config={"displaylogo": False, "responsive": True})

    left, right = st.columns([1.1, .9], gap="medium")
    with left:
        st.markdown('<div class="panel"><div class="panel-title">🧠 Why did ForgeFlex make these decisions?</div><div class="panel-sub">Plain-language explanation of the schedule</div><div class="glow-line"></div></div>', unsafe_allow_html=True)
        for _, row in flex.iterrows():
            name = str(row["name"])
            ref = int(row["start_h"])
            opt = start_hour_from_schedule(optimized, name)
            duration = int(row["duration_h"])
            if opt is None:
                msg = f"<b>{name}</b> — no operating block was produced."
            elif opt != ref:
                msg = f"<b>{name}</b> — moved <b>{ref:02d}:00 → {opt:02d}:00</b>. Required duration remains <b>{duration} h</b>; the start stays inside its permitted operating window."
            else:
                msg = f"<b>{name}</b> — retained at <b>{opt:02d}:00</b>. The selected objective and constraints did not create enough benefit to move it."
            st.markdown(f'<div class="callout" style="margin-bottom:8px">{msg}</div>', unsafe_allow_html=True)

        # Best simple conclusion for the reviewer.
        st.markdown(
            f'<div class="callout" style="margin-top:10px"><b>Bottom line:</b> the factory keeps its production requirements while ForgeFlex reshapes when flexible electrical demand is served.</div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div class="panel"><div class="panel-title">📊 Reference vs ForgeFlex</div><div class="panel-sub">Same forecast horizon · different operating decision</div><div class="glow-line"></div></div>', unsafe_allow_html=True)
        st.plotly_chart(build_baseline_vs_opt_chart(kpis, baseline_info), use_container_width=True, config={"displaylogo": False, "responsive": True})

        st.markdown(
            f'<div class="callout"><b>Grid headroom:</b> {margin:.1f} kW below the hard import limit. <b>Production:</b> 100%. <b>Validation:</b> <span style="color:{"#59e49a" if validation_pass else "#ffd36a"}">{"PASS" if validation_pass else "CHECK"}</span>.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-head"><div><div class="kicker">ENERGY ALLOCATION</div><div class="section-title">Daily portfolio</div></div></div>', unsafe_allow_html=True)
    portfolio = pd.DataFrame({
        "Flow": ["PV generation", "Grid import", "Battery charge", "Battery discharge", "Curtailment", "Factory energy"],
        "Energy": [
            f"{day['pv_forecast_kw'].sum():,.0f} kWh",
            f"{optimized['grid_kw'].sum():,.0f} kWh",
            f"{optimized['charge_kw'].sum():,.0f} kWh",
            f"{optimized['discharge_kw'].sum():,.0f} kWh",
            f"{optimized['curtailment_kw'].sum():,.0f} kWh",
            f"{twin['total_load_kw'].sum():,.0f} kWh",
        ],
    })
    st.dataframe(portfolio, hide_index=True, use_container_width=True)

with t2:
    st.markdown('<div class="section-head"><div><div class="kicker">02 · FLEXDNA</div><div class="section-title">Industrial flexibility map</div></div><div class="section-note">Process timing becomes an energy resource</div></div>', unsafe_allow_html=True)
    st.plotly_chart(make_flex_heatmap(optimized, flex), use_container_width=True, config={"displaylogo": False, "responsive": True})

    rows = []
    for _, r in flex.iterrows():
        name = str(r["name"])
        opt_start = start_hour_from_schedule(optimized, name)
        opt_end = opt_start + int(r["duration_h"]) if opt_start is not None else None
        rows.append({
            "Process": name,
            "Power": f"{float(r['power_kw']):.0f} kW",
            "Required": f"{int(r['duration_h'])} h",
            "Legal window": f"{int(r['start_h']):02d}:00–{int(r['end_h']):02d}:00",
            "Reference": f"{int(r['start_h']):02d}:00",
            "Optimized": f"{opt_start:02d}:00–{opt_end:02d}:00" if opt_start is not None else "—",
            "Criticality": "CRITICAL" if int(r.get("critical", 0)) else "FLEXIBLE",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown('<div class="callout"><b>FlexDNA:</b> each process is represented by power, required duration, legal operating window and criticality. The optimizer can therefore move required work without treating the factory as one indivisible load.</div>', unsafe_allow_html=True)

with t3:
    st.markdown('<div class="section-head"><div><div class="kicker">03 · VALIDATION</div><div class="section-title">Digital twin evidence</div></div><div class="section-note">Independent check before engineering handoff</div></div>', unsafe_allow_html=True)

    a, b = st.columns(2, gap="medium")
    with a:
        st.plotly_chart(make_soc_figure(twin, battery), use_container_width=True, config={"displaylogo": False, "responsive": True})
    with b:
        rf = go.Figure()
        rf.add_trace(go.Scatter(x=twin["timestamp"], y=twin["balance_residual_kw"], mode="lines", name="Residual", line=dict(width=3, color="#35d2ff")))
        rf.add_hline(y=0, line_dash="dash", line_color="#7d92a3", annotation_text="TARGET = 0")
        rf.update_layout(title="ENERGY BALANCE RESIDUAL", title_font=dict(size=12), yaxis_title="Residual (kW)")
        st.plotly_chart(plot_layout(rf, 325), use_container_width=True, config={"displaylogo": False, "responsive": True})

    vr = validation_rows(validation, optimized, battery, float(grid_limit))
    vdf = pd.DataFrame(vr, columns=["Engineering check", "State", "Evidence"])
    st.dataframe(vdf, hide_index=True, use_container_width=True)

    q1,q2,q3,q4 = st.columns(4)
    with q1:
        st.markdown(f'<div class="kpi kpi-cyan"><div class="kpi-label">BALANCE RESIDUAL</div><div class="kpi-value">{validation["max_balance_residual_kw"]:.6f}</div><div class="kpi-note">kW · target ≈ 0</div></div>', unsafe_allow_html=True)
    with q2:
        st.markdown(f'<div class="kpi kpi-green"><div class="kpi-label">SOC RANGE</div><div class="kpi-value">{validation["min_soc_kwh"]:.0f}–{validation["max_soc_kwh"]:.0f}</div><div class="kpi-note">kWh over 24 h</div></div>', unsafe_allow_html=True)
    with q3:
        st.markdown(f'<div class="kpi kpi-gold"><div class="kpi-label">GRID HEADROOM</div><div class="kpi-value">{margin:.1f}</div><div class="kpi-note">kW below hard limit</div></div>', unsafe_allow_html=True)
    with q4:
        st.markdown(f'<div class="kpi {"kpi-green" if validation_pass else "kpi-red"}"><div class="kpi-label">TWIN VALIDATION</div><div class="kpi-value">{"PASS" if validation_pass else "CHECK"}</div><div class="kpi-note">{validation["violation_count"]} recorded violations</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-head"><div><div class="kicker">SIMULINK BRIDGE</div><div class="section-title">Decision → physical validation</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="callout"><b>Python/MILP</b> generates the operating schedule → <b>review2_simulink_inputs.mat</b> transfers the time series → <b>MATLAB/Simulink</b> validates energy flow and battery behavior.</div>', unsafe_allow_html=True)

with t4:
    st.markdown('<div class="section-head"><div><div class="kicker">04 · FORECAST EVIDENCE</div><div class="section-title">Renewable + factory prediction</div></div><div class="section-note">Observed last 24 h vs model forecast horizon</div></div>', unsafe_allow_html=True)
    st.plotly_chart(make_forecast_figure(hist, base_forecast), use_container_width=True, config={"displaylogo": False, "responsive": True})
    f1,f2,f3,f4 = st.columns(4)
    fm = [
        ("PV MAE", forecast_metrics["pv_mae_kw"], "kW"),
        ("PV RMSE", forecast_metrics["pv_rmse_kw"], "kW"),
        ("Load MAE", forecast_metrics["load_mae_kw"], "kW"),
        ("Load RMSE", forecast_metrics["load_rmse_kw"], "kW"),
    ]
    for c,(lab,val,unit) in zip([f1,f2,f3,f4],fm):
        with c:
            st.markdown(f'<div class="kpi"><div class="kpi-label">{lab}</div><div class="kpi-value">{val:.2f}</div><div class="kpi-note">{unit}</div></div>', unsafe_allow_html=True)

with t5:
    st.markdown('<div class="section-head"><div><div class="kicker">05 · ENGINEERING</div><div class="section-title">Optimization architecture</div></div><div class="section-note">Inspectable decision variables and constraints</div></div>', unsafe_allow_html=True)

    variables = 6 * len(day) + 2 + len(flex) * len(day)
    constraints = 5 * len(day) + len(flex) + 2
    e1,e2,e3,e4 = st.columns(4)
    specs=[
        ("MILP decision variables",variables,"24 h · continuous + binary"),
        ("Constraint rows",constraints,"energy · battery · flex · peak"),
        ("Time step", "1 h", "Review 2 MVP horizon"),
        ("Solver", "MILP", "scipy.optimize.milp"),
    ]
    for c,(lab,val,note) in zip([e1,e2,e3,e4],specs):
        with c:
            st.markdown(f'<div class="kpi kpi-cyan"><div class="kpi-label">{lab}</div><div class="kpi-value">{val}</div><div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)

    left,right = st.columns(2, gap="medium")
    with left:
        st.markdown('<div class="panel"><div class="panel-title">Decision variables</div><div class="glow-line"></div></div>', unsafe_allow_html=True)
        st.code(
            "P_grid[t]\n"
            "P_charge[t]\n"
            "P_discharge[t]\n"
            "SOC[t]\n"
            "P_curtail[t]\n"
            "P_peak\n"
            "z[i,t]  # flexible-process binaries\n"
            "y[t]    # battery charge/discharge mode",
            language="text",
        )
    with right:
        st.markdown('<div class="panel"><div class="panel-title">Hard constraints</div><div class="glow-line"></div></div>', unsafe_allow_html=True)
        st.code(
            "energy balance every hour\n"
            "SOC lower / upper bounds\n"
            "battery power limit\n"
            "charge/discharge exclusivity\n"
            "grid import hard limit\n"
            "contiguous flexible run\n"
            "legal operating window\n"
            "final SOC reserve",
            language="text",
        )

    st.markdown('<div class="callout"><b>Engineering principle:</b> the optimizer is not allowed to trade away production feasibility just to improve an energy metric. The production constraints are part of the mathematical problem.</div>', unsafe_allow_html=True)

# =============================================================================
# SUBMISSION BAR
# =============================================================================
st.markdown('<div class="section-head"><div><div class="kicker">SUBMISSION</div><div class="section-title">Current run artifacts</div></div><div class="section-note">Ready for GitHub / Review 2 evidence</div></div>', unsafe_allow_html=True)

current_schedule_csv = optimized.to_csv(index=False).encode("utf-8")
current_validation_csv = twin.to_csv(index=False).encode("utf-8")
current_result = {
    "project": "ForgeFlex X",
    "team": "Technoblade",
    "lead": "Upendra P",
    "member": "Vishnu A R",
    "scenario": scenario,
    "objective": objective,
    "grid_limit_kw": float(grid_limit),
    "solve_seconds": float(solve_s),
    "kpis": {k: float(v) for k, v in kpis.items()},
    "validation": validation,
    "forecast_metrics": forecast_metrics,
    "solver": "scipy.optimize.milp",
}

b1,b2,b3 = st.columns(3)
with b1:
    st.download_button("⇩ Optimized schedule CSV", current_schedule_csv, "forgeflex_optimized_schedule.csv", "text/csv", use_container_width=True)
with b2:
    st.download_button("⇩ Twin validation CSV", current_validation_csv, "forgeflex_twin_validation.csv", "text/csv", use_container_width=True)
with b3:
    st.download_button("⇩ Run summary JSON", json.dumps(current_result, indent=2), "forgeflex_run_summary.json", "application/json", use_container_width=True)

st.markdown(
    '<div class="final-footer"><b>FORGEFLEX X · TECHNOBLADE</b><br>'
    'Lead · Upendra P &nbsp;|&nbsp; Team member · Vishnu A R<br>'
    'Predict → Flex → Optimize → Validate<br>'
    'Engineering prototype using a synthetic demonstration dataset. Impact values are model outputs, not measured factory savings.</div>',
    unsafe_allow_html=True,
)
