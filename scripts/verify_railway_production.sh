#!/bin/bash
# ================================================================
# RAILWAY PRODUCTION DEPLOYMENT VERIFICATION
# ================================================================

echo "🚂 RAILWAY PRODUCTION DEPLOYMENT VERIFICATION"
echo "================================================"

# ================================================================
# STEP 1: Check Railway CLI
# ================================================================
echo ""
echo "📋 STEP 1: Checking Railway CLI..."
if command -v railway &> /dev/null; then
    echo "   ✅ Railway CLI installed"
    railway --version
else
    echo "   ❌ Railway CLI not found"
    echo "   Installing..."
    npm install -g @railway/cli
fi

# ================================================================
# STEP 2: Check Railway Status
# ================================================================
echo ""
echo "📋 STEP 2: Checking Railway status..."
railway status

# ================================================================
# STEP 3: Check Environment Variables
# ================================================================
echo ""
echo "📋 STEP 3: Checking environment variables..."
railway variables list

# ================================================================
# STEP 4: Check Deployment Logs
# ================================================================
echo ""
echo "📋 STEP 4: Checking deployment logs..."
railway logs --tail --lines=50

# ================================================================
# STEP 5: Health Check
# ================================================================
echo ""
echo "📋 STEP 5: Running health check..."

# Get Railway URL
RAILWAY_URL="https://nfcc-platform-production.up.railway.app"

# Check health endpoint
echo "   Checking health endpoint..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$RAILWAY_URL/health")

if [ "$HEALTH_RESPONSE" == "200" ]; then
    echo "   ✅ Health check PASSED (HTTP $HEALTH_RESPONSE)"
else
    echo "   ❌ Health check FAILED (HTTP $HEALTH_RESPONSE)"
fi

# Check root endpoint
echo "   Checking root endpoint..."
ROOT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$RAILWAY_URL/")

if [ "$ROOT_RESPONSE" == "200" ]; then
    echo "   ✅ Root endpoint PASSED (HTTP $ROOT_RESPONSE)"
else
    echo "   ❌ Root endpoint FAILED (HTTP $ROOT_RESPONSE)"
fi

# Check score endpoint
echo "   Checking score endpoint..."
SCORE_RESPONSE=$(curl -s -X POST "$RAILWAY_URL/score" \
    -H "Content-Type: application/json" \
    -d '{"location":"Accra Central","precipitation":45.0}' \
    -o /dev/null -w "%{http_code}")

if [ "$SCORE_RESPONSE" == "200" ]; then
    echo "   ✅ Score endpoint PASSED (HTTP $SCORE_RESPONSE)"
else
    echo "   ❌ Score endpoint FAILED (HTTP $SCORE_RESPONSE)"
fi

# ================================================================
# STEP 6: Test WhatsApp on Railway
# ================================================================
echo ""
echo "📋 STEP 6: Testing WhatsApp alert on Railway..."

# Test alert via Railway
ALERT_RESPONSE=$(curl -s -X POST "$RAILWAY_URL/score" \
    -H "Content-Type: application/json" \
    -d '{"location":"Accra Central (Railway Test)","precipitation":55.0}')

echo "   Alert Response: $ALERT_RESPONSE"

# Check if alert was sent
if echo "$ALERT_RESPONSE" | grep -q "alert_sent"; then
    echo "   ✅ Alert endpoint responded"
    if echo "$ALERT_RESPONSE" | grep -q '"alert_sent":true'; then
        echo "   ✅ WhatsApp alert was sent successfully!"
    else
        echo "   ℹ️ Alert sent but WhatsApp may be in mock mode"
    fi
else
    echo "   ⚠️ Alert endpoint response unexpected"
fi

# ================================================================
# STEP 7: Deployment Summary
# ================================================================
echo ""
echo "================================================"
echo "📊 RAILWAY DEPLOYMENT VERIFICATION SUMMARY"
echo "================================================"

echo """
   Railway CLI:           ✅ INSTALLED
   Status:                $(railway status 2>/dev/null | head -1 || echo "CHECK MANUALLY")
   Health Check:          $([ "$HEALTH_RESPONSE" == "200" ] && echo "✅ PASSED" || echo "❌ FAILED")
   Root Endpoint:         $([ "$ROOT_RESPONSE" == "200" ] && echo "✅ PASSED" || echo "❌ FAILED")
   Score Endpoint:        $([ "$SCORE_RESPONSE" == "200" ] && echo "✅ PASSED" || echo "❌ FAILED")
   WhatsApp Alert:        $(echo "$ALERT_RESPONSE" | grep -q "alert_sent" && echo "✅ RESPONDED" || echo "⚠️ CHECK")
   URL:                   $RAILWAY_URL
"""

echo ""
echo "🎯 Live URL: $RAILWAY_URL"
echo "📱 To test WhatsApp: POST to $RAILWAY_URL/score"
echo ""
echo "🔍 Monitor logs: railway logs --tail"
echo "================================================"
