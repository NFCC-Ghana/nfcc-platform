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

| Secret name              | Cloud Run env var         |
|--------------------------|----------------------------|
| `twilio-account-sid`     | `TWILIO_ACCOUNT_SID`       |
| `twilio-auth-token`      | `TWILIO_AUTH_TOKEN`        |
| `nfcc-api-key`           | `API_KEY`                  |
| `telegram-bot-token`     | `TELEGRAM_BOT_TOKEN`       |
| `telegram-webhook-secret`| `TELEGRAM_WEBHOOK_SECRET`  |
| `dahiti-api-key`         | `DAHITI_API_KEY`           |
| `reliefweb-appname`      | `RELIEFWEB_APPNAME`        |

**Note on writing secrets from PowerShell**: piping a string directly to
`gcloud secrets versions add ... --data-file=-` (`$value | & gcloud ...`)
silently prepends a UTF-8 BOM and appends a CRLF - PowerShell's pipe-to-
stdin behavior, not a gcloud quirk. This corrupted all four Twilio/
Telegram secrets on first attempt and broke webhook signature validation
in a way that looked like a wrong credential. Write to a temp file first
with `[System.IO.File]::WriteAllText($path, $value, (New-Object
System.Text.UTF8Encoding $false))` (no BOM, no trailing newline), then
`--data-file=$path`.

Wired in with `--update-secrets=TWILIO_ACCOUNT_SID=twilio-account-sid:latest,...`
on `gcloud run services update`. The Cloud Run service's runtime identity
(the project's default compute service account,
`355353600602-compute@developer.gserviceaccount.com`) needs
`roles/secretmanager.secretAccessor` on each secret - already granted.

**Telegram setup** (src/api/routes/telegram_webhook.py) - a second,
always-free citizen-reporting channel added alongside WhatsApp because
Telegram's Bot API has no trial/billing restriction anywhere, unlike
Twilio:
1. Message `@BotFather` on Telegram, `/newbot`, get a bot token.
2. Generate a random webhook secret (any string - e.g. `openssl rand -hex 20`).
3. Store both in Secret Manager under the names above, wire them onto
   the Cloud Run service the same way as the Twilio secrets.
4. Register the webhook URL with Telegram (one-time, from any machine
   with the token, not a Cloud Run env step):
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://nfcc-platform-355353600602.europe-west1.run.app/webhooks/telegram" \
     -d "secret_token=<the same webhook secret from step 2>"
   ```

Non-secret config is set as plain env vars via `--update-env-vars`, currently:
`NFCC_ENV=production`, `ENVIRONMENT=production`.

**SMS and email are still genuinely disabled.** SMTP/email and Twilio SMS
were never functional even on Railway - the values there (`SMTP_USER`,
`SMTP_PASS`, `TWILIO_SMS_FROM`, some SMS recipients) were placeholder/
template text, not real credentials. Note also that Railway's variable
names (`SMTP_PASS`, `ALERT_EMAIL_FROM`) didn't even match what
`src/config/settings.py` reads (`SMTP_PASSWORD`, `SMTP_FROM`) - if/when real
SMTP credentials are added, set them under the names `settings.py` expects,
not the old Railway names.

**WhatsApp and Telegram outbound alerts are real and live**, not just
inbound reporting. Real per-district recipients come from
`src/database/channel_subscriptions_db.py` - a citizen replies "ALERTS ON
\<district\>" in the same chat they report floods from
(`src/community/alert_subscription_commands.py`), and
`WhatsAppAlertProvider`/`TelegramAlertProvider` genuinely query that table
on every real alert send. Neither provider requires a static recipient
list to be considered usable any more (`settings.get_provider_status()`
only checks credentials) - `WHATSAPP_RECIPIENTS`/`TWILIO_WHATSAPP_FROM` are
now optional and additive: set them only if you want specific numbers
(e.g. a NADMO/GMET duty phone) to receive every alert regardless of who's
subscribed, unioned with the real dynamic subscriber list:
```bash
gcloud run services update nfcc-platform --region=europe-west1 \
  --update-env-vars="TWILIO_WHATSAPP_FROM=whatsapp:+14155238886,ALERT_WHATSAPP_RECIPIENTS=+233244714242"
```

One real constraint specific to WhatsApp Sandbox (not Telegram, which has
none): each recipient - static or dynamically subscribed - must have
already sent the sandbox's join code to `whatsapp:+14155238886` before
messages deliver to them, and sandbox sessions can expire and need
repeating. This is why Telegram (`t.me/CivicFlood_Bot`) exists as a second
channel: no join step, no billing tier, works for anyone the moment they
send the bot one message.

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
