import json
import logging
from typing import Any, Dict, List, Optional
from src.alerts.models import AlertPayload

logger = logging.getLogger(__name__)


class AlertEngine:
    def __init__(
        self,
        providers: Optional[List[Any]] = None,
        rate_limiter: Optional[Any] = None,
        alert_threshold: float = 0.0,
        log_file: str = "alerts.log",
        **kwargs,
    ):
        self.providers = providers or []
        self.rate_limiter = rate_limiter
        self.alert_threshold = alert_threshold
        self.model = kwargs.get("model")
        logger.info(
            "Alert engine initialized | Providers: %s | Threshold: %.1f",
            [getattr(p, "name", p.__class__.__name__) for p in self.providers],
            self.alert_threshold,
        )

    def process(
        self, location: str = None, score: float = None, force: bool = False, **kwargs
    ):
        # Handle dict payload (test compatibility)
        if isinstance(location, dict) and score is None:
            payload = location
            location = payload.get("location")
            score = payload.get("score") or payload.get("risk_score")
            force = payload.get("force", force)

        if not location or score is None:
            raise TypeError(f"Missing required: location={location}, score={score}")

        if score < self.alert_threshold and not force:
            return {"sent": 0, "failed": 0, "dispatched": False, "blocked": False}

        if not self.providers:
            return {"sent": 0, "failed": 0, "dispatched": False, "blocked": False}

        if self.rate_limiter and not force:
            if not self.rate_limiter.can_send(location):
                return {"sent": 0, "failed": 0, "dispatched": False, "blocked": True}

        tier = kwargs.get("tier") or (
            "CRITICAL"
            if score >= 80
            else "HIGH" if score >= 60 else "MODERATE" if score >= 40 else "LOW"
        )
        payload = AlertPayload(
            location=location,
            score=score,
            risk_tier=tier,
            message=kwargs.get(
                "message",
                f"ALERT: {tier} flood risk in {location} (Score: {score:.1f})",
            ),
            precipitation=kwargs.get("precipitation", 0.0),
            roll_3d=kwargs.get("roll_3d", 0.0),
            z_score=kwargs.get("z_score", 0.0),
        )

        sent, failed = 0, 0
        for provider in self.providers:
            try:
                provider.send(payload)
                sent += 1
                logger.info(
                    "✅ [%s] Alert sent to %s",
                    getattr(provider, "name", "unknown"),
                    location,
                )
            except Exception as e:
                failed += 1
                logger.error("💥 Provider crashed: %s", e)

        if self.rate_limiter and sent > 0:
            self.rate_limiter.record_send(location)

        return {
            "sent": sent,
            "failed": failed,
            "dispatched": sent > 0,
            "blocked": False,
        }

    def send_alert(self, location: str = None, risk_score: float = None, **kwargs):
        score = risk_score or kwargs.get("score")
        return self.process(location=location, score=score, **kwargs)
