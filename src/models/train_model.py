"""
Train the XGBoost flood risk model.
Generates models/xgboost_flood_risk.pkl
"""

from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb

FEATURE_COLS = [
    "precipitation",
    "roll_3d",
    "roll_7d",
    "roll_30d",
    "cumulative",
    "z_score",
]


def train_model():
    print("Loading feature dataset...")

    df = pd.read_parquet("data/processed/accra_features_2024.parquet")

    if "flood_risk_score" not in df.columns:
        raise ValueError("Dataset must contain 'flood_risk_score' target column.")

    X = df[FEATURE_COLS]
    y = df["flood_risk_score"]

    print(f"Training rows: {len(df)}")

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
    )

    model.fit(X, y)

    Path("models").mkdir(exist_ok=True)

    output_path = "models/xgboost_flood_risk.pkl"

    joblib.dump(model, output_path)

    print(f"✅ Model saved to {output_path}")


if __name__ == "__main__":
    train_model()
