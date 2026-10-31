"""Satellite rainfall against Ghana's synoptic rain gauges.

Every rain feature in the study and the live platform comes from CHIRPS
v2.0 (UCSB-CHG/CHIRPS/DAILY) or GPM IMERG V07 (NASA/GPM_L3/IMERG_V07).
This checks both against the only open daily gauge record for Ghana: the
Ghana Meteorological Agency's synoptic stations as distributed by NOAA's
Global Surface Summary of the Day (GSOD), 2015-01-01 to 2025-08-31.

Gauge quality control. GSOD PRCP is in inches (99.99 = missing) with a
source flag. Only complete 24-hour totals are used: D (four 6-hour
reports), F (two 12-hour reports) and G (one 24-hour report). Flag I
("no precipitation report") is stored as 0.00 but is not an observed
zero, and A/B/C/E/H are partial-day sums; all are excluded. Stations
send the 24-hour group mostly when it has rained (3% of January days
carry a complete flag, 45% of September days), so complete days are
skewed wet. A sensitivity variant therefore also counts flag I as 0 mm:
on I days both satellites average ~1.5 mm against ~4.6 mm on complete
0.0 mm days, so I days are overwhelmingly dry, though not all of them.

Independence caveat. CHIRPS blends GTS station reports, which include
these stations, into its monthly-to-daily product, so its agreement here
is partly built in. IMERG Final is adjusted to GPCC monthly gauge
totals, not daily ones. Neither comparison is fully independent; IMERG
is the closer to it.

    python -m research.flood_experiments.station_check fetch     # GSOD + station list (NOAA)
    python -m research.flood_experiments.station_check extract   # CHIRPS + IMERG at stations (Earth Engine)
    python -m research.flood_experiments.station_check analyse   # results/station_check/
"""

import csv
import json
import sys
import time

import numpy as np
import pandas as pd
import requests

from .config import GEE_PROJECT, ROOT

DATA = ROOT / "data" / "stations"
OUT = ROOT / "results" / "station_check"
FIRST_YEAR, LAST_DAY = 2015, "2025-08-31"
COMPLETE_FLAGS = {"D", "F", "G"}
PRODUCTS = {"chirps": "CHIRPS v2.0", "imerg": "IMERG V07"}

# Synoptic station nearest each tracked district (Cape Coast has none;
# Saltpond is 30 km east along the same coast).
DISTRICT_STATION = {
    "Accra Central/West/East": "KOTOKA INTL",
    "Tema": "TEMA",
    "Kumasi": "KUMASI",
    "Tamale": "TAMALE",
    "Cape Coast": "SALTPOND",
    "Ho": "HO",
    "Sunyani": "SUNYANI",
}


def zone(lat):
    if lat < 6.0:
        return "Coast (<6°N)"
    if lat < 8.0:
        return "Forest-transition (6-8°N)"
    return "Northern savanna (>=8°N)"


def fetch():
    """GSOD daily files for every Ghana station active since 2015."""
    raw = DATA / "gsod"
    raw.mkdir(parents=True, exist_ok=True)
    hist = DATA / "isd-history.csv"
    if not hist.exists():
        r = requests.get("https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv", timeout=120)
        r.raise_for_status()
        hist.write_bytes(r.content)
    stations = [
        (r["USAF"] + r["WBAN"], r["STATION NAME"], float(r["LAT"]), float(r["LON"]))
        for r in csv.DictReader(open(hist, newline=""))
        if r["CTRY"] == "GH" and r["END"] >= f"{FIRST_YEAR}0101"
    ]
    pd.DataFrame(stations, columns=["station_id", "name", "lat", "lon"]).to_csv(
        DATA / "stations.csv", index=False
    )
    for sid, name, _, _ in stations:
        for year in range(FIRST_YEAR, int(LAST_DAY[:4]) + 1):
            p = raw / f"{sid}_{year}.csv"
            if p.exists():
                continue
            url = f"https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/{sid}.csv"
            for attempt in range(4):
                try:
                    r = requests.get(url, timeout=60)
                    break
                except requests.RequestException:
                    time.sleep(10 * (attempt + 1))
            else:
                raise RuntimeError(f"GSOD download failed: {url}")
            if r.status_code == 200:
                p.write_text(r.text, encoding="utf-8")
            elif r.status_code != 404:
                r.raise_for_status()
    print(len(stations), "stations")


