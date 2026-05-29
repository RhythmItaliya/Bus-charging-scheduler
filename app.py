"""
app.py — Streamlit presentation layer for the Bus Charging Scheduler.

Zero Streamlit imports in scheduler/. All scheduling logic is headless.
SVG icons are inlined via st.markdown(unsafe_allow_html=True) since
Streamlit does not support native SVG in button labels — this is the
correct pattern for custom icons in Streamlit.

References:
    docs/05-frontend/01-frontend-flow.md
    docs/05-frontend/02-ui-components.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import streamlit as st

from scheduler.adapters import to_bus_table, to_input_table, to_station_table
from scheduler.config import SCENARIOS_DIR
from scheduler.engine import schedule
from scheduler.loader import list_scenarios, load_scenario
from scheduler.model import ScheduleResult, Scenario, Weights
from scheduler.validate import validate

# ── Page config (must be FIRST Streamlit call) ──────────────────────────────

st.set_page_config(
    page_title="Bus Charging Scheduler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SVG icon library ─────────────────────────────────────────────────────────
# All icons are Material Design / Heroicons inline SVGs.
# Using viewBox="0 0 24 24" standard. Rendered via unsafe_allow_html.

ICONS: dict[str, str] = {
    # Sidebar / nav
    "bolt": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    "reset": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/></svg>',
    "map_pin": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    # Tab icons
    "clipboard": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>',
    "bus": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>',
    "zap": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    # Status icons
    "check_circle": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#28a745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "alert": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#dc3545" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    # Metric icons
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "trending_up": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "users": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "activity": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    # Expander icons
    "code": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    "bar_chart": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "route": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="6" r="3"/><circle cx="19" cy="18" r="3"/><path d="M5 9v12M5 9a6 6 0 0 0 6 6h3a6 6 0 0 1 6 6"/></svg>',
    "plug": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18"/><path d="M7 17H4a2 2 0 0 1-2-2v-4l3-3"/><path d="M9.5 14.5L14 10l5 5"/><path d="M17 7h3a2 2 0 0 1 2 2v4l-3 3"/><line x1="8" y1="8" x2="8.01" y2="8"/><line x1="16" y1="16" x2="16.01" y2="16"/></svg>',
}


def icon(name: str, label: str = "", gap: str = "6px") -> str:
    """Return an HTML span combining an SVG icon and an optional text label."""
    svg = ICONS.get(name, "")
    if label:
        return (
            f'<span style="display:inline-flex;align-items:center;gap:{gap}">'
            f'{svg}<span>{label}</span></span>'
        )
    return f'<span style="display:inline-flex;align-items:center">{svg}</span>'


# ── Global CSS ───────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* Wait cell colour coding */
    .wait-yellow { background-color: #fff3cd; font-weight: bold; }
    .wait-red    { background-color: #f8d7da; font-weight: bold; }

    /* Icon-label helper used throughout the page */
    .icon-label {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-weight: 600;
    }

    /* Metric row tighter spacing */
    [data-testid="stMetric"] { padding: 0.4rem 0.6rem; }

    /* Sidebar reset button gets a muted style */
    section[data-testid="stSidebar"] button[kind="secondary"] {
        border: 1px solid #ccc;
        color: #555;
    }

    /* Station expander header bold */
    [data-testid="stExpander"] summary { font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Cached scheduler ─────────────────────────────────────────────────────────


@st.cache_data(show_spinner="Scheduling…")
def cached_schedule(
    scenario_path: str,
    w_individual: float,
    w_operator: float,
    w_overall: float,
) -> Tuple[Scenario, ScheduleResult, list]:
    """Load → override weights → schedule → validate.  Cached by (path, weights)."""
    from dataclasses import replace

    scenario = load_scenario(scenario_path)
    overridden = Weights(
        individual=w_individual,
        operator=w_operator,
        overall=w_overall,
        extra=scenario.weights.extra,
    )
    scenario = replace(scenario, weights=overridden)
    result = schedule(scenario)
    violations = validate(result, scenario)
    return scenario, result, violations


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    # Header with bolt SVG
    st.markdown(
        f'<h2 class="icon-label">{ICONS["bolt"]}&nbsp;Bus Charging Scheduler</h2>',
        unsafe_allow_html=True,
    )
    st.caption("Bengaluru → A → B → C → D → Kochi · 540 km · 240 km range")
    st.divider()

    # ── Scenario dropdown (R32: first and topmost) ────────────────────────
    scenarios_dir = Path(SCENARIOS_DIR)
    try:
        scenario_list = list_scenarios(scenarios_dir)
    except FileNotFoundError:
        st.error(f"Scenarios directory not found: `{scenarios_dir.resolve()}`")
        st.stop()

    if not scenario_list:
        st.error("No scenario JSON files found in `data/scenarios/`.")
        st.stop()

    scenario_names = [name for name, _ in scenario_list]
    scenario_paths = {name: str(path) for name, path in scenario_list}

    selected_name = st.selectbox(
        "Select Scenario",
        options=scenario_names,
        index=0,
        help="Choose one of the five pre-encoded scenarios.",
        key="scenario_selector",
    )
    selected_path = scenario_paths[selected_name]

    st.divider()

    # ── Weight sliders ────────────────────────────────────────────────────
    _default_scenario = load_scenario(selected_path)
    default_weights = _default_scenario.weights

    st.markdown(
        f'<p class="icon-label">{ICONS["settings"]}&nbsp;Weight Controls</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Tune the three soft-objective multipliers. "
        "Scenario 4 uses operator = 2.0 by default."
    )

    w_individual = st.slider(
        "Individual Wait",
        min_value=0.0, max_value=5.0, step=0.5,
        value=default_weights.individual,
        help="Penalises total charger queue time per bus (S1).",
        key=f"w_ind_{selected_name}",
    )
    w_operator = st.slider(
        "Operator Fairness",
        min_value=0.0, max_value=5.0, step=0.5,
        value=default_weights.operator,
        help="Penalises uneven wait variance within each operator's fleet (S2).",
        key=f"w_op_{selected_name}",
    )
    w_overall = st.slider(
        "Overall Makespan",
        min_value=0.0, max_value=5.0, step=0.5,
        value=default_weights.overall,
        help="Penalises the total clock span of the operation (S3).",
        key=f"w_all_{selected_name}",
    )

    # Reset button — SVG icon rendered above the native button
    st.markdown(
        f'<p style="margin-bottom:4px">{icon("reset")}&nbsp;<small>Reset to scenario defaults</small></p>',
        unsafe_allow_html=True,
    )
    if st.button("Reset weights", use_container_width=True, key="reset_btn"):
        st.rerun()

    st.divider()
    st.markdown(
        f'{icon("activity")}&nbsp;<small>ind <b>{w_individual}</b> · '
        f'op <b>{w_operator}</b> · all <b>{w_overall}</b></small>',
        unsafe_allow_html=True,
    )

# ── Run scheduler ─────────────────────────────────────────────────────────────

try:
    scenario, result, violations = cached_schedule(
        selected_path, w_individual, w_operator, w_overall
    )
except ValueError as exc:
    st.error(f"**Scheduling error:** {exc}")
    st.stop()
except RuntimeError as exc:
    st.error(f"**Engine validation error:** {exc}")
    st.stop()

# Validation banner — always above tabs (UI edge case spec)
if violations:
    st.markdown(
        f'<div style="background:#f8d7da;border-left:4px solid #dc3545;padding:.6rem 1rem;'
        f'border-radius:4px;margin-bottom:.5rem">'
        f'{icon("alert")}&nbsp;<b>Schedule validation failures:</b><br>'
        + "<br>".join(f"• {v}" for v in violations)
        + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div style="background:#d4edda;border-left:4px solid #28a745;padding:.6rem 1rem;'
        f'border-radius:4px;margin-bottom:.5rem">'
        f'{icon("check_circle")}&nbsp;<b>Schedule valid</b> — '
        f'{len(result.bus_plans)} buses · total objective <b>{result.total_objective:,.1f}</b>'
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_input, tab_bus, tab_station = st.tabs([
    "📋 Input",
    "🚌 Per-Bus Timetable",
    "⚡ Per-Station Order",
])

# ── Tab 1: Input ──────────────────────────────────────────────────────────────

with tab_input:
    st.markdown(
        f'<h3 class="icon-label">{icon("clipboard")}&nbsp;{scenario.name}</h3>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(
            f'{icon("bus", "Bus Roster")}',
            unsafe_allow_html=True,
        )
        st.dataframe(
            to_input_table(scenario),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.markdown("**World constants**")
        st.json({
            "speed_kmph": scenario.world.speed_kmph,
            "charge_minutes": scenario.world.charge_minutes,
            "battery_range_km": scenario.world.battery_range_km,
        })
        st.markdown("**Active weights**")
        st.json({
            "individual": w_individual,
            "operator": w_operator,
            "overall": w_overall,
        })

    # Route summary with SVG route icon
    st.markdown(
        f'<p class="icon-label" style="margin-top:1rem">'
        f'{icon("route")}&nbsp;Route</p>',
        unsafe_allow_html=True,
    )
    route_str = " → ".join(scenario.route.nodes)
    segments_str = " | ".join(
        f"{s.from_node}→{s.to_node}: {s.distance_km:.0f} km"
        for s in scenario.route.segments
    )
    st.info(f"**{route_str}**\n\n{segments_str}")

    # Stations with plug icon
    st.markdown(
        f'<p class="icon-label">{icon("plug")}&nbsp;Stations</p>',
        unsafe_allow_html=True,
    )
    for node, stn in sorted(scenario.stations.items()):
        st.caption(f"• {node}: {stn.num_chargers} charger(s)")

    with st.expander(f"{ICONS['code']} Raw scenario JSON", expanded=False):
        st.markdown(
            f'<span class="icon-label">{icon("code", "scenario JSON")}</span>',
            unsafe_allow_html=True,
        )
        raw_path = Path(selected_path)
        st.code(raw_path.read_text(encoding="utf-8"), language="json")

    with st.expander(f"{ICONS['bar_chart']} Objective breakdown", expanded=False):
        st.markdown(
            f'<span class="icon-label">{icon("bar_chart", "Objective Breakdown")}</span>',
            unsafe_allow_html=True,
        )
        st.caption("Lower is better. Hard-rule violations appear as ∞.")
        bd_data = {k: round(v, 2) for k, v in result.objective_breakdown.items()}
        bd_data["TOTAL"] = round(result.total_objective, 2)
        for rule_name, val in bd_data.items():
            st.metric(label=rule_name, value=val)


# ── Tab 2: Per-bus timetable ─────────────────────────────────────────────────

with tab_bus:
    st.markdown(
        f'<h3 class="icon-label">{icon("bus")}&nbsp;Per-Bus Charging Timetable</h3>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Every row is one charge stop. "
        "Yellow = wait 1–30 min · Red = wait > 30 min. "
        "Final arrival time shown on each bus's last row."
    )

    bus_df = to_bus_table(result, scenario)

    def _highlight_wait(col):
        """Colour-code the Wait (min) column: yellow ≤30, red >30."""
        if col.name != "Wait (min)":
            return [""] * len(col)
        styles = []
        for val in col:
            if isinstance(val, (int, float)) and val > 0:
                if val > 30:
                    styles.append("background-color:#f8d7da;font-weight:bold")
                else:
                    styles.append("background-color:#fff3cd;font-weight:bold")
            else:
                styles.append("")
        return styles

    styled_df = bus_df.style.apply(_highlight_wait, axis=0)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.divider()

    # Summary metrics with SVG icons above each metric
    total_wait = sum(bp.total_wait for bp in result.bus_plans)
    max_wait = max((bp.total_wait for bp in result.bus_plans), default=0)
    arrivals = [bp.arrival_min for bp in result.bus_plans]
    departures = [b.departure_min for b in scenario.buses]
    makespan = max(arrivals) - min(departures) if arrivals else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(icon("clock", "Total Wait"), unsafe_allow_html=True)
        st.metric(label="All buses", value=f"{total_wait} min")
    with m2:
        st.markdown(icon("trending_up", "Max Wait"), unsafe_allow_html=True)
        st.metric(label="Worst bus", value=f"{max_wait} min")
    with m3:
        st.markdown(icon("activity", "Makespan"), unsafe_allow_html=True)
        st.metric(label="Network span", value=f"{makespan} min")
    with m4:
        st.markdown(icon("users", "Buses"), unsafe_allow_html=True)
        st.metric(label="Scheduled", value=len(result.bus_plans))


# ── Tab 3: Per-station order ─────────────────────────────────────────────────

with tab_station:
    st.markdown(
        f'<h3 class="icon-label">{icon("zap")}&nbsp;Per-Station Charge Order</h3>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Buses at each station sorted by charge start time. "
        "Ordering reflects the active weights — try raising Operator Fairness "
        "in Scenario 4 to see it reshuffle."
    )

    for node in scenario.intermediate_nodes:
        stn = scenario.stations[node]
        header = (
            f'{icon("plug")}&nbsp;<b>Station {node}</b> '
            f'— {stn.num_chargers} charger(s)'
        )
        with st.expander(f"Station {node} — {stn.num_chargers} charger(s)", expanded=True):
            # SVG header inside the expander body
            st.markdown(
                f'<p class="icon-label">{icon("map_pin")}&nbsp;'
                f'<b>Station {node}</b> · {stn.num_chargers} charger(s)</p>',
                unsafe_allow_html=True,
            )
            stn_df = to_station_table(result, node)
            if stn_df.empty:
                st.caption("No buses charged at this station in this scenario.")
            else:
                st.dataframe(stn_df, use_container_width=True, hide_index=True)
