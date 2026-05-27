"""FastAPI main application for NFCC flood alert platform."""

import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from src.alerts.engine import AlertEngine
from src.alerts.formatter import get_risk_tier
from src.alerts.logger_config import setup_logging
from src.config.settings import settings

# Import routers (SHAP explainability from PR #13)
from src.api import explain

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("nfcc-api")

# Global engine instance
alert_engine = None

# ── Load Model (optional at import so pytest/CI can patch before scoring) ──
model: Optional[Any] = None
MODEL_PATH = Path(settings.MODEL_PATH)
if MODEL_PATH.exists():
    import joblib

    model = joblib.load(MODEL_PATH)
    logger.info("✅ Model loaded from %s", MODEL_PATH)
else:
    logger.warning(
        "No model file at %s — scoring routes return 503 until it exists or tests inject a mock.",
        MODEL_PATH,
    )


# ============================================================
# SCHEMAS
# ============================================================


class RainfallInput(BaseModel):
    """Rainfall input for scoring."""

    location: str
    precipitation: float = Field(..., ge=0, description="Rainfall in mm")

    @field_validator("precipitation")
    def validate_precipitation(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Precipitation cannot be negative")
        return v


class RiskResponse(BaseModel):
    """Risk scoring response."""

    location: str
    risk_score: float
    risk_tier: str
    alert_triggered: bool
    timestamp: str


class ScoreRequest(BaseModel):
    """Score request model."""

    location: str = Field(..., description="District location")
    precipitation: float = Field(..., description="Precipitation in mm", ge=0)
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Accra Central",
                "precipitation": 45.5,
                "temperature": 28.0,
            }
        }


class BatchScoreRequest(BaseModel):
    """Batch score request model."""

    requests: List[ScoreRequest]


class ScoreResponse(BaseModel):
    """Score response model with timestamp."""

    location: str
    score: float
    risk_tier: str
    alert_sent: bool
    timestamp: str = Field(..., description="ISO format timestamp")


def calculate_score(precipitation: float, temperature: float = None) -> float:
    """Calculate flood risk score from precipitation."""
    if precipitation <= 0:
        return 0.0
    elif precipitation < 10:
        return precipitation * 3
    elif precipitation < 30:
        return 30 + (precipitation - 10) * 1.5
    elif precipitation < 60:
        return 60 + (precipitation - 30) * 0.83
    else:
        return min(100, 85 + (precipitation - 60) * 0.375)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global alert_engine

    logger.info(f"Starting NFCC Flood Alert Platform v{settings.API_VERSION}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Use the already-loaded model if available, otherwise settings.model
    try:
        if model is not None:
            logger.info("✅ Model already loaded at import")
        else:
            _ = settings.model
            logger.info("✅ Model loaded via settings")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")

    alert_engine = AlertEngine()
    logger.info("✅ Alert engine initialized")

    yield

    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (SHAP explainability from PR #13)
app.include_router(explain.router)


# ============================================================
# ENDPOINTS
# ============================================================


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint."""
    from src.api.health import health_check

    return await health_check()


@app.get("/districts")
async def get_districts() -> Dict[str, Any]:
    """Get list of available districts."""
    districts = [
        "Accra Central",
        "Accra East",
        "Accra West",
        "Tema",
        "Kumasi",
        "Takoradi",
        "Tamale",
        "Cape Coast",
        "Koforidua",
        "Ho",
    ]
    return {"status": "success", "districts": districts, "count": len(districts)}


@app.get("/alerts")
async def get_alerts() -> Dict[str, Any]:
    """Get recent alerts."""
    return {
        "status": "success",
        "alerts": [],
        "message": "Alert history endpoint - implement with database for production",
    }


@app.post("/score", response_model=RiskResponse, tags=["Scoring"])
async def score_single(
    payload: RainfallInput,
    background_tasks: BackgroundTasks,
) -> RiskResponse:
    """Calculate flood risk score and trigger alerts."""
    from datetime import datetime

    score = calculate_score(payload.precipitation)
    risk_tier = get_risk_tier(score)

    send_alert = score >= 30

    alert_sent = False
    if alert_engine and send_alert:
        result = alert_engine.process(
            location=payload.location,
            score=score,
            precipitation=payload.precipitation,
            message=f"Flood risk detected with {payload.precipitation:.1f}mm rainfall",
        )
        alert_sent = result.get("alert_sent", False)

    logger.info(
        f"Scored | {payload.location} | {score:.1f} | {risk_tier} | alert={alert_sent}"
    )

    return RiskResponse(
        location=payload.location,
        risk_score=round(score, 1),
        risk_tier=risk_tier,
        alert_triggered=alert_sent,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@app.post("/score/batch")
async def batch_score_endpoint(request: BatchScoreRequest) -> Dict[str, Any]:
    """Calculate scores for multiple locations."""
    results = []
    for req in request.requests:
        score = calculate_score(req.precipitation, req.temperature)
        risk_tier = get_risk_tier(score)

        alert_sent = False
        if alert_engine and score >= 30:
            result = alert_engine.process(
                location=req.location,
                score=score,
                precipitation=req.precipitation,
            )
            alert_sent = result.get("alert_sent", False)

        results.append(
            {
                "location": req.location,
                "score": round(score, 1),
                "risk_tier": risk_tier,
                "precipitation": req.precipitation,
                "alert_sent": alert_sent,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    return {"status": "success", "results": results, "count": len(results)}
