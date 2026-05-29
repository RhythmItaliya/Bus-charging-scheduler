"""
scheduler/plans.py — Candidate charging plan enumeration.

For each bus, enumerates every range-feasible, route-ordered subset of the bus's
downstream stations.  This is the "search space" the engine iterates over when
selecting the cheapest plan for each bus.

Verified feasibility sets (docs/00-requirements/01-requirements-analysis.md §4):
  Bengaluru→Kochi (positions A=100, B=220, C=320, D=440, Kochi=540):
    - First charge must be A or B (C=320 > 240 km range).
    - Valid 2-charge plans: {A,C}, {B,C}, {B,D}
      ({A,D} invalid: A→D = 340 > 240)
  Kochi→Bengaluru: mirrors above (reversed positions).

References:
    docs/02-scheduler-engine/01-scheduling-logic.md  (step 2: candidate plans)
    docs/00-requirements/02-constraints-and-rules.md (H1, H2)
    docs/07-testing/01-testing-plan.md               (test_plans.py)
"""

from __future__ import annotations

from itertools import combinations
from typing import List, Tuple

from scheduler.model import Bus, Scenario


# Type alias: a plan is an ordered tuple of station node names.
Plan = Tuple[str, ...]


def downstream_stations(bus: Bus, scenario: Scenario) -> List[str]:
    """
    Return the list of charging-eligible stations for a bus, in travel order.

    A station is downstream if it lies between (exclusive) the bus's origin and
    destination along the route.  Endpoints are never charging stations (R7).

    Args:
        bus:      The bus whose downstream stations to find.
        scenario: The fully-loaded scenario (contains route and station map).

    Returns:
        Ordered list of station node names in the bus's direction of travel.
    """
    nodes = list(scenario.route.nodes)
    try:
        origin_idx = nodes.index(bus.origin)
        dest_idx = nodes.index(bus.destination)
    except ValueError as exc:
        raise ValueError(
            f"bus '{bus.id}': origin or destination not in route nodes."
        ) from exc

    # Travel direction: may be forward (BK) or backward (KB)
    if origin_idx < dest_idx:
        # Bengaluru → Kochi direction
        segment = nodes[origin_idx + 1: dest_idx]
    else:
        # Kochi → Bengaluru direction (reversed)
        segment = nodes[dest_idx + 1: origin_idx][::-1]

    # Only keep nodes that are actual charging stations in this scenario
    return [n for n in segment if n in scenario.stations]


def candidate_plans(bus: Bus, scenario: Scenario) -> List[Plan]:
    """
    Enumerate all range-feasible, route-ordered subsets of downstream stations.

    A plan is feasible iff every leg (origin → first charge, charge → charge,
    last charge → destination) is ≤ bus.range_km (hard rule H1).

    The minimum plan size is 1 charge, but because a through-trip (540 km)
    exceeds 240 km range, plans with < 2 charges will be range-infeasible and
    will be filtered out — enforcing R15 without special-casing it.

    Plans are returned ordered: shortest first, then lexicographic by station
    names.  Tie-breaking within the engine prefers fewer charges when cost
    is equal (docs/02-scheduler-engine/01-scheduling-logic.md, edge handling).

    Args:
        bus:      The bus to generate plans for.
        scenario: The fully-loaded scenario.

    Returns:
        List of feasible plans, each a tuple of station names in route order.
        Empty list if NO feasible plan exists (infeasible bus — caller must
        raise a surfaced error, not silently continue).
    """
    stations = downstream_stations(bus, scenario)
    if not stations:
        return []

    positions = scenario.route.positions
    bus_range = bus.range_km  # per-bus range, defaults to world.battery_range_km
    feasible: List[Plan] = []

    # Enumerate all non-empty subsets, from size 1 upward
    for size in range(1, len(stations) + 1):
        for combo in combinations(stations, size):
            plan = combo  # already in route order because downstream_stations preserves it
            if _is_range_feasible(plan, bus, positions, bus_range):
                feasible.append(plan)

    # Sort: by length first (prefer fewer charges on equal cost), then lexicographic
    feasible.sort(key=lambda p: (len(p), p))
    return feasible


def _is_range_feasible(
    plan: Plan,
    bus: Bus,
    positions: dict[str, float],
    max_range: float,
) -> bool:
    """
    Check whether a charging plan satisfies the range constraint on every leg.

    Legs evaluated:
      • origin → first station in plan
      • consecutive stations in plan
      • last station in plan → destination

    All legs must be ≤ max_range.

    Returns:
        True if every leg is within range; False otherwise.
    """
    origin_pos = positions[bus.origin]
    dest_pos = positions[bus.destination]

    # Build the full stop sequence: [origin] + plan stations + [destination]
    stop_positions = [origin_pos]
    for node in plan:
        stop_positions.append(positions[node])
    stop_positions.append(dest_pos)

    # Check every consecutive leg
    for i in range(len(stop_positions) - 1):
        leg = abs(stop_positions[i + 1] - stop_positions[i])
        if leg > max_range:
            return False  # hard rule H1 violated

    return True
