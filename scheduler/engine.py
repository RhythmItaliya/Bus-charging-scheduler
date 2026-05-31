"""
scheduler/engine.py  —  The core scheduling algorithm.

WHAT THIS FILE DOES:
  This is the heart of the whole system. It takes a Scenario (all the input data)
  and produces a ScheduleResult (the complete charging schedule).

  Algorithm name: "Deterministic Event-Driven Greedy Scheduler"

  GREEDY means: we schedule one bus at a time, always picking the
  cheapest plan for that bus given what's already been committed.

  EVENT-DRIVEN means: we simulate the timeline of charge events
  (a bus arrives, waits, charges, leaves) rather than solving equations.

  DETERMINISTIC means: the same input always produces the same output.
  There is no randomness — every run gives exactly the same schedule.

HOW TO RUN AS A CLI (great for interview demo):
  python -m scheduler.engine data/scenarios/scenario_1.json
  → Shows the full scheduling process with rich coloured tables in the terminal.

ALGORITHM STEPS:
  Step 1: Initialise one ChargerPool per station (manages who charges when).
  Step 2: Sort buses by: priority (high first) → departure_min (early first) → id (alphabetical).
  Step 3: For each bus, try all candidate charging plans.
           For each plan:
             a. Simulate the plan (tentatively reserve charger slots).
             b. Score the plan using all rules (hard + soft).
             c. Roll back the tentative reservation.
          Commit the plan with the lowest cost.
  Step 4: Build the station_order output.
  Step 5: Compute the final objective score breakdown.
  Step 6: Post-validate the schedule (defence in depth).

PDF reference: Page 4, "The one thing we really care about"
  "Adding a new rule must not require rewriting the engine — just defining the new rule."
  → Engine uses a pluggable rule registry. Never imports rule classes directly.

PDF reference: Page 9, "The scheduler"
  "Decides each bus's charging plan and the ORDER in which buses use each station"

INTERVIEW TALKING POINT:
  "The greedy approach is the right fit for this problem because:
   1. Only 20 buses and 4 stations — the search space is tiny.
   2. Each bus has at most 3-4 valid plans, so evaluation is fast.
   3. The algorithm is fully explainable — every decision is traceable.
   4. Adding a new rule only requires a new file, never an engine edit."
"""

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

    log.scenario(
        scenario.name,
        buses=len(scenario.buses),
        stations=len(scenario.intermediate_nodes),
        weights=f"ind={scenario.weights.individual} op={scenario.weights.operator} all={scenario.weights.overall}",
    )

    # ── Step 1: Create a ChargerPool for every charging station ──────────────
    # A ChargerPool manages the queue at one station.
    # It tracks when each charger slot is free and assigns buses to slots.
    # PDF reference: Page 1 — "Each station has 1 charger"
    # Future change: set num_chargers=2 in JSON to allow 2 buses simultaneously.
    pools: Dict[str, ChargerPool] = {
        node: ChargerPool(
            node=node,
            num_chargers=station.num_chargers,
            charge_minutes=scenario.world.charge_minutes,
        )
        for node, station in scenario.stations.items()
    }

    # ── Step 2: Sort buses into scheduling order ──────────────────────────────
    # Sorting rule: priority DESC → departure_min ASC → id ASC
    #
    # WHY THIS ORDER?
    #   - Buses with higher priority (e.g., VIP buses) get scheduled first.
    #   - Among equal-priority buses, earlier departures go first
    #     (they arrive at stations first, so they should be scheduled first).
    #   - id as tiebreaker guarantees determinism (same result every run).
    #
    # PDF reference: Page 4 — "Growing the world (more buses) must not need a rewrite"
    # → Priority field is already in the Bus model for future VIP buses.
    sorted_buses: List[Bus] = sorted(
        scenario.buses,
        key=lambda b: (-b.priority, b.departure_min, b.id),
    )

    # ── Step 3: Greedy commitment — schedule one bus at a time ───────────────
    # This is the main loop of the scheduling algorithm.
    # For each bus (in priority/departure order), we:
    #   a) Get all valid charging plans
    #   b) Try each plan, score it, roll back
    #   c) Commit the cheapest feasible plan permanently
    #
    # INTERVIEW TALKING POINT:
    # "Greedy means we pick the best plan for the current bus given what
    #  has already been committed. We don't look ahead to future buses.
    #  This is fast and the decisions are fully explainable."
    committed_plans: List[BusPlan] = []

    log.separator("Scheduling buses")

    for bus in sorted_buses:
        # Get all physically possible charging plans for this bus.
        # Example: BK bus might have plans [("A","C"), ("B","C"), ("B","D")]
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
            # ── Snapshot pool state so we can roll back ──────────────────────
            # We are just TESTING this plan — not committing it yet.
            # Save the current state of all charger pools before we try.
            snapshots = {node: pool.snapshot() for node, pool in pools.items()}

            # ── Simulate this plan (tentative) ───────────────────────────────
            # Walk the bus through its charging stops, reserving charger slots.
            # This modifies the pool state — we will roll it back after scoring.
            events = _simulate_plan(bus, plan, pools, scenario)
            arrival = _compute_arrival(bus, events, scenario)

            # ── Score this plan using all rules ──────────────────────────────
            # The ScheduleContext packages everything a rule needs to evaluate this plan.
            # Rules read scenario data, committed plans, and this plan's charge events.
            ctx = ScheduleContext(
                bus_id=bus.id,
                plan=plan,
                charge_events=events,
                all_committed=committed_plans,
                scenario=scenario,
                weights=scenario.weights,
            )
            feasible, cost, breakdown = score(ctx, registry)

            # ── Roll back pool state ─────────────────────────────────────────
            # This plan was just a test. Remove the tentative reservations.
            # The winning plan will be re-simulated (permanently) below.
            for node, snap in snapshots.items():
                pools[node].restore(snap)

            if not feasible:
                continue  # this plan violates a hard rule → skip it

            # ── Compare to current best plan ─────────────────────────────────
            # Lower cost = better plan.
            # Tie-break: fewer charges → earlier arrival → lexicographic order.
            # These tie-breaks ensure determinism when two plans have equal cost.
            is_better = cost < best_cost
            if cost == best_cost and best_plan is not None:
                if len(plan) < len(best_plan):
                    is_better = True  # fewer charges is better (less time charging)
                elif len(plan) == len(best_plan):
                    best_arrival = _compute_arrival(bus, best_events, scenario)
                    if arrival < best_arrival:
                        is_better = True  # earlier arrival is better
                    elif arrival == best_arrival:
                        if plan < best_plan:
                            is_better = True  # alphabetical tiebreaker for determinism

            if is_better:
                best_plan = plan
                best_events = events
                best_cost = cost

        if best_plan is None:
            raise ValueError(
                f"Bus '{bus.id}': all candidate plans are infeasible after scoring. "
                f"This indicates a data or rule configuration error."
            )

        # ── Commit the winning plan permanently ──────────────────────────────
        # Re-simulate the best plan — this time the charger pool reservations
        # are permanent (not rolled back). The bus is now "scheduled".
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
        # Log one line per bus showing what plan was chosen and how long it waits.
        # This is the most useful output for understanding the algorithm step by step.
        log.bus_committed(
            bus.id,
            plan=best_plan,
            wait=total_wait,
            arrival=minutes_to_hhmm(final_arrival),
            operator=bus.operator,
        )

    # ── Step 4: Assemble the per-station charge order ─────────────────────────
    # Build a dict: station_name → [list of StationSlot sorted by start time]
    # This is what the "Per-Station Order" tab shows in the UI.
    # PDF reference: Page 9 — "per-station view: for each of A,B,C,D, show the order"
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

    # ── Step 5: Compute the final objective score breakdown ───────────────────
    # Now that all buses are committed, compute the final aggregate scores.
    # These are displayed in the UI's "Objective breakdown" expander.
    # PDF reference: Page 4, "What to optimize for" (S1, S2, S3)
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

    # --- Step 6: Post-schedule validation (defence in depth) ---
    violations = _validate.validate(result, scenario)
    if violations:
        for v in violations:
            log.error(f"Validation failure: {v}")
        raise RuntimeError(
            f"Post-schedule validation failed ({len(violations)} violation(s)):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    # Print a beautiful table showing the objective score breakdown.
    # PDF reference: Page 4 — "three soft rules" S1, S2, S3
    log.separator("Objective Score Breakdown")
    log.objective_table(final_breakdown, total_objective)
    log.success(
        f"Schedule complete — {len(committed_plans)} buses",
        objective=f"{total_objective:,.1f}",
        total_wait=f"{sum(bp.total_wait for bp in committed_plans)} min",
    )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

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
