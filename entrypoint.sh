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

exec litestream replicate -config /app/litestream.yml -restore-if-db-not-exists \
  -exec "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 4"
