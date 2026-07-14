"""FastAPI router for flood alert history and statistics endpoints."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.database.alert_db import (
    get_alert_history,
    get_alert_stats,
    get_total_alerts_count,
)

logger = logging.getLogger("nfcc-alerts-router")

# Create router with alerts prefix and tags
router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ============================================================
# Response Models
# ============================================================


class AlertRecord(BaseModel):
    """Model representing a single alert record from the database."""

    id: int
    timestamp: str
    location: str
    risk_score: float
    risk_tier: str
    alert_sent: bool
    provider: Optional[str] = None
    message_id: Optional[str] = None
    error: Optional[str] = None


class AlertHistoryResponse(BaseModel):
    """Response model for alert history endpoint."""

    status: str = Field(default="success", description="Response status")
    count: int = Field(..., description="Number of alerts returned")
    total_available: int = Field(
        default=None, description="Total alerts matching criteria (if known)"
    )
    limit: int = Field(..., description="Pagination limit used")
    offset: int = Field(..., description="Pagination offset used")
    location_filter: Optional[str] = Field(
        default=None, description="Location filter applied"
    )
    data: List[AlertRecord] = Field(..., description="List of alert records")


class RiskTierStats(BaseModel):
    """Model for risk tier statistics."""

    tier: str = Field(
        ..., description="Risk tier name (e.g., LOW, MEDIUM, HIGH, CRITICAL)"
    )
    count: int = Field(..., description="Number of alerts at this tier")


class TopLocation(BaseModel):
    """Model for top location in alert statistics."""

    location: str = Field(..., description="Location name")
    alert_count: int = Field(..., description="Number of alerts from this location")


class AlertStatsResponse(BaseModel):
    """Response model for alert statistics endpoint."""

    status: str = Field(default="success", description="Response status")
    by_risk_tier: List[RiskTierStats] = Field(
        ..., description="Alert counts grouped by risk tier"
    )
    top_locations: List[TopLocation] = Field(
        ..., description="Top 5 locations with most alerts"
    )


# ============================================================
# Endpoints
# ============================================================


@router.get("/history", response_model=AlertHistoryResponse)
async def get_history(
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of alerts to return"
    ),
    offset: int = Query(0, ge=0, description="Number of alerts to skip for pagination"),
    location: Optional[str] = Query(None, description="Optional location filter"),
) -> AlertHistoryResponse:
    """
    Retrieve paginated alert history with optional location filtering.

    Query Parameters:
    - **limit**: Maximum number of alerts to return (1-1000, default: 50)
    - **offset**: Number of records to skip for pagination (default: 0)
    - **location**: Optional location name to filter alerts

    Returns:
    - **status**: Operation status ("success" or "error")
    - **count**: Number of alerts in this response
    - **data**: List of alert records with full details

    Example:
    ```
    GET /alerts/history?limit=10&offset=0&location=Accra
    ```
    """
    try:
        total_available = get_total_alerts_count(location_filter=location_filter)
        # Fetch alerts from database
        alerts_data = get_alert_history(
            limit=limit,
            offset=offset,
            location_filter=location,
        )

        logger.info(
            f"Retrieved {len(alerts_data)} alerts | total_available={total_available} | "
            f"limit={limit} | offset={offset} | location={location}"
        )

        return AlertHistoryResponse(
            status="success",
            count=len(alerts_data),
            total_available=total_available,
            limit=limit,
            offset=offset,
            location_filter=location,
            data=[AlertRecord(**record) for record in alerts_data],
        )

    except Exception as e:
        logger.error(f"Error retrieving alert history: {str(e)}")
        raise


@router.get("/stats", response_model=AlertStatsResponse)
async def get_stats() -> AlertStatsResponse:
    """
    Retrieve comprehensive alert statistics.

    Returns:
    - **status**: Operation status ("success" or "error")
    - **by_risk_tier**: Alert count grouped by risk tier (LOW, MEDIUM, HIGH, CRITICAL)
    - **top_locations**: Top 5 locations with the highest number of alerts

    The statistics are aggregated across all historical alerts in the database.

    Example response:
    ```json
    {
        "status": "success",
        "by_risk_tier": [
            {"tier": "LOW", "count": 45},
            {"tier": "MEDIUM", "count": 32},
            {"tier": "HIGH", "count": 8},
            {"tier": "CRITICAL", "count": 2}
        ],
        "top_locations": [
            {"location": "Accra", "alert_count": 25},
            {"location": "Tema", "alert_count": 18},
            {"location": "Kumasi", "alert_count": 14}
        ]
    }
    ```
    """
    try:
        total_available = get_total_alerts_count(location_filter=location)
        # Fetch statistics from database
        stats_data = get_alert_stats()

        # Transform risk tier data to response format
        risk_tier_list = [
            RiskTierStats(tier=tier, count=count)
            for tier, count in stats_data.get("by_risk_tier", {}).items()
        ]

        # Transform top locations data to response format
        top_locations_list = [
            TopLocation(location=location, alert_count=count)
            for location, count in stats_data.get("top_locations", [])
        ]

        logger.info(
            f"Retrieved alert stats | "
            f"risk_tiers={len(risk_tier_list)} | "
            f"top_locations={len(top_locations_list)}"
        )

        return AlertStatsResponse(
            status="success",
            by_risk_tier=risk_tier_list,
            top_locations=top_locations_list,
        )

    except Exception as e:
        logger.error(f"Error retrieving alert statistics: {str(e)}")
        raise


# Add import at top (if not already there)
# from src.database.alert_db import get_total_alerts_count
