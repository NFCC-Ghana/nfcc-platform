# NFCC Live Data Sources

This document describes the real-time ingestion pipelines for CHIRPS rainfall,
GPM IMERG, and Ghana river gauge data.

## Overview

| Source | Module | Latency | Schedule | Output |
|--------|--------|---------|----------|--------|
| CHIRPS Daily | `src/ingestion/chirps_live.py` | ~1 day | Daily 08:00 UTC | `data/raw/chirps/` |
| GPM IMERG | `src/ingestion/gpm_live.py` | ~4 hours | Every 4 hours | `data/raw/gpm/` |
| River Gauges (HSD) | `src/ingestion/river_gauges.py` | Near real-time | Every 15 min | `data/raw/river_gauges/` |

Quality reports are written to `reports/data_quality/`.
Health dashboard state is written to `reports/data_health/latest.json`.

## CHIRPS (Climate Hazards Group InfraRed Precipitation with Station)

**Dataset:** `UCSB-CHG/CHIRPS/DAILY` via Google Earth Engine

**Region:** Accra bounding box `[-0.35, 5.45, 0.05, 5.75]`

### Features

- Automated daily fetch (yesterday UTC by default)
- Historical backfill over arbitrary date ranges
- Pixel-count and non-negative value validation
- Graceful handling when images are unavailable

### Usage

```python
from src.ingestion.chirps_live import ChirpsLiveIngester

ingester = ChirpsLiveIngester()
result = ingester.fetch_daily()          # single day
backfill = ingester.backfill("2024-01-01", "2024-12-31")
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEE_PROJECT_ID` | `nfcc-earth-engine-2026` | Google Earth Engine project |

### Prerequisites

```bash
earthengine authenticate
```

## GPM IMERG (Integrated Multi-satellitE Retrievals for GPM)

**Dataset:** `NASA/GPM_L3/IMERG_V07` via Google Earth Engine

**Product:** Final Run half-hourly precipitation

**Latency:** ~4 hours (configurable via `GPM_LATENCY_HOURS`)

### Features

- Near-real-time latest granule fetch
- Daily aggregation (sum of half-hourly rates)
- Automatic 4-hour refresh via scheduler
- Quality monitoring with pixel validation

### Usage

```python
from src.ingestion.gpm_live import GpmLiveIngester

ingester = GpmLiveIngester()
latest = ingester.fetch_latest()         # most recent granule
daily = ingester.fetch_daily("2026-05-18")
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEE_PROJECT_ID` | `nfcc-earth-engine-2026` | GEE project |
| `GPM_LATENCY_HOURS` | `4` | Latency offset for final-run granules |

## Ghana River Gauges (Hydrological Services Department)

**API:** HSD REST API (configurable base URL)

**Stations:** Akosombo, Kpong, Bui Dam, Weija, Nsawam (defaults when API unavailable)

### Features

- Real-time water level monitoring
- Flow rate (discharge) tracking
- Cached fallback on API failure (graceful degradation)
- Per-fetch quality reports

### Usage

```python
from src.ingestion.river_gauges import RiverGaugeClient

client = RiverGaugeClient()
levels = client.fetch_gauge_readings()
flows = client.fetch_flow_rates(station_ids=["akosombo", "kpong"])
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HSD_API_BASE_URL` | `https://api.hsd.gov.gh/v1` | HSD API base URL |
| `HSD_API_KEY` | _(empty)_ | Bearer token for authentication |
| `HSD_API_TIMEOUT_SECONDS` | `30` | HTTP request timeout |

### Expected API Response

```json
{
  "stations": [
    {
      "id": "akosombo",
      "name": "Akosombo",
      "river": "Volta",
      "water_level_m": 74.5,
      "flow_rate_m3s": 1100,
      "timestamp": "2026-05-19T10:00:00Z"
    }
  ]
}
```

## Scheduler

**Module:** `src/ingestion/scheduler.py`

Uses APScheduler to orchestrate all pipelines:

| Job ID | Trigger | Action |
|--------|---------|--------|
| `chirps_daily` | Cron 08:00 UTC | Daily CHIRPS fetch |
| `gpm_refresh` | Every 4 hours | Latest IMERG granule |
| `river_gauges_poll` | Every 15 minutes | HSD gauge readings |
| `data_health_dashboard` | Every 30 minutes | Refresh health dashboard |

### Usage

```python
from src.ingestion.scheduler import IngestionScheduler

scheduler = IngestionScheduler()
scheduler.start()

# Manual trigger
scheduler.run_job_now("chirps")
scheduler.run_job_now("gpm")
scheduler.run_job_now("river_gauges")

scheduler.stop()
```

## Data Health Monitoring

**Module:** `src/monitoring/data_health.py`

### Staleness Thresholds

| Source | Default Threshold |
|--------|-------------------|
| CHIRPS | 36 hours |
| GPM | 6 hours |
| River Gauges | 2 hours |

### Features

- Data quality monitoring dashboard (`reports/data_health/latest.json`)
- Alert triggering when data exceeds staleness thresholds
- Graceful degradation state reporting
- Forecasting impact assessment when sources are unavailable

### Usage

```python
from src.monitoring.data_health import DataHealthMonitor

monitor = DataHealthMonitor()
dashboard = monitor.get_dashboard()
alerts = monitor.check_delays()
state = monitor.get_degradation_state()
```

## Relationship to Existing Scripts

The live ingestion modules complement (but do not replace) existing tooling:

- `scripts/daily_chirps_pull.py` — standalone CLI used by GitHub Actions CI
- `src/data/ingestion/download_chirps.py` — annual historical time-series extraction

The scheduler can run alongside or instead of the GitHub Actions cron for local/production deployments.

## Testing

```bash
pytest tests/unit/test_ingestion.py -v
```

Tests mock Earth Engine and HTTP calls — no live credentials required. The ingestion
modules use lazy imports for `ee` and APScheduler so CI can collect tests without
`earthengine-api` installed (it is only needed for live GEE fetches at runtime).

**Note:** Other CI failures (for example `/health` model path, alert API typos) live
outside the ingestion modules and must be fixed separately on `develop`.
