import logging
from typing import Dict, Any
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.models import AlertPayload

logger = logging.getLogger("nfcc.alert.mock")


class MockAlertProvider(BaseAlertProvider):
    name = "mock"

    def send(self, payload: AlertPayload) -> Dict[str, Any]:
        logger.info(
            "[MOCK ALERT] %s | %s | Score: %.1f",
            payload.risk_tier,
            payload.location,
            payload.score,
        )
        print("\n" + "=" * 60)
        print(f"  [MOCK] ALERT TO: {payload.location}")
        print("=" * 60)
        print(f"  Risk Tier : {payload.risk_tier}")
        print(f"  Risk Score: {payload.score:.1f}/100")
        print("-" * 60)
        print(f"  {payload.message if payload.message else 'No message'}")
        print("=" * 60 + "\n")
        return {
            "success": True,
            "provider": self.name,
            "message_id": f"mock-{payload.timestamp}",
        }
