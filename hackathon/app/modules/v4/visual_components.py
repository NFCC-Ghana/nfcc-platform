"""
Visual Storytelling Components - Fixed HTML Structure
All components render COMPLETE, SELF-CONTAINED HTML blocks.
No fragmented HTML across multiple st.markdown() calls.
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
from html import escape
import math

# ============================================================
# THEME - Centralized Design Tokens
# ============================================================

class Theme:
    """Centralized design tokens."""
    # Colors
    SUCCESS = "#16A34A"
    WARNING = "#F59E0B"
    DANGER = "#DC2626"
    INFO = "#2563EB"
    
    # Neutrals
    WHITE = "#FFFFFF"
    BLACK = "#111827"
    GRAY_50 = "#F9FAFB"
    GRAY_100 = "#F3F4F6"
    GRAY_200 = "#E5E7EB"
    GRAY_300 = "#D1D5DB"
    GRAY_400 = "#9CA3AF"
    GRAY_500 = "#6B7280"
    GRAY_600 = "#4B5563"
    GRAY_700 = "#374151"
    GRAY_800 = "#1F2937"
    GRAY_900 = "#111827"
    
    # Spacing
    SPACE_2 = 2
    SPACE_4 = 4
    SPACE_6 = 6
    SPACE_8 = 8
    SPACE_10 = 10
    SPACE_12 = 12
    SPACE_14 = 14
    SPACE_16 = 16
    SPACE_18 = 18
    SPACE_20 = 20
    SPACE_22 = 22
    SPACE_24 = 24
    SPACE_28 = 28
    SPACE_30 = 30
    SPACE_32 = 32
    SPACE_40 = 40
    
    # Radius
    RADIUS_SM = "4px"
    RADIUS_MD = "6px"
    RADIUS_LG = "10px"
    RADIUS_XL = "16px"
    RADIUS_FULL = "9999px"
    
    # Shadows
    SHADOW_SM = "0 1px 2px rgba(0,0,0,0.05)"
    SHADOW_MD = "0 2px 8px rgba(0,0,0,0.06)"
    SHADOW_LG = "0 4px 16px rgba(0,0,0,0.08)"
    
    # Font sizes
    FONT_XS = "10px"
    FONT_SM = "12px"
    FONT_MD = "14px"
    FONT_BASE = "16px"
    FONT_LG = "18px"
    FONT_XL = "22px"
    FONT_2XL = "28px"
    FONT_3XL = "36px"
    FONT_4XL = "48px"

THEME = Theme()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clamp(value: float, min_val: float = 0, max_val: float = 100) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))

def risk_color(score: float) -> str:
    """Get color based on risk score."""
    if score >= 80:
        return THEME.DANGER
    if score >= 60:
        return "#EA580C"
    if score >= 40:
        return THEME.WARNING
    return THEME.SUCCESS

def risk_label(score: float) -> str:
    """Get label based on risk score."""
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    return "LOW"

def risk_emoji(score: float) -> str:
    """Get emoji based on risk score."""
    if score >= 80:
        return "🔴"
    if score >= 60:
        return "🟠"
    if score >= 40:
        return "🟡"
    return "🟢"

def safe_text(text: str) -> str:
    """Escape HTML to prevent injection."""
    from html import escape
    return escape(str(text))


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_number(value: float) -> str:
    """Format numbers with K, M, B suffixes."""
    if value is None:
        return "0"
    if value >= 1_000_000_000:
        return f"{value/1e9:.1f}B"
    if value >= 1_000_000:
        return f"{value/1e6:.1f}M"
    if value >= 1_000:
        return f"{value/1e3:.1f}K"
    return f"{value:,.0f}"

def format_currency(value: float, currency: str = "GH₵") -> str:
    """Format currency with proper suffixes."""
    if value is None or value == 0:
        return f"{currency} 0"
    if value >= 1_000_000_000:
        return f"{currency} {value/1e9:.2f}B"
    if value >= 1_000_000:
        return f"{currency} {value/1e6:.1f}M"
    if value >= 1_000:
        return f"{currency} {value/1e3:.1f}K"
    return f"{currency} {value:,.0f}"

def risk_color(score: float) -> str:
    """Get color based on risk score."""
    if score >= 80:
        return THEME.DANGER
    if score >= 60:
        return "#EA580C"
    if score >= 40:
        return THEME.WARNING
    return THEME.SUCCESS

def risk_label(score: float) -> str:
    """Get label based on risk score."""
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MODERATE"
    return "LOW"

def risk_emoji(score: float) -> str:
    """Get emoji based on risk score."""
    if score >= 80:
        return "🔴"
    if score >= 60:
        return "🟠"
    if score >= 40:
        return "🟡"
    return "🟢"

def clamp(value: float, min_val: float = 0, max_val: float = 100) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))

def safe_text(text: str) -> str:
    """Escape HTML to prevent injection."""
    return escape(str(text))

# ============================================================
# COMPONENT FUNCTIONS - ONE COMPLETE HTML BLOCK EACH
# ============================================================


def render_risk_indicator(risk_score: float, risk_category: str, show_progress: bool = True) -> None:
    """
    Render a complete risk indicator card - FIXED VERSION.
    Uses simple string concatenation to avoid nested f-string issues.
    """
    score = clamp(risk_score)
    color = risk_color(score)
    emoji = risk_emoji(score)
    label = risk_category or risk_label(score)
    
    # Build HTML using simple concatenation - NO NESTED F-STRINGS
    html = '<div style="background:#FFFFFF; padding:16px 20px; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.06); border-left:6px solid ' + color + '; margin-bottom:8px;">'
    html += '<div style="display:flex; align-items:center; gap:16px;">'
    html += '<span style="font-size:48px; line-height:1;">' + emoji + '</span>'
    html += '<div style="flex:1;">'
    html += '<div style="font-size:12px; color:#6B7280; font-weight:500;">Current Risk Level</div>'
    html += '<div style="font-size:28px; font-weight:700; color:' + color + ';">' + f"{score:.0f}%" + ' • ' + safe_text(label) + '</div>'
    html += '</div></div>'
    
    if show_progress:
        html += '<div style="margin-top:12px;">'
        html += '<div style="width:100%; background:#F3F4F6; border-radius:9999px; height:8px; overflow:hidden;">'
        html += '<div style="width:' + f"{score:.0f}" + '%; background:linear-gradient(to right, #16A34A, #F59E0B, #EA580C, #DC2626); height:8px; border-radius:9999px; transition:width 0.5s ease;"></div>'
        html += '</div></div>'
    
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)

def render_quick_stats(stats: List[Dict[str, Any]], columns: int = 4) -> None:
    """Render a row of quick statistics cards."""
    cols = st.columns(columns)
    for i, stat in enumerate(stats):
        with cols[i % columns]:
            color = stat.get('color', THEME.GRAY_700)
            value = stat.get('value', 'N/A')
            label = stat.get('label', '')
            emoji = stat.get('emoji', '')
            subtitle = stat.get('subtitle', '')
            
            if isinstance(value, (int, float)):
                display_value = format_number(value)
            else:
                display_value = str(value)
            
            html = f"""
            <div style="
                background: {THEME.WHITE};
                padding: {THEME.SPACE_12}px {THEME.SPACE_16}px;
                border-radius: {THEME.RADIUS_LG};
                box-shadow: {THEME.SHADOW_SM};
                text-align: center;
                border-bottom: 3px solid {color};
                height: 100%;
            ">
                <div style="font-size: {THEME.FONT_2XL}; margin-bottom: {THEME.SPACE_4}px;">{safe_text(emoji)}</div>
                <div style="font-size: {THEME.FONT_LG}; font-weight: 700; color: {color};">
                    {safe_text(display_value)}
                </div>
                <div style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_600}; font-weight: 500;">
                    {safe_text(label)}
                </div>
                {f'<div style="font-size: {THEME.FONT_XS}; color: {THEME.GRAY_400}; margin-top: {THEME.SPACE_4}px;">{safe_text(subtitle)}</div>' if subtitle else ''}
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)



