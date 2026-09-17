"""FastAPI main application for NFCC flood alert platform."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.alerts.engine import AlertEngine
from src.api.explain import router as explain_router
from src.api.health import router as health_router
from src.api.dam_router import router as dam_router
from src.api.routes.alerts import router as alerts_router
from src.api.routes.forecast import router as forecast_router
from src.api.routes.explain_fusion import router as explain_fusion_router
from src.api.routes.subscriptions import router as subscriptions_router
from src.api.routes.situation import router as situation_router
from src.api.routes.alert_review import router as alert_review_router
from src.api.routes.cap_export import router as cap_export_router
from src.api.routes.decision_card import router as decision_card_router
from src.api.v1 import router as v1_router
from src.alerts.formatter import calculate_score, get_risk_tier
from src.alerts.district_risk import DISTRICT_PROFILES
from src.alerts.logger_config import setup_logging
from src.config.settings import settings
from src.database.alert_db import init_subscriptions_table, get_alert_history, get_total_alerts_count

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("nfcc-api")

# Global engine instance
alert_engine = None


class ScoreRequest(BaseModel):
    location: str = Field(..., description="District location")
    precipitation: float = Field(..., description="Precipitation in mm", ge=0)
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")


class BatchScoreRequest(BaseModel):
    requests: List[ScoreRequest]


class ScoreResponse(BaseModel):
    location: str
    score: float
    risk_tier: str
    alert_sent: bool
    timestamp: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global alert_engine

    logger.info(f"Starting NFCC Flood Alert Platform v{settings.API_VERSION}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Verify model loads
    try:
        model = settings.model
        logger.info("✅ Model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")

    # Initialize subscription storage
    try:
        init_subscriptions_table()
        logger.info("✅ Subscriptions table initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize subscriptions table: {e}")

    # Initialize alert engine
    alert_engine = AlertEngine()
    logger.info("✅ Alert engine initialized")

    yield

    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="National Flood Intelligence Platform API",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }

# Bare alias for the alerts_router's GET /alerts/history - same
# underlying query functions, trimmed response. /alerts/history is the
# real, fully-featured endpoint (pagination, location filtering, response
# schema); this exists because a bare GET /alerts is also part of the
# documented API surface.
@app.get("/alerts")
async def alerts_root(limit: int = 50):
    return {
        "count": get_total_alerts_count(),
        "data": get_alert_history(limit=limit),
    }


# Districts endpoint - exposes the district risk profiles already used
# internally by src/alerts/district_risk.py (calculate_adjusted_score,
# should_alert_for_district) to adjust scores/thresholds per district, but
# which had no API surface of its own until now.
@app.get("/districts")
async def districts():
    return {
        "count": len(DISTRICT_PROFILES),
        "districts": [
            {
                "name": profile.name,
                "base_risk_factor": profile.base_risk_factor,
                "vulnerability_score": profile.vulnerability_score,
                "historical_flood_probability": profile.historical_flood_probability,
                "effective_threshold": profile.effective_threshold,
            }
            for profile in DISTRICT_PROFILES.values()
        ],
    }


def _score_one(request: ScoreRequest) -> ScoreResponse:
    score_value = calculate_score(request.precipitation, request.temperature)
    risk_tier = get_risk_tier(score_value)

    # Send alert if risk is high enough
    alert_sent = False
    if alert_engine and score_value > 50:
        try:
            # Keyword args, not positional - process()'s signature is
            # (location, score, force, precipitation, ...). A previous
            # positional call here, process(score_value, request.location,
            # request.precipitation), bound score_value to `location`,
            # the location string to `score`, and precipitation to the
            # `force` bool flag - every alert triggered from this endpoint
            # was recorded under a numeric "location" with a location-name
            # "score". alert_sent is also the engine's own real result now,
            # not just "the call didn't raise" - a provider genuinely
            # failing to send still reported alert_sent: true before this.
            result = alert_engine.process(
                location=request.location,
                score=score_value,
                precipitation=request.precipitation,
            )
            alert_sent = result.get("alert_sent", False)
        except Exception as e:
            logger.error(f"Alert failed: {e}")

    return ScoreResponse(
        location=request.location,
        score=round(score_value, 1),
        risk_tier=risk_tier,
        alert_sent=alert_sent,
        timestamp=datetime.now().isoformat()
    )


# Score endpoint
@app.post("/score", response_model=ScoreResponse)
async def score(request: ScoreRequest):
    return _score_one(request)


# Batch score endpoint - BatchScoreRequest already existed as a model with
# no route ever built for it. Scores each request the same way /score
# does (same alert side effects per location), sequentially - the alert
# engine's own rate limiter is what actually protects a real burst of
# locations from over-alerting, not anything batch-specific here.
@app.post("/score/batch", response_model=List[ScoreResponse])
async def score_batch(request: BatchScoreRequest):
    return [_score_one(r) for r in request.requests]


# Include all routers
app.include_router(alerts_router)
app.include_router(forecast_router)
app.include_router(explain_fusion_router)
app.include_router(dam_router)
app.include_router(subscriptions_router)
app.include_router(explain_router)
app.include_router(health_router)
app.include_router(situation_router)
app.include_router(alert_review_router)
app.include_router(cap_export_router)
app.include_router(decision_card_router)
app.include_router(v1_router)

# Ensure database is initialized on startup
from src.database.alert_db import init_db
from src.database.risk_history_db import init_risk_history_table
init_db()
init_risk_history_table()
