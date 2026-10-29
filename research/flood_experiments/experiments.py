"""Experiments from the Manuscript Writing Guide, plus the checks the
guide does not list but a reviewer would ask for.

E1  Model hierarchy and data configuration (rainfall-only vs multi-source)
E2  Cumulative source ablation: Baseline -> +Soil -> +River -> +Dam ->
    +Geographic -> +Exposure
E3  Temporal holdout: forward-chaining by year (train <= y-2, validate
    y-1, test y) over config.TEST_YEARS
E3b One-week-ahead forecast (inputs known when the week starts) vs the
    nowcast hindcast
E4  Spatial holdout: leave-one-region-out, separated in time
E5  Fusion strategy: early fusion, late fusion (mean), stacking, and the
    platform's hand-set weights
E6  Source degradation: a source missing (filled with its training
    median) or stale (last week's values) at prediction time
E7  Calibration: raw vs Platt scaling vs isotonic regression
E8  Impact layers: only with NADMO incident records (nadmo.py)
E9  SHAP fidelity (deletion test) and stability (bootstrap retraining)
E10 Label sensitivity (v2): the same models scored against news, SAR and
    union labels
LA  Label agreement (v2): how often news reports and Sentinel-1 agree

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


def e10_labels(panel):
    """The same models trained and scored on each flood record. If a
    conclusion flips between news and satellite labels, it is about the
    labels, not about flood prediction."""
    rows = []
    for label in C.S["labels"]:
        df = build_features(panel, label)
        for factory in [
            lambda: Mo.Climatology(),
            lambda: Mo.RainfallThreshold(),
            lambda: Mo.RiverPercentile(),
            lambda: Mo.XGB(Mo.MULTI_SOURCE, "Multi-source XGBoost"),
        ]:
            r = score(cross_validate(df, factory, temporal_folds(df)), factory().name)
            r["label"] = label
            rows.append(r)
            logger.info(f"E10 {label} {r['model']}: PR-AUC {r['pr_auc']:.3f}")
    return rows


def _keys(df, col):
    hit = df[df[col] == 1]
    return set(zip(hit["district_code"], hit["week"]))


def label_agreement(panel, tol=1):
    """News onsets vs Sentinel-1 flags, within +/- tol weeks. A news onset
    can only be confirmed where the satellite looked, so the confirmation
    rate is computed over news onsets with a SAR pass within the window."""
    news = build_features(panel, "news")
    sar = build_features(panel, "sar")
    p = panel.assign(week=pd.to_datetime(panel["week"]))
    observed, flagged, reported = (
        _keys(p, "sar_observed"),
        _keys(p, "flood_sar"),
        _keys(p, "flood_news"),
    )
    near = [pd.Timedelta(weeks=k) for k in range(-tol, tol + 1)]

    def any_in(keys, d, w):
        return any((d, w + k) in keys for k in near)

    n_on = news[news.onset == 1]
    seen = [r for r in n_on.itertuples() if any_in(observed, r.district_code, r.week)]
    confirmed = sum(any_in(flagged, r.district_code, r.week) for r in seen)
    s_on = sar[sar.onset == 1]
    in_news = sum(any_in(reported, r.district_code, r.week) for r in s_on.itertuples())
    return {
        "news_onsets": int(len(n_on)),
        "news_onsets_with_sar_pass": len(seen),
        "news_confirmed_by_sar": int(confirmed),
        "news_confirmation_rate": confirmed / len(seen) if seen else float("nan"),
        "sar_onsets": int(len(s_on)),
        "sar_onsets_reported_in_news": int(in_news),
        "sar_reporting_rate": in_news / len(s_on) if len(s_on) else float("nan"),
        "tolerance_weeks": tol,
    }


def e8_impact(panel):
    """E8 needs people affected per district per event (NADMO). It tests
    whether the exposure layer ranks impacts: Spearman correlation of
    affected counts with population density and with population x
    Sentinel-1 flooded share in the incident week."""
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
    exposed = m["population"] * (m["sar_flood_km2"].fillna(0) / m["area_km2"])
    affected = m["affected"].astype(float)
    return {
        "records": int(len(m)),
        "spearman_affected_vs_density": float(spearmanr(affected, density).statistic),
        "spearman_affected_vs_sar_exposure": float(
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
    if "flood_sar" in raw.columns:
        extra["sar_observed_share"] = float(raw["sar_observed"].mean())
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
        "E2": ("E2_ablation", e2_ablation),
        "E4": ("E4_spatial", e4_spatial),
        "E5": ("E5_fusion", e5_fusion),
        "E6": ("E6_degradation", e6_degradation),
        "E7": ("E7_calibration", e7_calibration),
        "E9": ("E9_shap", e9_shap),
    }
    if only == "labels":
        # After the Sentinel-1 exports land: add the label checks to an
        # existing run without repeating the main experiments.
        results = json.loads(out.read_text())
        results["dataset"] = dataset_summary(raw, df)
        results["E10_labels"] = e10_labels(raw)
        results["label_agreement"] = label_agreement(raw)
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
    results["E2_ablation"] = e2_ablation(df)
    results["E4_spatial"] = e4_spatial(df)
    results["E5_fusion"] = e5_fusion(df)
    results["E6_degradation"] = e6_degradation(df)
    results["E7_calibration"] = e7_calibration(df)
    results["E9_shap"] = e9_shap(df)
    if "flood_sar" in raw.columns:
        results["E10_labels"] = e10_labels(raw)
        results["label_agreement"] = label_agreement(raw)
    if C.STUDY != "v1_gfd":
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
