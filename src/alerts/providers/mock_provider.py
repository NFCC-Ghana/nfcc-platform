"""Mock alert provider for testing."""

import logging
from typing import Dict, Any
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.mock")


class MockAlertProvider(BaseAlertProvider):
    """Mock provider for testing without external dependencies."""

    name = "mock"

    def __init__(self, fail_on_next: bool = False):
        self.fail_on_next = fail_on_next

    def _format_message(self, alert: AlertPayload) -> str:
        return f"[MOCK] {alert.risk_tier} | {alert.location} | Score: {alert.score}"

    def send(self, alert: AlertPayload) -> Dict[str, Any]:
        """Mock send - just logs."""
        if self.fail_on_next:
            self.fail_on_next = False
            raise Exception("Provider crashed")

        logger.info(self._format_message(alert))
        return {
            "success": True,
            "message": f"Mock alert sent to {alert.location}",
            "provider": self.name,
            "mock": True,
        }
