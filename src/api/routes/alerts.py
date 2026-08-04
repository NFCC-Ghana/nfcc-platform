"""FastAPI router for flood alert history and statistics endpoints."""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.database.alert_db import (
    get_alert_history,
    get_alert_stats,
    get_total_alerts_count,
)

logger = logging.getLogger("nfcc-alerts-router")

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertRecord(BaseModel):
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
    status: str = Field(default="success")
    count: int
    total_available: int = Field(default=None)
    limit: int
    offset: int
    location_filter: Optional[str] = Field(default=None)
    data: List[AlertRecord]


class RiskTierStats(BaseModel):
    tier: str
    count: int


class TopLocation(BaseModel):
    location: str
    alert_count: int


class AlertStatsResponse(BaseModel):
    status: str = Field(default="success")
    by_risk_tier: List[RiskTierStats]
    top_locations: List[TopLocation]


@router.get("/history", response_model=AlertHistoryResponse)
async def get_history(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    location_filter: Optional[str] = Query(None),
) -> AlertHistoryResponse:
    try:
        total_available = get_total_alerts_count(location_filter=location_filter)
        alerts_data = get_alert_history(
            limit=limit,
            offset=offset,
            location_filter=location_filter,
        )
        logger.info(
            f"Retrieved {len(alerts_data)} alerts | "
            f"total_available={total_available}"
        )
        return AlertHistoryResponse(
            status="success",
            count=len(alerts_data),
            total_available=total_available,
            limit=limit,
            offset=offset,
            location_filter=location_filter,
            data=[AlertRecord(**record) for record in alerts_data],
        )
    except Exception as e:
        logger.error(f"Error retrieving alert history: {str(e)}")
        raise


@router.get("/stats", response_model=AlertStatsResponse)
async def get_stats(location: Optional[str] = None) -> AlertStatsResponse:
    try:
        stats_data = get_alert_stats()
        
        # Transform risk tier data to response format
        risk_tier_list = [
            RiskTierStats(tier=tier, count=count)
            for tier, count in stats_data.get("by_risk_tier", {}).items()
        ]
        
        # Transform top locations data to response format
        top_locations_data = stats_data.get("top_locations", [])
        top_locations_list = [
            TopLocation(location=item["location"], alert_count=item["count"])
            for item in top_locations_data[:5]
        ]
        
        logger.info(
            f"Retrieved alert stats | risk_tiers={len(risk_tier_list)} | "
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
