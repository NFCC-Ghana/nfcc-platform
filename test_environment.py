#!/usr/bin/env python3
"""
NFCC Environment Verification Script
"""

import sys

import ee
import fastapi
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly
import rasterio
import streamlit as st
import xarray as xr

# shap, scikit-learn and xgboost were dropped from the project on
# 2026-09-27 along with the unused trained model (see requirements.txt),
# so they're no longer part of a correct environment.


def test_core_imports():
    """Verify all major libraries import correctly."""

    modules = [
        np,
        pd,
        gpd,
        rasterio,
        xr,
        st,
        folium,
        plotly,
        fastapi,
    ]

    assert all(module is not None for module in modules)

    print("✅ Core imports successful")


def test_gee():
    """Verify Earth Engine initializes."""

    ee.Initialize(project="nfcc-earth-engine-2026")
    print("✅ Google Earth Engine initialized")


if __name__ == "__main__":
    print(f"Python version: {sys.version}")

    test_core_imports()
    test_gee()

    print("\n✅ Environment ready for NFCC development!")
