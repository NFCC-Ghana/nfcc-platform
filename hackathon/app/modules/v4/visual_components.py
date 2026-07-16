"""
Visual Storytelling Components for CivicFlood AI
Phase 4: International-standard visual storytelling
Palantir/IBM-level professional visualization components
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
import math

# ============================================================
# PROGRESS BAR COMPONENTS
# ============================================================


def render_horizontal_progress_bar(
    value: float,
    max_value: float = 100,
    label: str = "",
    color: str = "#00cc00",
    height: int = 8,
    show_percentage: bool = True,
    show_emoji: bool = True,
) -> None:
    """
    Render a professional horizontal progress bar with label.
    """
    percentage = min(100, (value / max_value) * 100)

    emoji = "🟢" if percentage >= 70 else "🟡" if percentage >= 40 else "🔴"

    if label:
        if show_emoji:
            st.markdown(f"{emoji} **{label}**")
        else:
            st.markdown(f"**{label}**")

    html = f"""
    <div style="width: 100%; background-color: #f0f0f0; border-radius: 4px; height: {height}px; overflow: hidden;">
        <div style="width: {percentage}%; background-color: {color}; height: {height}px; border-radius: 4px; transition: width 0.5s ease;">
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if show_percentage:
        st.caption(f"{percentage:.0f}%")


