"""Test fixtures for NFCC platform.

This module provides reusable fixtures for all tests.
"""

# DataFrame fixtures
from tests.fixtures.dataframe_fixtures import (
    district_rainfall_dict,
    empty_dataframe,
    sample_features_dataframe,
    sample_rainfall_dataframe,
)

# Model fixtures
from tests.fixtures.model_fixtures import (
    mock_model,
)
from tests.fixtures.model_fixtures import sample_alert_payload as model_sample_alert
from tests.fixtures.model_fixtures import (
    trained_model,
)

# Provider fixtures (using correct names from provider_fixtures.py)
from tests.fixtures.provider_fixtures import (
    mock_email_config,
    mock_sms_config,
    mock_whatsapp_config,
)
from tests.fixtures.provider_fixtures import (
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
