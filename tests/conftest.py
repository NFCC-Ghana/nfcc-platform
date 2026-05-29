# flake8: noqa: E402
"""Pytest configuration and fixtures for NFCC tests."""

# ============================================================
# CRITICAL: Force test environment BEFORE any src imports
# This must be at the VERY TOP of the file
# ============================================================
import os

os.environ["NFCC_ENV"] = "testing"
os.environ["ENVIRONMENT"] = "testing"
os.environ["ALERT_DRY_RUN"] = "true"

# ============================================================
# Now safe to import other modules
# ============================================================
import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all fixtures from fixtures directory
from tests.fixtures.model_fixtures import *  # noqa: E402, F403
from tests.fixtures.dataframe_fixtures import *  # noqa: E402, F403


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line(
        "markers", "provider: marks provider tests that need credentials"
    )


@pytest.fixture(scope="session")
def project_root():
    """Return project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def alert_engine():
    """Create an alert engine with mock provider for testing."""
    from src.alerts.engine import AlertEngine
    from src.alerts.providers.mock_provider import MockAlertProvider

    return AlertEngine(providers=[MockAlertProvider()])


@pytest.fixture
def alert_engine_no_cooldown():
    """AlertEngine with cooldown disabled for testing."""
    from src.alerts.engine import AlertEngine
    from src.alerts.providers.mock_provider import MockAlertProvider

    engine = AlertEngine(providers=[MockAlertProvider()])
    engine.cooldown_minutes = 0
    return engine


@pytest.fixture
def api_client():
    """Create a FastAPI test client."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    return TestClient(app)


# Note: set_test_env fixture is no longer needed because environment
# is already set at the top of the file. Keeping for backward compatibility.
@pytest.fixture(autouse=True)
def set_test_env():
    """Set test environment variables (already set at module level)."""
    # Environment already set at top of file
    yield
    # Do NOT clean up here - would affect other tests


@pytest.fixture(autouse=True)
def suppress_logging():
    """Suppress verbose logging during tests."""
    import logging

    # Set nfcc loggers to WARNING during tests
    for logger_name in ["nfcc", "nfcc-api", "nfcc.alert.engine", "nfcc-api.health"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    yield

    # Restore after tests (optional)
    for logger_name in ["nfcc", "nfcc-api", "nfcc.alert.engine", "nfcc-api.health"]:
        logging.getLogger(logger_name).setLevel(logging.INFO)


@pytest.fixture
def disable_dry_run_for_providers():
    """Disable dry run mode for provider tests that need real SDK calls."""
    import os

    original = os.environ.get("ALERT_DRY_RUN", "true")
    os.environ["ALERT_DRY_RUN"] = "false"
    yield
    os.environ["ALERT_DRY_RUN"] = original
