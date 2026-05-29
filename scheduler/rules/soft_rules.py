"""
scheduler/rules/soft_rules.py — Soft objective rules (penalty functions).

Three soft rules implement the weighted optimization objectives:
  S1 — IndividualWaitRule : penalise individual bus wait time.
  S2 — OperatorRule       : penalise uneven wait distribution within each operator fleet.
  S3 — OverallRule        : penalise network makespan.

Each rule returns a penalty that is already multiplied by its weight (read from
ctx.weights by key).  The engine never hardcodes a weight value anywhere.

Exact metric definitions: docs/02-scheduler-engine/03-optimization-rules.md
References:
    docs/00-requirements/02-constraints-and-rules.md  (S1–S3, tunability R23)
    docs/02-scheduler-engine/03-optimization-rules.md (pinned formulas)
    docs/07-testing/01-testing-plan.md                (test_rules.py, test_weights.py)
"""

from __future__ import annotations

import statistics
from typing import Dict, List

from scheduler.rules.registry import Rule, ScheduleContext, register


@register
class IndividualWaitRule(Rule):
    """
    S1 — Individual wait penalty.

    Default metric: w_ind · Σ_b wait(b) — sum of all charger-queue minutes across
    the full committed schedule plus the candidate bus's wait.  Directly penalises
    queueing so no single bus parks at a charger too long.

    Weight key: "individual".

    Documented alternative (toggle in code): w_ind · max_b wait(b) to target the
    worst-case bus specifically.  Default is sum.

    Ref: docs/02-scheduler-engine/03-optimization-rules.md §IndividualWaitRule
    """

    name = "IndividualWaitRule"
    kind = "soft"
    weight_key = "individual"

    def evaluate(self, ctx: ScheduleContext) -> float:
        """Return weighted sum of all bus wait times including the candidate bus."""
        weight = ctx.weights.get(self.weight_key)

        # Sum wait from previously committed buses
        committed_wait = sum(
            plan.total_wait for plan in ctx.all_committed
        )

        # Add candidate bus's wait from its provisional charge events
        candidate_wait = sum(e["wait_min"] for e in ctx.charge_events)

        total_wait = committed_wait + candidate_wait
        return weight * total_wait


@register
class OperatorRule(Rule):
    """
    S2 — Operator fairness penalty.

    Default metric: w_op · Σ_g Var_{b∈g}(wait(b)) — sum across operators of the
    within-fleet variance of per-bus wait.  Variance penalises *uneven* treatment
    inside an operator's fleet, which is exactly what "each operator's fleet runs
    smoothly as a group" means (R21).  This is also what makes Scenario 4 reshuffle
    visibly when operator weight changes (R28/R44).

    Weight key: "operator".

    Documented alternative: Σ_g Σ_{b∈g} wait(b) (total fleet wait, not variance).

    Ref: docs/02-scheduler-engine/03-optimization-rules.md §OperatorRule
    """

    name = "OperatorRule"
    kind = "soft"
    weight_key = "operator"

    def evaluate(self, ctx: ScheduleContext) -> float:
        """Return weighted sum of per-operator within-fleet wait variance."""
        weight = ctx.weights.get(self.weight_key)

        # Build operator→[wait] map from committed buses + candidate bus
        op_waits: Dict[str, List[int]] = {}

        for plan in ctx.all_committed:
            op_waits.setdefault(plan.operator, []).append(plan.total_wait)

        # Add the candidate bus
        candidate_bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        candidate_wait = sum(e["wait_min"] for e in ctx.charge_events)
        op_waits.setdefault(candidate_bus.operator, []).append(candidate_wait)

        # Compute variance per operator (0 for single-bus fleets)
        total_variance = 0.0
        for waits in op_waits.values():
            if len(waits) > 1:
                total_variance += statistics.variance(waits)
            # Single-bus fleet: variance = 0, no contribution

        return weight * total_variance


@register
class OverallRule(Rule):
    """
    S3 — Overall network time penalty.

    Default metric: w_all · makespan, where:
      makespan = max_b arrival(b) − min_b t0(b)

    Penalises the total clock spread of the operation — compressing makespan
    means the whole fleet finishes sooner.

    Weight key: "overall".

    Documented alternative: Σ_b (arrival(b) − t0(b)) (total person-time).

    Ref: docs/02-scheduler-engine/03-optimization-rules.md §OverallRule
    """

    name = "OverallRule"
    kind = "soft"
    weight_key = "overall"

    def evaluate(self, ctx: ScheduleContext) -> float:
        """Return weighted makespan across committed + candidate bus."""
        weight = ctx.weights.get(self.weight_key)

        # Gather all departure and arrival times
        departures = [b.departure_min for b in ctx.scenario.buses]
        arrivals = [plan.arrival_min for plan in ctx.all_committed]

        # Add the candidate bus's arrival from its provisional events + physics
        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        positions = ctx.scenario.route.positions
        speed = ctx.scenario.world.speed_kmph

        # The candidate bus's arrival = end of last charge + travel to destination
        if ctx.charge_events:
            last_event = ctx.charge_events[-1]
            last_end = last_event["end_min"]
            last_station = last_event["station"]
            dist_to_dest = abs(positions[bus.destination] - positions[last_station])
            travel = (dist_to_dest / speed) * 60.0
            candidate_arrival = int(last_end + travel)
        else:
            # No charges — direct travel (shouldn't happen for through-buses but guard it)
            total_dist = abs(positions[bus.destination] - positions[bus.origin])
            travel = (total_dist / speed) * 60.0
            candidate_arrival = int(bus.departure_min + travel)

        arrivals.append(candidate_arrival)

        if not arrivals or not departures:
            return 0.0

        makespan = max(arrivals) - min(departures)
        return weight * makespan
