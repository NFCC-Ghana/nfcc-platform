"""Mock alert provider for testing — no real messages sent."""

import logging
from src.alerts.providers.base import BaseAlertProvider, AlertPayload

logger = logging.getLogger("nfcc.alert.mock")


class MockAlertProvider(BaseAlertProvider):
    """Mock provider that prints alerts to console."""

    name = "mock"

    def send(self, payload: AlertPayload) -> dict:
        logger.info(
            f"[MOCK ALERT] {payload.risk_tier} | "
            f"{payload.location} | Score: {payload.risk_score:.1f}"
        )
        print("\n" + "=" * 60)
        print(f"  [MOCK] ALERT WOULD BE SENT TO: {payload.location}")
        print("=" * 60)
        print(payload.message)
        print("=" * 60 + "\n")
        return {
            "success": True,
            "provider": self.name,
            "message_id": f"mock-{payload.timestamp}",
            "error": None,
        }
