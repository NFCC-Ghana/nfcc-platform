"""API route modules for alerts, forecast, and explainability."""

from .alerts import router as alerts_router
from .forecast import router as forecast_router
from .explain_fusion import router as explain_fusion_router

__all__ = [
    "alerts_router",
    "forecast_router",
    "explain_fusion_router",
]
