"""Build the Ghana district-week panel used by every experiment.

One row per (GAUL 2015 district, Monday-start week) over the study
period in config.STUDY:

- Dynamic inputs: CHIRPS weekly rainfall total and daily maximum (district
  mean and, in v2, the 95th-percentile pixel); ERA5-Land top-layer soil
  moisture and surface runoff; GloFAS v4 river discharge (Open-Meteo
  Flood API) at the district centroid (v1) or at the district's main
  river, the MERIT Hydro cell with the most upstream area (v2).
- Static inputs: SRTM elevation and slope, JRC permanent-water share, GHSL
  built-up share, WorldPop population density.
- Labels: the district was flooded that week.
  v1: Global Flood Database (Tellman et al. 2021) + documented events.
  v2: flood_news = Groundsource news events (Mayo et al. 2026) +
      documented events + NADMO incidents if supplied (nadmo.py);
      flood_sar = Sentinel-1 detections (sar_labels.py);
      flood_union = either.

Raw pulls are cached under data/<study>/raw/ so a re-run only fetches
what is missing. Run: python -m research.flood_experiments.build_dataset
"""

import json
import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

from research.flood_experiments import config as C

logger = logging.getLogger("nfcc.research.dataset")
RAW = C.DATA_DIR / "raw"


def _init_ee():
    import ee

    from src.hydrology.ee_auth import initialize_earth_engine

    if not initialize_earth_engine(C.GEE_PROJECT):
        sys.exit("Earth Engine is not available - run `earthengine authenticate`.")
    return ee


def _week_starts():
    start = date.fromisoformat(C.FIRST_WEEK)
    end = date.fromisoformat(C.LAST_WEEK)
    weeks = []
    while start <= end:
        weeks.append(start)
        start += timedelta(days=7)
    return weeks


def _districts(ee):
    return ee.FeatureCollection(C.GAUL_DISTRICTS).filter(
        ee.Filter.eq("ADM0_NAME", "Ghana")
    )


def _fetch_features(fc, props):
    """getInfo() a FeatureCollection's properties only (no geometry)."""
    rows = fc.select(props, None, False).getInfo()["features"]
    return [r["properties"] for r in rows]


def fetch_static(ee) -> pd.DataFrame:
    out = RAW / "static.csv"
    if out.exists():
        return pd.read_csv(out)
    v1 = C.ROOT / "data" / "v1_gfd" / "raw" / "static.csv"
    if v1.exists():  # static layers don't depend on the study period
        df = pd.read_csv(v1)
        df.to_csv(out, index=False)
        return df
    districts = _districts(ee).map(
        lambda f: f.set(
            {
                "area_km2": f.geometry().area(100).divide(1e6),
                "lat": f.geometry().centroid(100).coordinates().get(1),
                "lon": f.geometry().centroid(100).coordinates().get(0),
            }
        )
    )
    dem = ee.Image(C.SRTM)
    slope = ee.Terrain.slope(dem)
    perm_water = (
        ee.Image(C.SURFACE_WATER).select("occurrence").unmask(0).gte(75).rename("pw")
    )
    built = (
        ee.ImageCollection(C.GHSL_BUILT)
        .filter(ee.Filter.eq("system:index", "2010"))
        .first()
        .select("built_surface")
        .divide(10000)
        .rename("built")
    )
    pop = (
        ee.ImageCollection(C.WORLDPOP)
        .filter(ee.Filter.eq("country", "GHA"))
        .filter(ee.Filter.eq("year", 2010))
        .first()
        .rename("pop")
    )
    means = (
        dem.rename("elev")
        .addBands(slope.rename("slope"))
        .addBands(perm_water)
        .addBands(built)
    )
    fc = means.reduceRegions(districts, ee.Reducer.mean(), scale=C.STATIC_SCALE_M)
    fc = pop.reduceRegions(fc, ee.Reducer.sum(), scale=100, tileScale=4)
    rows = _fetch_features(
        fc,
        ["ADM2_CODE", "ADM2_NAME", "ADM1_NAME", "area_km2", "lat", "lon"]
        + ["elev", "slope", "pw", "built", "sum"],
    )
    df = pd.DataFrame(rows).rename(
        columns={
            "ADM2_CODE": "district_code",
            "ADM2_NAME": "district",
            "ADM1_NAME": "region",
            "elev": "elev_mean",
            "slope": "slope_mean",
            "pw": "perm_water_frac",
            "built": "built_frac",
            "sum": "population",
        }
    )
    df.to_csv(out, index=False)
    return df


