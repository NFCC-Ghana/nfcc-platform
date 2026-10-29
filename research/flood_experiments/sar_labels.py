"""Sentinel-1 flood detections per district-week, 2015 onward.

Method: the UN-SPIDER Recommended Practice for flood mapping with
Sentinel-1 in Earth Engine, with Ghana-specific choices:

- VH backscatter, IW mode, ASCENDING pass only. Every regular pass over
  Ghana is ascending (tracks 45, 74 and 147), which meets UN-SPIDER's
  same-pass-direction requirement.
- Reference = median of all passes in the dry season (1 Jan - 28 Feb) of
  the same year. Sentinel-1 first imaged Ghana on 25 March 2015, so 2015
  uses the 2016 dry season.
- Computed on a 100 m grid (config.SAR_SCALE_M). Earth Engine's mean
  pyramid averages about 100 native 10 m looks per pixel, which
  suppresses speckle more than the 50 m focal filter UN-SPIDER applies
  at full resolution.
- Flood where after / reference > 1.25 (both in dB, so new water pushes
  the ratio up) AND after < -20 dB (open water is dark; this rejects
  moist-soil and crop changes).
- Masks: JRC Global Surface Water seasonality >= 10 months (permanent
  water), HydroSHEDS slope >= 5 %, and clusters under 8 pixels.

Each week records flooded km2 AND observed km2. Ghana is imaged every
6-12 days, so a week with no image is "not observed", not "no flood".

Runs as Earth Engine export tasks, one per half-year, because a
district-week reduction over Ghana exceeds the 5-minute interactive
limit. Run: python -m research.flood_experiments.sar_labels start
           python -m research.flood_experiments.sar_labels fetch
"""

import logging
import sys
from datetime import date, timedelta

import pandas as pd

from research.flood_experiments import config as C

logger = logging.getLogger("nfcc.research.sar")
ASSET_DIR = f"projects/{C.GEE_PROJECT}/assets/nfcc_research"
RATIO_THRESHOLD = 1.25
WATER_DB = -20.0
HALVES = {1: (1, 6), 2: (7, 12)}


def _name(year, half):
    return f"s1_flood_{year}_h{half}"


def _s1(ee, region):
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(region)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
        .select("VH")
    )


def _weeks(year, half):
    first, last = HALVES[half]
    start = date(year, 1, 1)
    start += timedelta(days=(7 - start.weekday()) % 7)  # first Monday
    weeks = []
    while start.year == year:
        if first <= start.month <= last:
            weeks.append(start.isoformat())
        start += timedelta(days=7)
    return weeks


def _half_collection(ee, year, half, districts):
    s1 = _s1(ee, districts.geometry())
    dry = s1.filterDate(f"{year}-01-01", f"{year}-03-01")
    dry_next = s1.filterDate(f"{year + 1}-01-01", f"{year + 1}-03-01")
    ref = ee.ImageCollection(ee.Algorithms.If(dry.size().gt(0), dry, dry_next)).median()
    static_ok = (
        ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        .select("seasonality")
        .unmask(0)
        .lt(10)
        .And(ee.Terrain.slope(ee.Image("WWF/HydroSHEDS/03VFDEM")).lt(5))
    )
    area = ee.Image.pixelArea().divide(1e6)

    def per_week(w):
        w = ee.Date(w)
        imgs = s1.filterDate(w, w.advance(7, "day"))
        after = imgs.mean()
        valid = after.mask().And(ref.mask()).unmask(0)
        flood = (
            after.divide(ref)
            .gt(RATIO_THRESHOLD)
            .And(after.lt(WATER_DB))
            .And(static_ok)
            .unmask(0)
        )
        flood = flood.updateMask(flood.connectedPixelCount(10).gte(8)).unmask(0)
        img = (
            flood.multiply(area)
            .rename("flood_km2")
            .addBands(valid.multiply(area).rename("obs_km2"))
        )
        fc = img.reduceRegions(
            districts, ee.Reducer.sum(), scale=C.SAR_SCALE_M, tileScale=16
        ).map(lambda f: f.set("week", w.format("YYYY-MM-dd")))
        return ee.Algorithms.If(imgs.size().gt(0), fc, ee.FeatureCollection([]))

    return ee.FeatureCollection(ee.List(_weeks(year, half)).map(per_week)).flatten()


def start_exports(ee, years):
    try:
        ee.data.createAsset({"type": "FOLDER"}, ASSET_DIR)
    except Exception:
        pass  # already exists
    districts = (
        ee.FeatureCollection(C.GAUL_DISTRICTS)
        .filter(ee.Filter.eq("ADM0_NAME", "Ghana"))
        .select(["ADM2_CODE"])
    )
    queued = {
        t["description"]
        for t in ee.data.getTaskList()
        if t["state"] in ("READY", "RUNNING")
    }
    for year in years:
        for half in HALVES:
            name = _name(year, half)
            try:
                ee.data.getAsset(f"{ASSET_DIR}/{name}")
                logger.info(f"{name}: already exported")
                continue
            except Exception:
                pass
            if f"nfcc_{name}" in queued:
                logger.info(f"{name}: export already queued or running")
                continue
            task = ee.batch.Export.table.toAsset(
                collection=_half_collection(ee, year, half, districts),
                description=f"nfcc_{name}",
                assetId=f"{ASSET_DIR}/{name}",
            )
            task.start()
            logger.info(f"{name}: started task {task.id}")


def fetch(ee, years) -> pd.DataFrame:
    """Read the exported tables into one DataFrame (cached as CSV)."""
    out = C.DATA_DIR / "raw" / "sar_district_weeks.csv"
    if out.exists():
        return pd.read_csv(out)
    frames = []
    for year in years:
        for half in HALVES:
            fc = ee.FeatureCollection(f"{ASSET_DIR}/{_name(year, half)}")
            rows = fc.select(
                ["ADM2_CODE", "week", "flood_km2", "obs_km2"], None, False
            ).getInfo()["features"]
            frames.append(pd.DataFrame([r["properties"] for r in rows]))
            logger.info(f"{_name(year, half)}: {len(rows)} district-weeks")
    df = pd.concat(frames, ignore_index=True).rename(
        columns={"ADM2_CODE": "district_code"}
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return df


def years():
    return list(range(int(C.FIRST_WEEK[:4]), int(C.LAST_WEEK[:4]) + 1))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    from research.flood_experiments.build_dataset import _init_ee

    _ee = _init_ee()
    if sys.argv[1] == "start":
        start_exports(_ee, years())
    else:
        fetch(_ee, years())
