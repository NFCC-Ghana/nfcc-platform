# CivicFlood AI
## AI-Powered Community Flood Intelligence Platform for Ghana

### Overview
CivicFlood AI is an AI-powered flood early warning system built specifically for Ghana. It combines satellite rainfall data (CHIRPS), river forecasts (GloFAS), and community WhatsApp reports to produce explainable flood risk predictions with impact estimates.

### Features
- 🌧️ **Flood Risk Prediction** - XGBoost model (R²=0.993)
- 🧠 **Explainable AI** - SHAP-based plain English explanations
- 📱 **Community Intelligence** - Validate citizen flood reports
- 📊 **Impact Estimation** - Population, schools, roads, health facilities
- 📈 **Timeline Forecast** - 7-day risk outlook
- 🇬🇭 **Ghana-Specific** - Accra districts, Akosombo/Bagre dams

### Built On
- **NFCC Platform** - Production flood intelligence system
- **FastAPI** - Backend API
- **Streamlit** - Interactive dashboard
- **XGBoost** - ML model (R²=0.993)
- **SHAP** - Explainable AI

### Datasets
| Dataset | Source | Use |
|---------|--------|-----|
| CHIRPS rainfall | UCSB | Precipitation data |
| GloFAS discharge | ECMWF | River levels |
| Ghana districts | Open Data | Geographic boundaries |
| OSM Ghana | OpenStreetMap | Infrastructure mapping |

### Team
- Youth in AI Ghana
- 6 engineers
- AI, geospatial, community engagement

### Ghana AI Innovation Challenge 2026
**Category:** Public Services - Disaster Management
**Submission:** July 1st, 2026
