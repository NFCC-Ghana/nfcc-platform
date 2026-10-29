"""Shared settings for the flood-prediction experiments (E1-E7, E9).

Every dataset here is open and is read through Google Earth Engine or the
Open-Meteo Flood API. Citations are in research/flood_experiments/README.md.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

GEE_PROJECT = "nfcc-earth-engine-2026"

# Study period is bounded by the Global Flood Database, the only
# satellite-observed flood record with district-resolvable extents for
# Ghana (MODIS, 2000-02-17 to 2018-12-10). Weeks start on Mondays.
FIRST_WEEK = "2000-03-06"
LAST_WEEK = "2018-12-03"

# Earth Engine assets
GAUL_DISTRICTS = "FAO/GAUL/2015/level2"
CHIRPS_DAILY = "UCSB-CHG/CHIRPS/DAILY"
ERA5_LAND_DAILY = "ECMWF/ERA5_LAND/DAILY_AGGR"
GLOBAL_FLOOD_DB = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
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
RAIN_LAGS = ["rain_lag1", "rain_lag2", "rain_lag3", "rain_lag4"]
SOIL = ["sm_start", "sm_week_mean"]
RIVER = ["runoff_week_sum", "runoff_prev4w_sum", "q_week_max_log", "q_ratio"]
GEOGRAPHIC = ["elev_mean", "slope_mean", "perm_water_frac", "built_frac"]
EXPOSURE = ["log_pop_density"]

RANDOM_SEED = 42
