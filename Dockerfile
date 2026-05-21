FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ gdal-bin libgdal-dev libproj-dev libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p models logs data/processed

# Generate dummy model (REQUIRED for API startup)
RUN python -c "
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import os

print('Creating dummy flood risk model for Railway deployment...')
X_dummy = np.random.rand(100, 6)
y_dummy = np.random.rand(100)
model = RandomForestRegressor(n_estimators=10, random_state=42)
model.fit(X_dummy, y_dummy)
os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/xgboost_flood_risk.pkl')
print('✅ Dummy model created at models/xgboost_flood_risk.pkl')
"

# Verify model exists (critical check)
RUN test -f models/xgboost_flood_risk.pkl && echo "✅ Model verified" || (echo "❌ Model missing" && exit 1)

# Generate dummy feature data (if needed by other parts of the app)
RUN python -c "
import pandas as pd
import numpy as np
import os

print('Creating dummy feature data...')
dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
df = pd.DataFrame({'date': dates})
for col in ['precipitation', 'roll_3d', 'roll_7d', 'roll_30d', 'cumulative', 'z_score', 'flood_risk_score']:
    df[col] = np.random.rand(len(dates)) * 100
os.makedirs('data/processed', exist_ok=True)
df.to_parquet('data/processed/accra_features_2024.parquet')
print('✅ Dummy feature data created at data/processed/accra_features_2024.parquet')
"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