def render_visual_metric_card(
    value: float,
    label: str,
    emoji: str = "",
    color: str = None,
    max_value: float = 100,
    subtitle: str = "",
    show_bar: bool = True
) -> None:
    """Render a complete visual metric card - FIXED VERSION with simple concatenation."""
    # Clamp the percentage
    pct = clamp((value / max_value) * 100 if max_value > 0 else 0)
    
    # Set color based on percentage if not provided
    if color is None:
        if pct >= 70:
            color = "#16A34A"  # Green
        elif pct >= 40:
            color = "#F59E0B"  # Yellow
        else:
            color = "#DC2626"  # Red
    
    # Format the display value
    if isinstance(value, (int, float)):
        if value >= 1_000_000:
            display_value = f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            display_value = f"{value/1_000:.1f}K"
        else:
            display_value = f"{value:,.0f}"
    else:
        display_value = str(value)
    
    # Build HTML using simple concatenation - NO NESTED F-STRINGS
    html = '<div style="background:#FFFFFF; padding:16px 20px; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.06); border:1px solid #E5E7EB; margin-bottom:10px;">'
    
    # Header with emoji, label, and value
    html += '<div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">'
    html += '<span style="font-size:28px; line-height:1;">' + safe_text(emoji) + '</span>'
    html += '<div style="flex:1;">'
    html += '<div style="font-size:14px; font-weight:600; color:#1F2937;">' + safe_text(label) + '</div>'
    html += '<div style="font-size:22px; font-weight:700; color:' + color + ';">' + safe_text(display_value) + '</div>'
    html += '</div></div>'
    
    # Progress bar
    if show_bar:
        html += '<div style="margin-top:4px;">'
        html += '<div style="width:100%; background:#F3F4F6; border-radius:9999px; height:6px; overflow:hidden;">'
        html += '<div style="width:' + f"{pct:.1f}" + '%; background:' + color + '; height:6px; border-radius:9999px; transition:width 0.5s ease;"></div>'
        html += '</div></div>'
    
    # Subtitle
    if subtitle:
        html += '<div style="font-size:10px; color:#9CA3AF; margin-top:4px;">' + safe_text(subtitle) + '</div>'
    
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)



