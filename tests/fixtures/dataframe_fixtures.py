"""Test fixtures for pandas DataFrames."""

import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_rainfall_dataframe():
    """Create a sample rainfall DataFrame for testing."""
    dates = pd.date_range('2024-01-01', '2024-01-31', freq='D')
    np.random.seed(42)
    data = {
        'date': dates,
        'precipitation': np.random.exponential(10, len(dates)) + 5,
        'district': ['Accra Central'] * len(dates)
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_district_dataframe():
    """Create a sample district DataFrame for testing."""
    data = {
        'district': ['Accra Central', 'Accra West', 'Tema', 'Kumasi'],
        'population': [187928, 203461, 198742, 443981],
        'elevation': [12, 10, 18, 25],
        'flood_risk_score': [0.92, 0.85, 0.78, 0.45]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_subscription_dataframe():
    """Create a sample subscription DataFrame for testing."""
    data = {
        'email': ['user1@test.com', 'user2@test.com'],
        'phone': ['+233244714242', '+233244714243'],
        'district': ['Accra Central', 'Tema'],
        'preferred_provider': ['email', 'whatsapp'],
        'min_risk_tier': ['HIGH', 'MODERATE']
    }
    return pd.DataFrame(data)
