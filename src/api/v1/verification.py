"""GET /v1/verification - does the live alert threshold have real
rare-event discriminative skill, or does it just get crossed by
ordinary wet-season rain (src/models/rare_event_verification.py)?

Answers the question src/api/v1/backtest.py's naive POD=1.0 result
raised but couldn't resolve on its own: scores the current threshold
(and a locally-calibrated percentile alternative) with SEDI against a
real full-record contingency table, with bootstrap confidence
intervals. Read-only, no side effects. Can take a while (real
multi-decade Earth Engine queries per district) - this is an
analysis/reporting endpoint, not a per-request path anything else
depends on.
"""

from fastapi import APIRouter

from src.models.rare_event_verification import run_full_verification

router = APIRouter(prefix="/verification", tags=["v1"])


@router.get("")
async def get_rare_event_verification() -> dict:
    return run_full_verification()