def fetch_river_points(ee) -> pd.DataFrame:
    """Each district's main river: the cell with the largest MERIT Hydro
    upstream area. GloFAS discharge read there tracks the river that
    floods the district, which a centroid often misses."""
    out = RAW / "river_points.csv"
    if out.exists():
        return pd.read_csv(out)
    img = ee.Image(C.MERIT_HYDRO).select("upa").addBands(ee.Image.pixelLonLat())
    fc = img.reduceRegions(
        _districts(ee), ee.Reducer.max(3), scale=C.STATIC_SCALE_M, tileScale=4
    )
    rows = _fetch_features(fc, ["ADM2_CODE", "max", "max1", "max2"])
    df = pd.DataFrame(rows).rename(
        columns={
            "ADM2_CODE": "district_code",
            "max": "river_upa_km2",
            "max1": "river_lon",
            "max2": "river_lat",
        }
    )
    df.to_csv(out, index=False)
    return df


def _weekly_image(ee, week_ms):
    start = ee.Date(week_ms)
    end = start.advance(7, "day")
    chirps = (
        ee.ImageCollection(C.CHIRPS_DAILY)
        .filterDate(start, end)
        .select("precipitation")
    )
    era5 = ee.ImageCollection(C.ERA5_LAND_DAILY).filterDate(start, end)
    return (
        chirps.sum()
        .rename("rain_week_sum")
        .addBands(chirps.max().rename("rain_week_max"))
        .addBands(
            era5.select("volumetric_soil_water_layer_1").mean().rename("sm_week_mean")
        )
        .addBands(
            era5.select("surface_runoff_sum")
            .sum()
            .multiply(1000)
            .rename("runoff_week_sum")
        )
        .set("week_ms", week_ms)
    )


def fetch_dynamic(ee, chunk_weeks: int = 10) -> pd.DataFrame:
    cache = RAW / "dynamic"
    cache.mkdir(parents=True, exist_ok=True)
    districts = _districts(ee).select(["ADM2_CODE"])
    weeks = _week_starts()
    base = ["rain_week_sum", "rain_week_max", "sm_week_mean", "runoff_week_sum"]
    if C.STUDY == "v1_gfd":
        reducer, bands = ee.Reducer.mean(), base
    else:
        # mean plus the wettest-pixel (95th percentile) value per band
        reducer = ee.Reducer.mean().combine(ee.Reducer.percentile([95]), "", True)
        bands = [f"{b}_mean" for b in base] + [f"{b}_p95" for b in base[:2]]
    for i in range(0, len(weeks), chunk_weeks):
        chunk = weeks[i : i + chunk_weeks]
        out = cache / f"{chunk[0].isoformat()}.csv"
        if out.exists():
            continue
        ms = [
            int(datetime(w.year, w.month, w.day, tzinfo=timezone.utc).timestamp())
            * 1000
            for w in chunk
        ]
        images = ee.ImageCollection(ee.List(ms).map(lambda m: _weekly_image(ee, m)))
        fc = images.map(
            lambda img: img.reduceRegions(
                districts, reducer, scale=C.DYNAMIC_SCALE_M, tileScale=2
            ).map(lambda f: f.set("week_ms", img.get("week_ms")))
        ).flatten()
        for attempt in range(4):
            try:
                rows = _fetch_features(fc, ["ADM2_CODE", "week_ms"] + bands)
                break
            except Exception as e:  # EE throttling / transient errors
                logger.warning(f"chunk {chunk[0]} attempt {attempt + 1}: {e}")
                time.sleep(20 * (attempt + 1))
        else:
            raise RuntimeError(f"Earth Engine kept failing for chunk {chunk[0]}")
        pd.DataFrame(rows).to_csv(out, index=False)
        logger.info(f"dynamic {chunk[0]} .. {chunk[-1]}: {len(rows)} rows")
    df = pd.concat(
        [pd.read_csv(p) for p in sorted(cache.glob("*.csv"))], ignore_index=True
    )
    df["week"] = pd.to_datetime(df["week_ms"], unit="ms").dt.date.astype(str)
    df.columns = [c[:-5] if c.endswith("_mean") else c for c in df.columns]
    return df.rename(columns={"ADM2_CODE": "district_code"}).drop(columns="week_ms")


