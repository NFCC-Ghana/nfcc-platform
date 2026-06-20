"""
CivicFlood AI - Minimal Test App
This is a minimal Streamlit app to test if Streamlit Cloud works.
"""

import streamlit as st

st.set_page_config(
    page_title="CivicFlood AI - Test",
    page_icon="🌊",
    layout="wide"
)

st.title("🌊 CivicFlood AI - Test App")
st.markdown("### If you can see this, Streamlit Cloud is working!")
st.success("✅ Deployment successful!")
st.info("📱 Now we can add the full dashboard.")
st.markdown("---")
st.markdown("🔗 Backend API: https://nfcc-platform-production.up.railway.app")

if __name__ == "__main__":
    pass
