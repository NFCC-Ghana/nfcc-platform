"""Sentinel-1 audit of the news flood labels (case-control design).

Question: when the news reports a flood onset in a district, does
satellite radar see new water there that week - and how often does it
see new water when no flood was reported?

Mapping every district-week of 2015-2025 with Sentinel-1 is tens of
compute-hours, more than the Earth Engine free tier delivers in a day
(the full-panel exports ran out of memory or ran for hours per year).
Labels are therefore audited, not replaced:

- Cases: every news-label flood onset (district, week).
- Controls, one of each per case, with no news flood that week:
  same week in a random other district (matches season and weather
  regime); same district and week of year in a random other year
  (matches place).

For each sampled district-week, radar is read over a +/- 1 week window.

Method: the UN-SPIDER Recommended Practice for flood mapping with
Sentinel-1 in Earth Engine. VH backscatter, IW mode, ASCENDING passes
(the only regular passes over Ghana, so the same-pass requirement
holds). Reference = median of the dry season (1 Jan - 28 Feb) of the
same year; Sentinel-1 first imaged Ghana on 25 March 2015, so 2015 uses
2016. "After" = the darkest pass in the window (any flooding). Flood
where after / reference > 1.25 (dB) AND after < -20 dB, outside
permanent water (JRC seasonality >= 10 months) and slopes >= 5 %
(HydroSHEDS), in clusters of at least 8 pixels, on a 100 m grid.

Each district-week takes under a second, so the audit runs as ordinary
requests in cached chunks (about 30 minutes for ~2,700 rows).
Run: python -m research.flood_experiments.sar_labels
"""

import logging
import time

import numpy as np
import pandas as pd

from research.flood_experiments import config as C

logger = logging.getLogger("nfcc.research.sar")
RATIO_THRESHOLD = 1.25
WATER_DB = -20.0
CHUNK = 50


def audit_sample(panel: pd.DataFrame, seed=C.RANDOM_SEED) -> pd.DataFrame:
    """Cases (news onsets) and two matched controls per case."""
    from research.flood_experiments.features import build_features

    rng = np.random.default_rng(seed)
    df = build_features(panel, "news")
    p = panel.assign(week=pd.to_datetime(panel["week"]))
    flooded = set(
        zip(p.loc[p.flood_news == 1, "district_code"], p.loc[p.flood_news == 1, "week"])
    )
    codes = p["district_code"].unique()
    weeks = set(p["week"].unique())
    rows = []
    for r in df[df.onset == 1].itertuples():
        rows.append((r.district_code, r.week, "onset"))
        for _ in range(50):  # same week, another district without a flood
            c = rng.choice(codes)
            if c != r.district_code and (c, r.week) not in flooded:
                rows.append((c, r.week, "control_same_week"))
                break
        years = [y for y in range(2015, 2026) if y != r.week.year]
        for _ in range(50):  # same district and week of year, another year
            w = r.week + pd.DateOffset(years=int(rng.choice(years)) - r.week.year)
            w = w - pd.Timedelta(days=w.weekday())  # back to Monday
            if w in weeks and (r.district_code, w) not in flooded:
                rows.append((r.district_code, w, "control_same_place"))
                break
    out = pd.DataFrame(rows, columns=["district_code", "week", "kind"])
    out["week"] = out["week"].dt.strftime("%Y-%m-%d")
    return out


