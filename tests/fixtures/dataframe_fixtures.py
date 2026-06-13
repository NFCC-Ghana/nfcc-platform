"""DataFrame fixtures for rainfall and feature-engineering tests."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACCRA_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "accra_features_2024.parquet"


def _synthetic_accra_features(rows: int = 90) -> pd.DataFrame:
    """Build a minimal Accra-like feature matrix for tests."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=rows, freq="D")
    precip = np.random.gamma(2.0, 4.0, rows)

    df = pd.DataFrame(
        {
            "precipitation": precip,
            "roll_3d": pd.Series(precip).rolling(3, min_periods=1).sum().values,
            "roll_7d": pd.Series(precip).rolling(7, min_periods=1).mean().values,
            "roll_30d": pd.Series(precip).rolling(30, min_periods=1).mean().values,
            "cumulative": np.cumsum(precip),
            "z_score": (precip - precip.mean()) / (precip.std() + 1e-6),
            "rainfall_class": np.select(
                [precip >= 30, precip >= 15, precip >= 5, precip > 0],
                ["Extreme", "High", "Moderate", "Light"],
                default="Dry",
            ),
            "flood_risk_score": np.clip(precip * 2.5, 0, 100),
        },
        index=dates,
    )
    df.index.name = "date"
    return df


@pytest.fixture(scope="session")
def accra_features_path():
    """Path to processed Accra feature parquet."""
    return ACCRA_FEATURES_PATH


@pytest.fixture
def accra_features_df(accra_features_path):
    """
    Accra feature DataFrame from processed parquet when present.

    Uses synthetic data otherwise so tests remain portable.
    """
    if accra_features_path.exists():
        df = pd.read_parquet(accra_features_path)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        return df.sort_index()
    return _synthetic_accra_features()


@pytest.fixture
def rainfall_timeseries_df():
    """Simple daily rainfall time series for pipeline tests."""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(30)]
    np.random.seed(7)
    rainfall = np.random.gamma(2, 5, 30)
    return pd.DataFrame({"date": dates, "precipitation": rainfall})
