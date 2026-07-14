#!/bin/bash
echo "🚀 Starting CivicFlood AI Demo"
echo "================================="
echo ""
echo "Starting API on port 8000..."
export ENVIRONMENT=production
export ALERT_DRY_RUN=false
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
sleep 3
echo "✅ API started: http://localhost:8000"
echo ""
echo "Starting Dashboard on port 8501..."
streamlit run hackathon/app/pages/dashboard_enhanced.py --server.port 8501 &
echo "✅ Dashboard started: http://localhost:8501"
echo ""
echo "📱 WhatsApp is enabled!"
echo "🌊 CivicFlood AI is ready!"
echo ""
echo "Press Ctrl+C to stop all services"
wait
