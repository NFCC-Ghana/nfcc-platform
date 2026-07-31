"""Confidence score (0–100) for multi-source forecast fusion."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.models.forecast_fusion import ForecastFusionInput


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class ConfidenceOutput:
    confidence: float
    coverage_factor: float
    agreement_factor: float
    num_sources: int


def forecast_confidence(
    inp: ForecastFusionInput,
    unified_risk: float,
    *,
    max_spread: Optional[float] = None,
) -> ConfidenceOutput:
    """
    Heuristic confidence: combines source coverage with agreement among present sources.

    ``max_spread`` scales disagreement (default 50.0 on 0–100 risk scale).
    """
    spread_cap = (
        max_spread
        if max_spread is not None
        else _env_float("FUSION_CONFIDENCE_MAX_SPREAD", 50.0)
    )
    spread_cap = max(spread_cap, 1e-6)

    x, m = inp.as_vector_and_mask()
    present = x[m > 0]
    n = int(present.size)

    if n == 0:
        return ConfidenceOutput(
            confidence=0.0,
            coverage_factor=0.0,
            agreement_factor=0.0,
            num_sources=0,
        )

    coverage_map = {1: 40.0, 2: 72.0, 3: 100.0}
    coverage = coverage_map.get(n, 40.0)

    if n == 1:
        agreement = 55.0
    else:
        std = float(np.std(present, ddof=0))
        agreement = float(100.0 * (1.0 - min(std / spread_cap, 1.0)))

    conf = float(np.clip((coverage * agreement) ** 0.5, 0.0, 100.0))
    _ = unified_risk
    return ConfidenceOutput(
        confidence=conf,
        coverage_factor=coverage,
        agreement_factor=agreement,
        num_sources=n,
    )
