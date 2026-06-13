"""Model fixtures for ML and scoring tests."""

from pathlib import Path

import joblib
import pytest
from sklearn.dummy import DummyRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "xgboost_flood_risk.pkl"
FEATURE_COLS = [
    "precipitation",
    "roll_3d",
    "roll_7d",
    "roll_30d",
    "cumulative",
    "z_score",
]


@pytest.fixture(scope="session")
def model_path():
    """Return path to the trained flood-risk model."""
    return DEFAULT_MODEL_PATH


@pytest.fixture(scope="session")
def flood_risk_model(model_path):
    """
    Load the XGBoost flood-risk model when available.

    Falls back to a dummy regressor so tests can run without a trained artifact.
    """
    if model_path.exists():
        return joblib.load(model_path)

    model = DummyRegressor(strategy="constant", constant=25.0)
    model.fit([[0.0] * len(FEATURE_COLS)], [25.0])
    return model


@pytest.fixture
def feature_columns():
    """Standard feature column names used by the flood-risk model."""
    return FEATURE_COLS.copy()
