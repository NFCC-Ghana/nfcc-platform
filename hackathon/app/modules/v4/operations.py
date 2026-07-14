"""Operations & Evacuation module."""

import streamlit as st


def render_operations(state):
    """Render the operations section."""
    st.markdown("## 🚗 Operations & Evacuation")
    st.caption("Shelters, evacuation routes, and resource status")

    st.markdown("### 🏛️ Emergency Shelters")
    st.success("**Accra High School** 🟢 OPEN")
    st.caption("📍 1.2 km • Capacity: 1,200")
    st.success("**Community Center** 🟢 OPEN")
    st.caption("📍 2.5 km • Capacity: 500")
    st.warning("**Trade Fair Centre** 🟡 PREPARING")
    st.caption("📍 4.0 km • Capacity: 2,000")

    st.markdown("### 🗺️ Safe Evacuation Routes")
    st.caption("Alajo → Accra High School")
    st.caption("Via: Ring Road • 15 min")
    st.caption("---")
    st.caption("Kaneshie → Community Center")
    st.caption("Via: Winneba Road • 20 min")
    st.caption("---")
    st.caption("Circle → Trade Fair Centre")
    st.caption("Via: Independence Avenue • 25 min")

    st.markdown("### 📦 Resource Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Rescue Boats", "3 🚤", "Ready")
        st.metric("Ambulances", "5 🚑", "Deployed")
    with col2:
        st.metric("Pumps", "10 💧", "Available")
        st.metric("Rescue Teams", "4 👥", "Active")
