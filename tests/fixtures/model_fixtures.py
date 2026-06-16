"""Test fixtures for ML models."""

import pytest
import numpy as np
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor


@pytest.fixture
def mock_xgboost_model():
    """Create a mock XGBoost model for testing."""
    model = XGBRegressor(n_estimators=10, max_depth=3)
    # Create dummy data to train a minimal model
    X = np.random.randn(100, 5)
    y = np.random.randn(100)
    model.fit(X, y)
    return model


@pytest.fixture
def mock_random_forest_model():
    """Create a mock Random Forest model for testing."""
    model = RandomForestRegressor(n_estimators=10, max_depth=3, random_state=42)
    X = np.random.randn(100, 5)
    y = np.random.randn(100)
    model.fit(X, y)
    return model


@pytest.fixture
def mock_model_predictions():
    """Return mock model predictions."""
    def _predict(features):
        return np.random.randn(len(features))
    return _predict


@pytest.fixture
def sample_features():
    """Return sample feature data for testing."""
    return {
        "precipitation": 45.5,
        "precipitation_7d_avg": 30.2,
        "precipitation_30d_avg": 25.1,
        "elevation": 12.0,
        "slope": 2.5,
        "population_density": 4132,
        "flood_history_score": 0.85
    }
