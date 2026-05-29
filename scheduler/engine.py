"""
scheduler/engine.py — The core scheduling algorithm (deterministic event-driven greedy).

This is the heart of the system.  Given a validated Scenario, it produces a
ScheduleResult deterministically.  It has zero Streamlit imports, no global
mutable state, and can be run headless:

    python -m scheduler.engine data/scenarios/scenario_1.json

Algorithm (docs/02-scheduler-engine/01-scheduling-logic.md):
  Step 1: Compute wait-free base arrivals for every bus at every node.
  Step 2: Enumerate candidate plans for each bus (range-feasible, route-ordered).
  Step 3: Sort buses by deterministic key: priority DESC → departure ASC → id ASC.
  Step 4: For each bus, evaluate all candidate plans; commit the lowest-cost feasible
          plan, persisting charger reservations.
  Step 5: Assemble BusPlan timelines and station_order.
  Step 6: Run validate() — raise if any invariant is violated.

References:
    docs/02-scheduler-engine/01-scheduling-logic.md   (full algorithm spec)
    docs/02-scheduler-engine/04-conflict-resolution.md (conflict resolution)
    docs/00-requirements/02-constraints-and-rules.md   (hard/soft rules)
    docs/04-api-contracts/01-internal-api-contracts.md (public contract)
"""

from __future__ import annotations

import math
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
from scheduler.physics import base_arrival_minutes
from scheduler.plans import candidate_plans
from scheduler.resources import ChargerPool
from scheduler.rules.registry import ScheduleContext, get_registry


# ---------------------------------------------------------------------------
# Direction helper
# ---------------------------------------------------------------------------

def _bus_direction(bus: Bus, scenario: Scenario) -> str:
    """Return 'BK' (Bengaluru→Kochi) or 'KB' (Kochi→Bengaluru)."""
    nodes = scenario.route.nodes
    origin_idx = list(nodes).index(bus.origin)
    dest_idx = list(nodes).index(bus.destination)
    return "BK" if origin_idx < dest_idx else "KB"


# ---------------------------------------------------------------------------
# Timeline simulation for a given plan
# ---------------------------------------------------------------------------

