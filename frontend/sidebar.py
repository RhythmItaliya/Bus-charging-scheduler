"""
frontend/sidebar.py — Streamlit sidebar for the Bus Charging Scheduler.

Renders:
  • App title with bolt SVG icon
  • Scenario dropdown (required first/topmost — R32)
  • Weight sliders (individual, operator, overall) defaulting to scenario values
  • Reset button (clears session state keys to restore scenario defaults)
  • Active-weight readout

Uses st.markdown(unsafe_allow_html=True) for SVG labels. Icons use explicit
hex stroke colours (not "currentColor") for maximum compatibility.

Returns selected_path, w_individual, w_operator, w_overall to the caller.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from scheduler.config import SCENARIOS_DIR
from scheduler.loader import list_scenarios, load_scenario
from frontend.icons import icon


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
            f'<div style="display:flex;align-items:center;gap:6px;'
            f'font-size:1.1rem;font-weight:700;margin:0 0 2px 0">'
            f'{icon("bolt", size=20)} Bus Charging Scheduler</div>',
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

        # Widget keys scoped to scenario so switching resets to scenario defaults
        _k_ind = f"w_ind_{selected_name}"
        _k_op  = f"w_op_{selected_name}"
        _k_all = f"w_all_{selected_name}"

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:5px;'
            f'font-weight:600;font-size:0.95rem;margin:4px 0 2px 0">'
            f'{icon("settings", size=16)} Weight Controls</div>',
            unsafe_allow_html=True,
        )
        st.caption("Tune the three soft-objective multipliers. Scenario 4 uses operator = 2.0.")

        w_individual = st.slider(
            "Individual Wait",
            min_value=0.0, max_value=5.0, step=0.5,
            value=default_weights.individual,
            help="Penalises total charger queue time per bus (S1).",
            key=_k_ind,
        )
        w_operator = st.slider(
            "Operator Fairness",
            min_value=0.0, max_value=5.0, step=0.5,
            value=default_weights.operator,
            help="Penalises uneven wait variance within each operator's fleet (S2).",
            key=_k_op,
        )
        w_overall = st.slider(
            "Overall Makespan",
            min_value=0.0, max_value=5.0, step=0.5,
            value=default_weights.overall,
            help="Penalises the total clock span of the operation (S3).",
            key=_k_all,
        )

        # ── Reset button ──────────────────────────────────────────────────
        # Deletes slider session-state keys so Streamlit reverts them to
        # their default= values on the next rerun — correct Streamlit reset pattern.
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:5px;'
            f'font-size:0.82rem;color:#555;margin:6px 0 2px 0">'
            f'{icon("reset", size=14)} Reset to scenario defaults</div>',
            unsafe_allow_html=True,
        )
        if st.button("Reset weights", use_container_width=True, key="reset_btn"):
            for key in (_k_ind, _k_op, _k_all):
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # ── Active weights readout ────────────────────────────────────────
        st.divider()
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:5px;'
            f'font-size:0.82rem;color:#555;margin:2px 0">'
            f'{icon("activity", size=14)} '
            f'ind <strong>{w_individual}</strong> · '
            f'op <strong>{w_operator}</strong> · '
            f'all <strong>{w_overall}</strong></div>',
            unsafe_allow_html=True,
        )

    return selected_path, w_individual, w_operator, w_overall
