"""The operational flood-onset model: train, package, score, shadow-run.

Which model is deployed follows the real-forecast test (E3c, 2024-2025,
archived ECMWF forecasts issued before each week):

- **Perfect prog:** a model trained on observed rain and fed the ECMWF
  forecast scored PR-AUC 0.050, below climatology (0.060).
- **MOS blend:** cross-fitted on the other year, it reached 0.075.
- **Antecedent-only (models.FORECAST):** inputs known when the week
  starts, no rain forecast; it scored 0.089, the best.
- **Live rule on the forecast:** 0.013.

So the deployed probability comes from the antecedent-only model. The
ECMWF ensemble is reported next to it as forecaster context (expected
rain and its local-climate percentile), not mixed into the probability,
until enough archived forecasts exist (2027+) to train a MOS layer that
beats it.

    python -m research.flood_experiments.operational fit
        Out-of-fold predictions (forward-chaining, 2018-2025) fit a Platt
        calibration; the final model trains on 2015-2024 with 2025 for
        early stopping. Writes model/ (model.json, meta.json,
        local_climate.json, MODEL_CARD.md).

    python -m research.flood_experiments.operational shadow [YYYY-MM-DD]
        Scores the week starting on that Monday (default: next Monday)
        for all 216 districts:
        - from live data: GPM IMERG rain (rescaled to CHIRPS) and
          ERA5-Land for the past four weeks, and GloFAS discharge at
          each district's main river;
        - alongside it, the 51-member ECMWF ensemble rain forecast.
        Writes data/v2/shadow/<week>.csv. It never sends an alert:
        shadow runs are compared with what happened before anyone acts
        on them.

Warning levels follow decision theory, not a tuned score: with
calibrated probabilities, acting is worthwhile when P(flood) exceeds the
cost/loss ratio of the action (Murphy 1977). WATCH (P >= 5%) suits
cheap actions - alert district officers, clear drains, pre-position
supplies. WARNING (P >= 20%) suits costly ones - move people and goods.
"""

import json
import logging
import sys
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
from sklearn.linear_model import LogisticRegression

from research.flood_experiments import config as C
from research.flood_experiments import metrics as M
from research.flood_experiments import models as Mo
from research.flood_experiments.features import LOCAL_PAIRS, build_features
from research.flood_experiments.features import local_climate, local_percentile

logger = logging.getLogger("nfcc.research.operational")
MODEL_DIR = C.ROOT / "model"
LEVELS = {"WATCH": 0.05, "WARNING": 0.20}
ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
IMERG = "NASA/GPM_L3/IMERG_V07"


# ----------------------------------------------------------------- fitting
def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _forecast_ratios(df):
    """Per-district rescaling of ECMWF point forecasts to the CHIRPS
    district means the model was trained on (mean CHIRPS / mean
    forecast over 2024-2025), and the district's usual wettest-pixel /
    mean ratio for the p95 inputs."""
    out = {}
    path = C.DATA_DIR / "raw" / "forecast_weekly.csv"
    fc = pd.read_csv(path, parse_dates=["week"])
    m = df.merge(fc, on=["district_code", "week"])
    g = m.groupby("district_code")
    for obs, f in (
        ("rain_week_sum", "fc_rain_week_sum"),
        ("rain_week_max", "fc_rain_week_max"),
    ):
        r = (g[obs].mean() / g[f].mean().replace(0, np.nan)).clip(0.2, 5)
        out[f"scale_{obs}"] = r.fillna(1.0).to_dict()
    for col in ("rain_week_sum", "rain_week_max"):
        k = (
            (df[f"{col}_p95"] / df[col].replace(0, np.nan))
            .groupby(df["district_code"])
            .median()
        )
        out[f"p95_ratio_{col}"] = k.fillna(1.0).to_dict()
    return out


