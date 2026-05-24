"""Single source of truth for alert payloads - NEVER duplicate this definition."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class AlertPayload:
    """
    SINGLE CONTRACT for all alert payloads.
    
    This is the ONLY definition. All providers and the engine MUST use this.
    Fields are immutable (frozen=True) to prevent accidental mutations.
    """
    
    location: str
    score: float  # ⚠️ ONLY 'score' - never 'risk_score'
    risk_tier: str
    message: str = ""
    precipitation: float = 0.0
    roll_3d: float = 0.0
    z_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self):
        """Validate payload after initialization."""
        if not isinstance(self.score, (int, float)):
            raise TypeError(f"score must be numeric, got {type(self.score)}")
        
        if self.score < 0 or self.score > 100:
            raise ValueError(f"score must be between 0 and 100, got {self.score}")
        
        if not self.location or not isinstance(self.location, str):
            raise ValueError(f"location must be non-empty string, got {self.location}")
        
        valid_tiers = ["LOW", "MODERATE", "HIGH", "CRITICAL", "EXTREME"]
        if self.risk_tier not in valid_tiers:
            raise ValueError(f"Invalid risk_tier: {self.risk_tier}. Must be one of {valid_tiers}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "location": self.location,
            "score": self.score,
            "risk_tier": self.risk_tier,
            "message": self.message,
            "precipitation": self.precipitation,
            "roll_3d": self.roll_3d,
            "z_score": self.z_score,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict())
