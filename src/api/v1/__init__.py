"""Versioned (/v1) API surface - stable contracts for districts, risk,
forecast, alerts, evidence, operational resources, AI decisions,
historical risk, and data-source health.

Rollout is deliberately additive (see src/api/v1/districts.py's module
docstring): every /v1 route is mounted alongside the existing unversioned
routes it supersedes, which stay exactly as they are. Nothing that
already depends on the current API surface breaks when /v1 routes are
added; the dashboard (and any other consumer) migrates to /v1 endpoint
by endpoint, on its own schedule.

src/api/v1/districts.py is the first contract built and the pattern the
rest follow. Each new /v1/<concern>.py module gets included below as it
lands.
"""

from fastapi import APIRouter

from src.api.v1.districts import router as districts_router
from src.api.v1.forecast import router as forecast_router
from src.api.v1.risk import router as risk_router

router = APIRouter(prefix="/v1")
router.include_router(districts_router)
router.include_router(risk_router)
router.include_router(forecast_router)
