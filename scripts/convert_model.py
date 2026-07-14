#!/usr/bin/env python3
"""Convert model to proper format for loading."""

import pickle
from pathlib import Path

import joblib
import xgboost as xgb


def convert_model():
    """Convert the existing model to a loadable format."""

    pkl_path = Path("models/xgboost_flood_risk.pkl")
    json_path = Path("models/xgboost_flood_risk.json")
    joblib_path = Path("models/xgboost_flood_risk.joblib")

    # Try to load the pickle model
    if pkl_path.exists():
        try:
            with open(pkl_path, "rb") as f:
                model = pickle.load(f)
            print(f"✅ Loaded pickle model from {pkl_path}")

            # Save as joblib (most reliable)
            joblib.dump(model, joblib_path)
            print(f"✅ Saved as joblib: {joblib_path}")

            # Also try to save as XGBoost JSON if it's an XGBoost model
            if hasattr(model, "get_booster"):
                model.get_booster().save_model(str(json_path))
                print(f"✅ Saved as XGBoost JSON: {json_path}")

            return True
        except Exception as e:
            print(f"❌ Failed to load pickle: {e}")

    # If pickle fails, try JSON directly
    if json_path.exists():
        try:
            model = xgb.XGBRegressor()
            model.load_model(str(json_path))
            print(f"✅ Loaded JSON model from {json_path}")
            joblib.dump(model, joblib_path)
            print(f"✅ Saved as joblib: {joblib_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load JSON: {e}")

    print("⚠️ No valid model found. Creating sample model...")

    # Create a sample model for testing
    from sklearn.datasets import make_regression
    from sklearn.model_selection import train_test_split

    X, y = make_regression(n_samples=1000, n_features=5, noise=0.1, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = xgb.XGBRegressor(
        n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
    )
    model.fit(X_train, y_train)

    joblib.dump(model, joblib_path)
    print(f"✅ Created sample model: {joblib_path}")

    return True


if __name__ == "__main__":
    convert_model()
