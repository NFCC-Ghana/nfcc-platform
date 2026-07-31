"""Unit tests for forecast fusion, confidence, and fusion SHAP helpers."""

import numpy as np
import pytest

from src.models.confidence_scoring import forecast_confidence
from src.models.forecast_fusion import (
    ForecastFusionInput,
    fuse_forecasts,
    fuse_from_arrays,
    fusion_weights,
)
from src.models.fusion_explain import explain_fusion_shap


def test_fusion_three_sources_equal_weights():
    inp = ForecastFusionInput(40.0, 60.0, 50.0)
    out = fuse_forecasts(inp, weights=np.ones(3))
    assert out.unified_risk == pytest.approx(50.0)
    assert set(out.present_sources) == {"chirps", "glofas", "flood_hub"}


def test_fusion_missing_source_reweights():
    inp = ForecastFusionInput(chirps_risk=0.0, glofas_risk=100.0, flood_hub_risk=None)
    out = fuse_forecasts(inp, weights=np.ones(3))
    assert out.unified_risk == pytest.approx(50.0)
    assert out.missing_sources == ["flood_hub"]


def test_fusion_clips_inputs():
    inp = ForecastFusionInput(200.0, -5.0, 50.0)
    out = fuse_forecasts(inp, weights=np.ones(3))
    assert out.unified_risk <= 100.0
    assert out.unified_risk >= 0.0


def test_fusion_no_sources():
    inp = ForecastFusionInput(None, None, None)
    out = fuse_forecasts(inp)
    assert out.unified_risk == 0.0
    assert out.present_sources == []


def test_confidence_high_when_agreement():
    inp = ForecastFusionInput(50.0, 50.0, 50.0)
    c = forecast_confidence(inp, 50.0)
    assert c.confidence > 90.0
    assert c.num_sources == 3


def test_confidence_lower_with_spread():
    inp = ForecastFusionInput(0.0, 50.0, 100.0)
    c = forecast_confidence(inp, 50.0)
    assert c.confidence < 90.0


def test_fuse_from_arrays_matches_fuse_forecasts():
    inp = ForecastFusionInput(10.0, None, 90.0)
    w = fusion_weights()
    x, m = inp.as_vector_and_mask()
    a = fuse_from_arrays(x, m, w)
    b = fuse_forecasts(inp, w).unified_risk
    assert a == pytest.approx(b)


def test_explain_fusion_shap_runs_small_nsamples():
    inp = ForecastFusionInput(80.0, 20.0, 50.0)
    out = explain_fusion_shap(inp, nsamples=24)
    assert "chirps" in out.shap_values
    assert out.unified_risk == pytest.approx(
        fuse_forecasts(inp).unified_risk, rel=1e-6, abs=1e-6
    )
    s = sum(out.shap_values.values())
    assert s == pytest.approx(out.unified_risk - out.expected_value, rel=0.15, abs=0.15)