def extract():
    """Daily CHIRPS and IMERG (sum of half-hourly rates x 0.5 h) at each
    station, one Earth Engine request per product per quarter (a year of
    22 stations exceeds the 5,000-element limit)."""
    import ee

    ee.Initialize(project=GEE_PROJECT)
    st = pd.read_csv(DATA / "stations.csv", dtype={"station_id": str})
    pts = ee.FeatureCollection(
        [
            ee.Feature(ee.Geometry.Point(r.lon, r.lat), {"station_id": r.station_id})
            for r in st.itertuples()
        ]
    )
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation")
    imerg = ee.ImageCollection("NASA/GPM_L3/IMERG_V07").select("precipitation")

    def daily_imerg(d):
        d = ee.Date(d)
        imgs = imerg.filterDate(d, d.advance(1, "day"))
        return (
            imgs.sum()
            .multiply(0.5)
            .rename("precipitation")
            .set({"system:time_start": d.millis(), "n": imgs.size()})
        )

    def fetch_fc(col, scale):
        fc = col.map(
            lambda img: img.reduceRegions(pts, ee.Reducer.first(), scale).map(
                lambda f: f.set("t", img.get("system:time_start"), "n", img.get("n"))
            )
        ).flatten()
        for attempt in range(4):
            try:
                return fc.select(["station_id", "t", "first", "n"], None, False).getInfo()[
                    "features"
                ]
            except Exception as e:  # noqa: BLE001 - Earth Engine raises generic errors
                print("retry", str(e)[:80], flush=True)
                time.sleep(20 * (attempt + 1))
        raise RuntimeError("Earth Engine request failed 4 times")

    end_all = (pd.Timestamp(LAST_DAY) + pd.Timedelta(days=1)).date().isoformat()
    out_dir = DATA / "satellite"
    out_dir.mkdir(exist_ok=True)
    for year in range(FIRST_YEAR, int(LAST_DAY[:4]) + 1):
        out = out_dir / f"{year}.csv"
        if out.exists():
            continue
        rows = []
        for q in range(4):
            start = f"{year}-{3 * q + 1:02d}-01"
            end = f"{year + 1}-01-01" if q == 3 else f"{year}-{3 * q + 4:02d}-01"
            if start >= end_all:
                break
            end = min(end, end_all)
            days = ee.List.sequence(
                ee.Date(start).millis(), ee.Date(end).advance(-1, "day").millis(), 86400000
            )
            for name, col, scale in (
                ("chirps", chirps.filterDate(start, end), 5566),
                ("imerg", ee.ImageCollection(days.map(daily_imerg)), 11132),
            ):
                for f in fetch_fc(col, scale):
                    p = f["properties"]
                    rows.append(
                        {
                            "station_id": p["station_id"],
                            "date": pd.to_datetime(p["t"], unit="ms").date().isoformat(),
                            "product": name,
                            "mm": p.get("first"),
                            "n_halfhours": p.get("n"),
                        }
                    )
            print(year, q + 1, len(rows), flush=True)
        pd.DataFrame(rows).to_csv(out, index=False)


def load_gauges(i_as_dry=False):
    frames = [pd.read_csv(p, dtype=str) for p in sorted((DATA / "gsod").glob("*.csv"))]
    g = pd.concat(frames, ignore_index=True)
    g["PRCP_ATTRIBUTES"] = g["PRCP_ATTRIBUTES"].fillna("").str.strip()
    flags = g["PRCP_ATTRIBUTES"].replace("", "(blank)").value_counts().to_dict()
    p = g["PRCP"].astype(float)
    flags_used = COMPLETE_FLAGS | ({"I"} if i_as_dry else set())
    ok = g["PRCP_ATTRIBUTES"].isin(flags_used) & (p < 99.99)
    out = pd.DataFrame(
        {
            "station_id": g.loc[ok, "STATION"].values,
            "date": pd.to_datetime(g.loc[ok, "DATE"]).values,
            "gauge": (p[ok] * 25.4).round(1).values,
        }
    )
    out = out[out["date"] <= LAST_DAY]
    return out, {"station_days_total": int(len(g)), "flags": flags, "complete_days": int(len(out))}


