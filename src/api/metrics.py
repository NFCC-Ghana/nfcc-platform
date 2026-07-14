"""Prometheus metrics for production monitoring."""

import time
from functools import wraps

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Metrics definitions
ALERTS_SENT = Counter(
    "nfcc_alerts_sent_total", "Total alerts sent", ["provider", "risk_tier"]
)
ALERTS_FAILED = Counter("nfcc_alerts_failed_total", "Total alerts failed", ["provider"])
SCORE_HISTOGRAM = Histogram("nfcc_score_duration_seconds", "Score calculation duration")
API_REQUESTS = Counter(
    "nfcc_api_requests_total", "Total API requests", ["endpoint", "method"]
)
API_DURATION = Histogram(
    "nfcc_api_duration_seconds", "API request duration", ["endpoint"]
)
ACTIVE_PROVIDERS = Gauge("nfcc_active_providers", "Number of active alert providers")
CIRCUIT_BREAKER_STATE = Gauge(
    "nfcc_circuit_breaker_state", "Circuit breaker state", ["provider"]
)


def track_request(endpoint: str):
    """Decorator to track API requests."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            API_REQUESTS.labels(endpoint=endpoint, method="POST").inc()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                API_DURATION.labels(endpoint=endpoint).observe(duration)

        return wrapper

    return decorator


def get_metrics():
    """Get Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