def _imerg_scale(ee, start="2024-01-01", end="2025-12-31"):
    """Per-district CHIRPS / IMERG rainfall-total ratio over 2024-2025,
    to put live IMERG antecedent rain on the CHIRPS scale."""
    districts = (
        ee.FeatureCollection(C.GAUL_DISTRICTS)
        .filter(ee.Filter.eq("ADM0_NAME", "Ghana"))
        .select(["ADM2_CODE"])
    )
    chirps = (
        ee.ImageCollection(C.CHIRPS_DAILY)
        .filterDate(start, end)
        .select("precipitation")
        .sum()
    )
    imerg = (
        ee.ImageCollection(IMERG)
        .filterDate(start, end)
        .select("precipitation")
        .sum()
        .multiply(0.5)
    )
    img = chirps.rename("chirps").addBands(imerg.rename("imerg"))
    fc = img.reduceRegions(
        districts, ee.Reducer.mean(), scale=C.DYNAMIC_SCALE_M, tileScale=4
    )
    rows = fc.select(["ADM2_CODE", "chirps", "imerg"], None, False).getInfo()[
        "features"
    ]
    return {
        str(r["properties"]["ADM2_CODE"]): float(
            np.clip(
                r["properties"]["chirps"] / max(r["properties"]["imerg"], 1e-6), 0.2, 5
            )
        )
        for r in rows
        if r["properties"].get("imerg")
    }


