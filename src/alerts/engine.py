"""Alert engine for processing and sending alerts."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from src.alerts.cooldown import should_send_alert
from src.alerts.models import AlertPayload
from src.alerts.provider_factory import ProviderFactory
from src.alerts.providers.base import BaseAlertProvider
from src.alerts.rate_limit import RateLimiter
from src.config.settings import settings
from src.database.alert_db import save_alert

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

    def __init__(
        self,
        providers: List[Union[str, BaseAlertProvider]] = None,
        alerts_per_hour: int = None,
    ):
        """Initialize alert engine with providers (accepts both names and instances)."""
        self.alerts_per_hour = alerts_per_hour or settings.ALERTS_PER_HOUR
        self.rate_limiter = RateLimiter(limit=self.alerts_per_hour)

        # Handle providers that are instances vs names
        self.providers = self._resolve_providers(providers)
        self.cooldown_minutes = getattr(settings, "ALERT_COOLDOWN_MINUTES", 30)

        logger.info(
            f"Alert engine initialized | Providers: {[p.name for p in self.providers]}"
        )

    def _resolve_providers(
        self, providers: List[Union[str, BaseAlertProvider]] = None
    ) -> List[BaseAlertProvider]:
        """Resolve providers from names or instances."""
        if providers is None:
            # Use default from factory
            return ProviderFactory.get_providers(None)

        result = []
        for p in providers:
            if isinstance(p, str):
                # It's a name - use factory
                factory_result = ProviderFactory.get_providers([p])
                result.extend(factory_result)
            elif isinstance(p, BaseAlertProvider):
                # It's already a provider instance
                result.append(p)
            else:
                logger.warning(f"Unknown provider type: {p}")

        # Ensure we have at least one provider
        if not result:
            result = ProviderFactory.get_providers(["mock"])

        return result

    def _get_risk_tier(self, score: float) -> str:
        """Determine risk tier from score."""
        for tier, (low, high) in self.THRESHOLDS.items():
            if low <= score < high:
                return tier
        return "EXTREME"

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

        # Check cooldown
        threshold = self.THRESHOLDS["MODERATE"][0]
        if not force and not should_send_alert(
            location, score, threshold, self.cooldown_minutes
        ):
            return {
                "alert_sent": False,
                "risk_tier": risk_tier,
                "score": score,
                "reason": f"Cooldown active ({self.cooldown_minutes} minutes)",
            }

        if score < threshold:
            return {
                "alert_sent": False,
                "risk_tier": risk_tier,
                "score": score,
                "reason": f"Score {score} below moderate threshold",
            }

        can_send, remaining = self.rate_limiter.can_send(location)
        if not can_send and not force:
            return {
                "alert_sent": False,
                "risk_tier": risk_tier,
                "score": score,
                "reason": f"Rate limited. {remaining} alerts remaining",
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
                    {"success": False, "message": str(e), "provider": provider.name}
                )

        any_success = any(r.get("success") for r in results)
        if any_success:
            self.rate_limiter.record_send(location)

        logger.warning(f"🚨 ALERT | {location} | Score: {score} | {risk_tier}")

        # Save alert to database for persistence and analytics
        self._save_alert_to_db(
            location=location,
            score=score,
            risk_tier=risk_tier,
            alert_sent=any_success,
            provider_results=results,
        )

        return {
            "alert_sent": any_success,
            "risk_tier": risk_tier,
            "score": score,
            "providers": results,
            "cooldown_minutes": self.cooldown_minutes,
        }

    def _save_alert_to_db(
        self,
        location: str,
        score: float,
        risk_tier: str,
        alert_sent: bool,
        provider_results: List[Dict[str, Any]],
    ) -> None:
        """
        Save alert to SQLite database after processing.

        Logs each provider's attempt separately if multiple providers were tried.
        For each provider result, creates a database record capturing:
        - Provider name that attempted to send the alert
        - Message ID if the send was successful
        - Error details if the send failed

        Args:
            location: Geographic location of the alert
            score: Alert risk score
            risk_tier: Categorical risk level (LOW, MODERATE, HIGH, CRITICAL, EXTREME)
            alert_sent: Whether at least one provider succeeded
            provider_results: List of result dicts from each provider
        """
        try:
            # Generate timestamp in ISO format
            timestamp = datetime.utcnow().isoformat() + "Z"

            # Save a record for each provider's attempt
            for result in provider_results:
                alert_record = {
                    "timestamp": timestamp,
                    "location": location,
                    "risk_score": score,
                    "risk_tier": risk_tier,
                    "alert_sent": result.get("success", False),
                    "provider": result.get("provider", "unknown"),
                    "message_id": result.get("message_id"),  # Present if successful
                    "error": (
                        None if result.get("success") else result.get("message")
                    ),  # Error if failed
                }

                # Insert into database
                alert_id = save_alert(alert_record)
                logger.debug(
                    f"Saved alert to DB | ID: {alert_id} | "
                    f"Provider: {alert_record['provider']} | "
                    f"Success: {alert_record['alert_sent']}"
                )

        except Exception as e:
            # Log but don't raise - database errors should not break alert processing
            logger.error(f"Failed to save alert to database: {str(e)}")

    def _get_default_message(self, risk_tier: str) -> str:
        messages = {
            "MODERATE": "Moderate flood risk. Monitor conditions.",
            "HIGH": "High flood risk. Take precautions.",
            "CRITICAL": "CRITICAL flood risk. Immediate action required.",
            "EXTREME": "EXTREME flood risk. Emergency response needed.",
        }
        return messages.get(risk_tier, "Flood alert issued.")
