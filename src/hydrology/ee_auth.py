"""Shared Google Earth Engine authentication.

Was previously duplicated as scripts/daily_chirps_pull.py's own
initialize_earth_engine() function - src/hydrology/sentinel_processor.py
called bare ee.Initialize() instead (no service account, no project),
which silently fails in any non-interactive environment (Cloud Run, CI)
and made it fall back to fabricated random flood-detection numbers
instead of the real Sentinel-1 satellite analysis it's built to do.
"""

import json
import logging
import os

import ee

logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GEE_PROJECT_ID", "nfcc-earth-engine-2026")


def initialize_earth_engine(project_id: str = PROJECT_ID) -> bool:
    """Authenticate to Earth Engine. Returns True on success, False on
    failure (never raises) - callers should fall back gracefully rather
    than crash, the same way the rest of this app treats every other
    external data source.

    In CI/Cloud Run (and any environment with no interactive login),
    GEE_SERVICE_ACCOUNT_KEY holds the full JSON key of a GCP service
    account with Earth Engine access - see docs/GEE_SETUP.md for how to
    create one and wire it in. Locally, an engineer instead runs
    `earthengine authenticate` once, which stores a token ee.Initialize()
    picks up on its own with no key material needed here.
    """
    key_json = os.getenv("GEE_SERVICE_ACCOUNT_KEY")
    try:
        if key_json:
            info = json.loads(key_json)
            credentials = ee.ServiceAccountCredentials(
                info["client_email"], key_data=key_json
            )
            ee.Initialize(credentials, project=project_id)
            logger.info(
                "Earth Engine initialized with service account: %s",
                info["client_email"],
            )
        else:
            ee.Initialize(project=project_id)
            logger.info("Earth Engine initialized with project: %s", project_id)
        return True
    except Exception as exc:
        logger.warning("Earth Engine initialization failed: %s", exc)
        return False