def fit(panel: pd.DataFrame):
    from research.flood_experiments.experiments import temporal_folds

    MODEL_DIR.mkdir(exist_ok=True)
    df = build_features(panel)
    feats = Mo.FORECAST

    oof = []
    for fold, train, val, test in temporal_folds(df):
        m = Mo.XGB(feats).fit(train, val)
        oof.append(test.assign(p_raw=m.predict(test)))
    oof = pd.concat(oof, ignore_index=True)
    platt = LogisticRegression(max_iter=1000).fit(
        _logit(oof["p_raw"]).to_numpy().reshape(-1, 1), oof["onset"]
    )
    a, b = float(platt.coef_[0][0]), float(platt.intercept_[0])
    oof["p"] = 1 / (1 + np.exp(-(a * _logit(oof["p_raw"]) + b)))

    last = int(df["year"].max())
    final = Mo.XGB(feats).fit(df[df["year"] < last], df[df["year"] == last])
    final.model.save_model(str(MODEL_DIR / "model.json"))

    y = oof["onset"].to_numpy()
    levels = {}
    for name, thr in LEVELS.items():
        alert = oof["p"].to_numpy() >= thr
        c = M.categorical(y, alert)
        t = M.tolerant(oof["district_code"], oof["week"], y, alert)
        levels[name] = {
            "threshold": thr,
            "alerts_per_year": float(alert.sum() / oof["year"].nunique()),
            "pod": c["recall_pod"],
            "far": c["false_alarm_ratio"],
            "pod_1wk": t["tol_pod"],
            "far_1wk": t["tol_far"],
        }
    clim = local_climate()
    q_median = (
        df[df["week"] <= C.S["q_climatology_end"]]
        .groupby("district_code")["q_week_max"]
        .median()
    )
    meta = {
        "features": feats,
        "platt": {"a": a, "b": b},
        "levels": levels,
        "train_years": [int(df["year"].min()), last - 1],
        "early_stopping_year": last,
        "best_iteration": int(final.model.best_iteration),
        "oof_years": sorted(int(v) for v in oof["year"].unique()),
        "oof": {
            **{
                k: v
                for k, v in M.probabilistic(y, oof["p"]).items()
                if k in ("events", "base_rate", "roc_auc", "pr_auc", "brier", "ece")
            },
            "within_district_auc": M.within_district_auc(
                oof["district_code"], y, oof["p"]
            ),
            "reliability": M.reliability(y, oof["p"])["bins"],
        },
        "q_median": {str(k): float(v) for k, v in q_median.items()},
        **{
            k: {str(c): float(v) for c, v in d.items()}
            for k, d in _forecast_ratios(df).items()
        },
    }
    from research.flood_experiments.build_dataset import _init_ee

    meta["scale_imerg"] = _imerg_scale(_init_ee())
    (MODEL_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
    (MODEL_DIR / "MODEL_CARD.md").write_text(model_card(meta), encoding="utf-8")
    raw = C.DATA_DIR / "raw"
    pd.read_csv(raw / "static.csv").to_csv(MODEL_DIR / "districts.csv", index=False)
    pd.read_csv(raw / "river_points.csv").to_csv(
        MODEL_DIR / "river_points.csv", index=False
    )
    (MODEL_DIR / "local_climate.json").write_text(
        json.dumps(
            {
                src: {
                    str(code): np.quantile(v, np.linspace(0, 1, 201)).round(2).tolist()
                    for code, v in clim[src].items()
                }
                for _, src in LOCAL_PAIRS
            }
        )
    )
    logger.info(f"model saved to {MODEL_DIR}; levels {levels}")
    return meta


def model_card(meta) -> str:
    """Model card (Mitchell et al. 2019): what the model is for, how well
    it does, and where it must not be trusted."""
    o, lv = meta["oof"], meta["levels"]
    rows = "\n".join(
        f"| {k} | P >= {v['threshold']:.0%} | {v['alerts_per_year']:.0f} | "
        f"{v['pod']:.2f} | {v['far']:.2f} | {v['pod_1wk']:.2f} | {v['far_1wk']:.2f} |"
        for k, v in lv.items()
    )
    rel = "\n".join(
        f"| {b['mean_predicted']:.4f} | {b['observed_rate']:.4f} | {b['n']} |"
        for b in o["reliability"]
    )
    return f"""# Model card: NFCC weekly flood-onset model

## What it predicts

The probability that a flood *starts* in a Ghanaian district (GAUL 2015,
216 districts) in the coming Monday-to-Sunday week.

## Intended use

- Decision support for district disaster officers (NADMO) and the NFCC
  platform.
- Shadow mode first: compare its probabilities with what happens before
  anyone acts on them.
- Not for automatic public alerts. Not for sub-daily flash-flood timing.
- Lead time: one week (issued before the week starts).

## Inputs

Only inputs known when the week starts:

- **Rain:** past four weeks (IMERG live, CHIRPS in training), and the
  4-week total as a percentile of the district's own 2000-2014 climate.
- **Soil and runoff:** ERA5-Land soil moisture and runoff.
- **River:** GloFAS discharge at the district's main river (last week).
- **Place:** terrain, permanent water, built-up share, population
  density.

Features: {", ".join(meta["features"])}.

The week's ECMWF rain forecast is *not* an input. In the real-forecast
test (E3c, 2024-2025), adding it lowered skill: PR-AUC 0.050 when fed
directly, 0.075 as a cross-fitted MOS blend, against 0.089 without it.
The shadow run reports the ensemble alongside the probability as context
for the forecaster.

## Training

- **Labels:** Groundsource news-reported floods plus documented events.
- **Data:** 2015-{meta["train_years"][1]}, with {meta["early_stopping_year"]}
  held out for early stopping.
- **Model:** XGBoost, monotone in every rain, soil and river input; best
  iteration {meta["best_iteration"]}.
- **Calibration:** Platt scaling fitted on out-of-fold forecasts for
  {meta["oof_years"][0]}-{meta["oof_years"][-1]}.

## Performance (out of fold, {meta["oof_years"][0]}-{meta["oof_years"][-1]})

{o["events"]} onsets, base rate {o["base_rate"]:.4f}. ROC-AUC {o["roc_auc"]:.3f},
PR-AUC {o["pr_auc"]:.3f}, Brier {o["brier"]:.5f}, ECE {o["ece"]:.5f}.
Within-district AUC (timing skill only) {o["within_district_auc"]:.3f}.

| Level | Rule | Alerts / year | POD | FAR | POD ±1 wk | FAR ±1 wk |
| --- | --- | --- | --- | --- | --- | --- |
{rows}

Reliability (calibrated, equal-count bins):

| Mean predicted | Observed rate | Weeks |
| --- | --- | --- |
{rel}

## Limitations: do not trust it here

- **Urban flood labels are unverified.** Radar cannot see them, so the
  model's urban skill partly reflects where news reports floods
  (results/v2: label audit). NADMO records are needed to verify it.
- **Weekly resolution.** It cannot time a flash flood within the week.
- **Dam releases are not inputs.** This covers Akosombo, Kpong and
  Bagre in Burkina Faso, so dam-driven floods on the Volta are under-
  predicted.
- **Boundaries.** GAUL 2015 districts; 261 districts exist since 2018.
- **Coverage is uneven.** Districts with little news coverage have few
  training events.
"""


# ----------------------------------------------------------------- scoring
class OperationalModel:
    def __init__(self, model_dir=MODEL_DIR):
        from xgboost import Booster

        self.meta = json.loads((model_dir / "meta.json").read_text())
        self.booster = Booster()
        self.booster.load_model(str(model_dir / "model.json"))
        clim = json.loads((model_dir / "local_climate.json").read_text())
        self.climate = {
            src: {int(c): np.asarray(q) for c, q in d.items()}
            for src, d in clim.items()
        }

    def percentile(self, code, source, value):
        q = self.climate[source].get(int(code))
        if q is None or value != value:
            return np.nan
        return float(np.interp(value, q, np.linspace(0, 1, len(q))))

    def score(self, X: pd.DataFrame) -> pd.DataFrame:
        """P(flood onset) per row, its warning level, and the three
        inputs pushing risk up the most (XGBoost SHAP contributions)."""
        from xgboost import DMatrix

        feats = self.meta["features"]
        dm = DMatrix(X[feats], feature_names=feats)
        raw = self.booster.predict(
            dm, iteration_range=(0, self.meta["best_iteration"] + 1)
        )
        a, b = self.meta["platt"]["a"], self.meta["platt"]["b"]
        p = 1 / (1 + np.exp(-(a * _logit(raw) + b)))
        contrib = self.booster.predict(
            dm, pred_contribs=True, iteration_range=(0, self.meta["best_iteration"] + 1)
        )[:, :-1]
        drivers = [
            ", ".join(feats[j] for j in np.argsort(-row)[:3] if row[j] > 0)
            for row in contrib
        ]
        return pd.DataFrame({"p": p, "drivers": drivers}, index=X.index)

    def level(self, p):
        out = "NONE"
        for name, lv in sorted(
            self.meta["levels"].items(), key=lambda kv: kv[1]["threshold"]
        ):
            if p >= lv["threshold"]:
                out = name
        return out


# ------------------------------------------------------------- shadow run
def _get_json(url, params, attempts=4):
    """GET with retries on timeouts, connection errors and non-200
    replies (backoff 15, 30, 45 s). Returns the JSON body, or None after
    the last attempt: a slow API must not crash the weekly run, it only
    leaves that input missing."""
    for attempt in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            logger.info(f"{url}: HTTP {r.status_code} (attempt {attempt + 1})")
        except requests.RequestException as e:
            logger.info(f"{url}: {type(e).__name__} (attempt {attempt + 1})")
        if attempt < attempts - 1:
            time.sleep(15 * (attempt + 1))
    return None


def _ensemble_week(lat, lon, week: date):
    """Per-member weekly total and wettest day from the ECMWF IFS
    ensemble (51 members) for the 7 days from `week`."""
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "hourly": "precipitation",
        "models": "ecmwf_ifs025",
        "start_date": week.isoformat(),
        "end_date": (week + timedelta(days=6)).isoformat(),
        "timezone": "GMT",
    }
    body = _get_json(ENSEMBLE_URL, params)
    if body is None:
        return None
    h = body["hourly"]
    t = pd.to_datetime(h["time"])
    cols = [k for k in h if k.startswith("precipitation")]
    daily = (
        pd.DataFrame({k: h[k] for k in cols}, index=t)
        .astype(float)
        .resample("D")
        .sum(min_count=1)
    )
    return pd.DataFrame({"sum": daily.sum(min_count=1), "max": daily.max()})


