# syntax=docker/dockerfile:1

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir \
    -r requirements.txt \
    scikit-learn \
    pandas \
    numpy \
    pyarrow \
    joblib \
    xgboost

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p models logs data/processed

# ============================================
# Create fallback model for Railway
# ============================================
RUN python - <<EOF
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from pathlib import Path

print("Creating fallback flood model...")

X_dummy = np.random.rand(100, 6)
y_dummy = np.random.rand(100)

model = RandomForestRegressor(
    n_estimators=10,
    random_state=42
)

model.fit(X_dummy, y_dummy)

model_path = Path("models/xgboost_flood_risk.pkl")
model_path.parent.mkdir(parents=True, exist_ok=True)

joblib.dump(model, model_path)

print(f"✅ Model created at {model_path}")
EOF

# Verify model exists
RUN test -f models/xgboost_flood_risk.pkl \
    && echo "✅ Model verified" \
    || (echo "❌ Model missing" && exit 1)

# ============================================
# Create dummy feature dataset
# ============================================
RUN python - <<EOF
import pandas as pd
import numpy as np
from pathlib import Path

print("Creating dummy feature dataset...")

dates = pd.date_range(
    "2024-01-01",
    "2024-12-31",
    freq="D"
)

df = pd.DataFrame({"date": dates})

for col in [
    "precipitation",
    "roll_3d",
    "roll_7d",
    "roll_30d",
    "cumulative",
    "z_score",
    "flood_risk_score"
]:
    df[col] = np.random.rand(len(dates)) * 100

output_path = Path("data/processed/accra_features_2024.parquet")
output_path.parent.mkdir(parents=True, exist_ok=True)

df.to_parquet(output_path)

print(f"✅ Dataset created at {output_path}")
EOF

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]