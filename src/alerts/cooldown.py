"""Alert cooldown system - Redis-backed with memory fallback."""

import logging
import time
from threading import Lock
from typing import Dict

logger = logging.getLogger("nfcc.alert.cooldown")

# Memory fallback (when Redis is not available)
_memory_cooldown: Dict[str, float] = {}
_memory_lock = Lock()
_redis_client = None
_redis_available = None


def get_redis_client():
    """Lazy load Redis client."""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("✅ Redis connected for cooldown")
        _redis_available = True
        return _redis_client
    except ImportError:
        logger.debug("Redis not installed - using memory cooldown")
        _redis_available = False
        return None
    except Exception as e:
        logger.debug(f"Redis connection failed: {e} - using memory cooldown")
        _redis_available = False
        return None


def is_redis_available() -> bool:
    """Check if Redis is available."""
    return get_redis_client() is not None


def get_cooldown_key(location: str) -> str:
    """Get Redis key for cooldown."""
    return f"nfcc:cooldown:{location}"


def should_send_alert(
    location: str, score: float, threshold: float = 30, cooldown_minutes: int = 30
) -> bool:
    """
    Check if an alert should be sent.

    Falls back to memory-only mode if Redis is unavailable.
    """
    if score < threshold:
        return False

    redis_client = get_redis_client()

    if redis_client:
        # Redis mode - distributed cooldown
        key = get_cooldown_key(location)
        if redis_client.exists(key):
            ttl = redis_client.ttl(key)
            logger.debug(f"[{location}] Cooldown active (Redis), {ttl}s remaining")
            return False

        # Set cooldown
        redis_client.setex(key, cooldown_minutes * 60, str(score))
        logger.debug(
            f"[{location}] Cooldown set (Redis) for {cooldown_minutes} minutes"
        )
        return True

    else:
        # Memory fallback mode (single worker)
        with _memory_lock:
            now = time.time()
            last_alert = _memory_cooldown.get(location, 0)

            if now - last_alert < (cooldown_minutes * 60):
                remaining = int((cooldown_minutes * 60) - (now - last_alert))
                logger.debug(
                    f"[{location}] Cooldown active (memory), {remaining}s remaining"
                )
                return False

            _memory_cooldown[location] = now
            logger.debug(
                f"[{location}] Cooldown set (memory) for {cooldown_minutes} minutes"
            )
            return True


def clear_cooldown(location: str) -> None:
    """Clear cooldown for a location (for testing/override)."""
    redis_client = get_redis_client()

    if redis_client:
        key = get_cooldown_key(location)
        redis_client.delete(key)
        logger.info(f"[{location}] Cooldown cleared (Redis)")
    else:
        with _memory_lock:
            _memory_cooldown.pop(location, None)
            logger.info(f"[{location}] Cooldown cleared (memory)")
