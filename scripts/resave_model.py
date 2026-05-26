#!/usr/bin/env python3
"""Resave XGBoost model in modern format to eliminate warnings."""

import pickle
import joblib
import warnings
from pathlib import Path

# Suppress warnings during loading
warnings.filterwarnings("ignore")


def resave_model():
    """Load old pickle model and resave as JSON."""
    old_path = Path("models/xgboost_flood_risk.pkl")
    new_path = Path("models/xgboost_flood_risk.json")

    if not old_path.exists():
        print(f"❌ Model not found at {old_path}")
        return False

    print(f"📁 Loading model from {old_path}...")

    try:
        # Load the old model
        with open(old_path, "rb") as f:
            model = pickle.load(f)

        # Save in new format
        model.save_model(str(new_path))
        print(f"✅ Model saved to {new_path}")

        # Verify the new model works
        import xgboost as xgb

        test_model = xgb.Booster()
        test_model.load_model(str(new_path))
        print("✅ New model verified and working")

        # Update .env.production
        env_file = Path(".env.production")
        if env_file.exists():
            content = env_file.read_text()
            content = content.replace(
                "MODEL_PATH=models/xgboost_flood_risk.pkl",
                "MODEL_PATH=models/xgboost_flood_risk.json",
            )
            env_file.write_text(content)
            print("✅ Updated .env.production with new model path")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = resave_model()
    exit(0 if success else 1)