def render_economic_impact(
    residential: float,
    infrastructure: float,
    total: float,
    agriculture: float = None,
    currency: str = "GH₵"
) -> None:
    """Render complete economic impact summary - Using st.components.v1.html for proper CSS."""
    if agriculture is None:
        agriculture = 0
    
    max_value = max(residential, infrastructure, agriculture, 1)
    colors = {
        "Residential": "#DC2626",
        "Infrastructure": "#EA580C",
        "Agriculture": "#16A34A"
    }
    
    total_display = format_currency(total, currency)
    res_display = format_currency(residential, currency)
    inf_display = format_currency(infrastructure, currency)
    ag_display = format_currency(agriculture, currency)
    
    res_pct = clamp((residential / max_value) * 100)
    inf_pct = clamp((infrastructure / max_value) * 100)
    ag_pct = clamp((agriculture / max_value) * 100)
    
    # Build HTML using string concatenation (NO indentation inside the string)
    html = "<div style='margin-bottom:16px; font-family: -apple-system, BlinkMacSystemFont, sans-serif;'>"
    html += "<h3 style='font-size:18px; font-weight:600; color:#1F2937; margin-bottom:12px;'>💰 Estimated Economic Impact</h3>"
    html += "<div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;'>"
    
    # Residential
    html += "<div style='background:#FFFFFF; padding:12px 16px; border-radius:10px; border-left:4px solid " + colors['Residential'] + "; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>"
    html += "<div style='font-size:12px; color:#6B7280;'>🏠 Residential</div>"
    html += "<div style='font-size:18px; font-weight:700; color:" + colors['Residential'] + ";'>" + res_display + "</div>"
    html += "<div style='width:100%; background:#F3F4F6; border-radius:9999px; height:4px; margin-top:6px; overflow:hidden;'>"
    html += "<div style='width:" + f"{res_pct:.0f}" + "%; background:" + colors['Residential'] + "; height:4px; border-radius:9999px;'></div>"
    html += "</div></div>"
    
    # Infrastructure
    html += "<div style='background:#FFFFFF; padding:12px 16px; border-radius:10px; border-left:4px solid " + colors['Infrastructure'] + "; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>"
    html += "<div style='font-size:12px; color:#6B7280;'>🏗️ Infrastructure</div>"
    html += "<div style='font-size:18px; font-weight:700; color:" + colors['Infrastructure'] + ";'>" + inf_display + "</div>"
    html += "<div style='width:100%; background:#F3F4F6; border-radius:9999px; height:4px; margin-top:6px; overflow:hidden;'>"
    html += "<div style='width:" + f"{inf_pct:.0f}" + "%; background:" + colors['Infrastructure'] + "; height:4px; border-radius:9999px;'></div>"
    html += "</div></div>"
    
    # Agriculture
    html += "<div style='background:#FFFFFF; padding:12px 16px; border-radius:10px; border-left:4px solid " + colors['Agriculture'] + "; box-shadow:0 1px 2px rgba(0,0,0,0.05);'>"
    html += "<div style='font-size:12px; color:#6B7280;'>🌾 Agriculture</div>"
    html += "<div style='font-size:18px; font-weight:700; color:" + colors['Agriculture'] + ";'>" + ag_display + "</div>"
    html += "<div style='width:100%; background:#F3F4F6; border-radius:9999px; height:4px; margin-top:6px; overflow:hidden;'>"
    html += "<div style='width:" + f"{ag_pct:.0f}" + "%; background:" + colors['Agriculture'] + "; height:4px; border-radius:9999px;'></div>"
    html += "</div></div>"
    
    html += "</div>"  # Close grid
    
    # Total Impact - with WHITE text
    html += "<div style='margin-top:12px; background:linear-gradient(135deg, #1a1a2e, #16213e); padding:20px 24px; border-radius:10px; text-align:center; border:1px solid #4B5563; box-shadow:0 4px 12px rgba(0,0,0,0.2);'>"
    html += "<div style='font-size:13px; color:#9CA3AF; font-weight:500; letter-spacing:0.5px;'>Total Estimated Impact</div>"
    # CRITICAL: White text on dark background
    html += "<div style='font-size:38px; font-weight:700; color:#FFFFFF; text-shadow:0 2px 8px rgba(0,0,0,0.5); padding:4px 0;'>"
    html += total_display
    html += "</div></div></div>"
    
    # Use st.components.v1.html for proper CSS rendering
    # Using st.html() for better style preservation
    st.html(html)

