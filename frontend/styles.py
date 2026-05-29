"""
frontend/styles.py — Global CSS injection for the Bus Charging Scheduler UI.

Call ``inject_css()`` once at app startup (after st.set_page_config).
All styling decisions live here; no inline style= strings elsewhere.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# SVG data-URIs for the three tab icons.
# Streamlit tab labels only accept plain text, so we inject icons via
# CSS ::before pseudo-elements keyed on [data-testid="stTab"]:nth-of-type(n).
# ---------------------------------------------------------------------------

_TAB_ICON_CSS = """
    /* ── Tab SVG icons via CSS ::before (data-URI, no emoji) ─────────────── */
    [data-testid="stTab"]:nth-of-type(1) p::before {
        content: "";
        display: inline-block;
        width: 13px; height: 13px;
        margin-right: 5px;
        vertical-align: middle;
        background-repeat: no-repeat;
        background-size: contain;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/%3E%3Crect x='8' y='2' width='8' height='4' rx='1' ry='1'/%3E%3C/svg%3E");
    }
    [data-testid="stTab"]:nth-of-type(2) p::before {
        content: "";
        display: inline-block;
        width: 13px; height: 13px;
        margin-right: 5px;
        vertical-align: middle;
        background-repeat: no-repeat;
        background-size: contain;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='1' y='3' width='15' height='13'/%3E%3Cpolygon points='16 8 20 8 23 11 23 16 16 16 16 8'/%3E%3Ccircle cx='5.5' cy='18.5' r='2.5'/%3E%3Ccircle cx='18.5' cy='18.5' r='2.5'/%3E%3C/svg%3E");
    }
    [data-testid="stTab"]:nth-of-type(3) p::before {
        content: "";
        display: inline-block;
        width: 13px; height: 13px;
        margin-right: 5px;
        vertical-align: middle;
        background-repeat: no-repeat;
        background-size: contain;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2'/%3E%3C/svg%3E");
    }
"""

_GLOBAL_CSS = f"""
<style>
/* Wait cell colour coding in the timetable dataframe */
.wait-yellow {{ background-color: #fff3cd; font-weight: bold; }}
.wait-red    {{ background-color: #f8d7da; font-weight: bold; }}

/* Shared icon-label helper: icon + text inline, no block margin */
.icon-label {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    line-height: 1.4;
    font-weight: 600;
    margin: 0;
}}

/* Tighter metric cards */
[data-testid="stMetric"] {{ padding: 0.3rem 0.5rem; }}

/* Station expander heading bold */
[data-testid="stExpander"] summary {{ font-weight: 600; }}

{_TAB_ICON_CSS}
</style>
"""


def inject_css() -> None:
    """Inject all global CSS into the Streamlit page.

    Must be called once after ``st.set_page_config``.
    """
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
