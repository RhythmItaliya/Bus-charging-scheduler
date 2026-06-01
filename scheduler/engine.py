from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from scheduler.model import (
    BusPlan,
    Bus,
    ChargeEvent,
    Scenario,
    ScheduleResult,
    StationSlot,
)
from scheduler.objective import score
from scheduler.physics import minutes_to_hhmm
from scheduler.plans import candidate_plans
from scheduler.resources import ChargerPool
from scheduler.rules.registry import ScheduleContext, get_registry
from scheduler.logger import log
from scheduler import validate as _validate


def _bus_direction(bus: Bus, scenario: Scenario) -> str:
    nodes = scenario.route.nodes
    origin_idx = list(nodes).index(bus.origin)
    dest_idx = list(nodes).index(bus.destination)
    return "BK" if origin_idx < dest_idx else "KB"


def _simulate_plan(
    bus: Bus,
    plan: Tuple[str, ...],
    pools: Dict[str, ChargerPool],
    scenario: Scenario,
) -> List[dict]:
    positions = scenario.route.positions
    world = scenario.world
    charge_events = []
    current_time = float(bus.departure_min)
    prev_node = bus.origin

    for station in plan:
        dist = abs(positions[station] - positions[prev_node])
        travel = (dist / world.speed_kmph) * 60.0
        arrive_min = int(current_time + travel)

        start_min, wait_min, charger_idx = pools[station].reserve(arrive_min)
        end_min = start_min + world.charge_minutes

        charge_events.append({
            "station": station,
            "arrive_min": arrive_min,
            "start_min": start_min,
            "wait_min": wait_min,
            "end_min": end_min,
            "charger_index": charger_idx,
        })

        current_time = float(end_min)
        prev_node = station

    return charge_events


def _compute_arrival(
    bus: Bus,
    charge_events: List[dict],
    scenario: Scenario,
) -> int:
    positions = scenario.route.positions
    world = scenario.world

    if charge_events:
        last = charge_events[-1]
        dist = abs(positions[bus.destination] - positions[last["station"]])
        travel = (dist / world.speed_kmph) * 60.0
        return int(last["end_min"] + travel)
    else:
        dist = abs(positions[bus.destination] - positions[bus.origin])
        travel = (dist / world.speed_kmph) * 60.0
        return int(bus.departure_min + travel)