def render_population_visual(
    total: int,
    children: int = 0,
    elderly: int = 0,
    households: int = 0
) -> None:
    """Render complete population overview card."""
    if total > 500000:
        emoji = "🏙️"
        color = THEME.DANGER
    elif total > 200000:
        emoji = "🏘️"
        color = "#EA580C"
    elif total > 100000:
        emoji = "🏠"
        color = THEME.WARNING
    else:
        emoji = "🏡"
        color = THEME.SUCCESS
    
    html = f"""
    <div style="margin-bottom: {THEME.SPACE_16}px;">
        <h3 style="font-size: {THEME.FONT_LG}; font-weight: 600; color: {THEME.GRAY_800}; margin-bottom: {THEME.SPACE_12}px;">
            👥 Population Overview
        </h3>
        <div style="background: {THEME.WHITE}; padding: {THEME.SPACE_16}px {THEME.SPACE_20}px; border-radius: {THEME.RADIUS_XL}; box-shadow: {THEME.SHADOW_MD};">
            <div style="display: flex; align-items: center; gap: {THEME.SPACE_16}px;">
                <span style="font-size: {THEME.FONT_4XL};">{emoji}</span>
                <div style="flex: 1;">
                    <div style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_500}; font-weight: 500;">Total Population</div>
                    <div style="font-size: {THEME.FONT_2XL}; font-weight: 700; color: {color};">{format_number(total)}</div>
                </div>
            </div>
            <div style="margin-top: {THEME.SPACE_8}px;">
                <div style="width: 100%; background: {THEME.GRAY_100}; border-radius: {THEME.RADIUS_FULL}; height: 8px; overflow: hidden;">
                    <div style="width: 100%; background: {color}; height: 8px; border-radius: {THEME.RADIUS_FULL};"></div>
                </div>
            </div>
            <div style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_600}; margin-top: {THEME.SPACE_8}px;">
                <span>👶 <span style="color: {THEME.GRAY_900}; font-weight: 500;">{format_number(children)}</span> Children</span>
                <span style="margin-left: {THEME.SPACE_20}px;">👴 <span style="color: {THEME.GRAY_900}; font-weight: 500;">{format_number(elderly)}</span> Elderly</span>
                <span style="margin-left: {THEME.SPACE_20}px;">🏠 <span style="color: {THEME.GRAY_900}; font-weight: 500;">{format_number(households)}</span> Households</span>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)



def render_shelter_status(shelters: List[Dict[str, Any]]) -> None:
    """Render complete shelter status cards - ONE self-contained HTML block per shelter."""
    html_parts = []
    for shelter in shelters:
        name = shelter.get('name', 'Unknown')
        status = shelter.get('status', 'UNKNOWN').upper()
        capacity = shelter.get('capacity', 0)
        available = shelter.get('available', 0)
        occupied = capacity - available
        pct = clamp((occupied / capacity) * 100 if capacity > 0 else 0)
        
        if status == 'OPEN':
            color = THEME.SUCCESS
            icon = "✅"
        elif status == 'PREPARING':
            color = THEME.WARNING
            icon = "⚡"
        else:
            color = THEME.DANGER
            icon = "❌"
        
        html_parts.append(f"""
        <div style="
            background: {THEME.WHITE};
            padding: {THEME.SPACE_12}px {THEME.SPACE_16}px;
            border-radius: {THEME.RADIUS_LG};
            box-shadow: {THEME.SHADOW_SM};
            border-left: 4px solid {color};
            margin-bottom: {THEME.SPACE_8}px;
        ">
            <div style="display: flex; align-items: center; gap: {THEME.SPACE_8}px; margin-bottom: {THEME.SPACE_8}px;">
                <span style="font-size: {THEME.FONT_MD};">{icon}</span>
                <span style="font-weight: 600; font-size: {THEME.FONT_MD}; color: {THEME.GRAY_900};">{safe_text(name)}</span>
                <span style="font-size: {THEME.FONT_SM}; color: {color}; font-weight: 500; margin-left: auto;">{safe_text(status)}</span>
            </div>
            <div style="display: flex; gap: {THEME.SPACE_16}px; font-size: {THEME.FONT_SM}; color: {THEME.GRAY_600}; margin-bottom: {THEME.SPACE_8}px;">
                <span>👤 <span style="color: {THEME.GRAY_900}; font-weight: 600;">{occupied:,}</span> occupied</span>
                <span>🏠 <span style="color: {THEME.GRAY_900}; font-weight: 600;">{available:,}</span> available</span>
                <span>📊 <span style="color: {THEME.GRAY_900}; font-weight: 600;">{pct:.0f}%</span> full</span>
            </div>
            <div style="width: 100%; background: {THEME.GRAY_100}; border-radius: {THEME.RADIUS_FULL}; height: 4px; overflow: hidden;">
                <div style="width: {pct:.0f}%; background: {color}; height: 4px; border-radius: {THEME.RADIUS_FULL};"></div>
            </div>
        </div>
        """)
    
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def render_evacuation_routes(routes: List[Dict[str, str]]) -> None:
    """Render complete evacuation route cards."""
    html_parts = []
    for route in routes:
        from_place = route.get('from', 'Unknown')
        to_place = route.get('to', 'Unknown')
        time = route.get('time', 'N/A')
        
        html_parts.append(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: {THEME.SPACE_12}px;
            background: {THEME.WHITE};
            padding: {THEME.SPACE_10}px {THEME.SPACE_16}px;
            border-radius: {THEME.RADIUS_LG};
            border-left: 3px solid #4299e1;
            box-shadow: {THEME.SHADOW_SM};
            font-size: {THEME.FONT_MD};
            margin-bottom: {THEME.SPACE_6}px;
        ">
            <span style="font-size: {THEME.FONT_LG};">🚗</span>
            <span style="font-weight: 600; color: {THEME.GRAY_900};">{safe_text(from_place)}</span>
            <span style="color: {THEME.GRAY_400};">→</span>
            <span style="font-weight: 600; color: {THEME.GRAY_900};">{safe_text(to_place)}</span>
            <span style="margin-left: auto; color: {THEME.GRAY_600}; font-weight: 500; font-size: {THEME.FONT_SM};">⏱️ {safe_text(time)}</span>
        </div>
        """)
    
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_affected_communities(communities: List[str], max_display: int = 5) -> None:
    """Render complete affected communities list."""
    if not communities:
        st.info("No affected communities reported.")
        return
    
    severity_colors = [THEME.DANGER, "#EA580C", THEME.WARNING, "#EA580C", THEME.SUCCESS]
    severity_emojis = ["🔴", "🟠", "🟡", "🟠", "🟢"]
    
    html_parts = []
    for i, community in enumerate(communities[:max_display]):
        color = severity_colors[i % len(severity_colors)]
        emoji = severity_emojis[i % len(severity_emojis)]
        
        html_parts.append(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: {THEME.SPACE_8}px;
            background: {THEME.GRAY_50};
            padding: {THEME.SPACE_8}px {THEME.SPACE_14}px;
            border-radius: {THEME.RADIUS_LG};
            margin-bottom: {THEME.SPACE_4}px;
            border-left: 3px solid {color};
        ">
            <span style="font-size: {THEME.FONT_MD};">{emoji}</span>
            <span style="font-size: {THEME.FONT_MD}; font-weight: 600; color: {THEME.GRAY_900};">{safe_text(community)}</span>
            <span style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_500}; margin-left: auto;">Affected</span>
        </div>
        """)
    
    if len(communities) > max_display:
        html_parts.append(f'<div style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_400}; margin-top: {THEME.SPACE_4}px;">And {len(communities) - max_display} more communities affected...</div>')
    
    st.markdown("".join(html_parts), unsafe_allow_html=True)



def render_evidence_confidence(evidence_items: List[Dict[str, Any]]) -> None:
    """Render complete evidence confidence bars - ONE self-contained HTML block per item."""
    html_parts = []
    for item in evidence_items:
        name = item.get('name', 'Unknown')
        score = clamp(item.get('score', 0))
        stars = item.get('stars', '★★★☆☆')
        confidence = clamp(item.get('confidence', 50))
        
        if score >= 70:
            color = THEME.SUCCESS
        elif score >= 40:
            color = THEME.WARNING
        else:
            color = THEME.DANGER
        
        html_parts.append(f"""
        <div style="margin-bottom: {THEME.SPACE_12}px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; font-size: {THEME.FONT_MD}; color: {THEME.GRAY_900};">{safe_text(name)}</span>
                <span style="font-size: {THEME.FONT_MD}; color: #f59e0b;">{safe_text(stars)}</span>
            </div>
            <div style="display: flex; align-items: center; gap: {THEME.SPACE_12}px;">
                <div style="flex: 1; width: 100%; background: {THEME.GRAY_100}; border-radius: {THEME.RADIUS_FULL}; height: 6px; overflow: hidden;">
                    <div style="width: {score:.0f}%; background: {color}; height: 6px; border-radius: {THEME.RADIUS_FULL}; transition: width 0.5s ease;"></div>
                </div>
                <span style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_600}; font-weight: 500; min-width: 40px; text-align: right;">
                    {score:.0f}%
                </span>
            </div>
            <div style="font-size: {THEME.FONT_XS}; color: {THEME.GRAY_400}; margin-top: {THEME.SPACE_2}px;">
                Confidence: {confidence:.0f}%
            </div>
        </div>
        """)
    
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def render_resource_status(resources: List[Dict[str, Any]]) -> None:
    """Render complete resource status cards."""
    cols = st.columns(len(resources))
    for i, resource in enumerate(resources):
        with cols[i]:
            name = resource.get('name', 'Unknown')
            value = resource.get('value', 0)
            emoji = resource.get('emoji', '📦')
            status = resource.get('status', 'Available')
            
            if status.lower() in ['ready', 'available']:
                color = THEME.SUCCESS
                icon = "✅"
            elif status.lower() in ['deployed', 'active']:
                color = THEME.WARNING
                icon = "🟡"
            else:
                color = THEME.DANGER
                icon = "❌"
            
            html = f"""
            <div style="
                background: {THEME.WHITE};
                padding: {THEME.SPACE_12}px {THEME.SPACE_16}px;
                border-radius: {THEME.RADIUS_LG};
                box-shadow: {THEME.SHADOW_SM};
                text-align: center;
                border-top: 4px solid {color};
                height: 100%;
            ">
                <div style="font-size: {THEME.FONT_2XL}; margin-bottom: {THEME.SPACE_4}px;">{safe_text(emoji)}</div>
                <div style="font-size: {THEME.FONT_XL}; font-weight: 700; color: {color};">{value}</div>
                <div style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_600}; font-weight: 500;">{safe_text(name)}</div>
                <div style="font-size: {THEME.FONT_XS}; color: {color}; margin-top: {THEME.SPACE_4}px;">{icon} {safe_text(status)}</div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)




