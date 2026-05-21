"""
NFCC Flood-Risk Intelligence API
National Flood Control Centre — Accra, Ghana
Phase 3C — FastAPI Live Scoring Endpoint
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationInfo, field_validator

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("nfcc-api")

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "xgboost_flood_risk.pkl"
LOG_PATH = BASE_DIR / "logs" / "alert_log.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Load Model (optional at import so pytest/CI can patch before scoring) ──
model: Optional[Any] = None
if MODEL_PATH.exists():
    model = joblib.load(MODEL_PATH)
    logger.info("✅ Model loaded from %s", MODEL_PATH)
else:
    logger.warning(
        "No model file at %s — scoring routes return 503 until it exists or tests inject a mock.",
        MODEL_PATH,
    )


def require_model() -> None:
    """Load model from disk if needed; raise 503 if still unavailable."""
    global model
    if model is None and MODEL_PATH.exists():
        try:
            model = joblib.load(MODEL_PATH)
            logger.info("✅ Model loaded from %s", MODEL_PATH)
        except Exception as e:
            logger.error("Failed to load model from %s: %s", MODEL_PATH, e)
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Risk model is not loaded. Add models/xgboost_flood_risk.pkl "
                "(e.g. run python -m src.models.train_model) to enable scoring."
            ),
        )


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="NFCC Flood-Risk Intelligence API",
    description=(
        "National Flood Control Centre — Accra, Ghana. "
        "Live flood-risk scoring from rainfall features. "
        "Phase 3C — Risk Emulation (XGBoost)."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════════


class RainfallInput(BaseModel):
    precipitation: float = Field(..., ge=0, le=500, description="Today's rainfall (mm)")
    roll_3d: float = Field(..., ge=0, le=1000, description="3-day total rainfall (mm)")
    roll_7d: float = Field(..., ge=0, le=500, description="7-day rolling average (mm)")
    roll_30d: float = Field(
        ..., ge=0, le=200, description="30-day rolling average (mm)"
    )
    cumulative: float = Field(
        ..., ge=0, le=5000, description="Year-to-date cumulative rainfall (mm)"
    )
    z_score: float = Field(
        ..., ge=-5, le=10, description="Rainfall z-score (30-day window)"
    )
    location: str = Field(default="Accra", description="District or station name")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of observation",
    )

    @field_validator("roll_3d")
    @classmethod
    def roll3d_gte_precip(cls, v: float, info: ValidationInfo) -> float:
        values = info.data

        if "precipitation" in values and v < values["precipitation"]:
            raise ValueError("roll_3d (3-day total) must be >= today's precipitation")

        return v


class RiskResponse(BaseModel):
    risk_score: float
    risk_tier: str
    alert: bool
    location: str
    timestamp: str
    model_version: str = "xgboost-phase3a"
    note: str = (
        "Phase 3A risk emulation. Score derived from rainfall features. "
        "Not yet a true flood forecast."
    )


class BatchInput(BaseModel):
    records: list[RainfallInput]


def rainfall_features_dict(record: RainfallInput) -> dict[str, float]:
    """Model feature columns in training order (single row as a dict)."""
    return {
        "precipitation": record.precipitation,
        "roll_3d": record.roll_3d,
        "roll_7d": record.roll_7d,
        "roll_30d": record.roll_30d,
        "cumulative": record.cumulative,
        "z_score": record.z_score,
    }


# Explainability routes (after schemas so explain can import RainfallInput from this module)
from src.api.explain import router as explain_router  # noqa: E402

app.include_router(explain_router)


# ══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

ALERT_THRESHOLD = 50


def compute_risk_tier(score: float) -> str:
    if score >= 75:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MODERATE"
    return "LOW"


def score_record(record: RainfallInput) -> float:
    require_model()
    features = pd.DataFrame([rainfall_features_dict(record)])
    raw = model.predict(features)[0]
    return float(np.clip(raw, 0, 100))


def log_alert(payload: dict):
    """Append alert record to JSONL log file."""
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(payload) + "\n")
    logger.warning(
        f"🚨 ALERT | {payload['location']} | "
        f"Score: {payload['risk_score']:.1f} | "
        f"Tier: {payload['risk_tier']}"
    )


# ══════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "NFCC Flood-Risk Intelligence API",
        "status": "operational",
        "version": "1.0.0",
        "phase": "3C",
        "time": datetime.utcnow().isoformat(),
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "model_path": str(MODEL_PATH),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Single Record Scoring ─────────────────────────────────────────────
@app.post("/score", response_model=RiskResponse, tags=["Scoring"])
def score_single(
    payload: RainfallInput,
    background_tasks: BackgroundTasks,
):
    """
    Score a single rainfall observation.
    Returns flood-risk score (0–100), risk tier, and alert flag.
    """
    try:
        risk_score = score_record(payload)
        tier = compute_risk_tier(risk_score)
        alert = risk_score >= ALERT_THRESHOLD

        response = RiskResponse(
            risk_score=round(risk_score, 2),
            risk_tier=tier,
            alert=alert,
            location=payload.location,
            timestamp=payload.timestamp,
        )

        # Log alerts asynchronously
        if alert:
            background_tasks.add_task(log_alert, response.model_dump())

        logger.info(
            f"Scored | {payload.location} | "
            f"{risk_score:.1f} | {tier} | alert={alert}"
        )
        return response

    except Exception as e:
        logger.error(f"Scoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Batch Scoring ─────────────────────────────────────────────────────
@app.post("/score/batch", tags=["Scoring"])
def score_batch(
    payload: BatchInput,
    background_tasks: BackgroundTasks,
):
    """
    Score multiple rainfall observations in one request.
    Returns a list of risk scores with summary statistics.
    """
    if len(payload.records) == 0:
        raise HTTPException(status_code=400, detail="No records provided.")
    if len(payload.records) > 365:
        raise HTTPException(
            status_code=400, detail="Batch limited to 365 records per request."
        )

    require_model()

    results = []
    alerts = []

    for record in payload.records:
        try:
            risk_score = score_record(record)
            tier = compute_risk_tier(risk_score)
            alert = risk_score >= ALERT_THRESHOLD

            row = {
                "location": record.location,
                "timestamp": record.timestamp,
                "risk_score": round(risk_score, 2),
                "risk_tier": tier,
                "alert": alert,
            }
            results.append(row)
            if alert:
                alerts.append(row)

        except Exception as e:
            results.append(
                {
                    "location": record.location,
                    "timestamp": record.timestamp,
                    "error": str(e),
                }
            )

    # Log all alerts asynchronously
    for alert_row in alerts:
        background_tasks.add_task(log_alert, alert_row)

    scores = [r["risk_score"] for r in results if "risk_score" in r]

    return {
        "total_records": len(results),
        "alert_count": len(alerts),
        "summary": {
            "mean_risk": round(np.mean(scores), 2) if scores else None,
            "max_risk": round(np.max(scores), 2) if scores else None,
            "min_risk": round(np.min(scores), 2) if scores else None,
        },
        "results": results,
        "model_version": "xgboost-phase3a",
    }


# ── Alert Log Retrieval ───────────────────────────────────────────────
@app.get("/alerts", tags=["Alerts"])
def get_alerts(limit: int = 50):
    """
    Return the most recent alert log entries.
    """
    if not LOG_PATH.exists():
        return {"alerts": [], "total": 0}

    with open(LOG_PATH, "r") as f:
        lines = f.readlines()

    recent = [json.loads(line) for line in lines[-limit:]]
    recent.reverse()  # Most recent first

    return {
        "total": len(lines),
        "showing": len(recent),
        "alerts": recent,
    }


# ── District Summary ──────────────────────────────────────────────────
@app.get("/districts", tags=["Intelligence"])
def district_summary():
    """
    Return a static district risk reference for Accra.
    Phase 4 will replace with live spatial scoring.
    """
    districts = [
        {"district": "Accra Central", "risk_zone": "HIGH", "elevation_m": 30},
        {"district": "Tema", "risk_zone": "MODERATE", "elevation_m": 20},
        {"district": "Adenta", "risk_zone": "MODERATE", "elevation_m": 85},
        {"district": "Ga East", "risk_zone": "HIGH", "elevation_m": 45},
        {"district": "Ga West", "risk_zone": "CRITICAL", "elevation_m": 15},
        {"district": "Ledzokuku", "risk_zone": "HIGH", "elevation_m": 25},
        {"district": "Ablekuma North", "risk_zone": "MODERATE", "elevation_m": 60},
        {"district": "Ningo Prampram", "risk_zone": "CRITICAL", "elevation_m": 8},
    ]
    return {
        "city": "Accra, Ghana",
        "phase": "3C — Static Reference (Phase 4 will be spatial+live)",
        "districts": districts,
        "timestamp": datetime.utcnow().isoformat(),
    }
