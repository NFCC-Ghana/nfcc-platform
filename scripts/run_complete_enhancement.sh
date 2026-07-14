#!/bin/bash
# ================================================================
# COMPLETE ENHANCEMENT EXECUTION SCRIPT
# ================================================================

echo "🚀 CIVICFLOOD AI - COMPLETE ENHANCEMENT"
echo "================================================"

# Step 1: Verify environment
echo ""
echo "📋 Step 1: Verifying environment..."
conda activate nfcc
python --version
echo "✅ Environment verified"

# Step 2: Test imports
echo ""
echo "🧪 Step 2: Testing imports..."
python -c "
import sys
sys.path.insert(0, '.')

print('Testing imports...')
try:
    from src.hydrology.weather_forecast import weather_forecast
    print('✅ weather_forecast')
except Exception as e:
    print(f'❌ weather_forecast: {e}')

try:
    from src.alerts.enhanced_alert_network import enhanced_alert_network
    print('✅ enhanced_alert_network')
except Exception as e:
    print(f'❌ enhanced_alert_network: {e}')

try:
    from src.alerts.subscriptions import subscription_manager
    print('✅ subscription_manager')
except Exception as e:
    print(f'❌ subscription_manager: {e}')

print('✅ All imports tested!')
"

# Step 3: Create directories
echo ""
echo "📁 Step 3: Creating directories..."
mkdir -p data/forecast_cache
mkdir -p data/alerts
echo "✅ Directories created"

# Step 4: Run dashboard
echo ""
echo "🚀 Step 4: Starting dashboard..."
echo "   Dashboard will start on port 8501"
echo "   Press Ctrl+C to stop"
echo ""

fuser -k 8501/tcp 2>/dev/null || true
streamlit run hackathon/app/pages/dashboard_enhanced.py --server.port 8501
