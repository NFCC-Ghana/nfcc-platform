"""Production health check endpoints - no startup network calls."""

import logging
from typing import Dict, Any
from fastapi import APIRouter

logger = logging.getLogger("nfcc-api.health")

router = APIRouter(tags=["health"])


def check_twilio_health() -> Dict[str, Any]:
    """Check Twilio configuration (no network calls)."""
    from src.config.settings import settings

    if not settings.TWILIO_ACCOUNT_SID:
        return {"status": "disabled", "message": "Missing Twilio credentials"}

    # Just return configured status without network call
    return {"status": "configured", "message": "Twilio credentials present"}


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check - no startup network calls."""
    from src.config.settings import settings
    from src.alerts.cooldown import is_redis_available

    provider_status = settings.get_provider_status()
    is_dry_run = getattr(settings, "ALERT_DRY_RUN", False)

    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.API_VERSION,
        "dry_run": is_dry_run,
        # Previously only ever reported "whatsapp" - sms/email silently
        # never appeared here at all, so a real gap (all three currently
        # disabled, alert dispatch falls back to MockAlertProvider -
        # src/alerts/provider_factory.py) had no visible signal anywhere
        # in this endpoint.
        "providers": {
            "whatsapp": (
                {"status": "configured"}
                if provider_status["whatsapp"]
                else {"status": "disabled"}
            ),
            "telegram": (
                {"status": "configured"}
                if provider_status["telegram"]
                else {"status": "disabled"}
            ),
            "sms": (
                {"status": "configured"}
                if provider_status["sms"]
                else {"status": "disabled"}
            ),
            "email": (
                {"status": "configured"}
                if provider_status["email"]
                else {"status": "disabled"}
            ),
            "using_mock_provider": not any(provider_status.values()),
        },
        "redis": {
            "available": is_redis_available(),
            "configured": bool(getattr(settings, "REDIS_URL", None)),
        },
        "config": {
            "alerts_per_hour": settings.ALERTS_PER_HOUR,
            "rate_limit": f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_PERIOD}s",
        },
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes readiness probe. Used to gate on a model file load
    (models/xgboost_flood_risk.pkl, removed - confirmed never used in
    live risk scoring and, when tested against real historical flood
    events, showed no reliable improvement over calculate_score()) -
    that was never a meaningful readiness signal anyway, since nothing
    this service actually serves depended on the model loading."""
    return {"status": "ready"}
