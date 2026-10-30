"""Experiments from the Manuscript Writing Guide, plus the checks the
guide does not list but a reviewer would ask for.

E1  Model hierarchy and data configuration (rainfall-only vs multi-source)
E2  Cumulative source ablation: Baseline -> +Soil -> +River -> +Dam ->
    +Geographic -> +Exposure
E3  Temporal holdout: forward-chaining by year (train <= y-2, validate
    y-1, test y) over config.TEST_YEARS
E3b One-week-ahead forecast (inputs known when the week starts) vs the
    nowcast hindcast
E3c Real lead time: 2024-2025 with archived ECMWF forecasts issued before
    each week, vs perfect forecast, no forecast and the live rule
E4  Spatial holdout: leave-one-region-out, separated in time
E5  Fusion strategy: early fusion, late fusion (mean), stacking, and the
    platform's hand-set weights
E6  Source degradation: a source missing (filled with its training
    median) or stale (last week's values) at prediction time
E7  Calibration: raw vs Platt scaling vs isotonic regression
E8  Impact layers: only with NADMO incident records (nadmo.py)
E9  SHAP fidelity (deletion test) and stability (bootstrap retraining)
LA  Label audit (v2): Sentinel-1 radar checked at every news flood onset
    and at matched no-flood controls (sar_labels.py)

Run: python -m research.flood_experiments.experiments
"""

import json
import logging
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from research.flood_experiments import config as C
from research.flood_experiments import metrics as M
from research.flood_experiments import models as Mo
from research.flood_experiments.features import build_features
from src.alerts.formatter import calculate_score
from src.models.multi_source_confidence import RAINFALL_WEIGHT, RIVER_GAUGE_WEIGHT

logger = logging.getLogger("nfcc.research.experiments")
TEST_YEARS = C.TEST_YEARS
MIN_VAL_ONSETS = 5


# ---------------------------------------------------------------- splits
def temporal_folds(df):
    for y in TEST_YEARS:
        yield (
            str(y),
            df[df["year"] <= y - 2],
            df[df["year"] == y - 1],
            df[df["year"] == y],
        )


def spatial_folds(df):
    """Leave one region out AND separate it in time. One Global Flood
    Database event floods several regions in the same weeks, so a purely
    spatial split trains on the very event it tests (the model learns the
    date). Train on other regions up to two years before the first test
    year, validate on them the year before, test the held-out region over
    the test years."""
    for region in sorted(df["region"].unique()):
        rest = df[df["region"] != region]
        yield (
            region,
            rest[rest["year"] <= TEST_YEARS[0] - 2],
            rest[rest["year"] == TEST_YEARS[0] - 1],
            df[(df["region"] == region) & (df["year"] >= TEST_YEARS[0])],
        )