def load_satellite():
    s = pd.concat(
        [pd.read_csv(p, dtype={"station_id": str}) for p in sorted((DATA / "satellite").glob("*.csv"))],
        ignore_index=True,
    )
    s = s[(s["product"] == "chirps") | (s["n_halfhours"] == 48)]
    s["date"] = pd.to_datetime(s["date"])
    return s.pivot_table(index=["station_id", "date"], columns="product", values="mm").reset_index()


def contingency(obs, est):
    """POD, FAR, CSI and frequency bias for two boolean series."""
    obs, est = np.asarray(obs, bool), np.asarray(est, bool)
    hits = int((obs & est).sum())
    misses = int((obs & ~est).sum())
    fa = int((~obs & est).sum())
    return {
        "events": int(obs.sum()),
        "pod": hits / (hits + misses) if hits + misses else None,
        "far": fa / (hits + fa) if hits + fa else None,
        "csi": hits / (hits + misses + fa) if hits + misses + fa else None,
        "freq_bias": (hits + fa) / (hits + misses) if hits + misses else None,
    }


def scores(df, product):
    """Continuous and categorical agreement of one product with the gauge."""
    g, s = df["gauge"].to_numpy(), df[product].to_numpy()
    out = {
        "n": int(len(df)),
        "gauge_mean_mm": float(g.mean()),
        "sat_mean_mm": float(s.mean()),
        "volume_ratio": float(s.sum() / g.sum()) if g.sum() else None,
        "pearson_r": float(np.corrcoef(g, s)[0, 1]) if len(df) > 2 else None,
        "spearman_r": float(pd.Series(g).corr(pd.Series(s), method="spearman"))
        if len(df) > 2
        else None,
        "rmse_mm": float(np.sqrt(np.mean((s - g) ** 2))),
        "mae_mm": float(np.mean(np.abs(s - g))),
    }
    return out


def daily_skill(df, product):
    out = scores(df, product)
    out["rain_1mm"] = contingency(df["gauge"] >= 1, df[product] >= 1)
    out["heavy_20mm"] = contingency(df["gauge"] >= 20, df[product] >= 20)
    out["heavy_50mm"] = contingency(df["gauge"] >= 50, df[product] >= 50)
    # Each series' own 95th percentile of wet days at that station,
    # so a volume bias doesn't masquerade as a detection failure.
    obs, est = [], []
    for _, d in df.groupby("station_id"):
        qg = d.loc[d["gauge"] >= 1, "gauge"].quantile(0.95)
        qs = d.loc[d[product] >= 1, product].quantile(0.95)
        obs.append(d["gauge"] >= qg)
        est.append(d[product] >= qs)
    out["heavy_own_p95"] = contingency(pd.concat(obs), pd.concat(est))
    return out


def weekly(df):
    """Monday-to-Sunday totals for weeks with all 7 gauge days complete,
    the unit every model in the study is built on."""
    d = df.copy()
    d["week"] = d["date"] - pd.to_timedelta(d["date"].dt.weekday, unit="D")
    agg = d.groupby(["station_id", "week"]).agg(
        days=("gauge", "size"), gauge=("gauge", "sum"), chirps=("chirps", "sum"), imerg=("imerg", "sum")
    )
    return agg[agg["days"] == 7].reset_index()


def weekly_skill(w, product):
    out = scores(w, product)
    obs, est = [], []
    for _, d in w.groupby("station_id"):
        obs.append(d["gauge"] >= d["gauge"].quantile(0.9))
        est.append(d[product] >= d[product].quantile(0.9))
    out["wet_week_own_p90"] = contingency(pd.concat(obs), pd.concat(est))
    return out


def anomaly_r(w, product):
    """Correlation of weekly totals after removing each station's
    week-of-year mean: skill beyond getting the seasons right."""
    d = w.copy()
    d["woy"] = d["week"].dt.isocalendar().week.astype(int)
    for c in ("gauge", product):
        d[c] = d[c] - d.groupby(["station_id", "woy"])[c].transform("mean")
    return float(np.corrcoef(d["gauge"], d[product])[0, 1])