def schedule(scenario: Scenario) -> ScheduleResult:
    registry = get_registry()

    log.scenario(
        scenario.name,
        buses=len(scenario.buses),
        stations=len(scenario.intermediate_nodes),
        weights=f"ind={scenario.weights.individual} op={scenario.weights.operator} all={scenario.weights.overall}",
    )


    pools: Dict[str, ChargerPool] = {
        node: ChargerPool(
            node=node,
            num_chargers=station.num_chargers,
            charge_minutes=scenario.world.charge_minutes,
        )
        for node, station in scenario.stations.items()
    }


    sorted_buses: List[Bus] = sorted(
        scenario.buses,
        key=lambda b: (-b.priority, b.departure_min, b.id),
    )


    committed_plans: List[BusPlan] = []

    log.separator("Scheduling buses")

    for bus in sorted_buses:


        plans = candidate_plans(bus, scenario)
        if not plans:
            raise ValueError(
                f"Bus '{bus.id}' has no feasible charging plan. "
                f"Check that its range ({bus.range_km} km) is sufficient for the route."
            )

        best_plan: Optional[Tuple] = None
        best_events: Optional[List[dict]] = None
        best_cost = math.inf

        direction = _bus_direction(bus, scenario)

        for plan in plans:


            snapshots = {node: pool.snapshot() for node, pool in pools.items()}


            events = _simulate_plan(bus, plan, pools, scenario)
            arrival = _compute_arrival(bus, events, scenario)


            ctx = ScheduleContext(
                bus_id=bus.id,
                plan=plan,
                charge_events=events,
                all_committed=committed_plans,
                scenario=scenario,
                weights=scenario.weights,
            )
            feasible, cost, breakdown = score(ctx, registry)


            for node, snap in snapshots.items():
                pools[node].restore(snap)

            if not feasible:
                continue


            is_better = cost < best_cost
            if cost == best_cost and best_plan is not None:
                if len(plan) < len(best_plan):
                    is_better = True
                elif len(plan) == len(best_plan):
                    best_arrival = _compute_arrival(bus, best_events, scenario)
                    if arrival < best_arrival:
                        is_better = True
                    elif arrival == best_arrival:
                        if plan < best_plan:
                            is_better = True

            if is_better:
                best_plan = plan
                best_events = events
                best_cost = cost

        if best_plan is None:
            raise ValueError(
                f"Bus '{bus.id}': all candidate plans are infeasible after scoring. "
                f"This indicates a data or rule configuration error."
            )


        final_events = _simulate_plan(bus, best_plan, pools, scenario)
        final_arrival = _compute_arrival(bus, final_events, scenario)
        total_wait = sum(e["wait_min"] for e in final_events)

        charge_event_objects = [
            ChargeEvent(
                station=e["station"],
                arrive_min=e["arrive_min"],
                start_min=e["start_min"],
                wait_min=e["wait_min"],
                end_min=e["end_min"],
                charger_index=e["charger_index"],
            )
            for e in final_events
        ]

        bus_plan = BusPlan(
            bus_id=bus.id,
            operator=bus.operator,
            direction=direction,
            charge_events=charge_event_objects,
            arrival_min=final_arrival,
            total_wait=total_wait,
        )
        committed_plans.append(bus_plan)


        log.bus_committed(
            bus.id,
            plan=best_plan,
            wait=total_wait,
            arrival=minutes_to_hhmm(final_arrival),
            operator=bus.operator,
        )


    station_order: Dict[str, List[StationSlot]] = defaultdict(list)
    for bp in committed_plans:
        for evt in bp.charge_events:
            station_order[evt.station].append(
                StationSlot(
                    bus_id=bp.bus_id,
                    operator=bp.operator,
                    charger_index=evt.charger_index,
                    start_min=evt.start_min,
                    wait_min=evt.wait_min,
                    end_min=evt.end_min,
                )
            )


    for node in station_order:
        station_order[node].sort(key=lambda s: s.start_min)


    final_breakdown: Dict[str, float] = {}
    total_individual = sum(bp.total_wait for bp in committed_plans)
    final_breakdown["IndividualWaitRule"] = scenario.weights.individual * total_individual

    op_waits: Dict[str, List[int]] = {}
    for bp in committed_plans:
        op_waits.setdefault(bp.operator, []).append(bp.total_wait)
    op_variance = sum(
        statistics.variance(waits) if len(waits) > 1 else 0.0
        for waits in op_waits.values()
    )
    final_breakdown["OperatorRule"] = scenario.weights.operator * op_variance

    if committed_plans:
        all_arrivals = [bp.arrival_min for bp in committed_plans]
        all_departures = [b.departure_min for b in scenario.buses]
        makespan = max(all_arrivals) - min(all_departures)
    else:
        makespan = 0
    final_breakdown["OverallRule"] = scenario.weights.overall * makespan

    total_objective = sum(final_breakdown.values())

    result = ScheduleResult(
        bus_plans=committed_plans,
        station_order=dict(station_order),
        objective_breakdown=final_breakdown,
        total_objective=total_objective,
    )


    violations = _validate.validate(result, scenario)
    if violations:
        for v in violations:
            log.error(f"Validation failure: {v}")
        raise RuntimeError(
            f"Post-schedule validation failed ({len(violations)} violation(s)):\n"
            + "\n".join(f"  {v}" for v in violations)
        )


    log.separator("Objective Score Breakdown")
    log.objective_table(final_breakdown, total_objective)
    log.success(
        f"Schedule complete — {len(committed_plans)} buses",
        objective=f"{total_objective:,.1f}",
        total_wait=f"{sum(bp.total_wait for bp in committed_plans)} min",
    )

    return result


if __name__ == "__main__":
    import sys
    from scheduler.loader import load_scenario
    from scheduler.validate import validate

    if len(sys.argv) < 2:
        log.error("Usage: python -m scheduler.engine <scenario.json>")
        sys.exit(1)

    log.header("Bus Charging Scheduler — Engine Demo")
    log.info("Loading scenario", path=sys.argv[1])

    _scenario = load_scenario(sys.argv[1])
    _result = schedule(_scenario)
    _violations = validate(_result, _scenario)

    log.separator("Station Order")
    for node, slots in _result.station_order.items():
        log.schedule_table(node, slots)

    log.separator("Validation")
    if _violations:
        for v in _violations:
            log.rule_check(v, status="FAIL")
    else:
        log.rule_check("All hard rules", status="PASS")
        log.success("Schedule is fully valid — ready for submission")