def _discharge_lag1(lat, lon, week: date):
    """GloFAS max discharge over the week before `week` (Open-Meteo);
    NaN (a missing input the model handles) if the API stays down."""
    body = _get_json(
        C.OPEN_METEO_FLOOD_URL,
        {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": "river_discharge",
            "start_date": (week - timedelta(days=7)).isoformat(),
            "end_date": (week - timedelta(days=1)).isoformat(),
        },
    )
    if body is None:
        return np.nan
    v = [x for x in body["daily"]["river_discharge"] if x is not None]
    return float(max(v)) if v else np.nan


def _past_weeks(ee, week: date):
    """District means for the four weeks before `week`: GPM IMERG rain
    rescaled to CHIRPS, ERA5-Land soil moisture (last week) and runoff.

    Rain comes from IMERG (about 2 days behind real time) because CHIRPS
    in Earth Engine - including the "near-real-time" v3 product - runs
    about a month behind. IMERG is rescaled per district to the CHIRPS
    district means the model was trained on (meta scale_imerg)."""
    districts = (
        ee.FeatureCollection(C.GAUL_DISTRICTS)
        .filter(ee.Filter.eq("ADM0_NAME", "Ghana"))
        .select(["ADM2_CODE"])
    )

    def band(col, select, reduce, name, scale=1):
        # ERA5-Land runs ~5 days behind real time and CHIRPS v3 1-2 days:
        # a week with no images yet becomes a masked band (-> missing
        # input, which the model handles) instead of an error.
        img = getattr(col.select(select), reduce)().multiply(scale).rename(name)
        empty = ee.Image.constant(0).updateMask(0).rename(name)
        return ee.Image(ee.Algorithms.If(col.size().gt(0), img, empty))

    rows = []
    for k in range(1, 5):
        start = ee.Date((week - timedelta(days=7 * k)).isoformat())
        end = start.advance(7, "day")
        imerg = ee.ImageCollection(IMERG).filterDate(start, end)
        era5 = ee.ImageCollection(C.ERA5_LAND_DAILY).filterDate(start, end)
        img = (
            band(imerg, "precipitation", "sum", "rain", 0.5)  # mm/h, half-hourly
            .addBands(band(era5, "volumetric_soil_water_layer_1", "mean", "sm"))
            .addBands(band(era5, "surface_runoff_sum", "sum", "runoff", 1000))
        )
        fc = img.reduceRegions(districts, ee.Reducer.mean(), scale=C.DYNAMIC_SCALE_M)
        # Days of rain actually observed: last week is usually incomplete
        # (IMERG is ~2 days behind), so its total is a lower bound.
        days = imerg.size().getInfo() / 48
        for f in fc.select(
            ["ADM2_CODE", "rain", "sm", "runoff"], None, False
        ).getInfo()["features"]:
            rows.append(
                {
                    "rain": np.nan,
                    "sm": np.nan,
                    "runoff": np.nan,
                    **f["properties"],
                    "lag": k,
                    "rain_days": round(days, 1),
                }
            )
    return pd.DataFrame(rows).rename(columns={"ADM2_CODE": "district_code"})


