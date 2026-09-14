# Google Earth Engine Authentication

The daily CHIRPS rainfall ingestion (`scripts/daily_chirps_pull.py`, run by
`.github/workflows/daily_chirps.yml`) needs to authenticate to Google Earth
Engine (GEE) under the `nfcc-earth-engine-2026` GCP project. There are two
separate setups: one for CI (no human present to log in), one for a local
engineer's machine.

## CI: service account (one-time setup, needs GCP project access)

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and
   select (or create) the `nfcc-earth-engine-2026` project.
2. **Enable the Earth Engine API** for the project, if not already enabled:
   [console.cloud.google.com/apis/library/earthengine.googleapis.com](https://console.cloud.google.com/apis/library/earthengine.googleapis.com)
3. **Register the project for Earth Engine** (only needed once per GCP
   project): [code.earthengine.google.com/register](https://code.earthengine.google.com/register) →
   choose "Google Cloud project" → select `nfcc-earth-engine-2026` → pick a
   non-commercial/nonprofit use case (this is a public early-warning system).
4. **Create a service account**: IAM & Admin → Service Accounts → Create
   Service Account (e.g. `nfcc-chirps-ingestion@nfcc-earth-engine-2026.iam.gserviceaccount.com`).
   No project-level IAM role is required for Earth Engine access itself — see
   the next step.
5. **Register that service account for Earth Engine access**: still on
   [code.earthengine.google.com/register](https://code.earthengine.google.com/register)
   (or via `earthengine acl` for a specific asset), grant the service
   account's email Earth Engine access the same way you would a person's
   email — the CHIRPS collection this pulls from (`UCSB-CHG/CHIRPS/DAILY`)
   is a public EE dataset, so no extra per-dataset permission is needed once
   the account itself can use Earth Engine at all.
6. **Create a JSON key** for the service account: Service Accounts → (select
   it) → Keys → Add Key → Create new key → JSON. This downloads a `.json`
   file — treat it like a password, it's a live credential.
7. **Add it as a GitHub Actions secret**: in this repo, Settings → Secrets
   and variables → Actions → New repository secret →
   - Name: `GEE_SERVICE_ACCOUNT_KEY`
   - Value: the **entire contents** of the downloaded JSON file, pasted as-is
     (it's read as a JSON string by `initialize_earth_engine()` in
     `scripts/daily_chirps_pull.py`, which pulls `client_email` out of it
     automatically — no second secret needed for the email).
8. Delete the local copy of the JSON key file once it's in GitHub Secrets;
   don't commit it, don't leave it in Downloads.

Once the secret exists, `.github/workflows/daily_chirps.yml` picks it up
automatically (`GEE_SERVICE_ACCOUNT_KEY: ${{ secrets.GEE_SERVICE_ACCOUNT_KEY }}`)
and `initialize_earth_engine()` uses it instead of falling back to the
interactive-login path below.

## Local development: personal Earth Engine login

Each engineer authenticates with their own Google account instead of the
service account — this only has to be done once per machine:

```bash
conda activate nfcc
earthengine authenticate
# Opens a browser window; sign in with a Google account that has Earth
# Engine access (register one at https://code.earthengine.google.com/register
# if it doesn't already), then paste the confirmation code back into the
# terminal if prompted.
```

This stores a token under `~/.config/earthengine/` (or the OS equivalent),
which `ee.Initialize(project=PROJECT_ID)` picks up automatically with no
`GEE_SERVICE_ACCOUNT_KEY` needed locally — that env var should stay unset on
a dev machine.

## Verifying it works

```bash
python scripts/daily_chirps_pull.py --date 2026-05-18
```

A successful run logs `Google Earth Engine initialized with ...` and writes
a CSV under `data/raw/chirps/` plus a report under `reports/data_quality/`.
A `ModuleNotFoundError: No module named 'ee'` means `environment.yml` wasn't
used to (re)create the `nfcc` conda environment after `earthengine-api` was
added to it — recreate it with `conda env update -f environment.yml` or
`conda env create -f environment.yml --force`.
