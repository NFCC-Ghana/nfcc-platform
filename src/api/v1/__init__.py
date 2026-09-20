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

from src.api.v1.alerts import router as alerts_router
from src.api.v1.antecedent_rainfall import router as antecedent_rainfall_router
from src.api.v1.backtest import router as backtest_router
from src.api.v1.community_reports import router as community_reports_router
from src.api.v1.copilot import router as copilot_router
from src.api.v1.data_quality import router as data_quality_router
from src.api.v1.decision import router as decision_router
from src.api.v1.districts import router as districts_router
from src.api.v1.evidence import router as evidence_router
from src.api.v1.fluvial_risk import router as fluvial_risk_router
from src.api.v1.forecast import router as forecast_router
from src.api.v1.observations import router as observations_router
from src.api.v1.predictions import router as predictions_router
from src.api.v1.health import router as v1_health_router
from src.api.v1.resources import router as resources_router
from src.api.v1.risk import router as risk_router
from src.api.v1.risk_history import router as risk_history_router
from src.api.v1.verification import router as verification_router

router = APIRouter(prefix="/v1")
router.include_router(districts_router)
router.include_router(risk_router)
router.include_router(forecast_router)
router.include_router(evidence_router)
router.include_router(resources_router)
router.include_router(decision_router)
router.include_router(risk_history_router)
router.include_router(alerts_router)
router.include_router(v1_health_router)
router.include_router(backtest_router)
router.include_router(verification_router)
router.include_router(antecedent_rainfall_router)
router.include_router(fluvial_risk_router)
router.include_router(data_quality_router)
router.include_router(observations_router)
router.include_router(predictions_router)
router.include_router(copilot_router)
router.include_router(community_reports_router)