def shadow(week: date):
    from research.flood_experiments.build_dataset import _init_ee

    ee = _init_ee()
    om = OperationalModel()
    meta = om.meta
    # District attributes and main-river points ship with the model, so
    # a scheduled run needs no data folder (data/ is git-ignored).
    static = pd.read_csv(MODEL_DIR / "districts.csv")
    points = pd.read_csv(MODEL_DIR / "river_points.csv")
    past = _past_weeks(ee, week)
    past["rain"] = past["rain"] * past["district_code"].astype(str).map(
        meta["scale_imerg"]
    ).fillna(1.0)
    woy = pd.Timestamp(week).isocalendar().week
    out = []
    for r in static.merge(points, on="district_code").itertuples():
        try:
            out.append(_score_district(r, past, week, woy, om, meta))
        except Exception as e:  # one district must not stop the other 215
            logger.warning(f"shadow {r.district}: {type(e).__name__}: {e}")
            out.append(
                {
                    "district_code": r.district_code,
                    "district": r.district,
                    "region": r.region,
                    "status": f"error: {type(e).__name__}",
                }
            )
    res = pd.DataFrame(out)
    d = C.DATA_DIR / "shadow"
    d.mkdir(parents=True, exist_ok=True)
    res.to_csv(d / f"{week.isoformat()}.csv", index=False)
    ok = res["status"] == "ok"
    logger.info(
        f"shadow {week}: {int(ok.sum())} of {len(res)} districts scored; "
        f"levels {res.loc[ok, 'level'].value_counts().to_dict() if ok.any() else {}}"
    )
    if ok.mean() < 0.9:  # mostly failed: make the scheduled job show red
        raise RuntimeError(f"only {int(ok.sum())} of {len(res)} districts scored")
    return res


