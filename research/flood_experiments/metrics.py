"""Verification metrics for rare binary flood events.

Probabilistic: ROC-AUC, PR-AUC (average precision), Brier score, expected
calibration error. Categorical, at a decision threshold: precision,
recall (POD), F1, false-alarm ratio (FAR), missed-event rate (MER),
probability of false detection (POFD) and SEDI (Ferro & Stephenson 2011).

Uncertainty: a block bootstrap that resamples whole years, because daily
and weekly flood series are autocorrelated within a season.
"""

import math

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

_EPS = 1e-6


def contingency(y, yhat):
    y = np.asarray(y).astype(bool)
    yhat = np.asarray(yhat).astype(bool)
    return {
        "hits": int((y & yhat).sum()),
        "misses": int((y & ~yhat).sum()),
        "false_alarms": int((~y & yhat).sum()),
        "correct_negatives": int((~y & ~yhat).sum()),
    }


def sedi(hits, misses, false_alarms, correct_negatives):
    """Symmetric Extremal Dependence Index; 0 = no skill, 1 = perfect."""
    if hits + misses == 0 or false_alarms + correct_negatives == 0:
        return float("nan")
    h = min(max(hits / (hits + misses), _EPS), 1 - _EPS)
    f = min(max(false_alarms / (false_alarms + correct_negatives), _EPS), 1 - _EPS)
    num = math.log(f) - math.log(h) - math.log(1 - f) + math.log(1 - h)
    den = math.log(f) + math.log(h) + math.log(1 - f) + math.log(1 - h)
    return num / den


def categorical(y, yhat):
    t = contingency(y, yhat)
    tp, fn, fp, tn = (
        t["hits"],
        t["misses"],
        t["false_alarms"],
        t["correct_negatives"],
    )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        **t,
        "precision": precision,
        "recall_pod": recall,
        "f1": f1,
        "false_alarm_ratio": fp / (tp + fp) if tp + fp else float("nan"),
        "missed_event_rate": fn / (tp + fn) if tp + fn else float("nan"),
        "pofd": fp / (fp + tn) if fp + tn else float("nan"),
        "sedi": sedi(tp, fn, fp, tn),
    }


def best_f1_threshold(y, p):
    """Decision threshold that maximises F1 - chosen on validation data
    only, then applied unchanged to the test fold."""
    y = np.asarray(y)
    p = np.asarray(p)
    if y.sum() == 0:
        return 0.5
    candidates = np.unique(np.quantile(p, np.linspace(0.5, 0.9999, 400)))
    best, best_t = -1.0, 0.5
    for t in candidates:
        f = categorical(y, p >= t)["f1"]
        if f > best:
            best, best_t = f, float(t)
    return best_t


def reliability(y, p, bins=10):
    """Equal-count bins (most probabilities are tiny, so equal-width bins
    would put almost everything in the first one)."""
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    rows, ece = [], 0.0
    for chunk in np.array_split(order, bins):
        if len(chunk) == 0:
            continue
        mp, fo = float(p[chunk].mean()), float(y[chunk].mean())
        rows.append({"mean_predicted": mp, "observed_rate": fo, "n": int(len(chunk))})
        ece += len(chunk) / len(p) * abs(mp - fo)
    return {"bins": rows, "ece": ece}


def probabilistic(y, p):
    y = np.asarray(y)
    p = np.clip(np.asarray(p, dtype=float), 0, 1)
    both = 0 < y.sum() < len(y)
    return {
        "n": int(len(y)),
        "events": int(y.sum()),
        "base_rate": float(y.mean()),
        "roc_auc": float(roc_auc_score(y, p)) if both else float("nan"),
        "pr_auc": float(average_precision_score(y, p)) if both else float("nan"),
        "brier": float(brier_score_loss(y, p)),
        "ece": reliability(y, p)["ece"],
    }


def evaluate(y, p, threshold):
    return {
        **probabilistic(y, p),
        "threshold": float(threshold),
        **categorical(y, np.asarray(p) >= threshold),
    }


def block_bootstrap_ci(y, p, years, metric, n_boot=300, alpha=0.10, seed=42):
    """(1 - alpha) interval for metric(y, p), resampling whole years."""
    rng = np.random.default_rng(seed)
    y, p, years = np.asarray(y), np.asarray(p), np.asarray(years)
    groups = {yr: np.flatnonzero(years == yr) for yr in np.unique(years)}
    keys = list(groups)
    vals = []
    for _ in range(n_boot):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys))])
        if 0 < y[idx].sum() < len(idx):
            vals.append(metric(y[idx], p[idx]))
    if not vals:
        return [float("nan"), float("nan")]
    return [
        float(np.quantile(vals, alpha / 2)),
        float(np.quantile(vals, 1 - alpha / 2)),
    ]
