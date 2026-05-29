"""
scheduler/physics.py — Pure travel-time arithmetic.

All time and distance calculations live here so they can be unit-tested in
isolation without instantiating a full Scenario.

References:
    docs/00-requirements/01-requirements-analysis.md  §2 (physical world)
    docs/02-scheduler-engine/01-scheduling-logic.md   (step 1: base arrivals)
    docs/07-testing/01-testing-plan.md                (test_physics.py)

Assumption: speed is constant, no traffic, no speed variation (documented in
ARCHITECTURE.md and docs/00-requirements/01-requirements-analysis.md §2).
"""

from __future__ import annotations


def travel_minutes(distance_km: float, speed_kmph: float) -> float:
    """
    Compute travel time in minutes for a given distance and speed.

    travel_min = (distance_km / speed_kmph) × 60

    Examples:
        100 km @ 60 km/h → 100 min
        120 km @ 60 km/h → 120 min

    Raises:
        ValueError: if speed_kmph ≤ 0 (caller's responsibility to validate).
    """
    if speed_kmph <= 0:
        raise ValueError(f"speed_kmph must be > 0, got {speed_kmph}")
    return (distance_km / speed_kmph) * 60.0


def base_arrival_minutes(
    departure_min: int,
    cumulative_distance_km: float,
    speed_kmph: float,
) -> float:
    """
    Compute the wall-clock minute at which a bus arrives at a node if it
    travels without stopping — i.e., the physics-only (wait-free) arrival.

    This is used in step 1 of the scheduling algorithm to establish a lower
    bound on arrival time before charger waits are factored in.

    Args:
        departure_min:          Departure time in minutes from midnight.
        cumulative_distance_km: Distance from the bus's origin to the target node.
        speed_kmph:             Assumed travel speed (from World.speed_kmph).

    Returns:
        Float minute value (may be fractional; the engine rounds when needed).
    """
    return departure_min + travel_minutes(cumulative_distance_km, speed_kmph)


def minutes_to_hhmm(minutes: float) -> str:
    """
    Convert an integer or float minute count (from midnight) to HH:MM string.

    Used only by the adapter layer for display; the engine always works in
    integer minutes to keep arithmetic clean (docs/03-data-model/02-scenario-schema.md).

    Examples:
        1140 → "19:00"
        1205 → "20:05"
    """
    total_minutes = int(round(minutes))
    hh = (total_minutes // 60) % 24
    mm = total_minutes % 60
    return f"{hh:02d}:{mm:02d}"


def leg_distance(
    route_positions: dict[str, float],
    from_node: str,
    to_node: str,
) -> float:
    """
    Return the absolute distance between two route nodes using the pre-computed
    cumulative-position map from Route.positions.

    Works for both directions (BK and KB) because positions are stored relative
    to route nodes[0]; absolute difference handles reverse direction.
    """
    return abs(route_positions[to_node] - route_positions[from_node])
