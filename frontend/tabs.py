"""
frontend/tabs.py — Three main tab views for the Bus Charging Scheduler UI.

Public functions (one per tab):
    render_input_tab(scenario, result, selected_path, w_individual, w_operator, w_overall)
    render_bus_tab(scenario, result)
    render_station_tab(scenario, result)

Each function is self-contained: it receives only the data it needs and
renders into the Streamlit context (must be called inside a ``with tab:`` block).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from scheduler.adapters import to_bus_table, to_input_table, to_station_table
from scheduler.model import Scenario, ScheduleResult
from frontend.icons import icon

_IL = "icon-label"  # CSS class defined in styles.inject_css()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _icon_header(level: int, icon_name: str, label: str) -> None:
    """Render an h2/h3 heading with an SVG icon."""
    sz = 20 if level == 2 else 17
    st.markdown(
        f'<h{level} style="display:flex;align-items:center;gap:6px;'
        f'font-weight:700;margin:0 0 4px 0">'
        f'{icon(icon_name, size=sz)} {label}</h{level}>',
        unsafe_allow_html=True,
    )


def _icon_label(icon_name: str, label: str, small: bool = False) -> None:
    """Render an inline icon-label span."""
    style = "font-size:0.82rem;color:#555" if small else "font-weight:600"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:5px;{style};margin:4px 0">'
        f'{icon(icon_name, size=14 if small else 15)} {label}</div>',
        unsafe_allow_html=True,
    )


def _highlight_wait(col):
    """Pandas Styler function: colour-code the Wait (min) column.

    Yellow  = 1–30 min wait.
    Red     = > 30 min wait.
    """
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


# ---------------------------------------------------------------------------
# Tab 1 — Input
# ---------------------------------------------------------------------------

def render_input_tab(
    scenario: Scenario,
    result: ScheduleResult,
    selected_path: str,
    w_individual: float,
    w_operator: float,
    w_overall: float,
) -> None:
    """Render the Input tab: bus roster, world constants, route, stations, expanders."""
    _icon_header(3, "clipboard", scenario.name)

    col1, col2 = st.columns([3, 1])

    with col1:
        _icon_label("bus", "Bus Roster")
        st.dataframe(to_input_table(scenario), width='stretch', hide_index=True)

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

    # Route
    _icon_label("route", "Route")
    route_str = " → ".join(scenario.route.nodes)
    segments_str = " | ".join(
        f"{s.from_node}→{s.to_node}: {s.distance_km:.0f} km"
        for s in scenario.route.segments
    )
    st.info(f"**{route_str}**\n\n{segments_str}")

    # Stations
    _icon_label("plug", "Stations")
    for node, stn in sorted(scenario.stations.items()):
        st.caption(f"• {node}: {stn.num_chargers} charger(s)")

    # Expanders
    with st.expander("Raw scenario JSON", expanded=False):
        st.code(Path(selected_path).read_text(encoding="utf-8"), language="json")

    with st.expander("Objective breakdown", expanded=False):
        st.caption("Lower is better. Hard-rule violations appear as ∞.")
        bd = {k: round(v, 2) for k, v in result.objective_breakdown.items()}
        bd["TOTAL"] = round(result.total_objective, 2)
        for rule_name, val in bd.items():
            st.metric(label=rule_name, value=val)


# ---------------------------------------------------------------------------
# Tab 2 — Per-bus timetable
# ---------------------------------------------------------------------------

def render_bus_tab(scenario: Scenario, result: ScheduleResult) -> None:
    """Render the Per-Bus Timetable tab: styled dataframe + four summary metrics."""
    _icon_header(3, "bus", "Per-Bus Charging Timetable")
    st.caption(
        "Every row is one charge stop. "
        "Yellow = wait 1–30 min · Red = wait > 30 min. "
        "Final arrival time shown on each bus's last row."
    )

    styled_df = to_bus_table(result, scenario).style.apply(_highlight_wait, axis=0)
    st.dataframe(styled_df, width='stretch', hide_index=True)

    st.divider()

    # Summary metrics
    total_wait = sum(bp.total_wait for bp in result.bus_plans)
    max_wait   = max((bp.total_wait for bp in result.bus_plans), default=0)
    arrivals   = [bp.arrival_min for bp in result.bus_plans]
    departures = [b.departure_min for b in scenario.buses]
    makespan   = max(arrivals) - min(departures) if arrivals else 0

    m1, m2, m3, m4 = st.columns(4)
    _metric_col(m1, "clock",       "Total Wait",   f"{total_wait} min",      "All buses")
    _metric_col(m2, "trending_up", "Max Wait",     f"{max_wait} min",        "Worst bus")
    _metric_col(m3, "activity",    "Makespan",     f"{makespan} min",        "Network span")
    _metric_col(m4, "users",       "Buses",        len(result.bus_plans),    "Scheduled")


def _metric_col(col, icon_name: str, label: str, value, sub: str) -> None:
    """Render an SVG icon label above a metric inside a column."""
    with col:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:4px;'
            f'font-size:0.8rem;font-weight:600;margin:2px 0">'
            f'{icon(icon_name, size=14)} {label}</div>',
            unsafe_allow_html=True,
        )
        st.metric(label=sub, value=value)


# ---------------------------------------------------------------------------
# Tab 3 — Per-station order
# ---------------------------------------------------------------------------

def render_station_tab(scenario: Scenario, result: ScheduleResult) -> None:
    """Render the Per-Station Order tab: one expander per intermediate station."""
    _icon_header(3, "zap", "Per-Station Charge Order")
    st.caption(
        "Buses at each station sorted by charge start time. "
        "Ordering reflects the active weights — try raising Operator Fairness "
        "in Scenario 4 to see it reshuffle."
    )

    for node in scenario.intermediate_nodes:
        stn = scenario.stations[node]
        with st.expander(f"Station {node} — {stn.num_chargers} charger(s)", expanded=True):
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:5px;'
                f'font-weight:600;margin:2px 0">'
                f'{icon("map_pin", size=14)} '
                f'<span>Station <strong>{node}</strong> · {stn.num_chargers} charger(s)</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            stn_df = to_station_table(result, node)
            if stn_df.empty:
                st.caption("No buses charged at this station in this scenario.")
            else:
                st.dataframe(stn_df, width='stretch', hide_index=True)
