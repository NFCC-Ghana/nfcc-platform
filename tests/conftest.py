"""Pytest configuration and shared fixtures."""

import pytest
import numpy as np
import pandas as pd



# ============================================================
# RANDOM SEED
# ============================================================


def pytest_configure():
    np.random.seed(42)
    print("\n🔧 Global random seed set to 42 for test reproducibility")


# ============================================================
# SAMPLE DATA
# ============================================================


@pytest.fixture
def sample_dataframe():
    """Generate a sample dataframe with 365 days of rainfall data."""
    dates = pd.date_range(start="2020-01-01", periods=365, freq="D")
    np.random.seed(42)
    precipitation = np.random.gamma(shape=2, scale=5, size=365)
    precipitation = np.maximum(precipitation, 0)

    df = pd.DataFrame(
        {
            "precipitation": precipitation,
            "date": dates,
        }
    )
    df.set_index("date", inplace=True)

    # Add rolling features
    df["roll_3d"] = df["precipitation"].rolling(window=3, min_periods=1).sum()
    df["roll_7d"] = df["precipitation"].rolling(window=7, min_periods=1).mean()
    df["roll_30d"] = df["precipitation"].rolling(window=30, min_periods=1).mean()
    df["cumulative"] = df["precipitation"].cumsum()

    # Add z-score
    mean_30d = df["precipitation"].rolling(window=30, min_periods=1).mean()
    std_30d = df["precipitation"].rolling(window=30, min_periods=1).std()
    df["z_score"] = (df["precipitation"] - mean_30d) / std_30d
    df["z_score"] = df["z_score"].fillna(0)

    return df


# ============================================================
# TRAINED MODEL FIXTURE
# ============================================================


@pytest.fixture
def trained_model(sample_dataframe):
    """Train a simple model for testing."""
    from sklearn.ensemble import RandomForestRegressor

    df = sample_dataframe.copy()

    # Create features
    feature_cols = [
        "precipitation",
        "roll_3d",
        "roll_7d",
        "roll_30d",
        "cumulative",
        "z_score",
    ]
    X = df[feature_cols].fillna(0)
    y = np.clip(df["precipitation"].shift(-1).fillna(0) * 2, 0, 100)

    model = RandomForestRegressor(n_estimators=10, random_state=42, n_jobs=1)
    model.fit(X, y)

    return model


# ============================================================
# OBSERVATION FIXTURES
# ============================================================


@pytest.fixture
def low_risk_observation():
    return {
        "precipitation": 5.0,
        "roll_3d": 15.0,
        "roll_7d": 20.0,
        "roll_30d": 30.0,
        "cumulative": 100.0,
        "z_score": 0.5,
        "location": "Accra",
    }


@pytest.fixture
def moderate_risk_observation():
    return {
        "precipitation": 25.0,
        "roll_3d": 50.0,
        "roll_7d": 60.0,
        "roll_30d": 70.0,
        "cumulative": 200.0,
        "z_score": 1.5,
        "location": "Accra",
    }


@pytest.fixture
def high_risk_observation():
    return {
        "precipitation": 50.0,
        "roll_3d": 100.0,
        "roll_7d": 120.0,
        "roll_30d": 150.0,
        "cumulative": 500.0,
        "z_score": 2.5,
        "location": "Accra",
    }


@pytest.fixture
def critical_risk_observation():
    return {
        "precipitation": 100.0,
        "roll_3d": 200.0,
        "roll_7d": 250.0,
        "roll_30d": 300.0,
        "cumulative": 1000.0,
        "z_score": 3.5,
        "location": "Accra",
    }


# ============================================================
# ALERT ENGINE FIXTURES
# ============================================================


@pytest.fixture
def mock_provider():
    from src.alerts.providers.mock_provider import MockAlertProvider

    return MockAlertProvider()


@pytest.fixture
def alert_engine(trained_model, mock_provider):
    from src.alerts.engine import AlertEngine

    engine = AlertEngine(
        providers=[mock_provider], alert_threshold=50.0, model=trained_model
    )
    return engine


@pytest.fixture
def api_client():
    """FastAPI test client for API tests."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    return TestClient(app)
