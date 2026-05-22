"""
NFCC Test Configuration & Shared Fixtures
All pytest fixtures available across all test modules.
"""

from pathlib import Path
from unittest.mock import MagicMock

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "xgboost_flood_risk.pkl"


# ══════════════════════════════════════════════════════════════════════
# GLOBAL RANDOM SEED (reproducibility)
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session", autouse=True)
def set_random_seed():
    np.random.seed(42)
    print("\n🔧 Global random seed set to 42 for test reproducibility")


# ══════════════════════════════════════════════════════════════════════
# SAMPLE DATA FIXTURES
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def low_risk_observation():
    return {
        "precipitation": 0.0,
        "roll_3d": 0.5,
        "roll_7d": 0.3,
        "roll_30d": 1.2,
        "cumulative": 120.0,
        "z_score": -0.5,
    }


@pytest.fixture
def moderate_risk_observation():
    return {
        "precipitation": 8.0,
        "roll_3d": 18.0,
        "roll_7d": 6.5,
        "roll_30d": 4.0,
        "cumulative": 300.0,
        "z_score": 0.8,
    }


@pytest.fixture
def high_risk_observation():
    return {
        "precipitation": 20.0,
        "roll_3d": 45.0,
        "roll_7d": 14.0,
        "roll_30d": 7.5,
        "cumulative": 480.0,
        "z_score": 2.1,
    }


@pytest.fixture
def critical_risk_observation():
    return {
        "precipitation": 45.0,
        "roll_3d": 95.0,
        "roll_7d": 30.0,
        "roll_30d": 14.0,
        "cumulative": 750.0,
        "z_score": 3.8,
    }


# ══════════════════════════════════════════════════════════════════════
# DATAFRAME FIXTURE (NOTE: column is 'risk_score', NOT 'flood_risk_score')
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def sample_dataframe():
    dates = pd.date_range("2024-01-01", periods=365, freq="D")
    np.random.seed(42)
    precip = np.random.exponential(scale=5.0, size=365)
    precip[60:75] = np.random.uniform(20, 50, 15)
    precip[180:195] = np.random.uniform(25, 60, 15)

    df = pd.DataFrame({"precipitation": precip}, index=dates)
    df.index.name = "date"

    df["roll_3d"] = df["precipitation"].rolling(3, min_periods=1).sum()
    df["roll_7d"] = df["precipitation"].rolling(7, min_periods=1).mean()
    df["roll_30d"] = df["precipitation"].rolling(30, min_periods=1).mean()
    df["cumulative"] = df["precipitation"].cumsum()

    roll_mean = df["precipitation"].rolling(30, min_periods=1).mean()
    roll_std = df["precipitation"].rolling(30, min_periods=1).std().fillna(1)
    df["z_score"] = (df["precipitation"] - roll_mean) / roll_std

    def flood_risk_score(row):
        score = min(row["precipitation"] / 30 * 40, 40)
        score += min(row["roll_3d"] / 60 * 35, 35)
        score += min(max(row["z_score"], 0) / 3 * 25, 25)
        return round(score, 2)

    df["risk_score"] = df.apply(flood_risk_score, axis=1)

    def classify(val):
        if val >= 30:
            return "Extreme"
        elif val >= 15:
            return "High"
        elif val >= 5:
            return "Moderate"
        elif val > 0:
            return "Light"
        return "Dry"

    df["rainfall_class"] = df["precipitation"].apply(classify)

    return df


# ══════════════════════════════════════════════════════════════════════
# MODEL FIXTURE (REQUIRED for tests)
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def trained_model():
    """Load real trained model if available, else return mock."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)

    print("\n🔧 Using mock model for tests (real model not found)")
    mock = MagicMock()
    mock.predict.return_value = np.array([42.0])
    mock.feature_importances_ = np.array([0.30, 0.25, 0.20, 0.10, 0.08, 0.07])
    return mock


# ══════════════════════════════════════════════════════════════════════
# API FIXTURE
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def api_client(trained_model):
    import src.api.main as api_module

    original_model = api_module.model
    api_module.model = trained_model

    from src.api.main import app

    client = TestClient(app)

    yield client

    api_module.model = original_model


# ══════════════════════════════════════════════════════════════════════
# ALERT ENGINE FIXTURE (FIXED: engine.model is set correctly)
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_provider():
    from src.alerts.providers.mock_provider import MockAlertProvider

    return MockAlertProvider()


@pytest.fixture
def alert_engine(trained_model, mock_provider):
    from src.alerts.engine import AlertEngine

    engine = AlertEngine(
        providers=[mock_provider],
        alert_threshold=50.0,
        rate_limit_minutes=60,
    )
    # CRITICAL FIX: Set the model on the engine
    engine.model = trained_model
    return engine
