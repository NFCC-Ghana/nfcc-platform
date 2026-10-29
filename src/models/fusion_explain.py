"""Exact Shapley attribution for linear multi-source forecast fusion.

The fused risk is a weighted mean of the active sources,
    fused(x) = sum_i(w_i * m_i * x_i) / sum_i(w_i * m_i),
which is linear in x for a fixed availability mask m. For a linear model
the Shapley value of each feature against a reference vector has a
closed form, w_i * m_i * (x_i - ref_i) / sum(w * m), so it's computed
directly here instead of estimated.

This module used to run SHAP's sampling KernelExplainer and fall back to
that closed form only when `shap` wasn't importable - but shap was
removed from requirements.txt on 2026-09-27, so the "fallback" (marked
`pragma: no cover`, beside a comment claiming shap was required in
production) had silently been the only code that ever ran. It is now
the implementation, with no dependency and no sampling noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Optional

import numpy as np

from src.models.forecast_fusion import (
    ForecastFusionInput,
    fuse_from_arrays,
    fusion_weights,
)

_SOURCE_ORDER = ("chirps", "glofas", "flood_hub")


@dataclass(frozen=True)
class FusionExplainOutput:
    unified_risk: float
    expected_value: float
    shap_values: Mapping[str, float]
    baseline: Mapping[str, float]
    feature_names: List[str]


def _reference_vector(
    baseline_per_source: Optional[Mapping[str, float]] = None,
) -> np.ndarray:
    base = baseline_per_source or {}
    ref = np.array(
        [
            float(np.clip(base.get("chirps", 50.0), 0.0, 100.0)),
            float(np.clip(base.get("glofas", 50.0), 0.0, 100.0)),
            float(np.clip(base.get("flood_hub", 50.0), 0.0, 100.0)),
        ],
        dtype=float,
    )
    return ref


def explain_fusion_shap(
    inp: ForecastFusionInput,
    *,
    baseline_per_source: Optional[Mapping[str, float]] = None,
    nsamples: int = 80,
) -> FusionExplainOutput:
    """Attribute fused risk to each source with exact Shapley values.

    Unavailable sources are masked out and receive zero attribution; the
    contributions of the active sources sum exactly to
    unified_risk - expected_value. `nsamples` is accepted for backward
    compatibility with callers of the old sampling explainer and ignored.
    """
    del nsamples
    x, m = inp.as_vector_and_mask()
    mask = (m > 0).astype(float)
    ref = _reference_vector(baseline_per_source)
    baseline = {k: float(ref[i]) for i, k in enumerate(_SOURCE_ORDER)}

    if mask.sum() == 0:
        return FusionExplainOutput(
            unified_risk=0.0,
            expected_value=0.0,
            shap_values={k: 0.0 for k in _SOURCE_ORDER},
            baseline=baseline,
            feature_names=list(_SOURCE_ORDER),
        )

    weights = fusion_weights()
    w_eff = weights * mask
    denom = float(w_eff.sum())
    delta = (x - ref) * mask
    contrib = {
        name: float(w_eff[idx] * delta[idx] / denom)
        for idx, name in enumerate(_SOURCE_ORDER)
    }
    return FusionExplainOutput(
        unified_risk=fuse_from_arrays(x, mask, weights),
        expected_value=float(fuse_from_arrays(ref, mask, weights)),
        shap_values=contrib,
        baseline=baseline,
        feature_names=list(_SOURCE_ORDER),
    )
