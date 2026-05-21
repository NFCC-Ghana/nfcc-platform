"""Shared Pydantic request/response models for the NFCC API."""

from datetime import datetime

from pydantic import BaseModel, Field


class RainfallInput(BaseModel):
    """Six rainfall drivers plus metadata, matching model training columns."""

    precipitation: float = Field(..., ge=0, description="Daily precipitation (mm)")
    roll_3d: float = Field(..., ge=0, description="3-day rolling sum of precipitation (mm)")
    roll_7d: float = Field(..., ge=0, description="7-day rolling mean (mm)")
    roll_30d: float = Field(..., ge=0, description="30-day rolling mean (mm)")
    cumulative: float = Field(..., ge=0, description="Seasonal or cumulative rainfall (mm)")
    z_score: float = Field(..., description="Precipitation anomaly vs recent window")
    location: str = Field(..., min_length=1, description="District or gauge label")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Observation time (ISO 8601)",
    )


class BatchInput(BaseModel):
    records: list[RainfallInput]


class RiskResponse(BaseModel):
    risk_score: float
    risk_tier: str
    alert: bool
    location: str
    timestamp: str
    model_version: str
    note: str
