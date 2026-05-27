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
    """Check model health (no network calls)."""
    from src.config.settings import settings

    try:
        # This will trigger model load if not already loaded
        model = settings.model
        return {
            "status": "healthy",
            "message": f"Model loaded from {settings.MODEL_PATH}",
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
        "providers": {
            "whatsapp": (
                {"status": "configured"}
                if provider_status["whatsapp"]
                else {"status": "disabled"}
            ),
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
