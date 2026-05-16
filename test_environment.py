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
import shap
import sklearn
import streamlit as st
import xarray as xr
import xgboost


def test_core_imports():
    """Verify all major libraries import correctly."""

    modules = [
        np,
        pd,
        gpd,
        rasterio,
        xr,
        sklearn,
        xgboost,
        shap,
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
