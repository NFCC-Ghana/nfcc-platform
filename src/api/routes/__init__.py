"""API route modules for alerts and related endpoints."""

from .alerts import router as alerts_router
from .subscriptions import router as subscriptions_router

__all__ = ["alerts_router", "subscriptions_router"]
