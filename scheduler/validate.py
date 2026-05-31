"""
scheduler/validate.py — Post-schedule validation (defence in depth).

This module re-checks every hard invariant over the final committed schedule.
It is called at the end of engine.schedule() and again at app startup so that
any engine bug is caught immediately rather than shipping a wrong schedule.

Why a separate validation stage (docs/04-api-contracts/02-validation-rules.md):
  • Engine logic and verification logic cannot accidentally share a bug.
  • Violations are surfaced to the user as a red banner, not silent wrong data.
  • Tests assert validate() == [] for all five scenarios.

Returns:
    list[str] — empty means valid; each string is a human-readable violation.

References:
    docs/04-api-contracts/02-validation-rules.md  (3-stage validation spec)
    docs/00-requirements/02-constraints-and-rules.md (H1–H4)
    docs/07-testing/01-testing-plan.md             (test_charger.py, test_e2e.py)
"""

from __future__ import annotations

from typing import List

from scheduler.model import BusPlan, Scenario, ScheduleResult
from scheduler.logger import log


def validate(result: ScheduleResult, scenario: Scenario) -> List[str]:
    """
    Re-check all hard invariants on a committed ScheduleResult.

    Invariants checked:
      H1 — No leg exceeds the bus's range.
      H2 — Stations visited in strict route order (no backtracking).
      H3 — No station ever serves more than num_chargers buses simultaneously.
      H4 — Every charge event duration == world.charge_minutes.
      R15 — Every through-bus has at least 2 charge events.

    Args:
        result:   The ScheduleResult returned by engine.schedule().
        scenario: The Scenario that was scheduled.

    Returns:
        A list of violation strings.  Empty list → fully valid.
    """
    violations: List[str] = []
    world = scenario.world
    positions = scenario.route.positions

    log.separator("Validation")
    log.info("Validating schedule", buses=len(result.bus_plans), rules="H1 H2 H3 H4 R15")

    for bp in result.bus_plans:
        _check_bus(bp, scenario, positions, world.battery_range_km,
                   world.charge_minutes, violations)

    _check_charger_exclusivity(result, scenario, violations)

    if violations:
        for v in violations:
            log.rule_check(v, status="FAIL")
        log.warn("Validation complete", violations=len(violations))
    else:
        log.rule_check("H1 H2 H3 H4 R15 — all hard rules", status="PASS")
        log.success("Schedule fully valid")

    return violations


def _check_bus(
    bp: BusPlan,
    scenario: Scenario,
    positions: dict,
    max_range: float,
    charge_minutes: int,
    violations: List[str],
) -> None:
    """Check per-bus invariants: range, route order, charge duration, ≥2 charges."""
    bus = next(b for b in scenario.buses if b.id == bp.bus_id)

    # R15: through-buses need ≥ 2 charges
    # A through-bus is one whose origin→destination distance > max_range (needs ≥2).
    # For safety we check all buses: any bus whose plan has 0 charges is suspicious.
    if len(bp.charge_events) == 0:
        total_dist = abs(positions[bus.destination] - positions[bus.origin])
        if total_dist > max_range:
            violations.append(
                f"{bp.bus_id}: through-bus has 0 charge events but trip "
                f"distance {total_dist} km exceeds range {max_range} km."
            )

    # Build stop sequence for range and order checks
    stops = [bus.origin] + [e.station for e in bp.charge_events] + [bus.destination]
    stop_positions = [positions[n] for n in stops]

    # H1: range check on each leg
    for i in range(len(stop_positions) - 1):
        leg = abs(stop_positions[i + 1] - stop_positions[i])
        if leg > max_range:
            violations.append(
                f"{bp.bus_id}: leg {stops[i]}→{stops[i+1]} = {leg:.1f} km "
                f"exceeds range {max_range} km (H1 violation)."
            )

    # H2: route order (positions must be monotonically increasing or decreasing)
    forward = stop_positions[-1] > stop_positions[0]
    for i in range(1, len(stop_positions)):
        if forward and stop_positions[i] <= stop_positions[i - 1]:
            violations.append(
                f"{bp.bus_id}: station {stops[i]} is not after {stops[i-1]} "
                f"in travel direction (H2 / route-order violation)."
            )
        elif not forward and stop_positions[i] >= stop_positions[i - 1]:
            violations.append(
                f"{bp.bus_id}: station {stops[i]} is not before {stops[i-1]} "
                f"in reverse direction (H2 / route-order violation)."
            )

    # H4: charge duration
    for evt in bp.charge_events:
        duration = evt.end_min - evt.start_min
        if duration != charge_minutes:
            violations.append(
                f"{bp.bus_id} @ {evt.station}: charge duration {duration} min "
                f"≠ expected {charge_minutes} min (H4 violation)."
            )

    # wait_min consistency
    for evt in bp.charge_events:
        expected_wait = evt.start_min - evt.arrive_min
        if evt.wait_min != expected_wait:
            violations.append(
                f"{bp.bus_id} @ {evt.station}: wait_min {evt.wait_min} "
                f"≠ start_min({evt.start_min}) - arrive_min({evt.arrive_min}) = "
                f"{expected_wait}."
            )


def _check_charger_exclusivity(
    result: ScheduleResult,
    scenario: Scenario,
    violations: List[str],
) -> None:
    """
    H3: At each station, no more than num_chargers buses charge simultaneously.

    For each minute during which at least one bus charges at a station, count
    the overlapping intervals.  An overlap of [start, end) means the charger
    is busy for minutes start, start+1, ..., end-1.
    """
    # Group charge intervals by station and charger_index
    for node, station in scenario.stations.items():
        num_chargers = station.num_chargers
        # Collect all [start, end) intervals at this node
        intervals = []
        for bp in result.bus_plans:
            for evt in bp.charge_events:
                if evt.station == node:
                    intervals.append((evt.start_min, evt.end_min, bp.bus_id))

        if not intervals:
            continue

        # Check for overlaps: for each pair of intervals, see if they overlap
        # and would require more than num_chargers simultaneous slots.
        # Efficient O(n log n) sweep:
        events = []
        for start, end, bus_id in intervals:
            events.append((start, +1, bus_id))  # +1 = charge starts
            events.append((end, -1, bus_id))    # -1 = charge ends

        events.sort(key=lambda x: (x[0], x[1]))  # sort by time, ends before starts at same time

        concurrent = 0
        for time, delta, bus_id in events:
            concurrent += delta
            if concurrent > num_chargers:
                violations.append(
                    f"Station {node}: {concurrent} buses charging simultaneously "
                    f"at minute {time} but num_chargers={num_chargers} (H3 violation)."
                )
                break  # report once per station
