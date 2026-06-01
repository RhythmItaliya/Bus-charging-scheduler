from __future__ import annotations

from pathlib import Path

import streamlit as st

from scheduler.adapters import to_bus_table, to_input_table, to_station_table
from scheduler.config import CONFIG
from scheduler.model import Scenario, ScheduleResult
from scheduler.rules.registry import get_registry
from frontend.icons import icon

_IL = "icon-label"


def _icon_header(level: int, icon_name: str, label: str) -> None:
    sz = 20 if level == 2 else 17
    st.markdown(
        f'<h{level} style="display:flex;align-items:center;gap:6px;'
        f'font-weight:700;margin:0 0 4px 0">'
        f'{icon(icon_name, size=sz)} {label}</h{level}>',
        unsafe_allow_html=True,
    )


def _icon_label(icon_name: str, label: str, small: bool = False) -> None:
    style = "font-size:0.82rem;color:#555" if small else "font-weight:600"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:5px;{style};margin:4px 0">'
        f'{icon(icon_name, size=14 if small else 15)} {label}</div>',
        unsafe_allow_html=True,
    )


def _highlight_wait(col):
    if col.name != "Wait (min)":
        return [""] * len(col)
    styles = []
    for val in col:
        if isinstance(val, (int, float)) and val >= CONFIG.wait_warn_min:
            if val > CONFIG.wait_crit_min:
                styles.append("background-color:#f8d7da;font-weight:bold")
            else:
                styles.append("background-color:#fff3cd;font-weight:bold")
        else:
            styles.append("")
    return styles


def render_input_tab(
    scenario: Scenario,
    result: ScheduleResult,
    selected_path: str,
    w_individual: float,
    w_operator: float,
    w_overall: float,
) -> None:
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


    _icon_label("route", "Route")
    route_str = " → ".join(scenario.route.nodes)
    segments_str = " | ".join(
        f"{s.from_node}→{s.to_node}: {s.distance_km:.0f} km"
        for s in scenario.route.segments
    )
    st.info(f"**{route_str}**\n\n{segments_str}")


    _icon_label("plug", "Stations")
    for node, stn in sorted(scenario.stations.items()):
        st.caption(f"• {node}: {stn.num_chargers} charger(s)")


    with st.expander("Raw scenario JSON", expanded=False):
        st.code(Path(selected_path).read_text(encoding="utf-8"), language="json")

    with st.expander("Objective breakdown", expanded=False):
        st.caption("Lower is better. Hard-rule violations appear as ∞.")
        bd = {k: round(v, 2) for k, v in result.objective_breakdown.items()}
        bd["TOTAL"] = round(result.total_objective, 2)
        for rule_name, val in bd.items():
            st.metric(label=rule_name, value=val)


def render_bus_tab(scenario: Scenario, result: ScheduleResult) -> None:
    _icon_header(3, "bus", "Per-Bus Charging Timetable")
    st.caption(
        f"Every row is one charge stop. "
        f"Yellow = wait {CONFIG.wait_warn_min}–{CONFIG.wait_crit_min} min · "
        f"Red = wait > {CONFIG.wait_crit_min} min. "
        f"Final arrival time shown on each bus's last row."
    )

    styled_df = to_bus_table(result, scenario).style.apply(_highlight_wait, axis=0)
    st.dataframe(styled_df, width='stretch', hide_index=True)

    st.divider()


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
    with col:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:4px;'
            f'font-size:0.8rem;font-weight:600;margin:2px 0">'
            f'{icon(icon_name, size=14)} {label}</div>',
            unsafe_allow_html=True,
        )
        st.metric(label=sub, value=value)


def render_station_tab(scenario: Scenario, result: ScheduleResult) -> None:
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