def analyse():
    OUT.mkdir(parents=True, exist_ok=True)
    st = pd.read_csv(DATA / "stations.csv", dtype={"station_id": str})
    st["name"] = st["name"].str.replace(", GH", "", regex=False).str.strip()
    st["zone"] = st["lat"].map(zone)
    sat = load_satellite()
    res = {"strict": compare(st, sat, *load_gauges()), "i_as_dry": compare(st, sat, *load_gauges(True))}
    res["district_stations"] = DISTRICT_STATION
    res["period"] = f"{FIRST_YEAR}-01-01 to {LAST_DAY}"
    pd.DataFrame(res["strict"]["by_station"]).to_csv(OUT / "by_station.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float))
    for v in ("strict", "i_as_dry"):
        r = res[v]
        print(v, {k: r[k] for k in ("lag_used_days", "paired_days", "complete_weeks", "stations_used")})
        for p in PRODUCTS:
            d, wk = r["daily"][p], r["weekly"][p]
            print(
                f"  {p}: daily r={d['pearson_r']:.2f} ratio={d['volume_ratio']:.2f} "
                f"CSI1={d['rain_1mm']['csi']:.2f} POD20={d['heavy_20mm']['pod']:.2f} "
                f"FAR20={d['heavy_20mm']['far']:.2f} | weekly r={wk['pearson_r']:.2f} "
                f"anom r={r['weekly_anomaly_r'][p]:.2f} wetweek CSI={wk['wet_week_own_p90']['csi']:.2f}"
            )


def compare(st, sat, gauges, qc):
    sat = sat.copy()

    # Day alignment: GSOD's single 24-hour report (flag G) is read in the
    # morning, so the gauge "day" can lag the satellite's UTC day.
    lags = {}
    for lag in (-1, 0, 1):
        s = sat.copy()
        s["date"] = s["date"] + pd.Timedelta(days=lag)
        m = gauges.merge(s, on=["station_id", "date"]).dropna()
        lags[lag] = {p: float(np.corrcoef(m["gauge"], m[p])[0, 1]) for p in PRODUCTS}
    best_lag = max(lags, key=lambda k: lags[k]["imerg"] + lags[k]["chirps"])
    sat["date"] = sat["date"] + pd.Timedelta(days=best_lag)
    m = gauges.merge(sat, on=["station_id", "date"]).dropna()
    m = m.merge(st[["station_id", "name", "lat", "zone"]], on="station_id")
    w = weekly(m).merge(st[["station_id", "name", "zone"]], on="station_id")

    res = {
        "gauge_qc": qc,
        "lag_test": {str(k): v for k, v in lags.items()},
        "lag_used_days": best_lag,
        "paired_days": int(len(m)),
        "complete_weeks": int(len(w)),
        "stations_used": int(m["station_id"].nunique()),
        "daily": {p: daily_skill(m, p) for p in PRODUCTS},
        "weekly": {p: weekly_skill(w, p) for p in PRODUCTS},
        "weekly_anomaly_r": {p: anomaly_r(w, p) for p in PRODUCTS},
        "by_zone": {},
        "by_station": [],
    }
    for z, d in m.groupby("zone"):
        wz = w[w["zone"] == z]
        res["by_zone"][z] = {
            "stations": int(d["station_id"].nunique()),
            **{
                p: {
                    "daily_r": scores(d, p)["pearson_r"],
                    "weekly_r": scores(wz, p)["pearson_r"] if len(wz) > 2 else None,
                    "volume_ratio": scores(d, p)["volume_ratio"],
                    "csi_1mm": contingency(d["gauge"] >= 1, d[p] >= 1)["csi"],
                }
                for p in PRODUCTS
            },
        }
    for sid, d in m.groupby("station_id"):
        ws = w[w["station_id"] == sid]
        row = {
            "station": d["name"].iloc[0],
            "station_id": sid,
            "lat": float(d["lat"].iloc[0]),
            "zone": d["zone"].iloc[0],
            "days": int(len(d)),
            "weeks": int(len(ws)),
            "first": d["date"].min().date().isoformat(),
            "last": d["date"].max().date().isoformat(),
            "gauge_mean_mm_day": float(d["gauge"].mean()),
        }
        for p in PRODUCTS:
            row[f"{p}_daily_r"] = scores(d, p)["pearson_r"]
            row[f"{p}_weekly_r"] = scores(ws, p)["pearson_r"] if len(ws) > 10 else None
            row[f"{p}_volume_ratio"] = scores(d, p)["volume_ratio"]
            row[f"{p}_csi_1mm"] = contingency(d["gauge"] >= 1, d[p] >= 1)["csi"]
        res["by_station"].append(row)
    res["by_station"].sort(key=lambda r: -r["lat"])
    return res


if __name__ == "__main__":
    {"fetch": fetch, "extract": extract, "analyse": analyse}[sys.argv[1]]()
