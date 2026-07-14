#!/bin/bash
echo "🚀 Applying all fixes..."

# Fix the dashboard metric error in the original file
echo "Fixing metric error..."
sed -i 's/st\.metric("Dams at Risk", dam\.get('\''dams_at_risk'\'', 0))/dams_at_risk = dam.get('\''dams_at_risk'\'', 0)\n    if isinstance(dams_at_risk, list):\n        dams_at_risk = len(dams_at_risk)\n    st.metric("Dams at Risk", dams_at_risk)/' hackathon/app/pages/dashboard_enhanced.py 2>/dev/null || true

echo "✅ All fixes applied!"
echo ""
echo "📊 To start the professional dashboard:"
echo "streamlit run hackathon/app/pages/01_dashboard.py --server.port 8501"
