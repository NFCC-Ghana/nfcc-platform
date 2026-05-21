FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ gdal-bin libgdal-dev libproj-dev libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure models directory exists
RUN mkdir -p models

# Create dummy model with explicit error handling
RUN python -c "
import sys
import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

try:
    # Create dummy training data
    X_dummy = np.random.rand(100, 6)
    y_dummy = np.random.rand(100)
    
    # Train dummy model
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X_dummy, y_dummy)
    
    # Save model
    joblib.dump(model, 'models/xgboost_flood_risk.pkl')
    print('✅ Dummy model created successfully')
except Exception as e:
    print(f'❌ Error creating dummy model: {e}')
    sys.exit(1)
"

# Test that the model file exists
RUN test -f models/xgboost_flood_risk.pkl && echo "✅ Model file verified" || (echo "❌ Model file missing" && exit 1)

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