def render_risk_timeline_visual(hours: List[str], risks: List[float], current_risk: float) -> None:
    """Render complete risk timeline - FIXED VERSION with simple concatenation."""
    html_parts = []
    
    for hour, risk in zip(hours, risks):
        score = clamp(risk)
        color = risk_color(score)
        emoji = risk_emoji(score)
        is_peak = score == max(clamp(r) for r in risks)
        is_current = score == clamp(current_risk)
        
        # Build each timeline row using simple concatenation - NO NESTED F-STRINGS
        row = '<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">'
        
        # Hour label
        row += '<div style="min-width:40px; font-weight:bold; color:#111827; font-size:12px;">' + safe_text(hour) + '</div>'
        
        # Progress bar area
        row += '<div style="flex:1;">'
        row += '<div style="display:flex; align-items:center; gap:8px;">'
        
        # Emoji
        row += '<span style="font-size:16px;">' + emoji + '</span>'
        
        # Progress bar
        row += '<div style="flex:1; width:100%; background:#F3F4F6; border-radius:9999px; height:10px; overflow:hidden;">'
        row += '<div style="width:' + f"{score:.0f}" + '%; background:' + color + '; height:10px; border-radius:9999px; transition:width 0.5s ease;"></div>'
        row += '</div>'
        
        # Percentage and indicators - using simple concatenation
        row += '<span style="font-size:12px; font-weight:' + ('700' if is_peak else '500') + '; color:' + color + '; min-width:45px; text-align:right;">'
        row += f"{score:.0f}%"
        if is_peak:
            row += ' ⭐'
        if is_current:
            row += ' 👈'
        row += '</span>'
        
        row += '</div></div></div>'
        html_parts.append(row)
    
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def render_status_indicator(status: str, label: str = "", show_icon: bool = True) -> None:
    """Render a status indicator badge."""
    status_map = {
        "ACTIVE": ("🟢", THEME.SUCCESS),
        "OPEN": ("✅", THEME.SUCCESS),
        "PREPARING": ("⚡", THEME.WARNING),
        "CLOSED": ("❌", THEME.DANGER),
        "HIGH": ("⚠️", THEME.DANGER),
        "MODERATE": ("⚡", THEME.WARNING),
        "LOW": ("✅", THEME.SUCCESS),
        "CRITICAL": ("🚨", THEME.DANGER),
    }
    icon, color = status_map.get(status.upper(), ("⚪", THEME.GRAY_400))
    display_label = label or status
    
    html = f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: {THEME.SPACE_6}px;
        background: {THEME.GRAY_50};
        padding: {THEME.SPACE_4}px {THEME.SPACE_12}px;
        border-radius: {THEME.RADIUS_FULL};
        border: 1px solid {color};
    ">
        {f'<span aria-hidden="true">{icon}</span>' if show_icon else ''}
        <span style="color: {color}; font-weight: 500; font-size: {THEME.FONT_SM};">{safe_text(display_label)}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_metric_card(value: Any, label: str, emoji: str = "", change: Optional[float] = None, change_label: str = "", color: str = None, size: str = "medium") -> None:
    """Render a metric card."""
    if color is None:
        color = THEME.GRAY_700
    
    if isinstance(value, (int, float)):
        display_value = format_number(value)
    else:
        display_value = str(value)
    
    if change is not None:
        change_color = THEME.SUCCESS if change >= 0 else THEME.DANGER
        arrow = "↑" if change >= 0 else "↓"
        change_html = f"""
        <div style="text-align: right;">
            <span style="color: {change_color}; font-weight: 600; font-size: {THEME.FONT_MD};">{arrow} {abs(change):.1f}%</span>
            <div style="font-size: {THEME.FONT_XS}; color: {THEME.GRAY_500};">{safe_text(change_label)}</div>
        </div>
        """
    else:
        change_html = ""
    
    html = f"""
    <div style="
        background: {THEME.WHITE};
        padding: {THEME.SPACE_16}px;
        border-radius: {THEME.RADIUS_LG};
        box-shadow: {THEME.SHADOW_MD};
        border-left: 4px solid {color};
        margin-bottom: {THEME.SPACE_8}px;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_500}; font-weight: 500;">{safe_text(label)}</span>
                <div style="font-size: {THEME.FONT_XL}; font-weight: 700; color: {color};">
                    {safe_text(emoji)} {display_value}
                </div>
            </div>
            {change_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_impact_card(value: float, label: str, emoji: str = "", color: str = None, detail: str = "") -> None:
    """Render an impact card."""
    if color is None or color == "auto":
        if value > 1000000:
            color = THEME.DANGER
        elif value > 500000:
            color = "#EA580C"
        else:
            color = THEME.SUCCESS
    
    html = f"""
    <div style="
        background: {THEME.WHITE};
        padding: {THEME.SPACE_16}px;
        border-radius: {THEME.RADIUS_LG};
        box-shadow: {THEME.SHADOW_MD};
        border-bottom: 3px solid {color};
        margin-bottom: {THEME.SPACE_8}px;
    ">
        <div style="display: flex; align-items: center; gap: {THEME.SPACE_12}px;">
            <span style="font-size: {THEME.FONT_2XL};">{safe_text(emoji)}</span>
            <div>
                <div style="font-size: {THEME.FONT_SM}; color: {THEME.GRAY_500}; font-weight: 500;">{safe_text(label)}</div>
                <div style="font-size: {THEME.FONT_XL}; font-weight: 700; color: {color};">{format_currency(value)}</div>
                {f'<div style="font-size: {THEME.FONT_XS}; color: {THEME.GRAY_500};">{safe_text(detail)}</div>' if detail else ''}
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_horizontal_progress_bar(value: float, max_value: float = 100, label: str = "", color: str = None, height: int = 8, show_percentage: bool = True, show_emoji: bool = True) -> None:
    """Render a horizontal progress bar."""
    pct = clamp((value / max_value) * 100 if max_value > 0 else 0)
    if color is None:
        color = THEME.SUCCESS
    
    emoji = "🟢" if pct >= 70 else "🟡" if pct >= 40 else "🔴"
    
    if label:
        if show_emoji:
            st.markdown(f"{emoji} **{safe_text(label)}**", unsafe_allow_html=True)
        else:
            st.markdown(f"**{safe_text(label)}**", unsafe_allow_html=True)
    
    html = f"""
    <div style="
        width: 100%;
        background: {THEME.GRAY_100};
        border-radius: {THEME.RADIUS_FULL};
        height: {height}px;
        overflow: hidden;
    ">
        <div style="
            width: {pct:.0f}%;
            background: {color};
            height: {height}px;
            border-radius: {THEME.RADIUS_FULL};
            transition: width 0.5s ease;
        ">
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    if show_percentage:
        st.caption(f"{pct:.0f}%")

# ============================================================
# EXPORT ALL FUNCTIONS
# ============================================================

__all__ = [
    'render_risk_indicator',
    'render_quick_stats',
    'render_visual_metric_card',
    'render_economic_impact',
    'render_population_visual',
    'render_shelter_status',
    'render_evacuation_routes',
    'render_affected_communities',
    'render_evidence_confidence',
    'render_resource_status',
    'render_risk_timeline_visual',
    'render_status_indicator',
    'render_metric_card',
    'render_impact_card',
    'render_horizontal_progress_bar',
    'THEME',
    'format_number',
    'format_currency',
]
