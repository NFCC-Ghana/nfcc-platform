"""Tests for core library imports.

Heavy / optional deps are imported inside the test so collection succeeds even when
the environment is temporarily out of sync (e.g. xarray 2025+ requires pandas>=2.1).

shap/sklearn/xgboost were removed 2026-09-27: leftover requirements.txt
entries from the trained XGBoost model that was backtested against real
historical flood events, found to show no reliable improvement over the
rule-based score, and deleted along with its training pipeline - nothing
in this codebase has imported any of the three since.
"""

import pytest


def test_imports():
    """Ensure all imports load successfully."""
    import numpy as np
    import pandas as pd

    try:
        import geopandas as gpd
    except ImportError as exc:
        pytest.skip(f"geopandas not installed: {exc}")

    try:
        import rasterio
    except ImportError as exc:
        pytest.skip(f"rasterio not installed: {exc}")

    try:
        import xarray as xr
    except (ImportError, AttributeError, ModuleNotFoundError) as exc:
        pytest.skip(
            "xarray needs pandas>=2.1 (pandas.arrays.NumpyExtensionArray). "
            f"Current pandas={pd.__version__}. "
            "Run: pip install -r requirements.txt  (or conda install 'pandas>=2.1'). "
            f"Original error: {exc}"
        )

    modules = [np, pd, gpd, rasterio, xr]
    assert all(module is not None for module in modules)
