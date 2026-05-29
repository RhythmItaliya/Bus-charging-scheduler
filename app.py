"""
app.py — Entry point for the Bus Charging Scheduler Streamlit app.

This file is intentionally thin: it wires the frontend/ UI layer to the
scheduler/ engine layer.  All rendering logic lives in frontend/, all
scheduling logic lives in scheduler/.

Layer rule: app.py → frontend/ → scheduler/ (no reverse imports).

References:
    docs/05-frontend/01-frontend-flow.md   (UX flow)
    docs/01-architecture/01-system-architecture.md (layer rule)
"""

from __future__ import annotations

from dataclasses import replace
from typing import Tuple

import streamlit as st

from scheduler.engine import schedule
from scheduler.loader import load_scenario
from scheduler.model import ScheduleResult, Scenario, Weights
from scheduler.validate import validate

from frontend.icons import icon
from frontend.styles import inject_css
from frontend.sidebar import render_sidebar
from frontend.tabs import render_input_tab, render_bus_tab, render_station_tab

# ── Page config — must be the FIRST Streamlit call ───────────────────────────

st.set_page_config(
    page_title="Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject global CSS (icons, colours, tab SVGs) ─────────────────────────────

inject_css()

# ── Sidebar — returns user selections ────────────────────────────────────────

selected_path, w_individual, w_operator, w_overall = render_sidebar()

# ── Cached scheduler ──────────────────────────────────────────────────────────


@st.cache_data(show_spinner="Scheduling…")
def _cached_schedule(
    scenario_path: str,
    w_ind: float,
    w_op: float,
    w_all: float,
) -> Tuple[Scenario, ScheduleResult, list]:
    """Load scenario, apply weight overrides, schedule, and validate.

    Cached by (path, w_ind, w_op, w_all) so reselecting the same
    scenario + weights is instant; recomputes only on change.

    Returns:
        (scenario, result, violations) — violations is [] for valid schedules.
    """
    scenario = load_scenario(scenario_path)
    scenario = replace(
        scenario,
        weights=Weights(
            individual=w_ind,
            operator=w_op,
            overall=w_all,
            extra=scenario.weights.extra,
        ),
    )
    result = schedule(scenario)
    return scenario, result, validate(result, scenario)


# ── Run scheduler ─────────────────────────────────────────────────────────────

try:
    scenario, result, violations = _cached_schedule(
        selected_path, w_individual, w_operator, w_overall
    )
except ValueError as exc:
    st.error(f"**Scheduling error:** {exc}")
    st.stop()
except RuntimeError as exc:
    st.error(f"**Engine error:** {exc}")
    st.stop()

# ── Validation banner — always visible above tabs ─────────────────────────────

_IL = "icon-label"

if violations:
    st.markdown(
        f'<div style="background:#f8d7da;border-left:4px solid #dc3545;'
        f'padding:.6rem 1rem;border-radius:4px;margin-bottom:.5rem">'
        f'<div style="display:flex;align-items:center;gap:5px;font-weight:600">'
        f'{icon("alert", size=18)} Schedule validation failures:</div><br>'
        + "<br>".join(f"&bull; {v}" for v in violations)
        + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div style="background:#d4edda;border-left:4px solid #28a745;'
        f'padding:.6rem 1rem;border-radius:4px;margin-bottom:.5rem">'
        f'<div style="display:flex;align-items:center;gap:5px">'
        f'{icon("check_circle", size=18)} '
        f'<span><b>Schedule valid</b> \u2014 '
        f'{len(result.bus_plans)} buses \u00b7 total objective <b>{result.total_objective:,.1f}</b>'
        f'</span></div></div>',
        unsafe_allow_html=True,
    )

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_input, tab_bus, tab_station = st.tabs([
    "Input",
    "Per-Bus Timetable",
    "Per-Station Order",
])

with tab_input:
    render_input_tab(scenario, result, selected_path, w_individual, w_operator, w_overall)

with tab_bus:
    render_bus_tab(scenario, result)

with tab_station:
    render_station_tab(scenario, result)
