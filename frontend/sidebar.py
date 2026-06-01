from __future__ import annotations

from pathlib import Path

import streamlit as st

from scheduler.config import CONFIG
from scheduler.loader import list_scenarios, load_scenario
from scheduler.model import ScheduleResult
from frontend.icons import icon


def render_sidebar() -> tuple[str, float, float, float, "st.delta_generator.DeltaGenerator"]:
    with st.sidebar:

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:7px;'
            f'font-size:1.1rem;font-weight:700;margin:0 0 2px 0">'
            f'{icon("bolt", size=20)} Bus Charging Scheduler</div>',
            unsafe_allow_html=True,
        )
        st.caption("Bengaluru → A → B → C → D → Kochi · 540 km · 240 km range")
        st.divider()


        scenarios_dir = Path(CONFIG.scenarios_dir)
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


        default_weights = load_scenario(selected_path).weights


        _k_ind   = f"w_ind_{selected_name}"
        _k_op    = f"w_op_{selected_name}"
        _k_all   = f"w_all_{selected_name}"
        _k_reset = f"_reset_{selected_name}"


        if st.session_state.get(_k_reset):
            st.session_state[_k_ind] = float(default_weights.individual)
            st.session_state[_k_op]  = float(default_weights.operator)
            st.session_state[_k_all] = float(default_weights.overall)
            del st.session_state[_k_reset]

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;'
            f'font-weight:600;font-size:0.95rem;margin:4px 0 2px 0">'
            f'{icon("settings", size=16)} Weight Controls</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Drag sliders to tune the three soft-objective weights. "
            "Watch the **score** update below — lower is better."
        )

        _sl = dict(
            min_value=CONFIG.weight_slider_min,
            max_value=CONFIG.weight_slider_max,
            step=CONFIG.weight_slider_step,
        )
        w_individual = st.slider(
            "Individual Wait",
            **_sl,
            value=float(default_weights.individual),
            help="S1 — Penalises total charger queue time per bus. "
                 "Higher = more pressure to minimise waiting.",
            key=_k_ind,
        )
        w_operator = st.slider(
            "Operator Fairness",
            **_sl,
            value=float(default_weights.operator),
            help="S2 — Penalises uneven wait within each operator's fleet. "
                 "Higher = more pressure to equalise KPN / Freshbus / Flixbus fleets. "
                 "Scenario 4 default = 2.0.",
            key=_k_op,
        )
        w_overall = st.slider(
            "Overall Makespan",
            **_sl,
            value=float(default_weights.overall),
            help="S3 — Penalises the total clock span of the whole operation. "
                 "Higher = more pressure to finish the whole fleet faster.",
            key=_k_all,
        )


        st.markdown(
            f'<div style="display:flex;align-items:center;gap:5px;'
            f'font-size:0.82rem;color:#555;margin:8px 0 2px 0">'
            f'{icon("reset", size=14)} Reset to scenario defaults</div>',
            unsafe_allow_html=True,
        )
        if st.button("Reset weights", use_container_width=True, key="reset_btn"):
            st.session_state[_k_reset] = True
            st.rerun()


        st.markdown(
            f'<div style="display:flex;align-items:center;gap:5px;'
            f'font-size:0.82rem;color:#555;margin:6px 0 2px 0">'
            f'{icon("activity", size=14)} '
            f'ind <strong>{w_individual}</strong> · '
            f'op <strong>{w_operator}</strong> · '
            f'all <strong>{w_overall}</strong></div>',
            unsafe_allow_html=True,
        )


        score_slot = st.empty()

    return selected_path, w_individual, w_operator, w_overall, score_slot


def render_sidebar_score(
    result: ScheduleResult,
    score_slot: "st.delta_generator.DeltaGenerator",
) -> None:
    breakdown = result.objective_breakdown
    total     = result.total_objective

    with score_slot.container():
        st.markdown("---")

        st.markdown(
            f'<div style="display:flex;align-items:center;gap:5px;'
            f'font-size:0.82rem;font-weight:600;margin:2px 0 4px 0;color:#374151">'
            f'{icon("activity", size=14)} Objective Score'
            f'<span style="font-size:0.75rem;font-weight:400;color:#6b7280">'
            f' — lower is better</span></div>',
            unsafe_allow_html=True,
        )
        st.metric(
            label="Total",
            value=f"{total:,.1f}",
            help="S1 (individual wait) + S2 (operator variance) + S3 (makespan). "
                 "Drag the sliders above — this number updates immediately.",
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Ind", f"{breakdown.get('IndividualWaitRule', 0):,.0f}",
                  help="IndividualWaitRule contribution")
        c2.metric("Op",  f"{breakdown.get('OperatorRule', 0):,.0f}",
                  help="OperatorRule contribution")
        c3.metric("All", f"{breakdown.get('OverallRule', 0):,.0f}",
                  help="OverallRule contribution")
        st.caption(
            "Weights scale each rule's contribution. "
            "Try Scenario 4 with Operator = 0 vs 4 to see Op score jump."
        )
