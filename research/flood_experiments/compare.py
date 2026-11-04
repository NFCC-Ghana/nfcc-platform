"""Paired model comparisons and subgroup performance (main study).

The results tables report a 90% interval for each model on its own. Two
models' intervals can overlap even when one is consistently better, and can
be disjoint by chance, so a difference has to be tested on the *same*
resamples. This module re-runs the key models with the same forward-chaining
folds as experiment E1/E3b, then

1. bootstraps whole test years (the same block bootstrap as the results
   tables) and reports, for each pair, the difference in PR-AUC and in
   within-district AUC with its 90% interval and the share of resamples in
   which the first model is better;
2. reports performance by region and by urban/rural district for the best
   model, the live rule and climatology (TRIPOD+AI item 14, fairness).

Usage:  python -m research.flood_experiments.compare
Writes: results/<study>/comparison.json
"""

import json
import logging

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from . import config as C
from . import metrics as M
from . import models as Mo
from .experiments import cross_validate, temporal_folds
from .features import build_features

logger = logging.getLogger("nfcc.research.compare")

N_BOOT = 1000

# (key, label shown in the report, factory)
MODELS = [
    ("M1", "Climatology", lambda: Mo.Climatology()),
    ("M3", "NFCC rainfall rule", lambda: Mo.RainfallThreshold()),
    ("M5", "Logistic regression, rainfall", lambda: Mo.logistic(Mo.RAIN_ONLY)),
    ("M9", "XGBoost, multi-source", lambda: Mo.XGB(Mo.MULTI_SOURCE)),
    ("M11", "XGBoost, multi-source + local climate", lambda: Mo.XGB(Mo.FINAL)),
    ("M12-raw", "XGBoost, forecast mode (M12 inputs)", lambda: Mo.XGB(Mo.FORECAST)),
]

PAIRS = [
    ("M11", "M1"),
    ("M11", "M9"),
    ("M11", "M3"),
    ("M9", "M1"),
    ("M5", "M1"),
    ("M3", "M1"),
    ("M12-raw", "M1"),
    ("M12-raw", "M3"),
]


def _pr_auc(y, p):
    return M.probabilistic(y, p)["pr_auc"]


def _within_auc(d, y, p):
    """metrics.within_district_auc via Mann-Whitney ranks (same value, with
    ties averaged as in roc_auc_score; fast enough for 1,000 resamples)."""
    order = np.lexsort((p, d))
    d, y, p = d[order], y[order].astype(bool), p[order]
    aucs, weights = [], []
    for s, e in _runs(d):
        yy, pp = y[s:e], p[s:e]
        n1 = int(yy.sum())
        n0 = len(yy) - n1
        if n1 == 0 or n0 == 0:
            continue
        ranks = rankdata(pp)
        aucs.append((ranks[yy].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
        weights.append(n1)
    return float(np.average(aucs, weights=weights)) if aucs else float("nan")


def _runs(sorted_keys):
    cut = np.flatnonzero(sorted_keys[1:] != sorted_keys[:-1]) + 1
    starts = np.r_[0, cut]
    ends = np.r_[cut, len(sorted_keys)]
    return zip(starts, ends)


def paired_bootstrap(preds, a, b, seed=C.RANDOM_SEED):
    """Year-block bootstrap of metric(a) - metric(b) on identical resamples."""
    pa, pb = preds[a], preds[b]
    assert (pa["district_code"].to_numpy() == pb["district_code"].to_numpy()).all()
    y = pa["y"].to_numpy()
    years = pa["year"].to_numpy()
    d = pa["district_code"].to_numpy()
    p1, p2 = pa["p"].to_numpy(), pb["p"].to_numpy()
    groups = {yr: np.flatnonzero(years == yr) for yr in np.unique(years)}
    keys = list(groups)
    rng = np.random.default_rng(seed)
    out = {"pr_auc": [], "within_district_auc": []}
    for _ in range(N_BOOT):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys))])
        if not 0 < y[idx].sum() < len(idx):
            continue
        out["pr_auc"].append(_pr_auc(y[idx], p1[idx]) - _pr_auc(y[idx], p2[idx]))
        out["within_district_auc"].append(
            _within_auc(d[idx], y[idx], p1[idx]) - _within_auc(d[idx], y[idx], p2[idx])
        )
    point = {
        "pr_auc": _pr_auc(y, p1) - _pr_auc(y, p2),
        "within_district_auc": _within_auc(d, y, p1) - _within_auc(d, y, p2),
    }
    # The fast version must agree with the reported metric.
    assert abs(_within_auc(d, y, p1) - M.within_district_auc(d, y, p1)) < 1e-9
    res = {"a": a, "b": b, "n_boot": len(out["pr_auc"])}
    for metric, vals in out.items():
        vals = np.asarray(vals)
        res[metric] = {
            "difference": float(point[metric]),
            "ci90": [float(np.quantile(vals, 0.05)), float(np.quantile(vals, 0.95))],
            "share_a_better": float((vals > 0).mean()),
        }
    return res


def subgroups(pred, df):
    """PR-AUC, base rate and within-district AUC by region and urban/rural."""
    region = df.drop_duplicates("district_code").set_index("district_code")["region"]
    pred = pred.assign(region=pred["district_code"].map(region))
    cut = pred.drop_duplicates("district_code")["built_frac"].quantile(0.75)
    pred["setting"] = np.where(pred["built_frac"] >= cut, "Urban", "Rural")
    rows = []
    for col in ("region", "setting"):
        for name, g in pred.groupby(col):
            y, p = g["y"].to_numpy(), g["p"].to_numpy()
            rows.append(
                {
                    "group_type": col,
                    "group": name,
                    "districts": int(g["district_code"].nunique()),
                    "onsets": int(y.sum()),
                    "base_rate": float(y.mean()),
                    "pr_auc": _pr_auc(y, p) if 0 < y.sum() < len(y) else float("nan"),
                    "within_district_auc": M.within_district_auc(
                        g["district_code"], y, p
                    ),
                    "pod": float(g.loc[g["y"] == 1, "alert"].mean())
                    if y.sum()
                    else float("nan"),
                }
            )
    return rows


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    raw = pd.read_parquet(C.DATA_DIR / "panel.parquet")
    df = build_features(raw)
    preds = {}
    cache = C.DATA_DIR / "comparison_predictions.parquet"
    cached = pd.read_parquet(cache) if cache.exists() else None
    for key, label, factory in MODELS:
        if cached is not None and key in set(cached["model"]):
            preds[key] = cached[cached["model"] == key].drop(columns="model").reset_index(drop=True)
        else:
            preds[key] = cross_validate(df, factory, temporal_folds(df)).sort_values(
                ["week", "district_code"], ignore_index=True
            )
        y, p = preds[key]["y"].to_numpy(), preds[key]["p"].to_numpy()
        logger.info(f"{key} {label}: PR-AUC {_pr_auc(y, p):.3f}")
    pd.concat([v.assign(model=k) for k, v in preds.items()]).to_parquet(cache)
    out = {
        "study": C.STUDY,
        "test_years": C.TEST_YEARS,
        "n_boot": N_BOOT,
        "models": {k: lab for k, lab, _ in MODELS},
        "pairs": [paired_bootstrap(preds, a, b) for a, b in PAIRS],
        "subgroups": {k: subgroups(preds[k], df) for k in ("M1", "M3", "M11")},
    }
    path = C.RESULTS_DIR / "comparison.json"
    path.write_text(json.dumps(out, indent=1))
    logger.info(f"wrote {path}")


if __name__ == "__main__":
    main()