_SYSTEM_DIAGRAM = """\
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                       Bus Charging Scheduler — Full System Architecture                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘

  PRESENTATION LAYER  (frontend/)
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │  app.py  — entry point: wires UI ↔ engine, zero business logic                      │
  │  sidebar.py  render_sidebar()  →  (path, w_ind, w_op, w_all)                        │
  │  tabs.py     render_input_tab · render_bus_tab · render_station_tab · render_arch_tab│
  │  styles.py   inject_css()        icons.py  icon()                                   │
  └────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │ calls
  ADAPTER LAYER  (scheduler/adapters.py)
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │  to_input_table(scenario)    →  bus roster DataFrame                                 │
  │  to_bus_table(result, scen)  →  per-bus charging timetable DataFrame                │
  │  to_station_table(result, n) →  per-station charge-order DataFrame                  │
  │  Only layer that knows about pandas & HH:MM time formatting                          │
  └────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │ reads
  SCHEDULING LAYER  (scheduler/)
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │  engine.py        schedule(scenario) → ScheduleResult                               │
  │    ├─ plans.py    candidate_plans()  →  range-feasible station subsets              │
  │    ├─ resources.py  ChargerPool  reserve() / snapshot() / restore()                 │
  │    └─ objective.py  score(ctx, registry)  →  (feasible, cost, breakdown)            │
  │                                                                                      │
  │  rules/  ──  pluggable rule registry  (@register → autodiscovered)                 │
  │    hard_rules.py  H1 RangeRule · H2 RouteOrderRule · H4 ChargeDurationRule          │
  │    soft_rules.py  S1 IndividualWaitRule · S2 OperatorRule · S3 OverallRule          │
  │    registry.py    RuleRegistry · get_registry() · @register decorator               │
  │    [new rule]     drop a file + @register → engine picks it up automatically        │
  │                                                                                      │
  │  loader.py    list_scenarios() · load_scenario()  →  Scenario  (3-stage validation) │
  │  validate.py  validate(result, scenario)  →  violations list  (H1–H4, R15)         │
  │  model.py     Scenario · World · Route · Bus · Weights · BusPlan · ChargeEvent     │
  │  physics.py   travel_minutes() · base_arrival_minutes() · minutes_to_hhmm()        │
  │  config.py    DEFAULTS · SCENARIOS_DIR                                              │
  └────────────────────────────────────┬─────────────────────────────────────────────────┘
                                       │ reads JSON
  DATA LAYER  (data/scenarios/)
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │  scenario_1.json  Even Spacing      (20 buses, w=1,1,1)                             │
  │  scenario_2.json  Bunched Start     (20 buses, w=1,1,1)                             │
  │  scenario_3.json  Asymmetric Load   (14 buses, w=1,1,1)                             │
  │  scenario_4.json  Operator-Heavy    (20 buses, w=1,2,1)  ← operator weight = 2     │
  │  scenario_5.json  Worst-Case Conv.  (20 buses, w=1,1,1)                             │
  │                                                                                      │
  │  Schema: { name, world, route{nodes,segments}, stations, weights, buses[] }         │
  └──────────────────────────────────────────────────────────────────────────────────────┘

  LAYER RULE: app.py → frontend/ → adapters → engine/validate/model
              Lower layers NEVER import higher ones.
              scheduler/* has ZERO Streamlit imports — fully headless & testable."""

_DATA_FLOW = """\
  User selects scenario + adjusts weights
           │
           ▼
  sidebar.py → render_sidebar() → (path, w_ind, w_op, w_all)
           │
           ▼
  app.py → _cached_schedule(path, w_ind, w_op, w_all)   [st.cache_data]
           │
           ├─► loader.load_scenario(path)  →  Scenario
           │       parse JSON → validate fields → compute route positions map
           │
           ├─► engine.schedule(scenario)   →  ScheduleResult
           │       1. Init ChargerPool per station
           │       2. Sort buses: priority DESC → departure_min ASC → id ASC
           │       3. For each bus:
           │            enumerate candidate_plans()
           │            for each plan: _simulate_plan() → score() → rollback
           │            commit lowest-cost feasible plan (permanently reserves slots)
           │       4. Assemble station_order (sorted by start_min)
           │       5. Post-validate (defence in depth)
           │
           ├─► validate.validate(result, scenario)  →  violations list
           │
           └─► (scenario, result, violations)
                         │
                         ▼
  tabs.py → adapters.to_*_table()  →  DataFrames rendered in Streamlit"""

