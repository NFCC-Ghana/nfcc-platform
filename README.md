# NFCC - National Flood Command Center

Flood early-warning platform for Ghana: automated risk assessment from
real rainfall, river/dam and satellite data, a human-in-the-loop alert
review queue, and WhatsApp/Telegram dissemination and citizen reporting.

## Components

| Part | Where | Hosted on |
|------|-------|-----------|
| FastAPI backend | `src/` (entry: `src/api/main.py`) | Google Cloud Run - see [docs/CLOUD_RUN_DEPLOY.md](docs/CLOUD_RUN_DEPLOY.md) |
| Operations dashboard (Streamlit) | `hackathon/app/pages/dashboard.py` | Streamlit Community Cloud |
| Scheduled jobs | `scripts/` + `.github/workflows/` | GitHub Actions (risk assessment, CHIRPS ingest, prediction verification, model validation) |
| Storage | SQLite in `data/`, replicated to GCS by Litestream (`litestream.yml`) | Cloud Run container + GCS |

## How an alert reaches people

1. `scripts/automated_risk_assessment.py` (scheduled) scores each tracked
   district and calls `POST /v1/alerts/assess`, which only **queues** a
   pending alert. Nothing is sent at this step.
2. A duty officer reviews it in the dashboard's Alert Review Queue and
   approves, dismisses, or later retracts it
   (`/v1/alerts/pending/{id}/approve|dismiss|cancel`). Real alerts can
   additionally require `ALERT_APPROVAL_KEY`.
3. Only an approval sends, through the configured providers
   (`src/alerts/providers/`), to citizens who subscribed per district.

`POST /score` and `/score/batch` are pure calculators. They never send.

## Local development

```bash
conda env create -f environment.yml     # or: python -m venv .venv
pip install -r requirements.txt -r requirements-dev.txt   # one command
uvicorn src.api.main:app --reload        # API on :8000, docs at /docs
streamlit run hackathon/app/pages/dashboard.py
pytest                                   # runs tests/ against a temp DB
```

Configuration comes from environment variables (see `.env.example`).
In `development` the API key defaults to `dev-key-for-testing-only`.
Production refuses to start without `API_KEY`.

## Further reading

- [docs/ONBOARDING.md](docs/ONBOARDING.md): environment setup
- [docs/CLOUD_RUN_DEPLOY.md](docs/CLOUD_RUN_DEPLOY.md): deploying, secrets
- [docs/data_sources.md](docs/data_sources.md): where each signal comes from
- [docs/forecast_fusion.md](docs/forecast_fusion.md): multi-source fusion
- [docs/api/](docs/api/): endpoint reference
