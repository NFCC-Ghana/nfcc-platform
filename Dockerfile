FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ gdal-bin libgdal-dev libproj-dev libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create dummy model directly (no data files required)
RUN python -c "
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

# Create dummy training data
X_dummy = np.random.rand(100, 6)
y_dummy = np.random.rand(100)

# Train dummy model
model = RandomForestRegressor(n_estimators=10, random_state=42)
model.fit(X_dummy, y_dummy)

# Save model
import os
os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/xgboost_flood_risk.pkl')
print('✅ Dummy model created at models/xgboost_flood_risk.pkl')
"

# Use Railway's PORT environment variable
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
