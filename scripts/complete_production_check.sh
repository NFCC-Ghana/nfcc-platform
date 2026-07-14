#!/bin/bash
# ================================================================
# COMPLETE PRODUCTION CHECK
# ================================================================

echo "🔍 CIVICFLOOD AI - COMPLETE PRODUCTION CHECK"
echo "================================================"
echo ""

# 1. Validate WhatsApp Production
echo "📱 1. Validating WhatsApp Production..."
python scripts/validate_whatsapp_production.py
echo ""

# 2. Verify Railway Deployment
echo "🚂 2. Verifying Railway Deployment..."
./scripts/verify_railway_production.sh
echo ""

# 3. Create Demo Backup
echo "📹 3. Creating Demo Backup..."
./scripts/create_demo_backup.sh
echo ""

echo "✅ COMPLETE PRODUCTION CHECK FINISHED!"
echo "================================================"
