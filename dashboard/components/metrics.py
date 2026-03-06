"""
Metric card components for the dashboard.

Displays KPI cards with optional sparklines.
"""

from typing import Any, List, Optional

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def format_number(num: float) -> str:
    """Format large numbers with K/M suffix."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f} M"
    if num >= 1_000:
        return f"{num / 1_000:.2f} K"
    return str(int(num))


def metric_card(
    title: str,
    value: str,
    sparkline_data: Optional[List[float]] = None,
    color: str = "white",
) -> None:
    """
    Render a metric card with optional sparkline.
    
    Args:
        title: Card title.
        value: Main value to display.
        sparkline_data: Optional list of values for mini trend chart.
        color: Accent color for value and sparkline.
    """
    if sparkline_data and len(sparkline_data) > 1:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                y=sparkline_data,
                mode="lines",
                line=dict(color=color, width=2),
                fill="tozeroy",
            )
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=50,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        with st.container():
            st.markdown(f"**{title}**")
            st.markdown(
                f"<span style='font-size:1.9rem; font-weight:600; color:{color};'>{value}</span>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"sparkline_{title.replace(' ', '_')}")
    else:
        st.metric(label=title, value=value)


def gauge_chart(value: float, title: str, max_val: float = 100, color: str = "green") -> None:
    """
    Render a semi-circular gauge chart.
    
    Args:
        value: Current value.
        title: Chart title.
        max_val: Maximum value for scale.
        color: Gauge color.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title},
            gauge={
                "axis": {"range": [0, max_val]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, max_val * 0.5], "color": "rgba(128,128,128,0.2)"},
                    {"range": [max_val * 0.5, max_val], "color": "rgba(128,128,128,0.1)"},
                ],
                "threshold": {
                    "line": {"color": color, "width": 4},
                    "thickness": 0.75,
                    "value": value,
                },
            },
            number={"suffix": "%" if max_val == 100 else "x"},
        )
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height=180,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"gauge_{title.replace(' ', '_')}")
