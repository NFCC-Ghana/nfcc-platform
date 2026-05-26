"""Alert engine for processing and sending alerts."""

import logging
from typing import Dict, Any, List, Optional
from src.alerts.models import AlertPayload
from src.alerts.rate_limit import RateLimiter
from src.alerts.provider_factory import ProviderFactory
from src.alerts.cooldown import should_send_alert
from src.config.settings import settings

logger = logging.getLogger("nfcc.alert.engine")


class AlertEngine:
    """Core alert processing engine with singleton providers."""

    THRESHOLDS = {
        "LOW": (0, 30),
        "MODERATE": (30, 50),
        "HIGH": (50, 70),
        "CRITICAL": (70, 85),
        "EXTREME": (85, 101),
    }

    def __init__(self, providers: List[str] = None, alerts_per_hour: int = None):
        """Initialize alert engine with singleton providers."""
        self.alerts_per_hour = alerts_per_hour or settings.ALERTS_PER_HOUR
        self.rate_limiter = RateLimiter(limit=self.alerts_per_hour)

        # Use singleton providers - no duplicate initialization
        self.providers = ProviderFactory.get_providers(providers)

        self.cooldown_minutes = getattr(settings, "ALERT_COOLDOWN_MINUTES", 30)

        logger.info(
            f"Alert engine initialized | Providers: {[p.name for p in self.providers]}"
        )

    def _get_risk_tier(self, score: float) -> str:
        """Determine risk tier from score."""
        for tier, (low, high) in self.THRESHOLDS.items():
            if low <= score < high:
                return tier
        return "EXTREME" if score >= 85 else "LOW"

    def process(
        self,
        location: str,
        score: float,
        force: bool = False,
        precipitation: float = 0.0,
        roll_3d: float = 0.0,
        z_score: float = 0.0,
        message: str = "",
    ) -> Dict[str, Any]:
        """Process a score and send alerts if needed."""

        risk_tier = self._get_risk_tier(score)

        alert = AlertPayload(
            location=location,
            score=score,
            risk_tier=risk_tier,
            message=message or self._get_default_message(risk_tier),
            precipitation=precipitation,
            roll_3d=roll_3d,
            z_score=z_score,
        )

        # Check cooldown first
        if not force and not should_send_alert(
            location,
            score,
            threshold=self.THRESHOLDS["MODERATE"][0],
            cooldown_minutes=self.cooldown_minutes,
        ):
            logger.info(f"[{location}] Score: {score} | {risk_tier} — cooldown active")
            return {
                "alert_sent": False,
                "risk_tier": risk_tier,
                "score": score,
                "reason": f"Cooldown active ({self.cooldown_minutes} minutes)",
            }

        should_alert = score >= self.THRESHOLDS["MODERATE"][0]

        if not should_alert:
            logger.info(f"[{location}] Score: {score} | {risk_tier} — no alert")
            return {
                "alert_sent": False,
                "risk_tier": risk_tier,
                "score": score,
                "reason": f"Score {score} below moderate threshold",
            }

        can_send, remaining = self.rate_limiter.can_send(location)

        if not can_send and not force:
            logger.info(f"[{location}] Rate limited. {remaining} alerts remaining")
            return {
                "alert_sent": False,
                "risk_tier": risk_tier,
                "score": score,
                "reason": f"Rate limited. {remaining} alerts remaining this hour",
            }

        results = []
        for provider in self.providers:
            try:
                result = provider.send(alert)
                results.append(result)

                if result.get("success"):
                    logger.info(f"✅ [{provider.name}] Alert sent to {location}")
                else:
                    logger.error(
                        f"❌ [{provider.name}] Failed: {result.get('message')}"
                    )

            except Exception as e:
                logger.error(f"Provider {provider.name} crashed: {e}")
                results.append(
                    {
                        "success": False,
                        "message": str(e),
                        "provider": provider.name,
                    }
                )

        any_success = any(r.get("success") for r in results)
        if any_success:
            self.rate_limiter.record_send(location)

        logger.warning(f"🚨 ALERT | {location} | Score: {score} | {risk_tier}")

        return {
            "alert_sent": any_success,
            "risk_tier": risk_tier,
            "score": score,
            "providers": results,
            "cooldown_minutes": self.cooldown_minutes,
        }

    def _get_default_message(self, risk_tier: str) -> str:
        messages = {
            "MODERATE": "Moderate flood risk. Monitor conditions.",
            "HIGH": "High flood risk. Take precautions.",
            "CRITICAL": "CRITICAL flood risk. Immediate action required.",
            "EXTREME": "EXTREME flood risk. Emergency response needed.",
        }
        return messages.get(risk_tier, "Flood alert issued.")
