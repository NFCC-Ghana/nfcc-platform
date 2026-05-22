"""Core alert engine — receives risk_score, does NOT load model."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.alerts.providers.base import BaseAlertProvider, AlertPayload
from src.alerts.providers.mock_provider import MockAlertProvider
from src.alerts.rate_limit import RateLimiter
from src.alerts.formatter import get_risk_tier
from src.alerts.logger_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger("nfcc.alert.engine")

LOG_PATH = Path("logs/alert_engine.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class AlertEngine:
    """
    Alert engine — orchestrates alert sending.
    Does NOT load the ML model. Receives risk_score from API.
    """

    def __init__(
        self,
        providers: Optional[List[BaseAlertProvider]] = None,
        alert_threshold: float = 50.0,
        rate_limit_minutes: int = 60,  # ✅ REQUIRED FROM origin/main
    ):
        self.providers = providers or [MockAlertProvider()]
        self.alert_threshold = alert_threshold

        # convert minutes → rate limiter config
        self.rate_limiter = RateLimiter(max_alerts_per_hour=3)

        # store config (important for tests / future expansion)
        self.rate_limit_minutes = rate_limit_minutes

        logger.info(
            f"Alert engine initialized | Providers: {[p.name for p in self.providers]}"
        )

    def should_alert(self, risk_score: float) -> bool:
        """Determine if an alert should be triggered."""
        return risk_score >= self.alert_threshold

    def _log_event(self, event: dict):
        """Log event to JSONL file."""
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")

    def process(
        self,
        risk_score: float,
        location: str = "Accra",
        observation: Optional[dict] = None,
        force: bool = False,
    ) -> dict:
        """
        Process a risk score and send alerts if needed.
        """

        risk_tier = get_risk_tier(risk_score)
        alert = self.should_alert(risk_score)
        timestamp = datetime.now().isoformat()

        event = {
            "timestamp": timestamp,
            "location": location,
            "risk_score": round(risk_score, 2),
            "risk_tier": risk_tier,
            "alert": alert,
            "observation": observation or {},
        }

        if not alert:
            logger.info(
                f"[{location}] Score: {risk_score:.1f} | {risk_tier} — no alert"
            )
            self._log_event(event)
            return event

        # Rate limiting
        if not force and not self.rate_limiter.can_send(location):
            remaining = self.rate_limiter.get_remaining(location)
            logger.info(f"[{location}] Rate limited. {remaining} alerts remaining")
            event["rate_limited"] = True
            self._log_event(event)
            return event

        # Build payload safely
        obs = observation or {}

        payload = AlertPayload(
            location=location,
            risk_score=risk_score,
            risk_tier=risk_tier,
            precipitation=obs.get("precipitation", 0.0),
            roll_3d=obs.get("roll_3d", 0.0),
            z_score=obs.get("z_score", 0.0),
            timestamp=timestamp,
        )

        # Dispatch
        results = []
        for provider in self.providers:
            try:
                result = provider.send(payload)
                results.append(result)

                status = "✅" if result["success"] else "❌"
                logger.info(f"{status} [{provider.name}] Alert sent to {location}")

            except Exception as e:
                logger.error(f"Provider {provider.name} crashed: {e}")
                results.append(
                    {"success": False, "provider": provider.name, "error": str(e)}
                )

        self.rate_limiter.record_send(location)

        event["dispatched"] = True
        event["results"] = results
        self._log_event(event)

        logger.warning(f"🚨 ALERT | {location} | Score: {risk_score:.1f} | {risk_tier}")

        return event
