"""Archived ECMWF rainfall forecasts for an honest lead-time test (E3c).

Every other experiment uses the target week's OBSERVED rainfall (a
perfect-forecast hindcast). An early-warning system never has that: it
has a forecast. This module rebuilds, for every district and week of
2024-2025, the rainfall forecast that existed BEFORE the week began.

Source: Open-Meteo Previous Runs API (archived from January 2024),
ECMWF IFS 0.25 degree. `precipitation_previous_dayN` is the value for an
hour as forecast N days earlier. Day k (k = 0..6) of a week starting
Monday 00 UTC needs a forecast issued at least k+1 days ahead; it uses the
shortest archived lead that satisfies that. Requests carry leads 2, 4, 6
and 7 (the free API weighs a request by its size, and seven leads x two
years exhaust the daily quota at ~200 districts), so days 0-1 use the
2-day lead, days 2-3 the 4-day lead, days 4-5 the 6-day lead and day 6 the
7-day lead. Every forecast predates the week - some by a day more than
necessary, which makes the test slightly conservative. Files fetched
with all seven leads are read the same way.

Read at each district's centroid (one 0.25 degree, ~28 km, model cell -
about the size of a district).

Run: python -m research.flood_experiments.forecast_archive
"""

import json
import logging
import time

import numpy as np
import pandas as pd
import requests

from research.flood_experiments import config as C

logger = logging.getLogger("nfcc.research.forecast")
URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
MODEL = "ecmwf_ifs025"
START, END = "2024-01-01", "2025-12-31"
LEADS = (2, 4, 6, 7)


def _fetch(lat, lon, name, out):
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "hourly": ",".join(f"precipitation_previous_day{n}" for n in LEADS),
        "models": MODEL,
        "start_date": START,
        "end_date": END,
        "timezone": "GMT",
    }
    for attempt in range(12):
        try:
            resp = requests.get(URL, params=params, timeout=120)
        except requests.RequestException as e:
            wait = 30 * (attempt + 1)
            logger.info(f"{name}: {type(e).__name__}, retry in {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code == 200:
            out.write_text(resp.text)
            return True
        wait = 600 if resp.status_code == 429 else 15 * (attempt + 1)
        logger.info(f"{name}: HTTP {resp.status_code}, retry in {wait}s")
        time.sleep(wait)
    return False


def weekly_forecast(hourly: dict) -> pd.DataFrame:
    """Weekly forecast total and wettest day, as issued before each
    Monday-start week: day k of the week from the shortest lead >= k+1
    present in `hourly`."""
    t = pd.to_datetime(hourly["time"])
    leads = sorted(
        int(key.rsplit("day", 1)[1])
        for key in hourly
        if key.startswith("precipitation_previous_day")
    )
    df = pd.DataFrame(
        {n: hourly[f"precipitation_previous_day{n}"] for n in leads}, index=t
    ).astype(float)
    day = df.index.normalize()
    week = day - pd.to_timedelta(day.weekday, unit="D")
    k = (day - week).days.to_numpy()
    col = {kk: leads.index(min(n for n in leads if n >= kk + 1)) for kk in range(7)}
    vals = df.to_numpy()[np.arange(len(df)), [col[kk] for kk in k]]
    daily = pd.Series(vals, index=df.index).groupby(day).sum(min_count=20)
    wk = daily.groupby(daily.index - pd.to_timedelta(daily.index.weekday, unit="D"))
    return (
        pd.DataFrame(
            {
                "fc_rain_week_sum": wk.sum(min_count=7),
                "fc_rain_week_max": wk.max(),
            }
        )
        .rename_axis("week")
        .reset_index()
    )


def fetch_all(static: pd.DataFrame) -> pd.DataFrame:
    cache = C.DATA_DIR / "raw" / "forecast_archive"
    cache.mkdir(parents=True, exist_ok=True)
    frames = []
    for r in static.itertuples():
        out = cache / f"{r.district_code}.json"
        if not out.exists() and not _fetch(r.lat, r.lon, r.district, out):
            logger.warning(f"no forecast archive for {r.district}")
            continue
        w = weekly_forecast(json.loads(out.read_text())["hourly"])
        w["district_code"] = r.district_code
        frames.append(w)
    df = pd.concat(frames, ignore_index=True)
    df["week"] = df["week"].dt.strftime("%Y-%m-%d")
    df.to_csv(C.DATA_DIR / "raw" / "forecast_weekly.csv", index=False)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    fetch_all(pd.read_csv(C.DATA_DIR / "raw" / "static.csv"))
