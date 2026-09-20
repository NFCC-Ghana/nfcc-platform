"""GET/PATCH /v1/community-reports - read and triage access to real citizen
reports (src/community/community_memory.py).

Before this file existed, the only consumer of this table was
src/api/routes/situation.py's aggregate get_report_stats() call (a count,
not the reports themselves) - there was no way to see an individual real
report, and no way to validate one. Validation matters beyond a "verified"
badge: src/verification/outcome_verifier.py's automated outcome checking
only counts VALIDATED reports (get_validated_report_count_in_window), so
an unvalidated report never actually influences the verified-outcome
dataset this platform is trying to accumulate for future real ML.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import verify_api_key
from src.community.community_memory import community_memory

router = APIRouter(prefix="/community-reports", tags=["v1"])


class CommunityReport(BaseModel):
    id: int
    report_id: str
    district: str
    community: str
    report_type: str
    description: Optional[str] = None
    flood_depth_m: Optional[float] = None
    photo_url: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    reporter_email: Optional[str] = None
    report_time: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    urgency: str = "MODERATE"
    validated: bool
    validation_confidence: float
    trusted_score: float
    created_at: str


class CommunityReportListResponse(BaseModel):
    count: int
    reports: List[CommunityReport]


class ValidateReportRequest(BaseModel):
    confidence: float = Field(0.9, ge=0.0, le=1.0, description="Human reviewer's confidence this report is real")


@router.get("", response_model=CommunityReportListResponse)
async def list_community_reports(
    district: Optional[str] = None, validated_only: bool = False, limit: int = 50
) -> CommunityReportListResponse:
    rows = community_memory.get_reports(district=district, validated_only=validated_only, limit=limit)
    return CommunityReportListResponse(count=len(rows), reports=rows)


@router.post("/{report_id}/validate", dependencies=[Depends(verify_api_key)])
async def validate_community_report(report_id: str, request: ValidateReportRequest) -> dict:
    matches = community_memory.get_reports(limit=1000)
    if not any(r["report_id"] == report_id for r in matches):
        raise HTTPException(status_code=404, detail=f"No report '{report_id}'")
    return community_memory.validate_report(report_id, request.confidence)
