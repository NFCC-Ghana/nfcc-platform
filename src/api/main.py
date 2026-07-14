"""FastAPI main application for NFCC flood alert platform."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.alerts.district_risk import should_alert_for_district
from src.alerts.engine import AlertEngine
from src.alerts.logger_config import setup_logging
from src.api.dam_router import router as dam_router
from src.api.health import router as health_router
from src.api.metrics_endpoint import router as metrics_router
from src.api.routes.alerts import router as alerts_router
from src.api.routes.community_reports import router as community_report_router
from src.api.routes.subscriptions import router as subscription_router
from src.config.settings import settings

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize alert engine
alert_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    global alert_engine

    # Startup
    logger.info("Starting NFCC Flood Alert Platform...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_VERSION}")

    # Initialize alert engine
    alert_engine = AlertEngine()
    logger.info("Alert engine initialized")

    yield

    # Shutdown
    logger.info("Shutting down NFCC Flood Alert Platform...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(alerts_router)
app.include_router(dam_router)
app.include_router(subscription_router)
app.include_router(community_report_router)

logger.info("All routers registered")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "healthy",
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
