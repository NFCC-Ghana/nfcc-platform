"""API routes package."""

from src.api.routes.alerts import router as alerts_router
from src.api.routes.forecast import router as forecast_router
from src.api.routes.explain_fusion import router as explain_fusion_router

__all__ = [
    "alerts_router",
    "forecast_router",
    "explain_fusion_router",
]
