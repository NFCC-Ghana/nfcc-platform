"""Shared settings for the flood-prediction experiments.

Every dataset here is open and is read through Google Earth Engine or the
Open-Meteo Flood API. Citations are in research/flood_experiments/README.md.

Two studies share the code; pick one with the NFCC_STUDY environment
variable (default "v2"):

- v2      2015-2025. Labels: Groundsource news-derived flood events
          (Mayo et al. 2026) + our documented events, with Sentinel-1
          detections as an independent second label. Main study.
- v1_gfd  2000-2018. Labels: Global Flood Database (MODIS, Tellman et
          al. 2021). Kept as a sensitivity analysis.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEE_PROJECT = "nfcc-earth-engine-2026"

STUDIES = {
    "v1_gfd": {
        "first_week": "2000-03-06",
        "last_week": "2018-12-03",
        "test_years": list(range(2008, 2019)),
        "q_climatology_end": "2007-12-31",
        "shap_train_end": 2012,
        "labels": ["gfd"],
        "discharge_point": "centroid",
    },
    "v2": {
        "first_week": "2015-01-05",
        "last_week": "2025-12-22",
        "test_years": list(range(2018, 2026)),
        "q_climatology_end": "2016-12-31",
        "shap_train_end": 2021,
        "labels": ["news"],
        "discharge_point": "river",
    },
}
STUDY = os.environ.get("NFCC_STUDY", "v2")
S = STUDIES[STUDY]
DATA_DIR = ROOT / "data" / STUDY
RESULTS_DIR = ROOT / "results" / STUDY

# Weeks start on Mondays.
FIRST_WEEK = S["first_week"]
LAST_WEEK = S["last_week"]
TEST_YEARS = S["test_years"]

# Earth Engine assets
GAUL_DISTRICTS = "FAO/GAUL/2015/level2"
CHIRPS_DAILY = "UCSB-CHG/CHIRPS/DAILY"
ERA5_LAND_DAILY = "ECMWF/ERA5_LAND/DAILY_AGGR"
GLOBAL_FLOOD_DB = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
GROUNDSOURCE = "projects/sat-io/open-datasets/groundsource_2026"
MERIT_HYDRO = "MERIT/Hydro/v1_0_1"
SRTM = "USGS/SRTMGL1_003"
SURFACE_WATER = "JRC/GSW1_4/GlobalSurfaceWater"
GHSL_BUILT = "JRC/GHSL/P2023A/GHS_BUILT_S"
WORLDPOP = "WorldPop/GP/100m/pop"

# Zonal means are taken on a 2 km grid so the smallest districts (e.g.
# Accra Metropolis) still contain enough resampled CHIRPS/ERA5 cells.
DYNAMIC_SCALE_M = 2000
STATIC_SCALE_M = 250

OPEN_METEO_FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"

# A district counts as flooded in a Global Flood Database event when the
# event's mapped water (excluding JRC permanent water) covers at least
# this many km2 inside it. 1 km2 = 16 MODIS 250 m pixels, which keeps
# single-pixel classification noise along river banks out of the labels.
LABEL_MIN_FLOODED_KM2 = 1.0

# Groundsource events are geocoded to the place a news story names: a
# street, a town or a whole region. Events larger than this are
# region- or country-level mentions that can't be placed in one
# district, so they are dropped (counted in the dataset summary).
# Smaller ones go to the district holding their centroid.
NEWS_MAX_AREA_KM2 = 1000.0

# Sentinel-1 audit (sar_labels.py): a sampled district-week counts as
# radar-confirmed when at least SAR_MIN_KM2 of new water is detected and
# at least SAR_MIN_OBSERVED of the district was imaged.
SAR_MIN_KM2 = 1.0
SAR_MIN_OBSERVED = 0.5

# Our own documented events (src/hydrology/flood_polygons.py) mapped to
# GAUL 2015 district names, so urban floods the MODIS record misses are
# still labelled.
CURATED_DISTRICT_NAMES = {
    "Accra Central": ["Accra Metropolis"],
    "Accra West": ["Accra Metropolis"],
    "Accra East": ["Accra Metropolis"],
    "Tamale": ["Tamale North Sub Metro", "Tamale Metropolis"],
    "Yendi": ["Yendi Municipal"],
    "Gushegu": ["Gushegu"],
    "North Tongu": ["North Tongu"],
    "South Tongu": ["South Tongu"],
    "Keta": ["Keta Municipal"],
    "Ada": ["Ada East", "Ada West"],
}

# Feature groups, in the ablation order the Manuscript Writing Guide
# specifies (Baseline -> +Soil -> +River -> +Dam -> +Geographic ->
# +Exposure). There is no historical dam record, so +Dam is reported as
# not runnable rather than faked.
SEASON = ["woy_sin", "woy_cos"]
RAIN = ["rain_week_sum", "rain_week_max", "rain_prev4w_sum"]
if STUDY != "v1_gfd":
    # Wettest-pixel rainfall (95th percentile across the district):
    # a district mean dilutes the convective cells that cause flash floods.
    RAIN = RAIN + ["rain_week_max_p95", "rain_week_sum_p95"]
RAIN_LAGS = ["rain_lag1", "rain_lag2", "rain_lag3", "rain_lag4"]
SOIL = ["sm_start", "sm_week_mean"]
RIVER = ["runoff_week_sum", "runoff_prev4w_sum", "q_week_max_log", "q_ratio"]
GEOGRAPHIC = ["elev_mean", "slope_mean", "perm_water_frac", "built_frac"]
EXPOSURE = ["log_pop_density"]

# Inputs whose increase can only raise flood risk; XGBoost is constrained
# to be monotone in them, so it cannot learn physically impossible
# shapes from a few hundred events.
MONOTONE_UP = set(RAIN + RAIN_LAGS + SOIL + RIVER)

RANDOM_SEED = 42
