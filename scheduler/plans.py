from __future__ import annotations

from itertools import combinations
from typing import List, Tuple

from scheduler.model import Bus, Scenario


Plan = Tuple[str, ...]


def downstream_stations(bus: Bus, scenario: Scenario) -> List[str]:
    nodes = list(scenario.route.nodes)
    origin_idx = nodes.index(bus.origin)
    dest_idx = nodes.index(bus.destination)

    if origin_idx < dest_idx:

        segment = nodes[origin_idx + 1 : dest_idx]
    else:

        segment = nodes[dest_idx + 1 : origin_idx][::-1]


    return [n for n in segment if n in scenario.stations]


def candidate_plans(bus: Bus, scenario: Scenario) -> List[Plan]:
    stations = downstream_stations(bus, scenario)
    if not stations:
        return []

    positions = scenario.route.positions
    bus_range = bus.range_km
    feasible: List[Plan] = []


    for size in range(1, len(stations) + 1):
        for combo in combinations(stations, size):

            plan = combo
            if _is_range_feasible(plan, bus, positions, bus_range):
                feasible.append(plan)


    feasible.sort(key=lambda p: (len(p), p))
    return feasible


def _is_range_feasible(
    plan: Plan,
    bus: Bus,
    positions: dict[str, float],
    max_range: float,
) -> bool:

    stop_positions = [positions[bus.origin]]
    for node in plan:
        stop_positions.append(positions[node])
    stop_positions.append(positions[bus.destination])


    for i in range(len(stop_positions) - 1):
        leg = abs(stop_positions[i + 1] - stop_positions[i])
        if leg > max_range:
            return False

    return True
