"""
scheduler/adapters.py — Transforms engine output into Streamlit-ready DataFrames.

This is the ONLY layer allowed to know about pandas, HH:MM formatting, and
column display names.  The engine and rules remain format-agnostic (minutes only).

Public API (docs/04-api-contracts/01-internal-api-contracts.md):
    to_input_table(scenario)              -> DataFrame  (bus roster + world summary)
    to_bus_table(result, scenario)        -> DataFrame  (per-bus timetable)
    to_station_table(result, node)        -> DataFrame  (per-station charge order)

References:
    docs/05-frontend/01-frontend-flow.md   (the three views)
    docs/05-frontend/02-ui-components.md   (component acceptance criteria)
    docs/04-api-contracts/01-internal-api-contracts.md
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from scheduler.model import Scenario, ScheduleResult
from scheduler.physics import minutes_to_hhmm


# ---------------------------------------------------------------------------
# Input table
# ---------------------------------------------------------------------------

def to_input_table(scenario: Scenario) -> pd.DataFrame:
    """
    Build the bus roster DataFrame for the Input tab.

    Columns: Bus ID | Operator | Direction | Departure (HH:MM) | Range (km) | Priority

    The direction is derived from origin/destination against the route so it is
    never hardcoded — adding a new route direction works automatically.

    Args:
        scenario: The fully-loaded scenario.

    Returns:
        A pandas DataFrame with one row per bus, sorted by departure time.
    """
    nodes = list(scenario.route.nodes)

    rows = []
    for bus in sorted(scenario.buses, key=lambda b: (b.departure_min, b.id)):
        origin_idx = nodes.index(bus.origin)
        dest_idx = nodes.index(bus.destination)
        direction = "BK (→ Kochi)" if origin_idx < dest_idx else "KB (→ Bengaluru)"
        rows.append({
            "Bus ID": bus.id,
            "Operator": bus.operator.upper(),
            "Direction": direction,
            "Departure": minutes_to_hhmm(bus.departure_min),
            "Range (km)": int(bus.range_km),
            "Priority": bus.priority,
        })

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Per-bus timetable
# ---------------------------------------------------------------------------

def to_bus_table(result: ScheduleResult, scenario: Scenario) -> pd.DataFrame:
    """
    Build the per-bus timetable DataFrame for the Per-bus tab.

    One row per (bus, charge_event) pair, plus a summary row for final arrival.
    Non-zero waits are surfaced in a dedicated column so Streamlit can highlight them.

    Columns:
        Bus ID | Operator | Dir | Station | Arrive | Wait (min) | Start | End | Arrival

    The "Arrival" column is populated only on the last row for each bus.

    Args:
        result:   The ScheduleResult from the engine.
        scenario: The scenario (used to derive direction).

    Returns:
        A pandas DataFrame sorted by bus departure then station.
    """
    nodes = list(scenario.route.nodes)
    rows = []

    for bp in result.bus_plans:
        bus = next(b for b in scenario.buses if b.id == bp.bus_id)
        origin_idx = nodes.index(bus.origin)
        dest_idx = nodes.index(bus.destination)
        direction = "BK" if origin_idx < dest_idx else "KB"

        for i, evt in enumerate(bp.charge_events):
            is_last = (i == len(bp.charge_events) - 1)
            rows.append({
                "Bus ID": bp.bus_id,
                "Operator": bp.operator.upper(),
                "Dir": direction,
                "Station": evt.station,
                "Arrive": minutes_to_hhmm(evt.arrive_min),
                "Wait (min)": evt.wait_min,
                "Charge Start": minutes_to_hhmm(evt.start_min),
                "Charge End": minutes_to_hhmm(evt.end_min),
                "Final Arrival": minutes_to_hhmm(bp.arrival_min) if is_last else "",
                "Charges #": len(bp.charge_events),
                "Total Wait": bp.total_wait if is_last else None,  # None → NaN (numeric, not str)
            })

        # If a bus somehow has no charge events (should be caught by validator)
        if not bp.charge_events:
            rows.append({
                "Bus ID": bp.bus_id,
                "Operator": bp.operator.upper(),
                "Dir": direction,
                "Station": "—",
                "Arrive": "—",
                "Wait (min)": 0,
                "Charge Start": "—",
                "Charge End": "—",
                "Final Arrival": minutes_to_hhmm(bp.arrival_min),
                "Charges #": 0,
                "Total Wait": 0,
            })

    df = pd.DataFrame(rows)
    # Keep Total Wait as a pure numeric column (Int64 allows NaN without object dtype)
    df["Total Wait"] = pd.to_numeric(df["Total Wait"], errors="coerce").astype("Int64")
    return df


# ---------------------------------------------------------------------------
# Per-station view
# ---------------------------------------------------------------------------

def to_station_table(result: ScheduleResult, node: str) -> pd.DataFrame:
    """
    Build the charge-order DataFrame for a single station.

    Rows are sorted by charge start time so a reviewer can judge whether the
    ordering is sensible given the active weights.

    Columns: Order | Bus ID | Operator | Charger # | Arrive | Wait (min) | Start | End

    Args:
        result: The ScheduleResult from the engine.
        node:   The station node name (e.g. "A", "B", "C", "D").

    Returns:
        A pandas DataFrame for this station, or empty DataFrame if no charges occurred.
    """
    slots = result.station_order.get(node, [])
    if not slots:
        return pd.DataFrame(columns=[
            "Order", "Bus ID", "Operator", "Charger #",
            "Arrive", "Wait (min)", "Charge Start", "Charge End",
        ])

    rows = []
    for i, slot in enumerate(slots, start=1):
        # Look up arrive_min from the bus plan
        arrive_str = "—"
        for bp in result.bus_plans:
            if bp.bus_id == slot.bus_id:
                for evt in bp.charge_events:
                    if evt.station == node and evt.start_min == slot.start_min:
                        arrive_str = minutes_to_hhmm(evt.arrive_min)
                        break
                break

        rows.append({
            "Order": i,
            "Bus ID": slot.bus_id,
            "Operator": slot.operator.upper(),
            "Charger #": slot.charger_index + 1,  # 1-indexed for display
            "Arrive": arrive_str,
            "Wait (min)": slot.wait_min,
            "Charge Start": minutes_to_hhmm(slot.start_min),
            "Charge End": minutes_to_hhmm(slot.end_min),
        })

    return pd.DataFrame(rows)
