# Production Hosting: Google Cloud Run

Production moved off Railway (trial expired, service offline) to Google Cloud
Run, under the same GCP project already used for Earth Engine:
`nfcc-earth-engine-2026`.

**Live URL**: https://nfcc-platform-355353600602.europe-west1.run.app

## Redeploying after a code change

From the repo root, with the `gcloud` CLI authenticated against
`nfcc-earth-engine-2026` and a service account (or user) that has the roles
listed below:

```bash
gcloud builds submit --config=cloudbuild.yaml .
gcloud run deploy nfcc-platform \
  --image=gcr.io/nfcc-earth-engine-2026/nfcc-platform \
  --region=europe-west1
```

`cloudbuild.yaml` builds `Dockerfile.prod` explicitly (Cloud Run's
`--source` auto-build only looks for a file literally named `Dockerfile`,
which this repo doesn't have at the root).

## Secrets and configuration

Real secrets (Twilio auth token, the API key) live in Secret Manager, not as
plain env vars:

| Secret name           | Cloud Run env var    |
|------------------------|-----------------------|
| `twilio-account-sid`   | `TWILIO_ACCOUNT_SID`  |
| `twilio-auth-token`    | `TWILIO_AUTH_TOKEN`   |
| `nfcc-api-key`         | `API_KEY`             |

Wired in with `--update-secrets=TWILIO_ACCOUNT_SID=twilio-account-sid:latest,...`
on `gcloud run services update`. The Cloud Run service's runtime identity
(the project's default compute service account,
`355353600602-compute@developer.gserviceaccount.com`) needs
`roles/secretmanager.secretAccessor` on each secret - already granted.

Non-secret config is set as plain env vars via `--update-env-vars`, currently:
`NFCC_ENV=production`, `ENVIRONMENT=production`.

**All external alert channels (WhatsApp, SMS, email) are currently
disabled** - `GET /health` reports `"whatsapp": {"status": "disabled"}` and
this is intentional, not a bug:

- SMTP/email and Twilio SMS were never functional even on Railway - the
  values there (`SMTP_USER`, `SMTP_PASS`, `TWILIO_SMS_FROM`, some SMS
  recipients) were placeholder/template text, not real credentials. Note also
  that Railway's variable names (`SMTP_PASS`, `ALERT_EMAIL_FROM`) didn't even
  match what `src/config/settings.py` reads (`SMTP_PASSWORD`, `SMTP_FROM`) -
  if/when real SMTP credentials are added, set them under the names
  `settings.py` expects, not the old Railway names.
- WhatsApp's `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN` secrets *are* real and
  wired up (see table above), but were left disconnected after testing showed
  the Twilio account behind them has no free trial units and Twilio does not
  offer free trials in Ghana at all - sending anything (even sandbox
  WhatsApp messages) requires an upgraded/paid Twilio account. `whatsapp` is
  disabled by simply not setting `TWILIO_WHATSAPP_FROM` /
  `ALERT_WHATSAPP_RECIPIENTS` as env vars (settings.py treats empty
  recipients as disabled), rather than by removing the secrets, so
  re-enabling later - once there's budget for a paid Twilio account - is just
  adding those two env vars back:
  ```bash
  gcloud run services update nfcc-platform --region=europe-west1 \
    --update-env-vars="TWILIO_WHATSAPP_FROM=whatsapp:+14155238886,ALERT_WHATSAPP_RECIPIENTS=+233244714242"
  ```
  Twilio's WhatsApp sandbox uses a shared number
  (`whatsapp:+14155238886`), not a purchased one - each recipient must send
  the sandbox's join code to it from WhatsApp before messages will deliver
  to them, and sandbox join codes/sessions can expire and need repeating.

## IAM roles needed by a deploying identity

The `nfcc-cloudrun-deployer` service account (or an equivalent principal)
needs, on the `nfcc-earth-engine-2026` project:

- Cloud Run Admin
- Service Account User
- Artifact Registry Administrator
- Cloud Build Editor
- Storage Admin (Cloud Build's staging bucket)
- Service Usage Admin (enabling APIs, `gcloud services list`)
- Secret Manager Admin (creating/updating secrets)

## Making the service public

`gcloud run deploy`'s `--allow-unauthenticated` flag (or, after the fact,
`gcloud run services add-iam-policy-binding ... --member=allUsers
--role=roles/run.invoker`) is required for the API to be reachable without an
auth token - this is a public flood-alert API meant to be hit by dashboards,
WhatsApp bots, and district officials, same as it was on Railway. This can
also be toggled from the console: Cloud Run -> service -> **Security** tab ->
**Allow public access**.

## Health check

`GET /health` returns provider/model/rate-limit status (backed by
`src/api/health.py`'s router, not a duplicate route - a duplicate inline
`/health` in `src/api/main.py` used to shadow this and was removed).
`GET /health/live` and `GET /health/ready` are separate liveness/readiness
probes.