def render_density_bar(
    value: float,
    max_value: float = 100,
    label: str = "",
    color: str = "#00cc00",
    show_value: bool = True,
) -> None:
    """Render a density-style progress bar with value display."""
    percentage = min(100, (value / max_value) * 100)

    if label:
        st.markdown(f"**{label}**")

    html = f"""
    <div style="width: 100%; background-color: #f0f0f0; border-radius: 4px; height: 20px; overflow: hidden; position: relative;">
        <div style="width: {percentage}%; background-color: {color}; height: 20px; border-radius: 4px; transition: width 0.5s ease;">
        </div>
        <span style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); font-size: 12px; font-weight: bold; color: #333;">
            {value:.0f}{"" if show_value else ""}
        </span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# METRIC CARDS
# ============================================================


def render_metric_card(
    value: Any,
    label: str,
    emoji: str = "",
    change: Optional[float] = None,
    change_label: str = "",
    color: str = "#333",
    size: str = "medium",
) -> None:
    """Render a professional metric card with optional trend indicator."""
    font_size = {"small": "18px", "medium": "24px", "large": "36px"}.get(size, "24px")

    if isinstance(value, (int, float)):
        if value >= 1_000_000:
            display_value = f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            display_value = f"{value/1_000:.1f}K"
        else:
            display_value = f"{value:,.0f}"
    else:
        display_value = str(value)

    html = f"""
    <div style="
        background: #ffffff;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 4px solid {color};
        margin-bottom: 8px;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-size: 14px; color: #666; font-weight: 500;">{label}</span>
                <div style="font-size: {font_size}; font-weight: 700; color: {color};">
                    {emoji} {display_value}
                </div>
            </div>
    """

    if change is not None:
        change_color = "#00cc00" if change >= 0 else "#ff0000"
        arrow = "↑" if change >= 0 else "↓"
        html += f"""
            <div style="text-align: right;">
                <span style="color: {change_color}; font-weight: 600; font-size: 14px;">
                    {arrow} {abs(change):.1f}%
                </span>
                <div style="font-size: 12px; color: #999;">{change_label}</div>
            </div>
        """

    html += """
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_impact_card(
    value: float, label: str, emoji: str = "", color: str = "#333", detail: str = ""
) -> None:
    """Render an impact card with visual emphasis."""
    if color == "auto" and isinstance(value, (int, float)):
        if value > 1000000:
            color = "#e53e3e"
        elif value > 500000:
            color = "#ed8936"
        else:
            color = "#38a169"

    if isinstance(value, (int, float)):
        if value >= 1_000_000:
            display_value = f"GH₵ {value/1_000_000:.2f}M"
        elif value >= 1_000:
            display_value = f"GH₵ {value/1_000:.1f}K"
        else:
            display_value = f"GH₵ {value:,.0f}"
    else:
        display_value = str(value)

    html = f"""
    <div style="
        background: #ffffff;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        border-bottom: 3px solid {color};
        margin-bottom: 8px;
    ">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 28px;">{emoji}</span>
            <div>
                <div style="font-size: 14px; color: #666; font-weight: 500;">{label}</div>
                <div style="font-size: 22px; font-weight: 700; color: {color};">
                    {display_value}
                </div>
                {f'<div style="font-size: 12px; color: #999;">{detail}</div>' if detail else ''}
            </div>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# VISUAL METRIC CARDS
# ============================================================


def render_visual_metric_card(
    value: float,
    label: str,
    emoji: str = "",
    color: str = "#333",
    max_value: float = 100,
    subtitle: str = "",
    show_bar: bool = True,
) -> None:
    """Render a visual metric card with integrated progress visualization."""
    percentage = min(100, (value / max_value) * 100)

    if not emoji:
        if percentage >= 70:
            emoji = "🟢"
        elif percentage >= 40:
            emoji = "🟡"
        else:
            emoji = "🔴"

    if isinstance(value, (int, float)):
        if value >= 1_000_000:
            display_value = f"{value/1_000_000:.2f}M"
        elif value >= 1_000:
            display_value = f"{value/1_000:.1f}K"
        else:
            display_value = f"{value:,.0f}"
    else:
        display_value = str(value)

    html = f"""
    <div style="
        background: #ffffff;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #f0f0f0;
        margin-bottom: 10px;
        transition: all 0.2s ease;
    ">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <span style="font-size: 28px; line-height: 1;">{emoji}</span>
            <div style="flex: 1;">
                <div style="font-size: 14px; font-weight: 600; color: #444;">
                    {label}
                </div>
                <div style="font-size: 22px; font-weight: 700; color: {color};">
                    {display_value}
                </div>
            </div>
        </div>
    """

    if show_bar:
        html += f"""
        <div style="margin-top: 4px;">
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 6px; height: 6px; overflow: hidden;">
                <div style="width: {percentage}%; background-color: {color}; height: 6px; border-radius: 6px; transition: width 0.5s ease;">
                </div>
            </div>
        </div>
        """

    if subtitle:
        html += f"""
        <div style="font-size: 12px; color: #999; margin-top: 6px;">
            {subtitle}
        </div>
        """

    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# ECONOMIC IMPACT VISUALIZATION - FIXED VERSION
# ============================================================


def render_economic_impact(
    residential: float,
    infrastructure: float,
    total: float,
    agriculture: float = None,
    currency: str = "GH₵",
) -> None:
    """
    Render a visual economic impact summary.
    Handles missing agriculture attribute gracefully.
    """
    # Handle missing agriculture
    if agriculture is None:
        agriculture = 0

    max_value = max(residential, infrastructure, agriculture, 1)

    colors = {
        "Residential": "#e53e3e",
        "Infrastructure": "#ed8936",
        "Agriculture": "#38a169",
    }

    st.markdown("### 💰 Estimated Economic Impact")

    col1, col2, col3 = st.columns(3)

    # Residential
    with col1:
        percentage = (residential / max_value) * 100 if max_value > 0 else 0
        display = (
            f"{currency} {residential/1_000_000:.1f}M"
            if residential >= 1_000_000
            else f"{currency} {residential:,.0f}"
        )
        st.markdown(
            f"""
        <div style="background: #ffffff; padding: 12px 16px; border-radius: 8px; border-left: 4px solid {colors['Residential']};">
            <div style="font-size: 12px; color: #666;">🏠 Residential</div>
            <div style="font-size: 20px; font-weight: 700; color: {colors['Residential']};">{display}</div>
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 4px; height: 4px; margin-top: 6px;">
                <div style="width: {percentage}%; background-color: {colors['Residential']}; height: 4px; border-radius: 4px;"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Infrastructure
    with col2:
        percentage = (infrastructure / max_value) * 100 if max_value > 0 else 0
        display = (
            f"{currency} {infrastructure/1_000_000:.1f}M"
            if infrastructure >= 1_000_000
            else f"{currency} {infrastructure:,.0f}"
        )
        st.markdown(
            f"""
        <div style="background: #ffffff; padding: 12px 16px; border-radius: 8px; border-left: 4px solid {colors['Infrastructure']};">
            <div style="font-size: 12px; color: #666;">🏗️ Infrastructure</div>
            <div style="font-size: 20px; font-weight: 700; color: {colors['Infrastructure']};">{display}</div>
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 4px; height: 4px; margin-top: 6px;">
                <div style="width: {percentage}%; background-color: {colors['Infrastructure']}; height: 4px; border-radius: 4px;"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Agriculture (if present)
    with col3:
        if agriculture > 0:
            percentage = (agriculture / max_value) * 100 if max_value > 0 else 0
            display = (
                f"{currency} {agriculture/1_000_000:.1f}M"
                if agriculture >= 1_000_000
                else f"{currency} {agriculture:,.0f}"
            )
        else:
            percentage = 0
            display = f"{currency} 0"
        st.markdown(
            f"""
        <div style="background: #ffffff; padding: 12px 16px; border-radius: 8px; border-left: 4px solid {colors['Agriculture']};">
            <div style="font-size: 12px; color: #666;">🌾 Agriculture</div>
            <div style="font-size: 20px; font-weight: 700; color: {colors['Agriculture']};">{display}</div>
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 4px; height: 4px; margin-top: 6px;">
                <div style="width: {percentage}%; background-color: {colors['Agriculture']}; height: 4px; border-radius: 4px;"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Total
    st.markdown("---")
    total_display = (
        f"{currency} {total/1_000_000_000:.2f}B"
        if total >= 1_000_000_000
        else f"{currency} {total/1_000_000:.1f}M"
    )
    st.markdown(
        f"""
    <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 16px 24px; border-radius: 8px; text-align: center;">
        <div style="font-size: 14px; color: #a0aec0;">Total Estimated Impact</div>
        <div style="font-size: 32px; font-weight: 700; color: #ffffff;">{total_display}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ============================================================
# POPULATION VISUALIZATION - FIXED VERSION
# ============================================================


def render_population_visual(
    total: int, children: int = 0, elderly: int = 0, households: int = 0
) -> None:
    """Render a visual population summary."""
    if total > 500000:
        emoji = "🏙️"
        color = "#e53e3e"
    elif total > 200000:
        emoji = "🏘️"
        color = "#ed8936"
    elif total > 100000:
        emoji = "🏠"
        color = "#38a169"
    else:
        emoji = "🏡"
        color = "#48bb78"

    st.markdown("### 👥 Population Overview")

    st.markdown(
        f"""
    <div style="background: #ffffff; padding: 16px 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 16px;">
            <span style="font-size: 36px;">{emoji}</span>
            <div style="flex: 1;">
                <div style="font-size: 14px; color: #666; font-weight: 500;">Total Population</div>
                <div style="font-size: 28px; font-weight: 700; color: {color};">{total:,.0f}</div>
            </div>
        </div>
        <div style="margin-top: 8px;">
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 6px; height: 8px; overflow: hidden;">
                <div style="width: 100%; background-color: {color}; height: 8px; border-radius: 6px;"></div>
            </div>
        </div>
        <div style="font-size: 12px; color: #999; margin-top: 4px;">
            <span>👶 Children: {children:,.0f}</span>
            <span style="margin-left: 16px;">👴 Elderly: {elderly:,.0f}</span>
            <span style="margin-left: 16px;">🏠 Households: {households:,.0f}</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ============================================================
# STATUS INDICATORS
# ============================================================


def render_status_indicator(
    status: str, label: str = "", show_icon: bool = True
) -> None:
    """Render a visual status indicator."""
    status_colors = {
        "ACTIVE": ("🟢", "#00cc00"),
        "OPEN": ("🟢", "#00cc00"),
        "PREPARING": ("🟡", "#ffaa00"),
        "CLOSED": ("🔴", "#ff0000"),
        "CRITICAL": ("🔴", "#ff0000"),
        "HIGH": ("🟠", "#ff6600"),
        "MODERATE": ("🟡", "#ffaa00"),
        "LOW": ("🟢", "#00cc00"),
        "NORMAL": ("🟢", "#00cc00"),
    }

    icon, color = status_colors.get(status.upper(), ("⚪", "#999"))

    html = f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #f8f9fa;
        padding: 4px 12px;
        border-radius: 20px;
        border: 1px solid {color};
    ">
        {f'<span style="font-size: 14px;">{icon}</span>' if show_icon else ''}
        <span style="font-size: 13px; font-weight: 500; color: {color};">
            {label or status}
        </span>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# RISK INDICATOR
# ============================================================


def render_risk_indicator(
    risk_score: float, risk_category: str, show_progress: bool = True
) -> None:
    """Render a visual risk indicator."""
    if risk_score >= 80:
        color = "#ff0000"
        emoji = "🔴"
    elif risk_score >= 60:
        color = "#ff6600"
        emoji = "🟠"
    elif risk_score >= 40:
        color = "#ffaa00"
        emoji = "🟡"
    else:
        color = "#00cc00"
        emoji = "🟢"

    st.markdown(f"""
    <div style="
        background: #ffffff;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border-left: 6px solid {color};
    ">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 36px;">{emoji}</span>
            <div style="flex: 1;">
                <div style="font-size: 14px; color: #666; font-weight: 500;">Current Risk Level</div>
                <div style="font-size: 28px; font-weight: 700; color: {color};">
                    {risk_score:.0f}% • {risk_category}
                </div>
            </div>
        </div>
    """)

    if show_progress:
        st.markdown(
            f"""
        <div style="margin-top: 8px;">
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 6px; height: 8px; overflow: hidden;">
                <div style="width: {risk_score}%; background: linear-gradient(to right, #00cc00, #ffaa00, #ff6600, #ff0000); height: 8px; border-radius: 6px; transition: width 0.5s ease;">
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# QUICK STATS ROW
# ============================================================


def render_quick_stats(stats: List[Dict[str, Any]], columns: int = 4) -> None:
    """Render a row of quick visual statistics."""
    cols = st.columns(columns)

    for i, stat in enumerate(stats):
        with cols[i % columns]:
            color = stat.get("color", "#333")
            value = stat.get("value", "N/A")
            label = stat.get("label", "")
            emoji = stat.get("emoji", "")
            subtitle = stat.get("subtitle", "")

            if isinstance(value, (int, float)):
                if value >= 1_000_000:
                    display_value = f"{value/1_000_000:.1f}M"
                elif value >= 1_000:
                    display_value = f"{value/1_000:.1f}K"
                else:
                    display_value = f"{value:,.0f}"
            else:
                display_value = str(value)

            st.markdown(
                f"""
            <div style="
                background: #ffffff;
                padding: 12px 16px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                text-align: center;
                border-bottom: 3px solid {color};
                height: 100%;
            ">
                <div style="font-size: 28px; margin-bottom: 4px;">{emoji}</div>
                <div style="font-size: 20px; font-weight: 700; color: {color};">
                    {display_value}
                </div>
                <div style="font-size: 12px; color: #666; font-weight: 500;">
                    {label}
                </div>
                {f'<div style="font-size: 10px; color: #999; margin-top: 4px;">{subtitle}</div>' if subtitle else ''}
            </div>
            """,
                unsafe_allow_html=True,
            )


# ============================================================
# SHELTER STATUS VISUALIZATION
# ============================================================


def render_shelter_status(shelters: List[Dict[str, Any]]) -> None:
    """Render visual shelter status cards."""
    for shelter in shelters:
        name = shelter.get("name", "Unknown")
        status = shelter.get("status", "UNKNOWN")
        capacity = shelter.get("capacity", 0)
        available = shelter.get("available", 0)
        occupied = capacity - available

        if status.upper() == "OPEN":
            color = "#00cc00"
            icon = "🟢"
        elif status.upper() == "PREPARING":
            color = "#ffaa00"
            icon = "🟡"
        else:
            color = "#ff0000"
            icon = "🔴"

        occupancy_percent = (occupied / capacity) * 100 if capacity > 0 else 0

        st.markdown(
            f"""
        <div style="
            background: #ffffff;
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border-left: 4px solid {color};
            margin-bottom: 8px;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">{icon}</span>
                <span style="font-weight: 600; font-size: 14px;">{name}</span>
                <span style="font-size: 12px; color: {color}; font-weight: 500; margin-left: auto;">
                    {status}
                </span>
            </div>
            <div style="display: flex; gap: 16px; margin-top: 8px; font-size: 13px; color: #666;">
                <span>👤 {occupied:,} occupied</span>
                <span>🏠 {available:,} available</span>
                <span>📊 {occupancy_percent:.0f}% full</span>
            </div>
            <div style="width: 100%; background-color: #f0f0f0; border-radius: 4px; height: 4px; margin-top: 4px;">
                <div style="width: {occupancy_percent}%; background-color: {color}; height: 4px; border-radius: 4px;"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ============================================================
# EVIDENCE CONFIDENCE VISUALIZATION
# ============================================================


def render_evidence_confidence(evidence_items: List[Dict[str, Any]]) -> None:
    """Render visual evidence confidence bars with star ratings."""
    for item in evidence_items:
        name = item.get("name", "Unknown")
        score = item.get("score", 0)
        stars = item.get("stars", "★★★☆☆")
        confidence = item.get("confidence", 50)

        if score >= 70:
            color = "#00cc00"
        elif score >= 40:
            color = "#ffaa00"
        else:
            color = "#ff0000"

        st.markdown(
            f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 500; font-size: 14px;">{name}</span>
                <span style="font-size: 14px; color: #666;">{stars}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="flex: 1; width: 100%; background-color: #f0f0f0; border-radius: 4px; height: 6px; overflow: hidden;">
                    <div style="width: {score}%; background-color: {color}; height: 6px; border-radius: 4px; transition: width 0.5s ease;"></div>
                </div>
                <span style="font-size: 12px; color: #666; min-width: 40px; text-align: right;">
                    {score:.0f}%
                </span>
            </div>
            <div style="font-size: 11px; color: #999; margin-top: 2px;">
                Confidence: {confidence:.0f}%
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ============================================================
# TIMELINE VISUALIZATION
# ============================================================


def render_risk_timeline_visual(
    hours: List[str], risks: List[float], current_risk: float
) -> None:
    """Render a visual risk timeline with gradient bars."""
    for hour, risk in zip(hours, risks):
        if risk >= 80:
            color = "#ff0000"
            emoji = "🔴"
        elif risk >= 60:
            color = "#ff6600"
            emoji = "🟠"
        elif risk >= 40:
            color = "#ffaa00"
            emoji = "🟡"
        else:
            color = "#00cc00"
            emoji = "🟢"

        is_peak = risk == max(risks)
        is_current = risk == current_risk

        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(f"**{hour}**")
        with col2:
            st.markdown(
                f"""
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">{emoji}</span>
                <div style="flex: 1; width: 100%; background-color: #f0f0f0; border-radius: 6px; height: 10px; overflow: hidden;">
                    <div style="width: {risk}%; background: {color}; height: 10px; border-radius: 6px; transition: width 0.5s ease;">
                    </div>
                </div>
                <span style="font-size: 12px; font-weight: {'700' if is_peak else '400'}; color: {color};">
                    {risk:.0f}%
                    {f' ★' if is_peak else ''}
                    {f' 👈' if is_current else ''}
                </span>
            </div>
            """,
                unsafe_allow_html=True,
            )


# ============================================================
# RESOURCE STATUS VISUALIZATION
# ============================================================


def render_resource_status(resources: List[Dict[str, Any]]) -> None:
    """Render visual resource status indicators."""
    cols = st.columns(len(resources))

    for i, resource in enumerate(resources):
        with cols[i]:
            name = resource.get("name", "Unknown")
            value = resource.get("value", 0)
            emoji = resource.get("emoji", "📦")
            status = resource.get("status", "Available")

            if status.lower() == "ready" or status.lower() == "available":
                color = "#00cc00"
                icon = "✅"
            elif status.lower() == "deployed" or status.lower() == "active":
                color = "#ffaa00"
                icon = "🟡"
            else:
                color = "#ff0000"
                icon = "❌"

            st.markdown(
                f"""
            <div style="
                background: #ffffff;
                padding: 12px 16px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                text-align: center;
                border-top: 4px solid {color};
                height: 100%;
            ">
                <div style="font-size: 28px; margin-bottom: 4px;">{emoji}</div>
                <div style="font-size: 22px; font-weight: 700; color: {color};">
                    {value}
                </div>
                <div style="font-size: 12px; color: #666; font-weight: 500;">
                    {name}
                </div>
                <div style="font-size: 11px; color: {color}; margin-top: 4px;">
                    {icon} {status}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )


# ============================================================
# COMMUNITY AFFECTED VISUALIZATION
# ============================================================


def render_affected_communities(communities: List[str], max_display: int = 5) -> None:
    """Render visual list of affected communities with severity indicators."""
    if not communities:
        st.info("No affected communities reported.")
        return

    display_communities = communities[:max_display]
    remaining = len(communities) - max_display

    for community in display_communities:
        color_hash = hash(community) % 3
        colors = ["#e53e3e", "#ed8936", "#ecc94b"]
        emojis = ["🔴", "🟠", "🟡"]

        st.markdown(
            f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 8px;
            background: #ffffff;
            padding: 6px 12px;
            border-radius: 6px;
            margin-bottom: 4px;
            border-left: 3px solid {colors[color_hash]};
        ">
            <span>{emojis[color_hash]}</span>
            <span style="font-size: 14px; font-weight: 500;">{community}</span>
            <span style="font-size: 11px; color: #999; margin-left: auto;">Affected</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    if remaining > 0:
        st.caption(f"And {remaining} more communities affected...")


# ============================================================
# EXPORT ALL COMPONENTS
# ============================================================

__all__ = [
    "render_horizontal_progress_bar",
    "render_density_bar",
    "render_metric_card",
    "render_impact_card",
    "render_visual_metric_card",
    "render_economic_impact",
    "render_population_visual",
    "render_status_indicator",
    "render_risk_indicator",
    "render_quick_stats",
    "render_shelter_status",
    "render_evidence_confidence",
    "render_risk_timeline_visual",
    "render_resource_status",
    "render_affected_communities",
]
