#!/usr/bin/env bash
# Production startup script - SAFE and NON-BREAKING

set -Eeuo pipefail

echo "🚀 Starting NFCC Flood Alert Platform (Production Mode)"
echo "========================================================"

# Force production environment
export NFCC_ENV=production
export ENVIRONMENT=production

# Validate environment first (non-breaking)
echo ""
echo "🔍 Validating environment configuration..."
python scripts/validate_env.py

# Load environment variables safely
echo ""
echo "📁 Loading environment variables..."
set -o allexport
source .env.production
set +o allexport

echo "✅ Environment loaded:"
echo "   NFCC_ENV=${NFCC_ENV:-not set}"
echo "   ENVIRONMENT=${ENVIRONMENT:-not set}"
echo "   WhatsApp: ${ENABLE_WHATSAPP:-true}"

# Start the server (existing working configuration)
echo ""
echo "🚀 Starting production server..."
echo "========================================================"

exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level ${LOG_LEVEL:-info} \
    --access-log
