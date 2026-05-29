"""
frontend/sidebar.py — Streamlit sidebar for the Bus Charging Scheduler.

Renders:
  • App title with bolt SVG icon
  • Scenario dropdown (required first/topmost — R32)
  • Weight sliders (individual, operator, overall) defaulting to scenario values
  • Reset button
  • Active-weight readout

Returns selected_path, w_individual, w_operator, w_overall to the caller.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from scheduler.config import SCENARIOS_DIR
from scheduler.loader import list_scenarios, load_scenario
from frontend.icons import icon

# Shared CSS class used on label spans — defined once in styles.inject_css()
_IL = "icon-label"


def render_sidebar() -> tuple[str, float, float, float]:
    """Render the full sidebar and return the user's current selections.

    Returns:
        (selected_path, w_individual, w_operator, w_overall)

    Calls ``st.stop()`` if no scenario files are found, so the caller can
    assume all four values are valid when this function returns.
    """
    with st.sidebar:
        # ── Title ─────────────────────────────────────────────────────────
        st.markdown(
            f'<h2 class="{_IL}">{icon("bolt")} Bus Charging Scheduler</h2>',
            unsafe_allow_html=True,
        )
        st.caption("Bengaluru → A → B → C → D → Kochi · 540 km · 240 km range")
        st.divider()

        # ── Scenario dropdown (R32: first and topmost element) ─────────────
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

        # ── Weight sliders ────────────────────────────────────────────────
        default_weights = load_scenario(selected_path).weights

        st.markdown(
            f'<span class="{_IL}">{icon("settings")} Weight Controls</span>',
            unsafe_allow_html=True,
        )
        st.caption("Tune the three soft-objective multipliers. Scenario 4 uses operator = 2.0.")

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

        # ── Reset button ──────────────────────────────────────────────────
        st.markdown(
            f'<span class="{_IL}" style="font-size:0.82rem;font-weight:400">'
            f'{icon("reset")} Reset to scenario defaults</span>',
            unsafe_allow_html=True,
        )
        if st.button("Reset weights", use_container_width=True, key="reset_btn"):
            st.rerun()

        # ── Active weights readout ────────────────────────────────────────
        st.divider()
        st.markdown(
            f'<span class="{_IL}" style="font-size:0.82rem;font-weight:400">'
            f'{icon("activity")} ind <b>{w_individual}</b> · '
            f'op <b>{w_operator}</b> · all <b>{w_overall}</b></span>',
            unsafe_allow_html=True,
        )

    return selected_path, w_individual, w_operator, w_overall
