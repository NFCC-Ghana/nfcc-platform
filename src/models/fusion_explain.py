"""SHAP-style attribution for linear multi-source forecast fusion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

import numpy as np

try:
    import shap
except ImportError:  # pragma: no cover - shap is required in production requirements
    shap = None  # type: ignore

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


def _reference_vector(baseline_per_source: Optional[Mapping[str, float]] = None) -> np.ndarray:
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
    """
    Attribute fused risk to each source using SHAP ``KernelExplainer``.

    Unavailable sources are fixed out of the model via a binary mask; SHAP
    mass is placed on active features only.
    """
    x, m = inp.as_vector_and_mask()
    mask = (m > 0).astype(float)
    if mask.sum() == 0:
        return FusionExplainOutput(
            unified_risk=0.0,
            expected_value=0.0,
            shap_values={k: 0.0 for k in _SOURCE_ORDER},
            baseline={k: float(_reference_vector(baseline_per_source)[i]) for i, k in enumerate(_SOURCE_ORDER)},
            feature_names=list(_SOURCE_ORDER),
        )

    weights = fusion_weights()
    fused = fuse_from_arrays(x, mask, weights)

    ref = _reference_vector(baseline_per_source)
    background = ref.reshape(1, 3)

    def _predict(z: np.ndarray) -> np.ndarray:
        z = np.atleast_2d(np.asarray(z, dtype=float))
        z = np.clip(z, 0.0, 100.0)
        out = np.empty(z.shape[0], dtype=float)
        for i in range(z.shape[0]):
            out[i] = fuse_from_arrays(z[i], mask, weights)
        return out

    if shap is None:  # pragma: no cover
        delta = (x - ref) * mask
        w_eff = weights * mask
        denom = float(w_eff.sum())
        contrib = {name: float(wi * delta[idx] / denom) for idx, (name, wi) in enumerate(zip(_SOURCE_ORDER, w_eff))}
        return FusionExplainOutput(
            unified_risk=fused,
            expected_value=float(fuse_from_arrays(ref, mask, weights)),
            shap_values=contrib,
            baseline={k: float(ref[i]) for i, k in enumerate(_SOURCE_ORDER)},
            feature_names=list(_SOURCE_ORDER),
        )

    instance = x.reshape(1, 3)
    kw: Dict[str, Any] = {"silent": True}
    try:
        explainer = shap.KernelExplainer(_predict, background)
        sv = explainer.shap_values(instance, nsamples=nsamples, **kw)
    except TypeError:
        explainer = shap.KernelExplainer(_predict, background)
        sv = explainer.shap_values(instance, nsamples=nsamples)

    arr = np.asarray(sv, dtype=float).reshape(3)
    arr = arr * mask
    exp_val = float(_predict(background)[0])
    shap_map = {name: float(arr[i]) for i, name in enumerate(_SOURCE_ORDER)}
    return FusionExplainOutput(
        unified_risk=fused,
        expected_value=exp_val,
        shap_values=shap_map,
        baseline={k: float(ref[i]) for i, k in enumerate(_SOURCE_ORDER)},
        feature_names=list(_SOURCE_ORDER),
    )
