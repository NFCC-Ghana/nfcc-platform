"""Tests for core library imports."""

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shap
import sklearn
import xarray as xr
import xgboost


def test_imports():
    """Ensure all imports load successfully."""

    modules = [
        np,
        pd,
        gpd,
        rasterio,
        xr,
        sklearn,
        xgboost,
        shap,
    ]

    assert all(module is not None for module in modules)
