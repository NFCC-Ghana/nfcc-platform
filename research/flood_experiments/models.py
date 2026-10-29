"""The model hierarchy from the Manuscript Writing Guide, section 9:

climatology -> persistence -> rainfall threshold -> logistic regression ->
random forest -> XGBoost -> temporal model -> multi-source model

Every model exposes fit(train, val) and predict(df) -> P(onset), where
train/val/df are feature DataFrames from features.build_features.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from research.flood_experiments import config as C
from src.alerts.formatter import calculate_score


class Climatology:
    """Each district's training-period onset rate by calendar month,
    shrunk toward the national monthly rate (Beta prior, strength 50
    weeks) so districts with few weeks don't get extreme rates."""

    name = "Climatology"
    features: list = []

    def fit(self, train, val=None):
        month = train["week"].dt.month
        national = train.groupby(month)["onset"].mean()
        grp = train.groupby([train["district_code"], month])["onset"]
        k = 50.0
        prior = national.reindex(grp.mean().index.get_level_values(1)).to_numpy()
        self.table = (grp.sum() + k * prior) / (grp.count() + k)
        self.national = national
        return self

    def predict(self, df):
        month = df["week"].dt.month
        key = pd.MultiIndex.from_arrays([df["district_code"], month])
        p = self.table.reindex(key).to_numpy()
        fallback = self.national.reindex(month).to_numpy()
        return np.where(np.isnan(p), fallback, p)


class Persistence:
    """A flood ended in this district within the last 8 weeks."""

    name = "Persistence"
    features = ["flood_recent8"]

    def fit(self, train, val=None):
        return self

    def predict(self, df):
        return df["flood_recent8"].to_numpy(dtype=float)


class RainfallThreshold:
    """The platform's live rule: calculate_score() on the week's wettest
    day, rescaled to 0-1. Not fitted."""

    name = "Rainfall threshold (live rule)"
    features = ["rain_week_max"]

    def fit(self, train, val=None):
        return self

    def predict(self, df):
        return np.array([calculate_score(v) / 100.0 for v in df["rain_week_max"]])


class RiverPercentile:
    """The GloFAS-style benchmark: how unusual this week's discharge is
    for the district - its percentile within the district's training
    weeks. Operational GloFAS warns on return-period exceedance; this is
    the same signal without a fixed return period. Not a probability, so
    judge it on ranking (ROC/PR-AUC) and thresholded scores, not Brier."""

    name = "River percentile (GloFAS-style)"
    features = ["q_week_max"]

    def fit(self, train, val=None):
        self.sorted = {
            k: np.sort(g.dropna().to_numpy())
            for k, g in train.groupby("district_code")["q_week_max"]
        }
        return self

    def predict(self, df):
        out = np.zeros(len(df))
        for i, (code, q) in enumerate(zip(df["district_code"], df["q_week_max"])):
            ref = self.sorted.get(code)
            if ref is not None and len(ref) and q == q:
                out[i] = np.searchsorted(ref, q, side="right") / len(ref)
        return out


class _Sklearn:
    def __init__(self, features, estimator, name):
        self.features = features
        self.estimator = estimator
        self.name = name

    def fit(self, train, val=None):
        self.median = train[self.features].median()
        X = train[self.features].fillna(self.median)
        self.estimator.fit(X, train["onset"])
        return self

    def predict(self, df):
        X = df[self.features].fillna(self.median)
        return self.estimator.predict_proba(X)[:, 1]


def logistic(features, name="Logistic regression"):
    return _Sklearn(
        features,
        make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)),
        name,
    )


def random_forest(features, name="Random forest"):
    return _Sklearn(
        features,
        RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=30,
            max_features="sqrt",
            n_jobs=-1,
            random_state=C.RANDOM_SEED,
        ),
        name,
    )


class XGB:
    """Gradient-boosted trees with early stopping on the validation fold's
    PR-AUC. Missing values are handled natively.

    With a few hundred events, unconstrained trees learn noise such as
    "more rain lowers risk" in some corner of the feature space. Rain,
    soil, runoff and discharge inputs (config.MONOTONE_UP) are therefore
    constrained to raise risk monotonically, and trees are kept shallow
    and regularised."""

    def __init__(self, features, name="XGBoost", seed=C.RANDOM_SEED):
        self.features = features
        self.name = name
        self.seed = seed

    def fit(self, train, val):
        from xgboost import XGBClassifier

        self.model = XGBClassifier(
            n_estimators=600,
            learning_rate=0.03,
            max_depth=3,
            min_child_weight=10,
            reg_lambda=5.0,
            subsample=0.8,
            colsample_bytree=0.8,
            monotone_constraints=tuple(
                1 if f in C.MONOTONE_UP else 0 for f in self.features
            ),
            eval_metric="aucpr",
            early_stopping_rounds=50,
            random_state=self.seed,
            n_jobs=-1,
            verbosity=0,
        )
        has_val = val is not None and val["onset"].sum() > 0
        ev = val if has_val else train
        self.model.fit(
            train[self.features],
            train["onset"],
            eval_set=[(ev[self.features], ev["onset"])],
            verbose=False,
        )
        return self

    def predict(self, df):
        return self.model.predict_proba(df[self.features])[:, 1]


RAIN_ONLY = C.SEASON + C.RAIN
TEMPORAL = C.SEASON + C.RAIN + C.RAIN_LAGS + C.SOIL
MULTI_SOURCE = (
    C.SEASON + C.RAIN + C.RAIN_LAGS + C.SOIL + C.RIVER + C.GEOGRAPHIC + C.EXPOSURE
)
# One week ahead: only what is known when the week starts.
FORECAST = (
    C.SEASON
    + C.RAIN_LAGS
    + ["rain_prev4w_sum", "sm_start", "runoff_prev4w_sum"]
    + ["q_ratio_lag1", "q_week_max_log_lag1"]
    + C.GEOGRAPHIC
    + C.EXPOSURE
)
C.MONOTONE_UP.update(
    ["rain_prev4w_sum", "sm_start", "runoff_prev4w_sum"]
    + ["q_ratio_lag1", "q_week_max_log_lag1"]
)


def hierarchy():
    """Factories (not instances) so every fold gets fresh models."""
    return [
        lambda: Climatology(),
        lambda: Persistence(),
        lambda: RainfallThreshold(),
        lambda: RiverPercentile(),
        lambda: logistic(RAIN_ONLY, "Logistic regression (rainfall)"),
        lambda: random_forest(RAIN_ONLY, "Random forest (rainfall)"),
        lambda: XGB(RAIN_ONLY, "XGBoost (rainfall)"),
        lambda: XGB(TEMPORAL, "Temporal XGBoost (rain lags + soil state)"),
        lambda: XGB(MULTI_SOURCE, "Multi-source XGBoost"),
    ]