def cross_validate(df, factory, folds):
    """Fit per fold, threshold on validation, pool the test predictions.

    A validation year with almost no onsets gives a meaningless F1
    threshold (v1 has six such years), so with fewer than MIN_VAL_ONSETS
    the threshold is chosen on the training predictions instead."""
    parts = []
    for fold, train, val, test in folds:
        model = factory().fit(train, val)
        tune = val if val["onset"].sum() >= MIN_VAL_ONSETS else train
        thr = M.best_f1_threshold(tune["onset"], model.predict(tune))
        p = model.predict(test)
        parts.append(
            pd.DataFrame(
                {
                    "fold": fold,
                    "year": test["year"].to_numpy(),
                    "week": test["week"].to_numpy(),
                    "district_code": test["district_code"].to_numpy(),
                    "built_frac": test["built_frac"].to_numpy(),
                    "y": test["onset"].to_numpy(),
                    "p": p,
                    "alert": p >= thr,
                    "p_val_threshold": thr,
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def score(pred, name):
    y, p = pred["y"].to_numpy(), pred["p"].to_numpy()
    out = {
        "model": name,
        **M.probabilistic(y, p),
        **M.categorical(y, pred["alert"].to_numpy()),
        **M.tolerant(pred["district_code"], pred["week"], y, pred["alert"]),
    }
    out["pr_auc_90ci"] = M.block_bootstrap_ci(
        y, p, pred["year"], lambda a, b: M.probabilistic(a, b)["pr_auc"]
    )
    out["sedi_90ci"] = M.block_bootstrap_ci(
        y,
        pred["alert"].to_numpy().astype(float),
        pred["year"],
        lambda a, b: M.categorical(a, b >= 0.5)["sedi"],
    )
    # WHEN vs WHERE: skill inside each district, and urban vs rural (the
    # radar audit confirms rural news labels; urban ones are unverified).
    out["within_district_auc"] = M.within_district_auc(pred["district_code"], y, p)
    cut = pred.drop_duplicates("district_code")["built_frac"].quantile(0.75)
    urban = pred["built_frac"].to_numpy() >= cut
    for name_, m in (("urban", urban), ("rural", ~urban)):
        out[f"{name_}_pr_auc"] = M.probabilistic(y[m], p[m])["pr_auc"]
        out[f"{name_}_base_rate"] = float(y[m].mean())
    rv = M.relative_value(y, p)
    out["peak_value"] = rv["peak_value"]
    out["useful_alpha_range"] = rv["useful_alpha_range"]
    out["value_curve"] = {"alpha": rv["alpha"], "value": rv["value"]}
    return out


# ----------------------------------------------------------- experiments
def e1_e3_hierarchy(df):
    """E1 + E3: every model in the hierarchy, temporal forward-chaining."""
    rows = []
    for factory in Mo.hierarchy():
        name = factory().name
        pred = cross_validate(df, factory, temporal_folds(df))
        rows.append(score(pred, name))
        logger.info(f"E3 {name}: PR-AUC {rows[-1]['pr_auc']:.3f}")
    return rows


def e3b_forecast(df):
    """One week ahead: models that see only what is known when the week
    starts, next to the nowcast multi-source model."""
    rows = []
    for factory in [
        lambda: Mo.XGB(Mo.MULTI_SOURCE, "Nowcast multi-source XGBoost"),
        lambda: Mo.logistic(Mo.FORECAST, "Forecast logistic regression"),
        lambda: Mo.XGB(Mo.FORECAST, "Forecast multi-source XGBoost"),
    ]:
        name = factory().name
        rows.append(score(cross_validate(df, factory, temporal_folds(df)), name))
        logger.info(f"E3b {name}: PR-AUC {rows[-1]['pr_auc']:.3f}")
    return rows


def _with_forecast(test, train, fc, other_years):
    """Replace the target week's observed rainfall with the archived
    ECMWF forecast issued before the week. ECMWF and CHIRPS differ in
    scale, so each district's forecast is rescaled by its mean CHIRPS /
    mean forecast ratio, fitted on the OTHER forecast year only (no use
    of the test year's observations)."""
    from research.flood_experiments.features import LOCAL_PAIRS, local_climate
    from research.flood_experiments.features import local_percentile

    t = test.merge(fc, on=["district_code", "week"], how="left")
    ref = train[train["year"].isin(other_years)].merge(
        fc, on=["district_code", "week"], how="inner"
    )
    for obs, f in (
        ("rain_week_sum", "fc_rain_week_sum"),
        ("rain_week_max", "fc_rain_week_max"),
    ):
        g = ref.groupby("district_code")
        ratio = (
            (g[obs].mean() / g[f].mean().replace(0, np.nan)).clip(0.2, 5).fillna(1.0)
        )
        t[obs] = t[f] * t["district_code"].map(ratio).fillna(1.0)
    # wettest-pixel features: the district's usual p95/mean ratio
    for col in ("rain_week_sum", "rain_week_max"):
        if f"{col}_p95" in t.columns:
            k = (
                (train[f"{col}_p95"] / train[col].replace(0, np.nan))
                .groupby(train["district_code"])
                .median()
            )
            t[f"{col}_p95"] = t[col] * t["district_code"].map(k).fillna(1.0)
    clim = local_climate()
    for target, source in LOCAL_PAIRS:
        if target in t.columns and source != "rain_prev4w_sum":
            t[target] = local_percentile(t, source, clim)
    return t.dropna(subset=["fc_rain_week_sum"])


def e3c_real_forecast(df):
    """Honest lead time: test 2024-2025 with the ECMWF forecast issued
    before each week (forecast_archive.py) in place of observed rain.

    Two ways to use a forecast:
    - Perfect prog: a model trained on observed rain is fed the forecast.
    - MOS (model output statistics): the antecedent-only model's
      probability is blended with the forecast's local-climate
      percentiles by a 3-parameter logistic model fitted on the OTHER
      forecast year (cross-fitted), so it learns how far to trust the
      forecast. With two years of archive, intervals are indicative."""
    path = C.DATA_DIR / "raw" / "forecast_weekly.csv"
    if not path.exists():
        return {"not_run": "No archived forecasts (forecast_archive.py)."}
    fc = pd.read_csv(path, parse_dates=["week"])
    years = sorted(set(fc["week"].dt.year) & set(TEST_YEARS))
    setups = {
        "Perfect forecast (observed rain), upper bound": "observed",
        "Real ECMWF forecast issued before the week": "forecast",
        "No rain forecast (antecedent only)": "none",
        "Live rule on the real ECMWF forecast": "live",
        "Climatology": "clim",
    }
    preds = {k: [] for k in setups}
    mos_parts = {}
    for y in years:
        train = df[df["year"] <= y - 2]
        val = df[df["year"] == y - 1]
        test = df[df["year"] == y]
        other = [o for o in years if o != y]
        tf = _with_forecast(test, df[df["year"].isin(other)], fc, other)
        test_obs = test.merge(
            tf[["district_code", "week"]], on=["district_code", "week"]
        )
        models = {
            "observed": Mo.XGB(Mo.OPERATIONAL).fit(train, val),
            "none": Mo.XGB(Mo.FORECAST).fit(train, val),
            "clim": Mo.Climatology().fit(train, val),
        }
        models["forecast"] = models["observed"]
        live = Mo.RainfallThreshold()
        for name, kind in setups.items():
            m = live if kind == "live" else models[kind]
            frame = test_obs if kind == "observed" else tf
            tune = val if val["onset"].sum() >= MIN_VAL_ONSETS else train
            thr = M.best_f1_threshold(tune["onset"], m.predict(tune))
            p = m.predict(frame)
            if kind == "none":
                mos_parts[y] = frame.assign(p_none=p)
            preds[name].append(
                pd.DataFrame(
                    {
                        "fold": str(y),
                        "year": frame["year"].to_numpy(),
                        "week": frame["week"].to_numpy(),
                        "district_code": frame["district_code"].to_numpy(),
                        "built_frac": frame["built_frac"].to_numpy(),
                        "y": frame["onset"].to_numpy(),
                        "p": p,
                        "alert": p >= thr,
                    }
                )
            )
    mos_name = "MOS blend: antecedent model + ECMWF forecast"
    preds[mos_name] = []
    cols = ["rain_week_max_pct", "rain_week_sum_pct"]
    for y in years:
        fit_on = pd.concat([mos_parts[o] for o in years if o != y])
        Xf = np.column_stack([_logit(fit_on["p_none"]), fit_on[cols].fillna(0.5)])
        blend = LogisticRegression(max_iter=1000).fit(Xf, fit_on["onset"])
        thr = M.best_f1_threshold(fit_on["onset"], blend.predict_proba(Xf)[:, 1])
        t = mos_parts[y]
        p = blend.predict_proba(
            np.column_stack([_logit(t["p_none"]), t[cols].fillna(0.5)])
        )[:, 1]
        preds[mos_name].append(
            pd.DataFrame(
                {
                    "fold": str(y),
                    "year": t["year"].to_numpy(),
                    "week": t["week"].to_numpy(),
                    "district_code": t["district_code"].to_numpy(),
                    "built_frac": t["built_frac"].to_numpy(),
                    "y": t["onset"].to_numpy(),
                    "p": p,
                    "alert": p >= thr,
                }
            )
        )
    rows = [score(pd.concat(v, ignore_index=True), k) for k, v in preds.items()]
    for r in rows:
        logger.info(f"E3c {r['model']}: PR-AUC {r['pr_auc']:.3f}")
    return {"test_years": years, "rows": rows}


def label_audit(panel):
    """Case-control audit of the news labels with Sentinel-1 (sar_labels).
    If news onsets are real floods, radar should see new water at them
    far more often than at matched weeks with no reported flood. Radar
    misses floods in built-up areas (buildings scatter the signal back)
    and short flash floods between passes, so the comparison is also
    split by urban and rural districts."""
    path = C.DATA_DIR / "raw" / "sar_audit.csv"
    if not path.exists():
        return {"not_run": "Sentinel-1 audit not run yet (sar_labels.py)."}
    a = pd.read_csv(path).merge(
        panel.drop_duplicates("district_code")[
            ["district_code", "area_km2", "built_frac"]
        ],
        on="district_code",
    )
    urban_cut = panel.drop_duplicates("district_code")["built_frac"].quantile(0.75)
    a["setting"] = np.where(a["built_frac"] >= urban_cut, "urban", "rural")
    a["observed"] = (a["n_images"] > 0) & (
        a["obs_km2"] >= C.SAR_MIN_OBSERVED * a["area_km2"]
    )
    a["detected"] = a["flood_km2"] >= C.SAR_MIN_KM2
    seen = a[a["observed"]]

    def rates(g):
        return {
            "sampled": int(len(g)),
            "observed": int(g["observed"].sum()),
            "detection_rate": float(g.loc[g["observed"], "detected"].mean()),
            "median_flood_km2": float(g.loc[g["observed"], "flood_km2"].median()),
        }

    def odds_ratio(case, ctrl):
        """Onset vs control odds of radar detection, Wald 90% interval
        (0.5 added to each cell)."""
        a1 = case["detected"].sum() + 0.5
        b1 = (~case["detected"]).sum() + 0.5
        a0 = ctrl["detected"].sum() + 0.5
        b0 = (~ctrl["detected"]).sum() + 0.5
        lor = np.log(a1 * b0 / (b1 * a0))
        se = np.sqrt(1 / a1 + 1 / b1 + 1 / a0 + 1 / b0)
        return [
            float(np.exp(lor)),
            float(np.exp(lor - 1.645 * se)),
            float(np.exp(lor + 1.645 * se)),
        ]

    out = {"by_kind": {k: rates(g) for k, g in a.groupby("kind")}, "by_setting": {}}
    for setting, g in a.groupby("setting"):
        out["by_setting"][setting] = {k: rates(h) for k, h in g.groupby("kind")}
    case = seen[seen["kind"] == "onset"]
    for ctrl in ["control_same_week", "control_same_place"]:
        out[f"odds_ratio_vs_{ctrl}"] = odds_ratio(case, seen[seen["kind"] == ctrl])
    out["urban_built_frac_cut"] = float(urban_cut)
    return out


def e8_impact(panel):
    """E8 needs people affected per district per event (NADMO). It tests
    whether the exposure layer ranks impacts: Spearman correlation of
    affected counts with population density and with population x
    built-up share."""
    from research.flood_experiments import nadmo

    static = panel.drop_duplicates("district_code")
    inc = nadmo.load_incidents(static)
    inc = inc[pd.to_numeric(inc["affected"], errors="coerce").notna()]
    if len(inc) < 20:
        return {
            "not_run": "Needs NADMO incident records with people affected per "
            "district (requested; see nadmo_data_request.md). "
            f"{len(inc)} usable records found."
        }
    p = panel.assign(week=pd.to_datetime(panel["week"]))
    day = pd.to_datetime(inc["date"])
    inc = inc.assign(week=day - pd.to_timedelta(day.dt.weekday, unit="D"))
    m = inc.merge(p, on=["district_code", "week"], how="left")
    density = m["population"] / m["area_km2"]
    exposed = m["population"] * m["built_frac"]
    affected = m["affected"].astype(float)
    return {
        "records": int(len(m)),
        "spearman_affected_vs_density": float(spearmanr(affected, density).statistic),
        "spearman_affected_vs_built_exposure": float(
            spearmanr(affected, exposed).statistic
        ),
    }


def e2_ablation(df):
    steps = [
        ("Baseline (rainfall + season)", Mo.RAIN_ONLY + C.RAIN_LAGS),
        ("+ Soil moisture", Mo.RAIN_ONLY + C.RAIN_LAGS + C.SOIL),
        ("+ River (runoff, discharge)", Mo.RAIN_ONLY + C.RAIN_LAGS + C.SOIL + C.RIVER),
        ("+ Dam", None),
        (
            "+ Geographic",
            Mo.RAIN_ONLY + C.RAIN_LAGS + C.SOIL + C.RIVER + C.GEOGRAPHIC,
        ),
        ("+ Exposure", Mo.MULTI_SOURCE),
    ]
    rows, prev = [], None
    for label, feats in steps:
        if feats is None:
            rows.append(
                {
                    "model": label,
                    "not_run": "No historical dam release or reservoir record exists "
                    "for Ghana (VRA data never obtained); DAHITI levels start "
                    "after most labelled events.",
                }
            )
            continue
        pred = cross_validate(
            df, lambda f=feats, n=label: Mo.XGB(f, n), temporal_folds(df)
        )
        r = score(pred, label)
        r["delta_pr_auc"] = None if prev is None else r["pr_auc"] - prev
        prev = r["pr_auc"]
        rows.append(r)
        logger.info(f"E2 {label}: PR-AUC {r['pr_auc']:.3f}")
    return rows


def e4_spatial(df):
    rows, per_region = [], []
    for factory in [
        lambda: Mo.Climatology(),
        lambda: Mo.RainfallThreshold(),
        lambda: Mo.logistic(Mo.RAIN_ONLY, "Logistic regression (rainfall)"),
        lambda: Mo.XGB(Mo.RAIN_ONLY, "XGBoost (rainfall)"),
        lambda: Mo.XGB(Mo.MULTI_SOURCE, "Multi-source XGBoost"),
    ]:
        name = factory().name
        pred = cross_validate(df, factory, spatial_folds(df))
        rows.append(score(pred, name))
        for region, g in pred.groupby("fold"):
            if g["y"].sum() > 0:
                per_region.append(
                    {
                        "model": name,
                        "region": region,
                        "events": int(g["y"].sum()),
                        "pr_auc": M.probabilistic(g["y"], g["p"])["pr_auc"],
                        "base_rate": float(g["y"].mean()),
                    }
                )
        logger.info(f"E4 {name}: PR-AUC {rows[-1]['pr_auc']:.3f}")
    return {"pooled": rows, "per_region": per_region}


class _LateFusion:
    """One logistic model per source group; probabilities averaged
    (mean) or combined by a logistic meta-model fitted on validation
    (stacking)."""

    GROUPS = {
        "rain": C.SEASON + C.RAIN + C.RAIN_LAGS,
        "soil": C.SEASON + C.SOIL,
        "river": C.SEASON + C.RIVER,
        "static": C.GEOGRAPHIC + C.EXPOSURE,
    }

    def __init__(self, stacked):
        self.stacked = stacked
        self.name = (
            "Stacking (logistic meta-model)" if stacked else "Late fusion (mean)"
        )

    def fit(self, train, val):
        self.members = {
            g: Mo.logistic(f, g).fit(train, val) for g, f in self.GROUPS.items()
        }
        if self.stacked:
            # A validation year with no onsets can't fit a meta-model;
            # fall back to the members' in-sample training predictions.
            fit_on = val if val["onset"].sum() > 0 else train
            Z = self._z(fit_on)
            self.meta = LogisticRegression(max_iter=1000).fit(Z, fit_on["onset"])
        return self

    def _z(self, df):
        return np.column_stack([m.predict(df) for m in self.members.values()])

    def predict(self, df):
        Z = self._z(df)
        return self.meta.predict_proba(Z)[:, 1] if self.stacked else Z.mean(axis=1)


class _ExpertWeights:
    """The platform's hand-set fusion (src/models/multi_source_confidence.py)
    restricted to the sources that have a history: rainfall (weight 1.0,
    calculate_score on the wettest day) and river (weight 2.0, discharge
    above its median, scaled 0-1 at three times the median). Soil, dam,
    satellite and citizen reports have no 2000-2018 record."""

    name = "Platform hand-set weights"

    def fit(self, train, val=None):
        return self

    def predict(self, df):
        rain = np.array([calculate_score(v) / 100 for v in df["rain_week_max"]])
        river = np.clip((df["q_ratio"].fillna(1).to_numpy() - 1) / 2, 0, 1)
        w = RAINFALL_WEIGHT + RIVER_GAUGE_WEIGHT
        return (RAINFALL_WEIGHT * rain + RIVER_GAUGE_WEIGHT * river) / w


def e5_fusion(df):
    rows = []
    for factory in [
        lambda: Mo.XGB(Mo.MULTI_SOURCE, "Early fusion (multi-source XGBoost)"),
        lambda: _LateFusion(stacked=False),
        lambda: _LateFusion(stacked=True),
        lambda: _ExpertWeights(),
    ]:
        name = factory().name
        rows.append(score(cross_validate(df, factory, temporal_folds(df)), name))
        logger.info(f"E5 {name}: PR-AUC {rows[-1]['pr_auc']:.3f}")
    return rows


def e6_degradation(df):
    groups = {
        "Rainfall": C.RAIN + C.RAIN_LAGS,
        "Soil moisture": C.SOIL,
        "River (runoff, discharge)": C.RIVER,
        "Geographic + exposure": C.GEOGRAPHIC + C.EXPOSURE,
    }
    dynamic = {"Rainfall", "Soil moisture", "River (runoff, discharge)"}
    full, missing, stale = [], {g: [] for g in groups}, {g: [] for g in dynamic}
    for fold, train, val, test in temporal_folds(df):
        model = Mo.XGB(Mo.MULTI_SOURCE).fit(train, val)
        full.append((test["onset"].to_numpy(), model.predict(test), test["year"]))
        med = train[Mo.MULTI_SOURCE].median()
        for g, feats in groups.items():
            t = test.copy()
            t[feats] = med[feats].to_numpy()
            missing[g].append(model.predict(t))
            if g in dynamic:
                t = test.copy()
                t[feats] = test.groupby("district_code")[feats].shift(1).to_numpy()
                stale[g].append(model.predict(t))
    y = np.concatenate([f[0] for f in full])
    p_full = np.concatenate([f[1] for f in full])
    base = M.probabilistic(y, p_full)["pr_auc"]
    rows = [{"condition": "All sources", "pr_auc": base, "delta_pr_auc": 0.0}]
    for g in groups:
        pr = M.probabilistic(y, np.concatenate(missing[g]))["pr_auc"]
        rows.append(
            {"condition": f"{g} missing", "pr_auc": pr, "delta_pr_auc": pr - base}
        )
        if g in stale:
            pr = M.probabilistic(y, np.concatenate(stale[g]))["pr_auc"]
            rows.append(
                {
                    "condition": f"{g} one week stale",
                    "pr_auc": pr,
                    "delta_pr_auc": pr - base,
                }
            )
    logger.info("E6 done")
    return rows


def _logit(q):
    q = np.clip(q, 1e-6, 1 - 1e-6)
    return np.log(q / (1 - q))


def e7_calibration(df):
    raw, platt, iso, ys = [], [], [], []
    for fold, train, val, test in temporal_folds(df):
        model = Mo.XGB(Mo.MULTI_SOURCE).fit(train, val)
        pv, pt = model.predict(val), model.predict(test)
        if val["onset"].sum() > 0:
            pl = LogisticRegression(max_iter=1000).fit(
                _logit(pv).reshape(-1, 1), val["onset"]
            )
            platt.append(pl.predict_proba(_logit(pt).reshape(-1, 1))[:, 1])
            ir = IsotonicRegression(out_of_bounds="clip").fit(pv, val["onset"])
            iso.append(ir.predict(pt))
        else:
            platt.append(pt)
            iso.append(pt)
        raw.append(pt)
        ys.append(test["onset"].to_numpy())
    y = np.concatenate(ys)
    out = []
    for name, parts in [("Raw", raw), ("Platt scaling", platt), ("Isotonic", iso)]:
        p = np.concatenate(parts)
        out.append(
            {
                "method": name,
                **M.probabilistic(y, p),
                "reliability": M.reliability(y, p)["bins"],
            }
        )
    logger.info("E7 done")
    return out


def e9_shap(df, n_bootstrap=5):
    import shap

    end = C.S["shap_train_end"]
    train = df[df["year"] <= end]
    val = df[df["year"] == end + 1]
    test = df[df["year"] >= end + 2]
    feats = Mo.MULTI_SOURCE
    model = Mo.XGB(feats).fit(train, val)
    rng = np.random.default_rng(C.RANDOM_SEED)
    neg = test[test["onset"] == 0]
    sample = pd.concat(
        [test[test["onset"] == 1], neg.sample(min(3000, len(neg)), random_state=1)]
    )
    explainer = shap.TreeExplainer(model.model)
    sv = explainer.shap_values(sample[feats])
    global_imp = pd.Series(np.abs(sv).mean(axis=0), index=feats).sort_values(
        ascending=False
    )

    # Fidelity: replacing a sample's top-k SHAP features with training
    # medians should move its prediction more than replacing k random ones.
    med = train[feats].median()
    p0 = model.predict(sample)
    top = sample.assign(p=p0).nlargest(min(300, len(sample)), "p").index
    sub = sample.loc[top]
    sv_sub = sv[sample.index.get_indexer(top)]
    fidelity = []
    for k in (1, 3, 5):
        X_top, X_rand = sub.copy(), sub.copy()
        for i, row_sv in enumerate(np.abs(sv_sub)):
            idx_top = np.argsort(-row_sv)[:k]
            idx_rand = rng.choice(len(feats), k, replace=False)
            for j in idx_top:
                X_top.iat[i, X_top.columns.get_loc(feats[j])] = med.iloc[j]
            for j in idx_rand:
                X_rand.iat[i, X_rand.columns.get_loc(feats[j])] = med.iloc[j]
        base = model.predict(sub)
        fidelity.append(
            {
                "k": k,
                "mean_abs_change_top_shap": float(
                    np.mean(np.abs(base - model.predict(X_top)))
                ),
                "mean_abs_change_random": float(
                    np.mean(np.abs(base - model.predict(X_rand)))
                ),
            }
        )

    # Stability: global importance rankings across models retrained on
    # bootstrap resamples of training districts.
    codes = train["district_code"].unique()
    rankings = []
    for b in range(n_bootstrap):
        pick = rng.choice(codes, len(codes), replace=True)
        boot = pd.concat([train[train["district_code"] == c] for c in pick])
        m = Mo.XGB(feats, seed=C.RANDOM_SEED + b).fit(boot, val)
        s = shap.TreeExplainer(m.model).shap_values(sample[feats])
        rankings.append(np.abs(s).mean(axis=0))
    rhos = [spearmanr(a, b).statistic for a, b in combinations(rankings, 2)]
    logger.info("E9 done")
    return {
        "global_mean_abs_shap": {k: float(v) for k, v in global_imp.items()},
        "fidelity_deletion": fidelity,
        "stability_spearman": {
            "mean": float(np.mean(rhos)),
            "min": float(np.min(rhos)),
            "pairs": len(rhos),
        },
        "test_period": f"{end + 2}-{TEST_YEARS[-1]}",
    }


def dataset_summary(raw, df):
    flooded = raw[raw["flood"] == 1]
    extra = {}
    if "flood_news" in raw.columns:
        news = pd.read_csv(C.DATA_DIR / "raw" / "groundsource_events.csv")
        extra = {
            "news_events_in_ghana": int(len(news)),
            "news_events_placed": int(news["district_code"].notna().sum()),
            "news_events_too_large_to_place": int(
                (news["area_km2"] > C.NEWS_MAX_AREA_KM2).sum()
            ),
            "flood_weeks_by_label": {
                k: int(raw[f"flood_{k}"].sum())
                for k in C.S["labels"]
                if f"flood_{k}" in raw.columns
            },
        }
    return {
        "study": C.STUDY,
        **extra,
        "districts": int(raw["district_code"].nunique()),
        "regions": int(raw["region"].nunique()),
        "weeks": int(raw["week"].nunique()),
        "rows_raw": int(len(raw)),
        "flood_weeks": int(raw["flood"].sum()),
        "rows_scored": int(len(df)),
        "onset_events": int(df["onset"].sum()),
        "districts_with_onset": int(df.loc[df.onset == 1, "district_code"].nunique()),
        "onsets_by_region": df[df.onset == 1].groupby("region").size().to_dict(),
        "onsets_by_year": {
            int(k): int(v) for k, v in df[df.onset == 1].groupby("year").size().items()
        },
        "label_sources": flooded["label_source"].value_counts().to_dict(),
    }


def main(only=None):
    """only: re-run a single experiment (e.g. "E4") and update it in the
    existing results.json instead of re-running everything."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    C.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raw = pd.read_parquet(C.DATA_DIR / "panel.parquet")
    df = build_features(raw)
    out = C.RESULTS_DIR / "results.json"
    single = {
        "E1": ("E1_E3_hierarchy_temporal", e1_e3_hierarchy),
        "E3b": ("E3b_forecast", e3b_forecast),
        "E3c": ("E3c_real_forecast", e3c_real_forecast),
        "E2": ("E2_ablation", e2_ablation),
        "E4": ("E4_spatial", e4_spatial),
        "E5": ("E5_fusion", e5_fusion),
        "E6": ("E6_degradation", e6_degradation),
        "E7": ("E7_calibration", e7_calibration),
        "E9": ("E9_shap", e9_shap),
    }
    if only == "labels":
        # After sar_labels.py has run: add the label audit to an
        # existing run without repeating the main experiments.
        results = json.loads(out.read_text())
        results["dataset"] = dataset_summary(raw, df)
        results["label_audit"] = label_audit(raw)
        results["E8_impact"] = e8_impact(raw)
        out.write_text(json.dumps(results, indent=2, default=str))
        logger.info(f"updated label checks in {out}")
        return
    if only:
        key, fn = single[only]
        results = json.loads(out.read_text())
        results[key] = fn(df)
        out.write_text(json.dumps(results, indent=2, default=str))
        logger.info(f"updated {key} in {out}")
        return
    results = {"dataset": dataset_summary(raw, df)}
    logger.info(json.dumps(results["dataset"], default=str))
    results["E1_E3_hierarchy_temporal"] = e1_e3_hierarchy(df)
    results["E3b_forecast"] = e3b_forecast(df)
    results["E3c_real_forecast"] = e3c_real_forecast(df)
    results["E2_ablation"] = e2_ablation(df)
    results["E4_spatial"] = e4_spatial(df)
    results["E5_fusion"] = e5_fusion(df)
    results["E6_degradation"] = e6_degradation(df)
    results["E7_calibration"] = e7_calibration(df)
    results["E9_shap"] = e9_shap(df)
    if C.STUDY != "v1_gfd":
        results["label_audit"] = label_audit(raw)
        results["E8_impact"] = e8_impact(raw)
    else:
        results["E8_impact"] = {
            "not_run": "Needs people-affected counts per district per event; "
            "open sources (DFO, EM-DAT, ReliefWeb) report them per event or "
            "per country only."
        }
    out.write_text(json.dumps(results, indent=2, default=str))
    logger.info(f"wrote {out}")


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else None)