_VALID_PLANS_NOTE = """\
  Route: Bengaluru(0) → A(100) → B(220) → C(320) → D(440) → Kochi(540 km)
  Battery range: 240 km.  Any leg > 240 km is infeasible.

  BK buses (Bengaluru → Kochi) — valid 2-charge plans:
    {A, C}  legs: 100 · 220 · 220 ✓   ← A→D = 340 km ✗ so {A,D} is invalid
    {B, C}  legs: 220 · 100 · 220 ✓
    {B, D}  legs: 220 · 220 · 100 ✓

  KB buses (Kochi → Bengaluru) — valid 2-charge plans:
    {D, C}  legs: 100 · 120 · 320 ... wait: D→Bengaluru=440>240 via C→A→Bng
            Actually C→A=220, A→Bengaluru=100 ✓  legs: 100·120·220·100 ✓
    {D, B}  legs: 100 · 220 · 220 ✓
    {C, B}  legs: 220 · 100 · 220 ✓
    {C, A}  legs: 220 · 220 · 100 ✓"""


def render_architecture_tab(scenario: Scenario, result: ScheduleResult) -> None:
    _icon_header(3, "settings", "System Architecture")
    st.caption("Full system structure, data flow, scheduling algorithm, and rule registry.")


    with st.expander("Full system diagram", expanded=True):
        st.code(_SYSTEM_DIAGRAM, language=None)


    with st.expander("Data flow (one scheduling run)", expanded=False):
        st.code(_DATA_FLOW, language=None)


    with st.expander("Valid charging plans (range analysis)", expanded=False):
        st.code(_VALID_PLANS_NOTE, language=None)


    with st.expander("Live rule registry", expanded=False):
        registry = get_registry()
        st.markdown("**Hard rules** (feasibility gates — return `math.inf` on violation):")
        for rule in registry.hard_rules:
            st.markdown(f"- `{rule.name}`")
        st.markdown("**Soft rules** (weighted penalty functions):")
        for rule in registry.soft_rules:
            weight_key = getattr(rule, "weight_key", "—")
            st.markdown(f"- `{rule.name}` &nbsp; weight key: `{weight_key}`")
        st.caption(
            "Add a new rule by dropping a file in `scheduler/rules/` with `@register`. "
            "No engine edits needed — autodiscovery picks it up automatically."
        )


    with st.expander("Current scenario data model", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**World constants**")
            st.json({
                "speed_kmph": scenario.world.speed_kmph,
                "charge_minutes": scenario.world.charge_minutes,
                "battery_range_km": scenario.world.battery_range_km,
            })
            st.markdown("**Weights**")
            st.json({
                "individual": scenario.weights.individual,
                "operator": scenario.weights.operator,
                "overall": scenario.weights.overall,
                **({"extra": scenario.weights.extra} if scenario.weights.extra else {}),
            })
        with col2:
            st.markdown("**Route nodes**")
            st.json(list(scenario.route.nodes))
            st.markdown("**Stations**")
            st.json({
                node: {"num_chargers": stn.num_chargers}
                for node, stn in sorted(scenario.stations.items())
            })


    with st.expander("Objective breakdown (current schedule)", expanded=False):
        st.caption("Lower is better. All hard-rule violations are caught before this stage.")
        for rule_name, val in result.objective_breakdown.items():
            st.metric(label=rule_name, value=round(val, 2))
        st.metric(label="TOTAL", value=round(result.total_objective, 2))


    with st.expander("Anticipated changes — handled by data alone", expanded=False):
        import pandas as pd
        changes = [
            ("Add a station",             "Edit route.nodes, route.segments, stations{}",    "Data only"),
            ("Change segment distance",   "Edit route.segments[i].distance_km",              "Data only"),
            ("Add chargers at station",   "Set stations[node].num_chargers = N",             "Data only"),
            ("Add a new operator",        "Add buses with operator='new_name'",              "Data only"),
            ("Add buses",                 "Append to buses[]",                               "Data only"),
            ("Priority buses",            "Set bus.priority > 0; engine sorts DESC",         "Data only"),
            ("Per-bus range",             "Set bus.range_km per vehicle",                    "Data only"),
            ("New soft objective",        "New Rule file + weight key in JSON",              "Data + 1 file"),
            ("New hard rule",             "New Rule file with @register",                    "1 file only"),
            ("Change travel speed",       "Set world.speed_kmph",                            "Data only"),
            ("Change charge duration",    "Set world.charge_minutes",                        "Data only"),
            ("100+ buses",                "Engine is O(buses×plans×stations); linear",       "No change"),
            ("Swap solver to CP-SAT",     "Implement CpSatStrategy behind Strategy ABC",    "No engine edit"),
        ]
        st.dataframe(
            pd.DataFrame(changes, columns=["Change", "How absorbed", "Type"]),
            width="stretch", hide_index=True,
        )
