#!/bin/bash
echo "🚀 Starting Render deployment..."
echo "📦 Installing required packages..."
pip install --upgrade pip
pip install streamlit==1.46.0 folium==0.19.0 streamlit-folium==0.24.0
pip install -r requirements.txt
echo "✅ Installation complete!"
echo "🚀 Starting Streamlit..."
streamlit run hackathon/app/pages/dashboard.py --server.port $PORT --server.address 0.0.0.0