def _simulate_plan(
    bus: Bus,
    plan: Tuple[str, ...],
    pools: Dict[str, ChargerPool],
    scenario: Scenario,
) -> List[dict]:
    """
    Walk a bus through its plan and return a list of provisional charge-event dicts.

    Each dict has keys: station, arrive_min, start_min, wait_min, end_min,
    charger_index — matching the ChargeEvent fields.

    This function is called TENTATIVELY: pools are modified by reserve() and
    must be rolled back if this plan is not committed.

    Args:
        bus:      The bus being planned.
        plan:     Ordered tuple of station nodes to charge at.
        pools:    The live ChargerPool map (modified in-place by reserve()).
        scenario: The full scenario.

    Returns:
        List of charge-event dicts in route order.
    """
    positions = scenario.route.positions
    world = scenario.world
    charge_events = []
    # current_time tracks when the bus is free (starts at departure)
    current_time: float = bus.departure_min

    for station in plan:
        # Physics-only arrival at this station from current_time position
        # (current_time after the previous charge end, or departure for first stop)
        # We need to know where the bus currently "is" — which is the previous node.
        # For simplicity, compute arrival = current_time + travel from previous stop.
        # Track the previous node through the loop.
        pass

    # Simpler re-implementation using cumulative position arithmetic:
    # After each charge, the bus's "time" = end_min; its position = station.
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
    """Compute the bus's final arrival minute at its destination."""
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def schedule(scenario: Scenario) -> ScheduleResult:
    """
    Run the deterministic event-driven greedy scheduler on a scenario.

    This is a pure function: no I/O, no global state, idempotent for identical
    input.  Given identical scenario + weights → identical ScheduleResult.

    Args:
        scenario: A validated Scenario (from loader.load_scenario).

    Returns:
        A fully-populated ScheduleResult.

    Raises:
        ValueError: if any bus has no feasible charging plan.
        RuntimeError: if the post-schedule validator detects a hard-rule violation
                      (indicates an engine bug; should never occur with valid data).
    """
    registry = get_registry()

    # --- Step 1: Initialise charger pools (one per station) ---
    pools: Dict[str, ChargerPool] = {
        node: ChargerPool(
            node=node,
            num_chargers=station.num_chargers,
            charge_minutes=scenario.world.charge_minutes,
        )
        for node, station in scenario.stations.items()
    }

    # --- Step 2 & 3: Sort buses by deterministic key (R determinism) ---
    # priority DESC → departure_min ASC → id ASC
    sorted_buses: List[Bus] = sorted(
        scenario.buses,
        key=lambda b: (-b.priority, b.departure_min, b.id),
    )

    # --- Step 4: Greedy commitment ---
    committed_plans: List[BusPlan] = []

    for bus in sorted_buses:
        plans = candidate_plans(bus, scenario)
        if not plans:
            raise ValueError(
                f"Bus '{bus.id}' has no feasible charging plan.  "
                f"Check that its range ({bus.range_km} km) is sufficient for the route."
            )

        best_plan: Optional[Tuple] = None
        best_events: Optional[List[dict]] = None
        best_cost = math.inf
        best_breakdown: dict = {}

        direction = _bus_direction(bus, scenario)

        for plan in plans:
            # Snapshot pool state for rollback
            snapshots = {node: pool.snapshot() for node, pool in pools.items()}

            # Tentatively simulate and score this plan
            events = _simulate_plan(bus, plan, pools, scenario)
            arrival = _compute_arrival(bus, events, scenario)

            # Build a provisional BusPlan-like object for scoring context
            tentative_bus_plan_wait = sum(e["wait_min"] for e in events)

            ctx = ScheduleContext(
                bus_id=bus.id,
                plan=plan,
                charge_events=events,
                all_committed=committed_plans,
                scenario=scenario,
                weights=scenario.weights,
            )
            feasible, cost, breakdown = score(ctx, registry)

            # Rollback pool state (tentative reservation removed)
            for node, snap in snapshots.items():
                pools[node].restore(snap)

            if not feasible:
                continue  # plan violates a hard rule — skip

            # Tie-break: cost asc → fewer charges → earlier finishing → lex plan
            is_better = cost < best_cost
            if cost == best_cost and best_plan is not None:
                # Tie-break: prefer fewer charges
                if len(plan) < len(best_plan):
                    is_better = True
                elif len(plan) == len(best_plan):
                    # Further tie-break: earlier last arrival
                    best_arrival = _compute_arrival(bus, best_events, scenario)
                    if arrival < best_arrival:
                        is_better = True
                    elif arrival == best_arrival:
                        # Final tie-break: lexicographic plan order
                        if plan < best_plan:
                            is_better = True

            if is_better:
                best_plan = plan
                best_events = events
                best_cost = cost
                best_breakdown = breakdown

        if best_plan is None:
            raise ValueError(
                f"Bus '{bus.id}': all candidate plans are infeasible after scoring.  "
                f"This indicates a data or rule configuration error."
            )

        # Commit the best plan — re-simulate (actually reserve slots permanently)
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

    # --- Step 5: Assemble station_order ---
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

    # Sort each station's list by charge start time
    for node in station_order:
        station_order[node].sort(key=lambda s: s.start_min)

    # --- Step 6: Compute final objective breakdown ---
    # Re-score against the full committed schedule for display
    final_breakdown: Dict[str, float] = {}
    total_individual = sum(bp.total_wait for bp in committed_plans)
    final_breakdown["IndividualWaitRule"] = scenario.weights.individual * total_individual

    import statistics as _stats
    op_waits: Dict[str, List[int]] = {}
    for bp in committed_plans:
        op_waits.setdefault(bp.operator, []).append(bp.total_wait)
    op_variance = sum(
        _stats.variance(waits) if len(waits) > 1 else 0.0
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

    # --- Step 6: Post-schedule validation (defence in depth) ---
    from scheduler import validate as _validate
    violations = _validate.validate(result, scenario)
    if violations:
        raise RuntimeError(
            f"Post-schedule validation failed ({len(violations)} violation(s)):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json
    from scheduler.loader import load_scenario

    if len(sys.argv) < 2:
        print("Usage: python -m scheduler.engine <scenario.json>")
        sys.exit(1)

    _scenario = load_scenario(sys.argv[1])
    _result = schedule(_scenario)
    print(f"Scheduled {len(_result.bus_plans)} buses. "
          f"Total objective: {_result.total_objective:.1f}")
    print("Objective breakdown:", _result.objective_breakdown)
