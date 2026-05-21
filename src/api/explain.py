"""
SHAP-based local explainability for the flood-risk XGBoost model.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.schemas import RainfallInput
from src.models.train_model import FEATURE_COLS

logger = logging.getLogger("nfcc-api")

router = APIRouter(tags=["Explainability"])


class FeatureImportanceItem(BaseModel):
    """Per-feature contribution for a single scored observation."""

    feature: str = Field(..., description="Rainfall feature name")
    importance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of total |contribution| for this row (0–1, sums to 1); ×100 for percent",
    )
    shap_value: float = Field(
        ...,
        description="Signed SHAP value: effect on risk vs model baseline",
    )


class ExplainResponse(BaseModel):
    """Local feature attribution for one rainfall record."""

    location: str
    timestamp: str
    risk_score: float = Field(..., description="Model risk score 0–100 (same as /score)")
    base_value: float = Field(
        ...,
        description="Expected risk (SHAP baseline / model intercept) before this row",
    )
    features: list[FeatureImportanceItem] = Field(
        ...,
        description="All six rainfall drivers with SHAP-based importance for this input",
    )
    model_version: str = "xgboost-phase3a"
    method: str = Field(
        default="shap_tree",
        description=(
            "xgboost_pred_contribs: native XGBoost tree contributions (preferred for XGB models). "
            "shap_tree: SHAP TreeExplainer. feature_importances: global fallback when explainers fail."
        ),
    )


def _row_frame(record: RainfallInput) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "precipitation": record.precipitation,
                "roll_3d": record.roll_3d,
                "roll_7d": record.roll_7d,
                "roll_30d": record.roll_30d,
                "cumulative": record.cumulative,
                "z_score": record.z_score,
            }
        ],
        columns=FEATURE_COLS,
    )


def _coerce_float_scalar(val: Any) -> float:
    """
    Parse a single numeric from SHAP / XGBoost outputs.
    Some versions expose values as bracketed strings (e.g. '[1.25E1]') or nested lists.
    """
    if isinstance(val, (int, float, np.floating, np.integer)):
        return float(val)
    if isinstance(val, str):
        s = val.strip().strip("[]").split(",")[0].strip()
        return float(s)
    if isinstance(val, (list, tuple)) and val:
        return _coerce_float_scalar(val[0])
    try:
        a = np.asarray(val, dtype=np.float64).ravel()
        if a.size:
            return float(a[0])
    except (TypeError, ValueError):
        pass
    s = str(val).strip().strip("[]").split(",")[0].strip()
    return float(s)


def _coerce_shap_values_vector(raw: Any, n: int) -> np.ndarray:
    """Flatten SHAP values to length n float vector (handles object / string quirks)."""
    if isinstance(raw, list):
        raw = raw[0]
    raw_np = np.asarray(raw)
    flat = np.squeeze(raw_np).reshape(-1)
    if flat.size != n:
        raise ValueError(f"Unexpected SHAP shape: {getattr(raw_np, 'shape', np.shape(raw_np))}")
    if raw_np.dtype.kind in "OUS":
        return np.array([_coerce_float_scalar(flat[i]) for i in range(n)], dtype=np.float64)
    return flat.astype(np.float64)


def _is_xgboost_sklearn_model(model: Any) -> bool:
    try:
        from xgboost.sklearn import XGBModel

        return isinstance(model, XGBModel)
    except Exception:
        return False


def _shap_vector_via_xgb_pred_contribs(
    model: Any, X: pd.DataFrame
) -> tuple[np.ndarray, float, str]:
    """
    Per-row tree contributions from XGBoost (same decomposition as tree SHAP for GBDTs).
    Avoids SHAP's XGBoost JSON loader, which breaks on XGBoost 3.1+ base_score formatting.
    """
    contribs = model.predict(X, pred_contribs=True)
    contribs = np.asarray(contribs, dtype=np.float64)
    if contribs.ndim == 1:
        contribs = contribs.reshape(1, -1)
    nfeat = len(FEATURE_COLS)
    if contribs.shape[1] != nfeat + 1:
        raise ValueError(
            f"pred_contribs expected {nfeat + 1} columns, got shape {contribs.shape}"
        )
    row = contribs[0]
    vec = row[:-1].astype(np.float64, copy=False)
    base = float(row[-1])
    return vec, base, "xgboost_pred_contribs"


def _shap_vector_for_row(model: Any, X: pd.DataFrame) -> tuple[np.ndarray, float, str]:
    """
    Return (shap_values length 6, base_value, method_label).
    Prefers XGBoost native pred_contribs for sklearn XGB models.
    Falls back to SHAP TreeExplainer, then global feature_importances_ (e.g. test mocks).
    """
    if _is_xgboost_sklearn_model(model):
        try:
            return _shap_vector_via_xgb_pred_contribs(model, X)
        except Exception as e:
            logger.debug("XGBoost pred_contribs path skipped: %s", e)

    try:
        import shap

        explainer = shap.TreeExplainer(model)
        raw = explainer.shap_values(X)
        vec = _coerce_shap_values_vector(raw, len(FEATURE_COLS))
        ev = explainer.expected_value
        if isinstance(ev, (list, tuple)) and ev:
            ev = ev[0]
        base = _coerce_float_scalar(ev)
        return vec, base, "shap_tree"
    except Exception as e:
        logger.debug("SHAP TreeExplainer unavailable (%s); using feature_importances_ fallback", e)
        imp = getattr(model, "feature_importances_", None)
        if imp is not None:
            vec = np.asarray(imp, dtype=float).ravel()
            if vec.size != len(FEATURE_COLS):
                vec = np.ones(len(FEATURE_COLS), dtype=float) / len(FEATURE_COLS)
            base = 50.0
            return vec, base, "feature_importances"
        vec = np.ones(len(FEATURE_COLS), dtype=float) / len(FEATURE_COLS)
        return vec, 50.0, "uniform_fallback"


def _importance_from_shap(vec: np.ndarray) -> tuple[list[float], list[float]]:
    """Normalize |SHAP| to probabilities; return (importance list, raw shap list)."""
    shap_list = [float(x) for x in vec]
    abs_v = np.abs(vec)
    total = float(abs_v.sum())
    if total > 0:
        imp = (abs_v / total).tolist()
    else:
        imp = [1.0 / len(FEATURE_COLS)] * len(FEATURE_COLS)
    return [float(x) for x in imp], shap_list


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="SHAP feature importance for one observation",
    response_description=(
        "Per-feature tree contributions for the six rainfall drivers. "
        "`shap_value` is the signed effect on the model output vs the row bias term; "
        "`importance` is the share of total |contribution| as a 0–1 fraction (sums to 1); "
        "multiply by 100 for percent."
    ),
)
def explain_rainfall(payload: RainfallInput) -> ExplainResponse:
    """
    Compute per-feature importance for the given rainfall features.

    Uses XGBoost ``pred_contribs`` when the loaded model is an XGBoost sklearn estimator
    (avoids SHAP/XGBoost JSON incompatibilities). Otherwise tries SHAP ``TreeExplainer``,
    then ``feature_importances_`` for non-tree mocks.
    """
    import src.api.main as api_main

    api_main.require_model()
    model = api_main.model
    X = _row_frame(payload)

    try:
        raw_pred = model.predict(X)[0]
        risk_score = float(np.clip(raw_pred, 0, 100))
    except Exception as e:
        logger.error("Explain scoring error: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    vec, base_value, method = _shap_vector_for_row(model, X)
    importance, shap_values = _importance_from_shap(vec)

    features = [
        FeatureImportanceItem(
            feature=name,
            importance=round(importance[i], 6),
            shap_value=round(shap_values[i], 6),
        )
        for i, name in enumerate(FEATURE_COLS)
    ]

    return ExplainResponse(
        location=payload.location,
        timestamp=payload.timestamp,
        risk_score=round(risk_score, 2),
        base_value=round(base_value, 4),
        features=features,
        model_version="xgboost-phase3a",
        method=method,
    )
