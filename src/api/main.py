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
from src.alerts.formatter import get_risk_tier
from src.alerts.logger_config import setup_logging
from src.config.settings import settings
from src.database.alert_db import init_subscriptions_table

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


def calculate_score(precipitation: float, temperature: float = None) -> float:
    if precipitation <= 0:
        return 0.0
    elif precipitation < 10:
        return min(100, precipitation * 3)
    elif precipitation < 30:
        return min(100, 30 + (precipitation - 10) * 2)
    elif precipitation < 50:
        return min(100, 70 + (precipitation - 30) * 1.5)
    else:
        return min(100, 95 + (precipitation - 50) * 0.2)


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

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.API_VERSION,
        "model": "loaded" if settings.model else "not loaded"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }

# Score endpoint
@app.post("/score", response_model=ScoreResponse)
async def score(request: ScoreRequest):
    score_value = calculate_score(request.precipitation, request.temperature)
    risk_tier = get_risk_tier(score_value)

    # Send alert if risk is high enough
    alert_sent = False
    if alert_engine and score_value > 50:
        try:
            alert_engine.process(score_value, request.location, request.precipitation)
            alert_sent = True
        except Exception as e:
            logger.error(f"Alert failed: {e}")

    return ScoreResponse(
        location=request.location,
        score=round(score_value, 1),
        risk_tier=risk_tier,
        alert_sent=alert_sent,
        timestamp=datetime.now().isoformat()
    )


# Include all routers
app.include_router(alerts_router)
app.include_router(forecast_router)
app.include_router(explain_fusion_router)
app.include_router(dam_router)
app.include_router(subscriptions_router)
app.include_router(explain_router)
app.include_router(health_router)
