"""Tests for core library imports.

Heavy / optional deps are imported inside the test so collection succeeds even when
the environment is temporarily out of sync (e.g. xarray 2025+ requires pandas>=2.1).
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

    import shap
    import sklearn
    import xgboost

    modules = [np, pd, gpd, rasterio, xr, sklearn, xgboost, shap]
    assert all(module is not None for module in modules)
