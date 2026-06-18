"""DataFrame-related pytest fixtures for NFCC tests."""

import pytest
import pandas as pd


@pytest.fixture
def sample_dataframe_with_features():
    """Return a small rainfall dataframe with engineered features."""

    precipitation = [0.0, 5.0, 12.0, 25.0, 40.0]

    df = pd.DataFrame(
        {
            "precipitation": precipitation,
        }
    )

    df["roll_3d"] = df["precipitation"].rolling(3, min_periods=1).mean()
    df["roll_7d"] = df["precipitation"].rolling(7, min_periods=1).mean()
    df["roll_30d"] = df["precipitation"].rolling(30, min_periods=1).mean()
    df["cumulative"] = df["precipitation"].cumsum()

    mean_rain = df["precipitation"].mean()
    std_rain = df["precipitation"].std()
    df["z_score"] = (df["precipitation"] - mean_rain) / (std_rain + 0.001)

    return df