def _audit_collection(ee, sample: pd.DataFrame):
    districts = ee.FeatureCollection(C.GAUL_DISTRICTS).filter(
        ee.Filter.eq("ADM0_NAME", "Ghana")
    )
    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
        .select("VH")
    )
    static_ok = (
        ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        .select("seasonality")
        .unmask(0)
        .lt(10)
        .And(ee.Terrain.slope(ee.Image("WWF/HydroSHEDS/03VFDEM")).lt(5))
    )
    area = ee.Image.pixelArea().divide(1e6)
    feats = ee.FeatureCollection(
        [
            ee.Feature(
                None,
                {"district_code": int(r.district_code), "week": r.week, "kind": r.kind},
            )
            for r in sample.itertuples()
        ]
    )
    joined = ee.Join.saveFirst("d").apply(
        feats,
        districts,
        ee.Filter.equals(leftField="district_code", rightField="ADM2_CODE"),
    )

    def measure(f):
        geom = ee.Feature(f.get("d")).geometry()
        w = ee.Date(f.get("week"))
        year = w.get("year")
        here = s1.filterBounds(geom)
        dry = here.filterDate(ee.Date.fromYMD(year, 1, 1), ee.Date.fromYMD(year, 3, 1))
        dry_next = here.filterDate(
            ee.Date.fromYMD(year.add(1), 1, 1), ee.Date.fromYMD(year.add(1), 3, 1)
        )
        ref_src = ee.ImageCollection(ee.Algorithms.If(dry.size().gt(0), dry, dry_next))
        imgs = here.filterDate(w.advance(-7, "day"), w.advance(14, "day"))
        ok = imgs.size().gt(0).And(ref_src.size().gt(0))

        def compute():
            ref = ref_src.median()
            after = imgs.min()
            # A composite of several passes has no native grid or
            # footprint: a plain unmask(0) keeps it fully masked, and the
            # cluster filter would run on a 1-degree default grid. Unmask
            # outside the footprint and fix a 100 m grid first; without
            # this every district reads 0 km2 flooded.
            flood = (
                after.divide(ref)
                .gt(RATIO_THRESHOLD)
                .And(after.lt(WATER_DB))
                .And(static_ok)
                .unmask(0, False)
                .reproject(crs="EPSG:4326", scale=100)
            )
            flood = flood.updateMask(flood.connectedPixelCount(10).gte(8)).unmask(0)
            valid = after.mask().And(ref.mask()).unmask(0)
            sums = (
                flood.multiply(area)
                .rename("flood_km2")
                .addBands(valid.multiply(area).rename("obs_km2"))
                .reduceRegion(ee.Reducer.sum(), geom, 100, maxPixels=1e9, tileScale=4)
            )
            return ee.Feature(None, sums).copyProperties(
                f, ["district_code", "week", "kind"]
            )

        empty = ee.Feature(None, {"flood_km2": 0, "obs_km2": 0}).copyProperties(
            f, ["district_code", "week", "kind"]
        )
        return ee.Feature(ee.Algorithms.If(ok, compute(), empty)).set(
            "n_images", imgs.size()
        )

    return joined.map(measure)


def run_audit(ee, sample: pd.DataFrame) -> pd.DataFrame:
    """Measure every sampled district-week, CHUNK rows per request.
    Each chunk is cached, so an interrupted run resumes where it
    stopped."""
    out = C.DATA_DIR / "raw" / "sar_audit.csv"
    if out.exists():
        return pd.read_csv(out)
    parts = C.DATA_DIR / "raw" / "sar_audit_parts"
    parts.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(sample), CHUNK):
        part = parts / f"{i // CHUNK:03d}.csv"
        if part.exists():
            continue
        for attempt in range(4):
            try:
                fc = _audit_collection(ee, sample.iloc[i : i + CHUNK])
                rows = [f["properties"] for f in fc.getInfo()["features"]]
                break
            except Exception as e:  # EE throttling / network blips
                logger.warning(f"audit rows {i}: attempt {attempt + 1}: {e}")
                time.sleep(30 * (attempt + 1))
        else:
            raise RuntimeError(f"Earth Engine kept failing at audit row {i}")
        pd.DataFrame(rows).to_csv(part, index=False)
        logger.info(f"audit rows {i}-{i + len(rows) - 1} done")
    df = pd.concat(
        [pd.read_csv(p) for p in sorted(parts.glob("*.csv"))], ignore_index=True
    )
    df = df[["district_code", "week", "kind", "flood_km2", "obs_km2", "n_images"]]
    df.to_csv(out, index=False)
    return df


def _sample():
    """The audit sample, built once from the panel and cached, so the
    cached chunks always line up with it."""
    path = C.DATA_DIR / "raw" / "sar_audit_sample.csv"
    if path.exists():
        return pd.read_csv(path)
    s = audit_sample(pd.read_parquet(C.DATA_DIR / "panel.parquet"))
    s.to_csv(path, index=False)
    return s


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    from research.flood_experiments.build_dataset import _init_ee

    _ee = _init_ee()
    sample = _sample()
    logger.info(f"audit sample: {sample['kind'].value_counts().to_dict()}")
    run_audit(_ee, sample)
