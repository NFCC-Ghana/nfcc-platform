"""Linear fusion of normalized multi-source flood forecasts (0–100 scale)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

import numpy as np

_DEFAULT_WEIGHTS: Tuple[float, float, float] = (1.0, 1.0, 1.0)
_SOURCE_ORDER: Tuple[str, str, str] = ("chirps", "glofas", "flood_hub")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def fusion_weights() -> np.ndarray:
    """Per-source positive weights (CHIRPS, GloFAS, Flood Hub)."""
    w = np.array(
        [
            _env_float("FUSION_WEIGHT_CHIRPS", _DEFAULT_WEIGHTS[0]),
            _env_float("FUSION_WEIGHT_GLOFAS", _DEFAULT_WEIGHTS[1]),
            _env_float("FUSION_WEIGHT_FLOOD_HUB", _DEFAULT_WEIGHTS[2]),
        ],
        dtype=float,
    )
    w = np.maximum(w, 0.0)
    return w


@dataclass(frozen=True)
class ForecastFusionInput:
    """Normalized source risks on 0–100; ``None`` means source unavailable."""

    chirps_risk: Optional[float] = None
    glofas_risk: Optional[float] = None
    flood_hub_risk: Optional[float] = None

    def as_vector_and_mask(self) -> Tuple[np.ndarray, np.ndarray]:
        values = []
        mask = []
        for v in (self.chirps_risk, self.glofas_risk, self.flood_hub_risk):
            if v is None:
                values.append(0.0)
                mask.append(0.0)
            else:
                values.append(float(np.clip(v, 0.0, 100.0)))
                mask.append(1.0)
        return np.array(values, dtype=float), np.array(mask, dtype=float)


@dataclass(frozen=True)
class ForecastFusionOutput:
    unified_risk: float
    weights: Mapping[str, float]
    present_sources: List[str]
    missing_sources: List[str]


def fuse_forecasts(
    inp: ForecastFusionInput,
    weights: Optional[np.ndarray] = None,
) -> ForecastFusionOutput:
    """
    Weighted mean over available sources only.

    unified_risk = sum_i (w_i * m_i * x_i) / sum_i (w_i * m_i)
    where m_i in {0,1} indicates presence.
    """
    w = (
        fusion_weights()
        if weights is None
        else np.maximum(np.asarray(weights, dtype=float), 0.0)
    )
    x, m = inp.as_vector_and_mask()
    eff = w * m
    denom = float(eff.sum())
    if denom <= 0.0:
        return ForecastFusionOutput(
            unified_risk=0.0,
            weights={k: float(wi) for k, wi in zip(_SOURCE_ORDER, w)},
            present_sources=[],
            missing_sources=list(_SOURCE_ORDER),
        )
    unified = float((x * eff).sum() / denom)
    unified = float(np.clip(unified, 0.0, 100.0))
    present = [name for name, mi in zip(_SOURCE_ORDER, m) if mi > 0]
    missing = [name for name, mi in zip(_SOURCE_ORDER, m) if mi == 0]
    return ForecastFusionOutput(
        unified_risk=unified,
        weights={k: float(wi) for k, wi in zip(_SOURCE_ORDER, w)},
        present_sources=present,
        missing_sources=missing,
    )


def fuse_from_arrays(
    values: np.ndarray,
    mask: np.ndarray,
    weights: Optional[np.ndarray] = None,
) -> float:
    """Fuse a single row ``values`` (shape (3,)) with binary ``mask`` (shape (3,))."""
    w = (
        fusion_weights()
        if weights is None
        else np.maximum(np.asarray(weights, dtype=float), 0.0)
    )
    x = np.clip(np.asarray(values, dtype=float).reshape(3), 0.0, 100.0)
    m = np.asarray(mask, dtype=float).reshape(3)
    eff = w * m
    denom = float(eff.sum())
    if denom <= 0.0:
        return 0.0
    return float(np.clip(float((x * eff).sum() / denom), 0.0, 100.0))
