"""Turn the raw district-week panel into model inputs and the onset target.

Target: flood ONSET - the district is flooded this week and was not
flooded last week. Flood records span several weeks, so the plain weekly
label is dominated by "still flooded" weeks that any persistence rule
predicts trivially. Every week that follows a flooded week (flood still
under way, or just receding) is dropped from training and scoring, so
every model is judged on predicting a new flood.

Two input timings:
- Nowcast (default feature sets): inputs known by the END of the target
  week, including that week's rainfall and runoff - a perfect-forecast
  hindcast, the standard upper bound for a forecast system.
- Forecast (models.FORECAST): only inputs known at the START of the
  target week (lagged rain, soil, runoff and discharge). This is what an
  operational one-week-ahead warning could use.
No input uses labels.
"""

import numpy as np
import pandas as pd

from research.flood_experiments import config as C


def build_features(panel: pd.DataFrame, label: str = "news") -> pd.DataFrame:
    """label: which flood record defines the target - "news" in v2
    (column flood_news); v1 has a single `flood`."""
    df = panel.copy()
    col = f"flood_{label}"
    if col in df.columns:
        df["flood"] = df[col]
    df["week"] = pd.to_datetime(df["week"])
    df = df.sort_values(["district_code", "week"]).reset_index(drop=True)
    df["year"] = df["week"].dt.year
    woy = df["week"].dt.isocalendar().week.astype(float)
    df["woy_sin"] = np.sin(2 * np.pi * woy / 52.18)
    df["woy_cos"] = np.cos(2 * np.pi * woy / 52.18)

    g = df.groupby("district_code", sort=False)
    for k in range(1, 5):
        df[f"rain_lag{k}"] = g["rain_week_sum"].shift(k)
    df["rain_prev4w_sum"] = df[[f"rain_lag{k}" for k in range(1, 5)]].sum(
        axis=1, min_count=4
    )
    df["sm_start"] = g["sm_week_mean"].shift(1)
    df["runoff_prev4w_sum"] = sum(g["runoff_week_sum"].shift(k) for k in range(1, 5))

    df["q_week_max"] = df["q_week_max"].clip(lower=0)
    df["q_week_max_log"] = np.log1p(df["q_week_max"])
    # Discharge climatology comes only from years before the first test
    # year, so q_ratio never sees test data.
    early = df[df["week"] <= C.S["q_climatology_end"]]
    q_median = early.groupby("district_code")["q_week_max"].median()
    df["q_ratio"] = df["q_week_max"] / (
        df["district_code"].map(q_median).replace(0, np.nan) + 1e-3
    )
    df["q_ratio_lag1"] = g["q_ratio"].shift(1)
    df["q_week_max_log_lag1"] = g["q_week_max_log"].shift(1)

    df["log_pop_density"] = np.log1p(df["population"] / df["area_km2"])

    df["flood_prev"] = g["flood"].shift(1).fillna(0).astype(int)
    df["flood_recent8"] = (
        sum(g["flood"].shift(k).fillna(0) for k in range(2, 9)) > 0
    ).astype(int)
    df["onset"] = ((df["flood"] == 1) & (df["flood_prev"] == 0)).astype(int)

    # First 4 weeks per district lack full lags; continuing-flood weeks
    # are not onset candidates.
    df = df[df["rain_lag4"].notna() & (df["flood_prev"] == 0)].copy()
    return df.reset_index(drop=True)


def all_features():
    return (
        C.SEASON + C.RAIN + C.RAIN_LAGS + C.SOIL + C.RIVER + C.GEOGRAPHIC + C.EXPOSURE
    )