def _score_district(r, past, week, woy, om, meta):
    """One district's shadow forecast row."""
    code = r.district_code
    p = past[past["district_code"] == code].set_index("lag")
    ens = _ensemble_week(r.lat, r.lon, week)
    if ens is None or p.empty:
        return {
            "district_code": code,
            "district": r.district,
            "region": r.region,
            "status": "inputs unavailable",
        }
    q1 = _discharge_lag1(r.river_lat, r.river_lon, week)
    qm = meta["q_median"].get(str(code), np.nan)
    base = {
        "woy_sin": np.sin(2 * np.pi * woy / 52.18),
        "woy_cos": np.cos(2 * np.pi * woy / 52.18),
        **{
            f"rain_lag{k}": p.loc[k, "rain"] if k in p.index else np.nan
            for k in range(1, 5)
        },
        "sm_start": p.loc[1, "sm"] if 1 in p.index else np.nan,
        "runoff_prev4w_sum": p["runoff"].sum(min_count=4),
        "q_week_max_log_lag1": np.log1p(q1) if q1 == q1 else np.nan,
        "q_ratio_lag1": q1 / (qm + 1e-3) if q1 == q1 and qm == qm else np.nan,
        "elev_mean": r.elev_mean,
        "slope_mean": r.slope_mean,
        "perm_water_frac": r.perm_water_frac,
        "built_frac": r.built_frac,
        "log_pop_density": np.log1p(r.population / r.area_km2),
    }
    base["rain_prev4w_sum"] = sum(base[f"rain_lag{k}"] for k in range(1, 5))
    base["rain_prev4w_pct"] = om.percentile(
        code, "rain_prev4w_sum", base["rain_prev4w_sum"]
    )
    s = om.score(pd.DataFrame([base]))
    pm = float(s["p"].iloc[0])
    # Forecaster context, not model input (see module docstring).
    ws = ens["sum"] * meta["scale_rain_week_sum"].get(str(code), 1.0)
    wm = ens["max"] * meta["scale_rain_week_max"].get(str(code), 1.0)
    return {
        "district_code": code,
        "district": r.district,
        "region": r.region,
        "p_flood_onset": round(pm, 4),
        "level": om.level(pm),
        "drivers": s["drivers"].iloc[0],
        "ecmwf_rain_week_mm_median": round(float(ws.median()), 1),
        "ecmwf_rain_week_mm_p90": round(float(ws.quantile(0.9)), 1),
        "ecmwf_wettest_day_local_pct_median": round(
            om.percentile(code, "rain_week_max", float(wm.median())), 2
        ),
        "ecmwf_members": int(len(ens)),
        "river_discharge_available": bool(q1 == q1),
        "last_week_rain_days_observed": (
            float(p.loc[1, "rain_days"]) if 1 in p.index else 0.0
        ),
        "status": "ok",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if sys.argv[1] == "fit":
        fit(pd.read_parquet(C.DATA_DIR / "panel.parquet"))
    else:
        if len(sys.argv) > 2:
            wk = date.fromisoformat(sys.argv[2])
        else:
            today = date.today()
            wk = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        shadow(wk)
