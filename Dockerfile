FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ gdal-bin libgdal-dev libproj-dev libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create required directories
RUN mkdir -p models logs data/processed

# Create dummy model
RUN python -c "
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

X_dummy = np.random.rand(100, 6)
y_dummy = np.random.rand(100)
model = RandomForestRegressor(n_estimators=10, random_state=42)
model.fit(X_dummy, y_dummy)
joblib.dump(model, 'models/xgboost_flood_risk.pkl')
print('✅ Dummy model created')
"

# Create dummy feature data (if needed by API at import time)
RUN python -c "
import pandas as pd
import numpy as np
dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
df = pd.DataFrame({'date': dates})
for col in ['precipitation', 'roll_3d', 'roll_7d', 'roll_30d', 'cumulative', 'z_score', 'flood_risk_score']:
    df[col] = np.random.rand(len(dates)) * 100
df.to_parquet('data/processed/accra_features_2024.parquet')
print('✅ Dummy feature data created')
"

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
