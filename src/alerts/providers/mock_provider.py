"""Mock alert provider for testing — no real messages sent."""

import logging
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.mock")


class MockAlertProvider(BaseAlertProvider):
    """Mock provider that prints alerts to console."""
    
    name = "mock"
    
    def send(self, payload: AlertPayload) -> dict:
        # Use payload.score (not risk_score)
        logger.info(
            "[MOCK] %s | %s | Score: %.1f",
            payload.risk_tier,
            payload.location,
            payload.score,
        )
        print("\n" + "=" * 50)
        print(f"  [MOCK] ALERT: {payload.location}")
        print("=" * 50)
        print(f"  Risk Tier : {payload.risk_tier}")
        print(f"  Risk Score: {payload.score:.1f}/100")
        print("-" * 50)
        print(f"  {payload.message}")
        print("=" * 50 + "\n")
        
        return {
            "success": True,
            "provider": self.name,
            "message_id": f"mock-{payload.timestamp}",
        }
