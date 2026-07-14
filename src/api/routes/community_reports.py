"""Community report API endpoints for citizen flood reporting."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from src.community.community_memory import community_memory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/community", tags=["Community"])


class ReportRequest(BaseModel):
    """Community report request model."""

    district: str = Field(..., description="District", example="Accra Central")
    community: str = Field(..., description="Community name", example="Alajo")
    report_type: str = Field(
        "flood", description="Report type: flood, water_level, weather"
    )
    description: str = Field(..., description="Report description")
    flood_depth_m: float = Field(0.0, description="Flood depth in meters")
    photo_url: Optional[str] = Field(None, description="URL to photo")
    reporter_name: Optional[str] = Field(None, description="Reporter name")
    reporter_phone: Optional[str] = Field(None, description="Reporter phone")
    reporter_email: Optional[str] = Field(None, description="Reporter email")


class ReportResponse(BaseModel):
    """Report response model."""

    status: str
    report_id: str
    timestamp: str
    message: str


class ReportValidationRequest(BaseModel):
    """Report validation request model."""

    confidence: float = Field(0.8, description="Validation confidence (0-1)")


@router.post("/report", response_model=ReportResponse)
async def submit_report(request: ReportRequest):
    """Submit a community flood report."""
    try:
        result = community_memory.submit_report(request.dict())
        return ReportResponse(
            status="success",
            report_id=result.get("report_id", ""),
            timestamp=result.get("timestamp", ""),
            message="✅ Report submitted successfully! Thank you for helping your community.",
        )
    except Exception as e:
        logger.error(f"Report submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def get_reports(
    district: Optional[str] = Query(None, description="Filter by district"),
    validated_only: bool = Query(False, description="Only show validated reports"),
    limit: int = Query(50, description="Maximum number of reports", ge=1, le=100),
):
    """Get community reports."""
    try:
        reports = community_memory.get_reports(district, validated_only, limit)
        return {"status": "success", "count": len(reports), "reports": reports}
    except Exception as e:
        logger.error(f"Failed to get reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/{report_id}/validate")
async def validate_report(report_id: str, request: ReportValidationRequest):
    """Validate a community report."""
    try:
        result = community_memory.validate_report(report_id, request.confidence)
        return {
            "status": "success",
            "report_id": report_id,
            "confidence": request.confidence,
            "message": f"✅ Report validated with {request.confidence*100:.0f}% confidence",
        }
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/stats")
async def get_report_stats(
    district: Optional[str] = Query(None, description="Filter by district")
):
    """Get report statistics."""
    try:
        stats = community_memory.get_report_stats(district)
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/recent")
async def get_recent_reports(
    limit: int = Query(10, description="Number of recent reports")
):
    """Get most recent community reports."""
    try:
        reports = community_memory.get_reports(limit=limit)
        return {"status": "success", "count": len(reports), "reports": reports}
    except Exception as e:
        logger.error(f"Failed to get recent reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))
