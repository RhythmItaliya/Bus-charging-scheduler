from __future__ import annotations

import pandas as pd

from scheduler.model import Scenario, ScheduleResult
from scheduler.physics import minutes_to_hhmm


def to_input_table(scenario: Scenario) -> pd.DataFrame:
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


def to_bus_table(result: ScheduleResult, scenario: Scenario) -> pd.DataFrame:
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
                "Total Wait": str(bp.total_wait) if is_last else "",
            })


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

    return pd.DataFrame(rows)


def to_station_table(result: ScheduleResult, node: str) -> pd.DataFrame:
    slots = result.station_order.get(node, [])
    if not slots:
        return pd.DataFrame(columns=[
            "Order", "Bus ID", "Operator", "Charger #",
            "Arrive", "Wait (min)", "Charge Start", "Charge End",
        ])

    rows = []
    for i, slot in enumerate(slots, start=1):

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
            "Charger #": slot.charger_index + 1,
            "Arrive": arrive_str,
            "Wait (min)": slot.wait_min,
            "Charge Start": minutes_to_hhmm(slot.start_min),
            "Charge End": minutes_to_hhmm(slot.end_min),
        })

    return pd.DataFrame(rows)
