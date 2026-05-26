"""Advanced health metrics endpoint."""

import time
import psutil
import logging
from typing import Dict, Any
from fastapi import APIRouter
from src.config.settings import settings
from src.alerts.rate_limit import RateLimiter
from src.alerts.cooldown import is_redis_available

logger = logging.getLogger("nfcc-api.metrics")

router = APIRouter(tags=["metrics"])

# Track metrics
_metrics_cache = {}
_metrics_last_update = 0
_metrics_ttl = 30  # seconds


def collect_system_metrics() -> Dict[str, Any]:
    """Collect system-level metrics."""
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available // (1024 * 1024),
            "disk_usage_percent": psutil.disk_usage("/").percent,
        }
    except:
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_available_mb": 0,
            "disk_usage_percent": 0,
        }


def collect_alert_metrics() -> Dict[str, Any]:
    """Collect alert-specific metrics."""
    from src.alerts.engine import AlertEngine

    # These would need to be tracked properly in production
    return {
        "alerts_sent_today": 0,  # Would need persistent storage
        "active_cooldowns": 0,  # Would need Redis scan
        "rate_limit_remaining": 100,
    }


def collect_provider_metrics() -> Dict[str, Any]:
    """Collect provider performance metrics."""
    return {
        "whatsapp": {
            "status": "healthy",
            "latency_ms": 0,
            "error_rate": 0,
        }
    }


@router.get("/metrics/deep")
async def deep_metrics() -> Dict[str, Any]:
    """Return deep operational metrics."""
    global _metrics_cache, _metrics_last_update

    now = time.time()

    # Return cached metrics if fresh
    if now - _metrics_last_update < _metrics_ttl:
        return _metrics_cache

    metrics = {
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": 0,  # Would need startup tracking
        "system": collect_system_metrics(),
        "alert": collect_alert_metrics(),
        "providers": collect_provider_metrics(),
        "redis": {
            "available": is_redis_available(),
            "configured": bool(getattr(settings, "REDIS_URL", None)),
        },
        "celery": {"available": False, "queue_depth": 0},  # Would need to check worker
    }

    _metrics_cache = metrics
    _metrics_last_update = now
    return metrics


@router.get("/metrics/queue")
async def queue_metrics() -> Dict[str, Any]:
    """Get queue depth metrics."""
    # Placeholder - would need Redis/Celery monitoring
    return {
        "pending_alerts": 0,
        "processing_alerts": 0,
        "failed_alerts": 0,
        "queue_latency_seconds": 0,
    }
