from __future__ import annotations

from typing import List

from scheduler.model import BusPlan, Scenario, ScheduleResult
from scheduler.logger import log


def validate(result: ScheduleResult, scenario: Scenario) -> List[str]:
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
    bus = next(b for b in scenario.buses if b.id == bp.bus_id)


    if len(bp.charge_events) == 0:
        total_dist = abs(positions[bus.destination] - positions[bus.origin])
        if total_dist > max_range:
            violations.append(
                f"{bp.bus_id}: through-bus has 0 charge events but trip "
                f"distance {total_dist} km exceeds range {max_range} km."
            )


    stops = [bus.origin] + [e.station for e in bp.charge_events] + [bus.destination]
    stop_positions = [positions[n] for n in stops]


    for i in range(len(stop_positions) - 1):
        leg = abs(stop_positions[i + 1] - stop_positions[i])
        if leg > max_range:
            violations.append(
                f"{bp.bus_id}: leg {stops[i]}→{stops[i+1]} = {leg:.1f} km "
                f"exceeds range {max_range} km (H1 violation)."
            )


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


    for evt in bp.charge_events:
        duration = evt.end_min - evt.start_min
        if duration != charge_minutes:
            violations.append(
                f"{bp.bus_id} @ {evt.station}: charge duration {duration} min "
                f"≠ expected {charge_minutes} min (H4 violation)."
            )


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

    for node, station in scenario.stations.items():
        num_chargers = station.num_chargers

        intervals = []
        for bp in result.bus_plans:
            for evt in bp.charge_events:
                if evt.station == node:
                    intervals.append((evt.start_min, evt.end_min, bp.bus_id))

        if not intervals:
            continue


        events = []
        for start, end, bus_id in intervals:
            events.append((start, +1, bus_id))
            events.append((end, -1, bus_id))

        events.sort(key=lambda x: (x[0], x[1]))

        concurrent = 0
        for time, delta, bus_id in events:
            concurrent += delta
            if concurrent > num_chargers:
                violations.append(
                    f"Station {node}: {concurrent} buses charging simultaneously "
                    f"at minute {time} but num_chargers={num_chargers} (H3 violation)."
                )
                break
