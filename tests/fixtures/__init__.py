"""Test fixtures for NFCC unit and integration tests.

This module provides reusable fixtures for testing:
- Alert engine components
- Database operations
- API endpoints
- Model predictions
"""

import pytest
from pathlib import Path

# Import all fixtures from submodules
from tests.fixtures.dataframe_fixtures import *
from tests.fixtures.model_fixtures import *
from tests.fixtures.provider_fixtures import *

__all__ = [
    # From dataframe_fixtures
    "sample_dataframe",
    "rainfall_dataframe",
    "empty_dataframe",
    # From model_fixtures
    "mock_model",
    "mock_predictions",
    "mock_features",
    # From provider_fixtures
    "mock_provider_config",
    "mock_whatsapp_config",
    "mock_sms_config",
]
