"""SHAP Explainability Module - Show WHY risk exists."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_explainability(district: str, risk_score: float) -> None:
    """Render SHAP explainability panel."""

    st.markdown("### 🧠 Why This Risk? (SHAP Explainability)")

    # Simulated SHAP values (in production: from API)
    factors = {
        "Rainfall (30-day accumulation)": 35,
        "Soil Saturation": 25,
        "River Level": 15,
        "Poor Drainage": 15,
        "Historical Flood Similarity": 10,
    }

    # Create DataFrame
    df = pd.DataFrame(
        {"Factor": list(factors.keys()), "Contribution": list(factors.values())}
    )

    # Sort descending
    df = df.sort_values("Contribution", ascending=False)

    # Create bar chart
    fig = px.bar(
        df,
        x="Contribution",
        y="Factor",
        orientation="h",
        title="Risk Factor Contributions",
        color="Contribution",
        color_continuous_scale="RdYlGn_r",
        text=df["Contribution"].apply(lambda x: f"+{x}%"),
    )

    fig.update_layout(
        height=300,
        xaxis_title="Contribution to Risk (%)",
        yaxis_title="",
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary
    top_factor = df.iloc[0]["Factor"]
    st.info(
        f"💡 Key driver: **{top_factor}** contributes {df.iloc[0]['Contribution']}% to the risk score."
    )
