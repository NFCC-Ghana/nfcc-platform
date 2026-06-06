"""Test fixtures for NFCC platform.

This module provides reusable fixtures for all tests.
"""

# Model fixtures
from tests.fixtures.model_fixtures import (
    trained_model,
    mock_model,
    sample_alert_payload as model_sample_alert,
)

# DataFrame fixtures
from tests.fixtures.dataframe_fixtures import (
    sample_rainfall_dataframe,
    sample_features_dataframe,
    empty_dataframe,
    district_rainfall_dict,
)

# Provider fixtures (using correct names from provider_fixtures.py)
from tests.fixtures.provider_fixtures import (
    mock_email_config,
    mock_sms_config,
    mock_whatsapp_config,
    sample_alert_payload as provider_sample_alert,
)

# Re-export commonly used fixtures
__all__ = [
    # Model fixtures
    "trained_model",
    "mock_model",
    # DataFrame fixtures
    "sample_rainfall_dataframe",
    "sample_features_dataframe",
    "empty_dataframe",
    "district_rainfall_dict",
    # Provider fixtures
    "mock_email_config",
    "mock_sms_config",
    "mock_whatsapp_config",
    "sample_alert_payload",
]

# Create an alias for sample_alert_payload to avoid confusion
sample_alert_payload = provider_sample_alert
