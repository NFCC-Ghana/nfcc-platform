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


def check_model_health() -> Dict[str, Any]:
    """Check model health (no network calls).

    Honesty note for anyone reading this endpoint's output: a "healthy"
    XGBoost model here does NOT mean flood risk scoring is ML-driven.
    grep confirms .predict() is never called anywhere in the live
    request path (src/models/historical_backtest.py's own module
    docstring documents this) - every real score comes from
    calculate_score()'s hand-authored precipitation curve
    (src/alerts/formatter.py). This model is loaded and reported on here
    only so a genuine load failure is visible; it is not part of any
    real prediction today.
    """
    from src.config.settings import settings

    try:
        # This will trigger model load if not already loaded
        model = settings.model
        return {
            "status": "healthy",
            "message": (
                f"Model file loads correctly from {settings.MODEL_PATH}. "
                "Not used in live risk scoring - see calculate_score() "
                "(src/alerts/formatter.py) for the real scoring logic."
            ),
        }
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


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
        "model": check_model_health(),
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
    """Kubernetes readiness probe."""
    model_health = check_model_health()
    if model_health["status"] != "healthy":
        return {"status": "not_ready", "reason": model_health["message"]}

    return {"status": "ready"}
