"""
NFCC Flood-Risk Intelligence Dashboard
National Flood Control Centre — Accra, Ghana
Phase 3B — Streamlit MVP
"""

import warnings
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore")

# ── Page Configuration ────────────────────────────────────────────────
st.set_page_config(
    page_title="NFCC Flood-Risk Dashboard",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        .main { background-color: #0f1923; }
        .block-container { padding-top: 1.5rem; }
        .metric-card {
            background-color: #1a2535;
            border-radius: 10px;
            padding: 18px 24px;
            margin-bottom: 10px;
            border-left: 5px solid #2980b9;
        }
        .metric-critical { border-left-color: #c0392b; }
        .metric-high     { border-left-color: #e67e22; }
        .metric-moderate { border-left-color: #f1c40f; }
        .metric-low      { border-left-color: #27ae60; }
        .section-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: #7fb3d3;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
    </style>
""",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════
# SAFE FILE PATH HANDLING WITH PATHLIB
# ══════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "accra_features_2024.parquet"
MODEL_PATH = BASE_DIR / "models" / "xgboost_flood_risk.pkl"

if not DATA_PATH.exists():
    st.error(f"❌ Data file not found: {DATA_PATH}")
    st.stop()

if not MODEL_PATH.exists():
    st.error(f"❌ Model file not found: {MODEL_PATH}")
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# DATA & MODEL LOADING
# ══════════════════════════════════════════════════════════════════════


@st.cache_data
def load_data():
    df = pd.read_parquet(DATA_PATH)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
    else:
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
    return df


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


df = load_data()
model = load_model()

FEATURE_COLS = [
    "precipitation",
    "roll_3d",
    "roll_7d",
    "roll_30d",
    "cumulative",
    "z_score",
]

# Generate model predictions across full dataset
df_pred = df[FEATURE_COLS].dropna()
df["predicted_risk"] = np.nan
df.loc[df_pred.index, "predicted_risk"] = np.clip(model.predict(df_pred), 0, 100)


# ══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════


def risk_tier(score):
    if score >= 75:
        return "🔴 CRITICAL"
    elif score >= 50:
        return "🟠 HIGH"
    elif score >= 25:
        return "🟡 MODERATE"
    return "🟢 LOW"


def risk_color(score):
    if score >= 75:
        return "#c0392b"
    elif score >= 50:
        return "#e67e22"
    elif score >= 25:
        return "#f1c40f"
    return "#27ae60"


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/"
        "Flag_of_Ghana.svg/320px-Flag_of_Ghana.svg.png",
        width=80,
    )
    st.markdown("## 🌧️ NFCC Dashboard")
    st.markdown("**National Flood Control Centre**")
    st.markdown("Accra, Ghana · 2024")
    st.divider()

    st.markdown("### 📅 Date Range")
    min_date = df.index.min().date()
    max_date = df.index.max().date()

    date_start = st.date_input(
        "From", value=min_date, min_value=min_date, max_value=max_date
    )
    date_end = st.date_input(
        "To", value=max_date, min_value=min_date, max_value=max_date
    )

    st.divider()

    st.markdown("### ⚠️ Alert Threshold")
    alert_threshold = st.slider(
        "Minimum risk score to flag", min_value=0, max_value=100, value=50, step=5
    )

    st.divider()
    st.markdown("### 🔮 Live Risk Scorer")
    live_precip = st.number_input("Today's rainfall (mm)", 0.0, 200.0, 10.0, 0.5)
    live_roll3d = st.number_input("3-day total (mm)", 0.0, 300.0, 25.0, 1.0)
    live_roll7d = st.number_input("7-day avg (mm)", 0.0, 100.0, 8.0, 0.5)
    live_roll30d = st.number_input("30-day avg (mm)", 0.0, 80.0, 5.0, 0.5)
    live_cumul = st.number_input("Cumulative (mm)", 0.0, 2000.0, 500.0, 10.0)
    live_zscore = st.number_input("Z-Score", -3.0, 5.0, 1.0, 0.1)

    # ── FIX: use_container_width → width="stretch" ────────────────────
    if st.button("🔍 Score Now", width="stretch"):
        sample = pd.DataFrame(
            [
                {
                    "precipitation": live_precip,
                    "roll_3d": live_roll3d,
                    "roll_7d": live_roll7d,
                    "roll_30d": live_roll30d,
                    "cumulative": live_cumul,
                    "z_score": live_zscore,
                }
            ]
        )
        score = float(np.clip(model.predict(sample)[0], 0, 100))
        tier = risk_tier(score)
        color = risk_color(score)
        st.markdown(
            f"""
            <div style='background:{color}22; border-left:5px solid {color};
                        padding:14px; border-radius:8px; margin-top:10px;'>
                <b style='font-size:1.3rem;'>{tier}</b><br>
                <span style='font-size:2rem; font-weight:900;
                             color:{color};'>{score:.1f}</span>
                <span style='color:#aaa;'> / 100</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # ── Model Honesty Notice ──────────────────────────────────────────
    st.divider()
    st.markdown("### ℹ️ Model Status")
    st.info(
        "**Phase 3A — Risk Emulation**\n\n"
        "Current model predicts a risk score derived from "
        "rainfall features (precipitation, rolling averages, z-score). "
        "This is operationally valid for MVP.\n\n"
        "**Phase 4** will introduce true forecasting using lagged "
        "features, DEM/slope, drainage, and historical flood labels."
    )


# ══════════════════════════════════════════════════════════════════════
# FILTER DATA BY DATE RANGE
# ══════════════════════════════════════════════════════════════════════

mask = (df.index.date >= date_start) & (df.index.date <= date_end)
dff = df[mask].copy()


# ══════════════════════════════════════════════════════════════════════
# EMPTY DATA PROTECTION
# ══════════════════════════════════════════════════════════════════════

valid_rows = dff.dropna(subset=["predicted_risk"])

if valid_rows.empty:
    st.error(
        "⚠️ No data available for the selected date range. "
        "Please adjust the date filter in the sidebar."
    )
    st.stop()

latest = valid_rows.iloc[-1]
latest_score = latest["predicted_risk"]
latest_date = latest.name.strftime("%d %b %Y")


# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════

st.markdown("# 🌧️ NFCC Flood-Risk Intelligence Dashboard")
st.markdown(
    f"**Accra, Ghana** · {date_start.strftime('%d %b %Y')} "
    f"→ {date_end.strftime('%d %b %Y')} · "
    f"Alert threshold: **{alert_threshold}** · "
    f"Latest scored: **{latest_date}**"
)
st.divider()


# ══════════════════════════════════════════════════════════════════════
# KPI METRICS ROW
# ══════════════════════════════════════════════════════════════════════

total_rain = dff["precipitation"].sum()
extreme_days = int((dff["precipitation"] >= 30).sum())
high_risk_days = int((dff["predicted_risk"] >= alert_threshold).sum())
max_risk = dff["predicted_risk"].max()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Latest Risk Score", f"{latest_score:.1f}", delta=risk_tier(latest_score))
with col2:
    st.metric("Total Rainfall", f"{total_rain:.1f} mm")
with col3:
    st.metric("Extreme Rain Days", f"{extreme_days} days", delta="≥ 30 mm/day")
with col4:
    st.metric(f"High-Risk Days (≥{alert_threshold})", f"{high_risk_days} days")
with col5:
    st.metric("Peak Risk Score", f"{max_risk:.1f}", delta=risk_tier(max_risk))

st.divider()


# ══════════════════════════════════════════════════════════════════════
# ROW 1: RAINFALL TIMELINE + PREDICTED RISK
# ══════════════════════════════════════════════════════════════════════

st.markdown(
    '<div class="section-header">📈 Rainfall & Flood-Risk Timeline</div>',
    unsafe_allow_html=True,
)

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True, facecolor="#0f1923")

for ax in axes:
    ax.set_facecolor("#1a2535")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#2c3e50")

# Top: Daily rainfall bars
axes[0].bar(
    dff.index,
    dff["precipitation"],
    color="#2980b9",
    alpha=0.8,
    width=1.0,
    label="Daily Rainfall",
)
axes[0].plot(
    dff.index, dff["roll_7d"], color="#f39c12", linewidth=1.5, label="7-Day Avg"
)
axes[0].plot(
    dff.index, dff["roll_30d"], color="#e74c3c", linewidth=1.5, label="30-Day Avg"
)
axes[0].set_ylabel("Rainfall (mm)", fontsize=10, color="white")
axes[0].set_title(
    "Daily Rainfall with Rolling Averages", fontsize=11, color="white", pad=8
)
axes[0].legend(fontsize=9, facecolor="#1a2535", labelcolor="white", framealpha=0.8)
axes[0].grid(True, linestyle="--", alpha=0.25, color="white")

# Bottom: Predicted flood-risk score
risk_vals = dff["predicted_risk"].values
risk_idx = dff.index

axes[1].fill_between(
    risk_idx,
    risk_vals,
    where=risk_vals >= 75,
    color="#c0392b",
    alpha=0.7,
    label="Critical (≥75)",
)
axes[1].fill_between(
    risk_idx,
    risk_vals,
    where=(risk_vals >= 50) & (risk_vals < 75),
    color="#e67e22",
    alpha=0.7,
    label="High (50–74)",
)
axes[1].fill_between(
    risk_idx,
    risk_vals,
    where=(risk_vals >= 25) & (risk_vals < 50),
    color="#f1c40f",
    alpha=0.6,
    label="Moderate (25–49)",
)
axes[1].fill_between(
    risk_idx,
    risk_vals,
    where=risk_vals < 25,
    color="#27ae60",
    alpha=0.5,
    label="Low (<25)",
)
axes[1].plot(risk_idx, risk_vals, color="white", linewidth=0.7, alpha=0.5)
axes[1].axhline(
    y=alert_threshold,
    color="white",
    linestyle="--",
    linewidth=1.0,
    alpha=0.6,
    label=f"Alert Threshold ({alert_threshold})",
)
axes[1].set_ylim(0, 100)
axes[1].set_ylabel("Risk Score (0–100)", fontsize=10, color="white")
axes[1].set_title(
    "XGBoost Predicted Flood-Risk Score — Phase 3A Risk Emulation",
    fontsize=11,
    color="white",
    pad=8,
)
axes[1].legend(fontsize=9, facecolor="#1a2535", labelcolor="white", framealpha=0.8)
axes[1].grid(True, linestyle="--", alpha=0.25, color="white")

axes[1].xaxis.set_major_locator(mdates.MonthLocator())
axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
plt.setp(axes[1].get_xticklabels(), rotation=45, ha="right", color="white")

plt.tight_layout()
st.pyplot(fig)
plt.close()


# ══════════════════════════════════════════════════════════════════════
# ROW 2: ALERT TABLE + FEATURE IMPORTANCE
# ══════════════════════════════════════════════════════════════════════

col_left, col_right = st.columns([1.2, 1])

with col_left:

    alert_days = (
        dff[dff["predicted_risk"] >= alert_threshold][
            [
                "precipitation",
                "roll_3d",
                "roll_7d",
                "z_score",
                "predicted_risk",
                "rainfall_class",
            ]
        ]
        .sort_values("predicted_risk", ascending=False)
        .head(20)
        .copy()
    )
    alert_days.index = alert_days.index.strftime("%d %b %Y")
    alert_days.columns = [
        "Rain (mm)",
        "3d Total",
        "7d Avg",
        "Z-Score",
        "Risk Score",
        "Class",
    ]

    if len(alert_days) > 0:
        # ── FIX: use_container_width → width="stretch" ────────────────
        st.dataframe(
            alert_days.style.background_gradient(
                subset=["Risk Score"], cmap="RdYlGn_r", vmin=0, vmax=100
            ).format(precision=2),
            width="stretch",
            height=380,
        )
    else:
        st.success(
            f"✅ No days exceeded the alert threshold of {alert_threshold} "
            "in the selected date range."
        )

with col_right:
    st.markdown(
        '<div class="section-header">📊 Feature Importance</div>',
        unsafe_allow_html=True,
    )
    importance = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(
        ascending=True
    )

    bar_colors = [
        (
            "#c0392b"
            if v == importance.max()
            else "#e67e22" if v >= importance.quantile(0.75) else "#2980b9"
        )
        for v in importance.values
    ]

    fig2, ax2 = plt.subplots(figsize=(7, 4), facecolor="#1a2535")
    ax2.set_facecolor("#1a2535")
    ax2.tick_params(colors="white")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#2c3e50")

    bars = ax2.barh(
        importance.index, importance.values, color=bar_colors, edgecolor="#0f1923"
    )
    for bar, val in zip(bars, importance.values):
        ax2.text(
            bar.get_width() + 0.005,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.3f}",
            va="center",
            fontsize=9,
            color="white",
        )

    ax2.set_title("Flood-Risk Feature Importance", fontsize=11, color="white", pad=8)
    ax2.set_xlabel("Importance Score", fontsize=9, color="white")
    ax2.tick_params(axis="both", colors="white")
    ax2.grid(True, axis="x", linestyle="--", alpha=0.25, color="white")

    plt.tight_layout()
    st.pyplot(fig2)
    plt.close()


# ══════════════════════════════════════════════════════════════════════
# ROW 3: MONTHLY SUMMARY + CLASS DISTRIBUTION
# ══════════════════════════════════════════════════════════════════════

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(
        '<div class="section-header">🗓️ Monthly Rainfall Summary</div>',
        unsafe_allow_html=True,
    )
    # resample("M") for pandas compatibility
    monthly = dff["precipitation"].resample("M").sum().reset_index()
    monthly.columns = ["month", "total"]

    fig3, ax3 = plt.subplots(figsize=(7, 4), facecolor="#1a2535")
    ax3.set_facecolor("#1a2535")
    ax3.tick_params(colors="white")
    for spine in ax3.spines.values():
        spine.set_edgecolor("#2c3e50")

    ax3.bar(
        monthly["month"],
        monthly["total"],
        color="#2980b9",
        edgecolor="#0f1923",
        width=20,
    )
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    plt.setp(ax3.get_xticklabels(), color="white")
    ax3.set_title("Monthly Rainfall Totals (mm)", fontsize=11, color="white")
    ax3.set_ylabel("mm", fontsize=9, color="white")
    ax3.grid(True, axis="y", linestyle="--", alpha=0.25, color="white")

    plt.tight_layout()
    st.pyplot(fig3)
    plt.close()

with col_b:
    st.markdown(
        '<div class="section-header">🎯 Rainfall Class Distribution</div>',
        unsafe_allow_html=True,
    )
    class_order = ["Dry", "Light", "Moderate", "High", "Extreme"]
    class_colors = ["#d0e8f1", "#74b9e7", "#2980b9", "#e67e22", "#c0392b"]
    class_counts = dff["rainfall_class"].value_counts().reindex(class_order).fillna(0)

    fig4, ax4 = plt.subplots(figsize=(7, 4), facecolor="#1a2535")
    ax4.set_facecolor("#1a2535")
    ax4.tick_params(colors="white")
    for spine in ax4.spines.values():
        spine.set_edgecolor("#2c3e50")

    bars4 = ax4.bar(
        class_counts.index, class_counts.values, color=class_colors, edgecolor="#0f1923"
    )
    for bar in bars4:
        ax4.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{int(bar.get_height())}d",
            ha="center",
            va="bottom",
            fontsize=9,
            color="white",
        )
    ax4.set_title("Days per Rainfall Class", fontsize=11, color="white")
    ax4.set_ylabel("Days", fontsize=9, color="white")
    plt.setp(ax4.get_xticklabels(), color="white")
    ax4.grid(True, axis="y", linestyle="--", alpha=0.25, color="white")

    plt.tight_layout()
    st.pyplot(fig4)
    plt.close()


# ══════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════

st.divider()
st.markdown(
    "**⚠️ Scientific Note:** This dashboard currently performs "
    "**risk emulation** (Phase 3A) — the model predicts a score "
    "derived from engineered rainfall features. True flood forecasting "
    "(Phase 4) will incorporate lagged features, DEM/slope, drainage "
    "density, soil saturation, and validated historical flood labels."
)
st.caption(
    "NFCC Flood-Risk Intelligence Platform · Accra, Ghana · "
    "Powered by CHIRPS + XGBoost · Phase 3B MVP"
)
# ══════════════════════════════════════════════════════════════════════
# CIVISENTI COMMUNITY FLOOD REPORTS
# ══════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("## 📲 CiviSenti Community Flood Reports")

CIVISENTI_REPORTS_PATH = BASE_DIR / "data" / "community_reports" / "reports.jsonl"


def load_civisenti_reports():
    """Load CiviSenti community flood reports from JSONL storage."""

    if not CIVISENTI_REPORTS_PATH.exists():
        return pd.DataFrame()

    records = []

    with CIVISENTI_REPORTS_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                records.append(pd.json_normalize(pd.read_json(line, typ="series")))

    if not records:
        return pd.DataFrame()

    return pd.concat(records, ignore_index=True)


community_reports = load_civisenti_reports()

if community_reports.empty:
    st.info(
        "No CiviSenti community flood reports found yet. "
        "Reports will appear here after WhatsApp submissions are processed."
    )
else:
    total_reports = len(community_reports)

    validated_reports = (
        community_reports["status"].eq("validated").sum()
        if "status" in community_reports.columns
        else 0
    )

    supported_reports = (
        community_reports["satellite_validation"].eq("supported").sum()
        if "satellite_validation" in community_reports.columns
        else 0
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Reports", total_reports)
    col2.metric("Validated Reports", int(validated_reports))
    col3.metric("Satellite Supported", int(supported_reports))

    display_columns = [
        "report_id",
        "created_at",
        "reporter_phone",
        "location_text",
        "latitude",
        "longitude",
        "severity",
        "status",
        "satellite_validation",
        "message",
    ]

    available_columns = [
        column for column in display_columns if column in community_reports.columns
    ]

    if "created_at" in community_reports.columns:
        community_reports["created_at"] = pd.to_datetime(
            community_reports["created_at"], errors="coerce"
        )
        community_reports = community_reports.sort_values("created_at", ascending=False)

    st.dataframe(community_reports[available_columns], use_container_width=True)

    if "severity" in community_reports.columns:
        st.markdown("### Severity Breakdown")
        st.bar_chart(community_reports["severity"].value_counts())