def _fetch_discharge_file(lat, lon, name, out) -> bool:
    """One whole-period request per district. The free API weighs a
    request by its length, so about 100 19-year requests use up the
    hourly quota; on HTTP 429 wait for the quota to reset instead of
    skipping the district."""
    for attempt in range(12):
        try:
            resp = requests.get(
                C.OPEN_METEO_FLOOD_URL,
                params={
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "daily": "river_discharge",
                    "start_date": f"{C.FIRST_WEEK[:4]}-01-01",
                    "end_date": f"{C.LAST_WEEK[:4]}-12-31",
                },
                timeout=60,
            )
        except requests.RequestException as e:  # DNS / connection drops
            wait = 30 * (attempt + 1)
            logger.info(f"discharge {name}: {type(e).__name__}, retry in {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code == 200:
            out.write_text(resp.text)
            time.sleep(0.5)
            return True
        wait = 600 if resp.status_code == 429 else 15 * (attempt + 1)
        logger.info(f"discharge {name}: HTTP {resp.status_code}, retry in {wait}s")
        time.sleep(wait)
    return False


def fetch_discharge(static: pd.DataFrame, points=None) -> pd.DataFrame:
    """Weekly max GloFAS v4 discharge at each district's point: the
    centroid (v1), or the main-river cell from fetch_river_points (v2).
    The API reads the 0.05 degree GloFAS cell holding the point."""
    cache = RAW / "discharge"
    cache.mkdir(parents=True, exist_ok=True)
    if points is not None:
        static = static.drop(columns=["lat", "lon"]).merge(
            points.rename(columns={"river_lat": "lat", "river_lon": "lon"}),
            on="district_code",
        )
    frames = []
    for row in static.itertuples():
        out = cache / f"{row.district_code}.json"
        if not out.exists() and not _fetch_discharge_file(
            row.lat, row.lon, row.district, out
        ):
            logger.warning(f"No discharge for {row.district}")
            continue
        daily = json.loads(out.read_text())["daily"]
        s = pd.Series(
            daily["river_discharge"], index=pd.to_datetime(daily["time"]), dtype=float
        )
        weekly = s.resample("W-MON", label="left", closed="left").max()
        weekly.index = weekly.index.date.astype(str)
        frames.append(
            pd.DataFrame(
                {
                    "district_code": row.district_code,
                    "week": weekly.index,
                    "q_week_max": weekly.values,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def fetch_gfd_labels(ee) -> pd.DataFrame:
    """Flooded km2 per district for every Global Flood Database event that
    touches Ghana, with each event's start and end dates."""
    out = RAW / "gfd_district_events.csv"
    if out.exists():
        return pd.read_csv(out)
    districts = _districts(ee).select(["ADM2_CODE"])
    events = ee.ImageCollection(C.GLOBAL_FLOOD_DB).filterBounds(districts.geometry())
    ids = events.aggregate_array("system:index").getInfo()
    rows = []
    for idx in ids:
        img = ee.Image(f"{C.GLOBAL_FLOOD_DB}/{idx}")
        meta = ee.Dictionary(
            {
                "id": img.get("id"),
                "start": img.get("system:time_start"),
                "end": img.get("system:time_end"),
            }
        ).getInfo()
        water = (
            img.select("flooded")
            .eq(1)
            .And(img.select("jrc_perm_water").eq(0))
            .multiply(ee.Image.pixelArea())
            .divide(1e6)
            .rename("flooded_km2")
        )
        fc = water.reduceRegions(
            districts, ee.Reducer.sum(), scale=C.STATIC_SCALE_M, tileScale=4
        )
        for p in _fetch_features(fc, ["ADM2_CODE", "sum"]):
            if (p.get("sum") or 0) > 0:
                rows.append(
                    {
                        "gfd_id": meta["id"],
                        "start": pd.to_datetime(meta["start"], unit="ms").date(),
                        "end": pd.to_datetime(meta["end"], unit="ms").date(),
                        "district_code": p["ADM2_CODE"],
                        "flooded_km2": p["sum"],
                    }
                )
        logger.info(f"GFD event {meta['id']}: {len(rows)} district hits so far")
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    return df


def fetch_news_events(ee) -> pd.DataFrame:
    """Groundsource flood events in Ghana, each placed in the district
    holding its centroid. Events larger than NEWS_MAX_AREA_KM2 (region-
    or country-level mentions) keep district_code = NaN, so the summary
    can count them, but never label a district."""
    out = RAW / "groundsource_events.csv"
    if out.exists():
        return pd.read_csv(out)
    districts = _districts(ee).select(["ADM2_CODE"])
    events = (
        ee.FeatureCollection(C.GROUNDSOURCE)
        .filterBounds(districts.geometry())
        .map(lambda f: f.setGeometry(f.geometry().centroid(100)))
    )
    joined = ee.Join.saveFirst("district").apply(
        events, districts, ee.Filter.intersects(".geo", None, ".geo")
    )
    joined = joined.map(
        lambda f: f.set("ADM2_CODE", ee.Feature(f.get("district")).get("ADM2_CODE"))
    )
    rows = _fetch_features(
        joined, ["uuid", "start_date", "end_date", "area_km2", "ADM2_CODE"]
    )
    df = pd.DataFrame(rows).rename(columns={"ADM2_CODE": "district_code"})
    df.loc[df["area_km2"] > C.NEWS_MAX_AREA_KM2, "district_code"] = np.nan
    df.to_csv(out, index=False)
    return df


def curated_events():
    from src.hydrology.flood_polygons import flood_polygons

    return flood_polygons.get_flood_events()


def _mark(panel, col, code, start, end, source):
    """Flag every week of district `code` that overlaps [start, end]."""
    week = pd.to_datetime(panel["week"])
    mask = (
        (panel["district_code"] == code)
        & (week + pd.Timedelta(days=6) >= start)
        & (week <= end)
    )
    panel.loc[mask, col] = 1
    src = panel.loc[mask, "label_source"]
    panel.loc[mask, "label_source"] = np.where(
        src.str.contains(source, regex=False),
        src,
        (src + "|" + source).str.strip("|"),
    )


def _mark_curated(panel, static, col):
    name_to_code = static.groupby("district")["district_code"].apply(list).to_dict()
    for ev in curated_events():
        day = pd.Timestamp(ev["date"])
        for name in ev["districts"]:
            for gaul_name in C.CURATED_DISTRICT_NAMES.get(name, [name]):
                for code in name_to_code.get(gaul_name, []):
                    _mark(panel, col, code, day, day, "curated")


def build_labels(panel, static, gfd):
    """v1. flood = 1 for every week overlapping a GFD event that flooded
    at least LABEL_MIN_FLOODED_KM2 of the district, or containing one of
    our documented events for a district it names."""
    panel["flood"] = 0
    panel["label_source"] = ""
    hits = gfd[gfd["flooded_km2"] >= C.LABEL_MIN_FLOODED_KM2]
    for ev in hits.itertuples():
        _mark(
            panel,
            "flood",
            ev.district_code,
            pd.Timestamp(ev.start),
            pd.Timestamp(ev.end),
            "GFD",
        )
    _mark_curated(panel, static, "flood")
    return panel


def sar_flags(sar: pd.DataFrame) -> pd.Series:
    """A Sentinel-1 district-week is a flood when the new water is at
    least SAR_MIN_KM2 and SAR_ANOMALY_FACTOR times the district's median
    detection over observed weeks (seasonal wetlands and irrigated rice
    flag every year; a real flood stands out from that)."""
    observed = sar[sar["obs_km2"] > 0]
    typical = observed.groupby("district_code")["flood_km2"].median()
    floor = C.SAR_ANOMALY_FACTOR * sar["district_code"].map(typical).fillna(0)
    return (
        (sar["obs_km2"] > 0)
        & (sar["flood_km2"] >= C.SAR_MIN_KM2)
        & (sar["flood_km2"] >= floor)
    ).astype(int)


def build_labels_v2(panel, static, news, sar):
    """flood_news: a Groundsource event (or a documented / NADMO event)
    overlaps the week in the district. flood_sar: a Sentinel-1 anomaly
    (sar_flags). flood_union: either."""
    from research.flood_experiments import nadmo

    panel["flood_news"] = 0
    panel["label_source"] = ""
    for ev in news.dropna(subset=["district_code"]).itertuples():
        _mark(
            panel,
            "flood_news",
            ev.district_code,
            pd.Timestamp(ev.start_date),
            pd.Timestamp(ev.end_date),
            "news",
        )
    _mark_curated(panel, static, "flood_news")
    for ev in nadmo.load_incidents(static).itertuples():
        day = pd.Timestamp(ev.date)
        _mark(panel, "flood_news", ev.district_code, day, day, "nadmo")

    sar = sar.assign(sar_flag=sar_flags(sar))
    panel = panel.merge(
        sar[["district_code", "week", "flood_km2", "obs_km2", "sar_flag"]].rename(
            columns={"flood_km2": "sar_flood_km2", "obs_km2": "sar_obs_km2"}
        ),
        on=["district_code", "week"],
        how="left",
    )
    panel["sar_observed"] = (panel["sar_obs_km2"].fillna(0) > 0).astype(int)
    panel["flood_sar"] = panel["sar_flag"].fillna(0).astype(int)
    is_sar = panel["flood_sar"] == 1
    panel.loc[is_sar, "label_source"] = (
        panel.loc[is_sar, "label_source"] + "|sar"
    ).str.strip("|")
    panel["flood_union"] = panel[["flood_news", "flood_sar"]].max(axis=1)
    return panel.drop(columns="sar_flag")


def main(stage: str = "all"):
    """stage: all | discharge | dynamic | news. The discharge and Earth
    Engine pulls are independent, so they can run as separate processes
    at once; `all` then merges from the caches. In v2 the Sentinel-1
    export tasks (sar_labels.py start) must have finished first."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    RAW.mkdir(parents=True, exist_ok=True)
    ee = _init_ee()
    static = fetch_static(ee)
    logger.info(f"{len(static)} districts")
    points = fetch_river_points(ee) if C.S["discharge_point"] == "river" else None
    if stage == "discharge":
        fetch_discharge(static, points)
        return
    if stage == "dynamic":
        fetch_dynamic(ee)
        return
    if stage == "news":
        logger.info(f"{len(fetch_news_events(ee))} Groundsource events")
        return
    discharge = fetch_discharge(static, points)
    dynamic = fetch_dynamic(ee)
    panel = dynamic.merge(discharge, on=["district_code", "week"], how="left")
    panel = panel.merge(static, on="district_code", how="left")
    if C.STUDY == "v1_gfd":
        gfd = fetch_gfd_labels(ee)
        logger.info(f"{len(gfd)} GFD district-event hits")
        panel = build_labels(panel, static, gfd)
    else:
        from research.flood_experiments import sar_labels

        news = fetch_news_events(ee)
        sar = sar_labels.fetch(ee, sar_labels.years())
        panel = build_labels_v2(panel, static, news, sar)
        panel["flood"] = panel["flood_news"]
    panel = panel.sort_values(["district_code", "week"]).reset_index(drop=True)
    out = C.DATA_DIR / "panel.parquet"
    panel.to_parquet(out, index=False)
    logger.info(
        f"wrote {out}: {len(panel)} rows, {int(panel['flood'].sum())} flood weeks, "
        f"{panel.loc[panel.flood == 1, 'district_code'].nunique()} districts ever flooded"
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
