"""Sentinel-1 flood detections per district-week, 2015 onward.

Method: the UN-SPIDER Recommended Practice for flood mapping with
Sentinel-1 in Earth Engine, with Ghana-specific choices:

- VH backscatter, IW mode, ASCENDING pass only (the only pass with
  regular coverage of Ghana; tracks 45, 74 and 147).
- Reference = median of the same relative orbit over the dry season
  (1 Jan - 28 Feb) of the same year, so wet and dry images share the
  viewing geometry.
- 50 m focal-mean smoothing; flood where after / reference > 1.25 (both
  in dB, so water darkens the ratio upward) AND after < -20 dB (open
  water is dark; this rejects moist-soil and crop changes).
- Masks: JRC Global Surface Water seasonality >= 10 months (permanent
  water), HydroSHEDS slope >= 5 %, and clusters under 8 pixels.

Each week records flooded km2 AND observed km2. Ghana is imaged every
6-12 days, so a week with no image is "not observed", not "no flood".

Runs as Earth Engine export tasks (one per year), because a single
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


def _asset(year):
    return f"{ASSET_DIR}/s1_flood_{year}"


def _year_collection(ee, year, districts):
    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(districts.geometry())
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
        .select("VH")
    )
    dry = s1.filterDate(f"{year}-01-01", f"{year}-03-01")
    # Sentinel-1 only began imaging Ghana mid-2015, so a track with no
    # dry-season pass this year takes next year's: the reference only
    # has to show dry ground in the same viewing geometry.
    dry_next = s1.filterDate(f"{year + 1}-01-01", f"{year + 1}-03-01")
    orbits = dry.merge(dry_next).aggregate_array("relativeOrbitNumber_start").distinct()

    def reference(o):
        this = dry.filter(ee.Filter.eq("relativeOrbitNumber_start", o))
        nxt = dry_next.filter(ee.Filter.eq("relativeOrbitNumber_start", o))
        src = ee.ImageCollection(ee.Algorithms.If(this.size().gt(0), this, nxt))
        return src.median().focal_mean(50, "circle", "meters").set("orbit", o)

    refs = ee.ImageCollection(orbits.map(reference))
    static_ok = (
        ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        .select("seasonality")
        .unmask(0)
        .lt(10)
        .And(ee.Terrain.slope(ee.Image("WWF/HydroSHEDS/03VFDEM")).lt(5))
    )

    def flood(img):
        ref = ee.Image(
            refs.filter(
                ee.Filter.eq("orbit", img.get("relativeOrbitNumber_start"))
            ).first()
        )
        after = img.focal_mean(50, "circle", "meters")
        valid = after.mask().And(ref.mask()).unmask(0).rename("valid")
        f = (
            after.divide(ref)
            .gt(RATIO_THRESHOLD)
            .And(after.lt(WATER_DB))
            .And(static_ok)
            .unmask(0)
            .rename("flood")
        )
        return f.addBands(valid)

    # Tracks with no dry-season reference in either year are skipped.
    s1 = s1.filter(ee.Filter.inList("relativeOrbitNumber_start", orbits))
    start = date(year, 1, 1)
    start += timedelta(days=(7 - start.weekday()) % 7)  # first Monday
    weeks = []
    while start.year == year:
        weeks.append(start.isoformat())
        start += timedelta(days=7)

    def per_week(w):
        w = ee.Date(w)
        imgs = s1.filterDate(w, w.advance(7, "day"))
        m = imgs.map(flood).max()
        fl = m.select("flood")
        fl = fl.updateMask(fl.connectedPixelCount(10).gte(8)).unmask(0)
        area = ee.Image.pixelArea().divide(1e6)
        img = (
            fl.multiply(area)
            .rename("flood_km2")
            .addBands(m.select("valid").multiply(area).rename("obs_km2"))
        )
        fc = img.reduceRegions(
            districts, ee.Reducer.sum(), scale=C.SAR_SCALE_M, tileScale=8
        ).map(lambda f: f.set("week", w.format("YYYY-MM-dd")))
        return ee.Algorithms.If(imgs.size().gt(0), fc, ee.FeatureCollection([]))

    return ee.FeatureCollection(ee.List(weeks).map(per_week)).flatten()


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
        try:
            ee.data.getAsset(_asset(year))
            logger.info(f"{year}: already exported")
            continue
        except Exception:
            pass
        if f"nfcc_s1_flood_{year}" in queued:
            logger.info(f"{year}: export already queued or running")
            continue
        task = ee.batch.Export.table.toAsset(
            collection=_year_collection(ee, year, districts),
            description=f"nfcc_s1_flood_{year}",
            assetId=_asset(year),
        )
        task.start()
        logger.info(f"{year}: started task {task.id}")


def fetch(ee, years) -> pd.DataFrame:
    """Read the exported tables into one DataFrame (cached as CSV)."""
    out = C.DATA_DIR / "raw" / "sar_district_weeks.csv"
    if out.exists():
        return pd.read_csv(out)
    frames = []
    for year in years:
        fc = ee.FeatureCollection(_asset(year))
        rows = fc.select(
            ["ADM2_CODE", "week", "flood_km2", "obs_km2"], None, False
        ).getInfo()["features"]
        frames.append(pd.DataFrame([r["properties"] for r in rows]))
        logger.info(f"{year}: {len(rows)} district-weeks")
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
