# CivicFlood AI Architecture

## System Overview
┌─────────────────────────────────────────────────────────────┐
│ CIVICFLOOD AI │
├─────────────────────────────────────────────────────────────┤
│ │
│ 📡 DATA SOURCES │
│ ├── CHIRPS rainfall (UCSB) │
│ ├── GloFAS discharge (ECMWF) │
│ ├── Google Flood Hub │
│ └── Community WhatsApp reports │
│ │
│ 🧠 AI ENGINE │
│ ├── Flood Explainer (SHAP) │
│ ├── Community Classifier (NLP) │
│ ├── Impact Estimator │
│ └── Timeline Predictor │
│ │
│ 🚨 OUTPUTS │
│ ├── Risk Score (0-100) │
│ ├── Plain English Explanation │
│ ├── Impact Estimate │
│ └── WhatsApp Alert │
│ │
└─────────────────────────────────────────────────────────────┘

text

## NFCC Integration
All AI modules leverage the existing NFCC production platform:
- `src/models/flood_risk.py` - XGBoost model
- `src/data/ingestion/chirps/` - Rainfall data
- `src/alerts/engine.py` - Alert dispatch

## Deployment
- **Backend:** Railway (https://nfcc-platform-production.up.railway.app)
- **Dashboard:** Local / Streamlit Cloud
- **Repository:** github.com/NFCC-Ghana/nfcc-platform
