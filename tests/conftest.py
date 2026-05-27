"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add src to path - MUST be before imports from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.config.settings import settings
from src.alerts.engine import AlertEngine
from src.alerts.providers.mock_provider import MockAlertProvider
from src.alerts.provider_factory import ProviderFactory


@pytest.fixture(autouse=True)
def reset_provider_factory():
    """Reset provider factory before each test to ensure isolation."""
    ProviderFactory.reset()
    yield
    ProviderFactory.reset()


@pytest.fixture
def api_client():
    """Create a test client for the FastAPI app."""
    from src.api.main import app
    return TestClient(app)


@pytest.fixture
def alert_engine():
    """Create an alert engine for testing."""
    return AlertEngine(providers=[MockAlertProvider()])


@pytest.fixture
def trained_model():
    """Return a mock trained model."""
    class MockModel:
        def predict(self, X):
            return np.array([50.0] * len(X))
    return MockModel()


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for feature engineering tests."""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(365)]
    np.random.seed(42)
    rainfall = np.random.gamma(2, 5, 365)
    
    df = pd.DataFrame({
        'time': dates,
        'precipitation': rainfall,
        'roll_7d': np.convolve(rainfall, np.ones(7)/7, mode='same'),
        'roll_30d': np.convolve(rainfall, np.ones(30)/30, mode='same'),
        'cumulative': np.cumsum(rainfall),
        'z_score': (rainfall - np.mean(rainfall)) / np.std(rainfall)
    })
    df.set_index('time', inplace=True)
    return df


@pytest.fixture
def sample_dataframe_with_features(sample_dataframe):
    """Enhanced dataframe with all required ML features."""
    df = sample_dataframe.copy()
    df['roll_3d'] = df['precipitation'].rolling(3, min_periods=1).mean()
    df['roll_7d'] = df['precipitation'].rolling(7, min_periods=1).mean()
    df['roll_30d'] = df['precipitation'].rolling(30, min_periods=1).mean()
    df['cumulative'] = df['precipitation'].cumsum()
    mean_rain = df['precipitation'].mean()
    std_rain = df['precipitation'].std()
    df['z_score'] = (df['precipitation'] - mean_rain) / (std_rain + 0.001)
    return df


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("NFCC_ENV", "testing")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "test_sid")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test_token")
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "whatsapp:+1234567890")
    monkeypatch.setenv("ALERT_WHATSAPP_RECIPIENTS", "whatsapp:+1234567890")
    monkeypatch.setenv("ALERT_DRY_RUN", "true")
    return monkeypatch
