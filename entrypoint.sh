#!/bin/sh
# Wraps the app's real startup command with Litestream so the two
# SQLite databases (see litestream.yml) survive Cloud Run's ephemeral
# container storage. `-restore-if-db-not-exists` restores each db from
# its GCS replica on a fresh container before the app ever touches an
# empty file (a no-op, not an error, on the very first deploy when no
# replica exists yet); `-exec` then runs the real app as a supervised
# child process while replication continues underneath it.
set -e

mkdir -p /app/data

# --proxy-headers --forwarded-allow-ips='*': without this, uvicorn
# trusts nothing but the raw TCP connection it sees - which, behind
# Cloud Run's front-end, is Cloud Run's own internal proxy, not the
# real caller. request.client.host (what slowapi's rate limiter keys
# on, src/api/auth.py) would silently return that same proxy address
# for every single request, meaning the rate limits added this session
# couldn't actually distinguish one client from another. Cloud Run
# containers are never directly internet-reachable - all traffic must
# already pass through Cloud Run's own front-end first - so trusting
# the immediate hop's X-Forwarded-For unconditionally is the standard,
# documented pattern for this specific topology, not a general "trust
# any proxy" weakening.
exec litestream replicate -config /app/litestream.yml -restore-if-db-not-exists \
  -exec "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4 --proxy-headers --forwarded-allow-ips='*'"
