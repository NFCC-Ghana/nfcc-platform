#!/bin/bash
echo "🔍 Checking current versions..."
python -c "import streamlit; import folium; import streamlit_folium; print(f'Streamlit: {streamlit.__version__}'); print(f'Folium: {folium.__version__}'); print(f'Streamlit-Folium: {streamlit_folium.__version__}')"

echo "📦 Installing compatible versions..."
pip install --upgrade streamlit==1.46.0 folium==0.20.0 streamlit-folium==0.25.0

echo "✅ Done! Restart your app."
