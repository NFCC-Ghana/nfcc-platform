"""FastAPI main application for NFCC flood alert platform."""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.alerts.engine import AlertEngine
from src.alerts.formatter import get_risk_tier
from src.alerts.logger_config import setup_logging
from src.config.settings import settings
from src.api.dam_spillage import router as dam_spillage_router



# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("nfcc-api")

# Global engine instance
alert_engine = None


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
    # global alert_engine

    # Startup
    logger.info(f"Starting NFCC Flood Alert Platform v{settings.API_VERSION}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Verify model loads
    try:
        model = settings.model
        logger.info("✅ Model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")

    # Initialize alert engine (only once - shared across workers)
    alert_engine = AlertEngine()
    logger.info("✅ Alert engine initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

app.include_router(
    dam_spillage_router,
    prefix="/forecast"
)
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/score")
async def score_endpoint(request: ScoreRequest) -> ScoreResponse:
    """Calculate flood risk score and trigger alerts."""
    # global alert_engine

    # Calculate score
    score = calculate_score(request.precipitation, request.temperature)
    risk_tier = get_risk_tier(score)

    # Determine if alert should be sent (MODERATE or higher)
    send_alert = score >= 30

    # Process through alert engine
    alert_sent = False
    if alert_engine and send_alert:
        result = alert_engine.process(
            location=request.location,
            score=score,
            precipitation=request.precipitation,
            message=f"Flood risk detected with {request.precipitation:.1f}mm rainfall",
        )
        alert_sent = result.get("alert_sent", False)

    logger.info(
        f"Scored | {request.location} | {score:.1f} | {risk_tier} | alert={alert_sent}"
    )

    # Generate ISO timestamp
    current_timestamp = datetime.utcnow().isoformat() + "Z"

    return ScoreResponse(
        location=request.location,
        score=round(score, 1),
        risk_tier=risk_tier,
        alert_sent=alert_sent,
        timestamp=current_timestamp,
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


@app.get("/version")
async def version():
    return {
        "version": "2.1.0",
        "environment": "production",
        "build": "production-hardening",
    }
