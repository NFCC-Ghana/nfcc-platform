#!/usr/bin/env python3
"""Standardize model to joblib format only."""

import pickle
from pathlib import Path

import joblib


def standardize_model():
    """Convert any model format to joblib."""

    pkl_path = Path("models/xgboost_flood_risk.pkl")
    joblib_path = Path("models/xgboost_flood_risk.joblib")

    if pkl_path.exists():
        try:
            with open(pkl_path, "rb") as f:
                model = pickle.load(f)
            joblib.dump(model, joblib_path)
            print(f"✅ Converted {pkl_path} -> {joblib_path}")
        except Exception as e:
            print(f"❌ Failed to convert: {e}")
    elif joblib_path.exists():
        print(f"✅ Joblib model already exists: {joblib_path}")
    else:
        print("❌ No model found")
        return False

    # Test load
    test_model = joblib.load(joblib_path)
    print(f"✅ Model verified: {type(test_model)}")
    return True


if __name__ == "__main__":
    standardize_model()
