"""
scheduler/rules/soft_rules.py  —  Soft objective rules (the things we want to minimise).

WHAT ARE SOFT RULES?
  Soft rules are preferences — they make the schedule better but don't make
  it illegal if violated. The scheduler tries to find the plan with the
  lowest total soft-rule penalty.

  Each soft rule returns:  weight × penalty
  The engine picks the plan with the LOWEST total across all soft rules.

PDF reference: Page 4, "What to optimize for"
  "When the scheduler has flexibility (which stations to use, who charges first),
   it should weigh three soft rules:"

  S1 — Individual bus: "no single bus should wait too long"
       → IndividualWaitRule
  S2 — Operator: "each operator's fleet should run smoothly as a group"
       → OperatorRule
  S3 — Overall: "total time across the whole network should be low"
       → OverallRule

  "These weights should be TUNABLE — engineers will change them as we learn
   what matters operationally. DON'T HARDCODE THEM." (PDF page 4, emphasis theirs)

HOW WEIGHTS WORK:
  Each soft rule reads its weight from the scenario JSON via ctx.weights.get(key).
  The penalty is then:  weight × raw_metric.
  If weight = 0.0, this rule has no influence on the schedule.
  If weight = 5.0, this rule is 5× more important than a weight-1 rule.

INTERVIEW TALKING POINT:
  "The PDF specifically says 'don't hardcode weights'. So every weight lives
   in the scenario JSON file. In the UI, you can drag the sliders to change
   weights in real time without touching any code.
   Scenario 4 sets operator weight = 2.0 to show operator fairness matters more."
"""

from __future__ import annotations

import statistics
from typing import Dict, List

from scheduler.rules.registry import Rule, ScheduleContext, register


# ─────────────────────────────────────────────────────────────────────────────
# S1 — Individual Wait Rule
# PDF reference: Page 4 — "Individual bus — no single bus should wait too long"
# ─────────────────────────────────────────────────────────────────────────────

@register
class IndividualWaitRule(Rule):
    """
    Soft rule S1: Penalise long waiting times for individual buses.

    WHAT IT MEASURES:
      Total minutes all buses have spent waiting in charger queues.
      Lower = better (buses spend less time just sitting in a queue).

    FORMULA:
      penalty = weight_individual × Σ(wait_min for every bus)

    HOW IT WORKS:
      1. Add up the total_wait of all already-committed buses.
      2. Add the candidate bus's wait from its provisional charge events.
      3. Multiply by the "individual" weight from the scenario.

    WHY CUMULATIVE (not just this bus)?
      We evaluate each plan in the context of all committed buses.
      A plan that adds more total waiting to the system is worse,
      even if the current bus itself waits less.

    PDF reference: Page 4 — "Individual bus — no single bus should wait too long"
    Weight key: "individual"  (default 1.0)

    Example: Scenario 1 with all weights = 1.0
      Total wait across all 20 buses = 900 minutes
      IndividualWaitRule penalty = 1.0 × 900 = 900.0
    """

    name = "IndividualWaitRule"
    kind = "soft"
    weight_key = "individual"  # matches the key in scenario JSON and UI slider

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)  # 1.0 default, read from scenario JSON

        # Sum up waits from all buses that have already been scheduled
        committed_wait = sum(plan.total_wait for plan in ctx.all_committed)

        # Add this candidate bus's wait (from provisional charge events)
        candidate_wait = sum(e["wait_min"] for e in ctx.charge_events)

        total_wait = committed_wait + candidate_wait
        return weight * total_wait  # higher weight → more penalty for waiting


# ─────────────────────────────────────────────────────────────────────────────
# S2 — Operator Rule
# PDF reference: Page 4 — "Operator — each operator's fleet should run smoothly"
# ─────────────────────────────────────────────────────────────────────────────

@register
class OperatorRule(Rule):
    """
    Soft rule S2: Penalise unfair treatment within an operator's fleet.

    WHAT IT MEASURES:
      Within each operator (KPN, Freshbus, Flixbus), how unequal are the
      waiting times between that operator's buses?
      We use statistical VARIANCE to measure this inequality.

    WHY VARIANCE (not average)?
      Variance measures how SPREAD OUT the waits are.
      If KPN's buses wait [0, 0, 0, 90] minutes, the average is 22.5
      but the variance is HUGE — one bus waited 90 min while others waited 0.
      This is unfair. High variance = unfair treatment.
      Low variance = all buses in the fleet experience similar delays.

    FORMULA:
      For each operator fleet, compute variance of wait times.
      penalty = weight_operator × Σ(variance per fleet)

    WHEN DOES THIS MATTER?
      Scenario 4 has 8 KPN buses in BK direction.
      They all queue at station A and accumulate different wait times.
      With high operator weight, the scheduler tries harder to
      equalise wait times within the KPN fleet.

    PDF reference: Page 4 — "Operator — each operator's fleet should run smoothly as a group"
                   Scenario 4 description — "operator weight = 2.0 should produce
                   visibly different schedules"
    Weight key: "operator"  (default 1.0; Scenario 4 uses 2.0)
    """

    name = "OperatorRule"
    kind = "soft"
    weight_key = "operator"

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)

        # Build a dict: operator_name → [wait_min for each of that operator's buses]
        op_waits: Dict[str, List[int]] = {}

        # Start with all already-committed buses
        for plan in ctx.all_committed:
            op_waits.setdefault(plan.operator, []).append(plan.total_wait)

        # Add this candidate bus to its operator's wait list
        candidate_bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        candidate_wait = sum(e["wait_min"] for e in ctx.charge_events)
        op_waits.setdefault(candidate_bus.operator, []).append(candidate_wait)

        # Compute variance for each operator fleet
        # Variance = 0 if only 1 bus in fleet (no comparison to make)
        # Variance > 0 if buses have different wait times (unfair)
        total_variance = 0.0
        for waits in op_waits.values():
            if len(waits) > 1:
                total_variance += statistics.variance(waits)

        return weight * total_variance  # higher weight → more penalty for uneven waits


# ─────────────────────────────────────────────────────────────────────────────
# S3 — Overall Rule
# PDF reference: Page 4 — "Overall — total time across the whole network should be low"
# ─────────────────────────────────────────────────────────────────────────────

@register
class OverallRule(Rule):
    """
    Soft rule S3: Penalise long total operation time across the whole network.

    WHAT IT MEASURES:
      Makespan = latest arrival time of any bus − earliest departure time of any bus.
      This is how long the whole operation takes from start to finish.
      Lower makespan = the network is more efficient.

    WHY MAKESPAN?
      If some buses arrive very late (because they waited a long time in queues),
      the total operation window is stretched out. Makespan captures this.
      An efficient schedule gets all buses to their destination quickly.

    FORMULA:
      makespan = max(all arrival times) − min(all departure times)
      penalty  = weight_overall × makespan

    ALTERNATIVE (not used, documented for transparency):
      Some schedulers use "total person-time" = Σ(arrival − departure per bus).
      We chose makespan because it directly measures the operation window.

    PDF reference: Page 4 — "Overall — total time across the whole network should be low"
    Weight key: "overall"  (default 1.0)

    Example: Scenario 1
      Min departure: 19:00 (1140 min)
      Max arrival:   ~03:15 next day (~1955 min)
      Makespan: 1955 - 1140 = 815 min
      OverallRule penalty: 1.0 × 815 = 815.0
    """

    name = "OverallRule"
    kind = "soft"
    weight_key = "overall"

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)

        # Collect all departure times (these are fixed — buses leave when scheduled)
        departures = [b.departure_min for b in ctx.scenario.buses]

        # Collect arrivals from already-committed buses
        arrivals = [plan.arrival_min for plan in ctx.all_committed]

        # Estimate this candidate bus's arrival:
        # last charge end + travel time from last station to destination
        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        positions = ctx.scenario.route.positions
        speed = ctx.scenario.world.speed_kmph

        if ctx.charge_events:
            last_event = ctx.charge_events[-1]
            last_end = last_event["end_min"]
            last_station = last_event["station"]
            dist_to_dest = abs(positions[bus.destination] - positions[last_station])
            travel_to_dest = (dist_to_dest / speed) * 60.0
            candidate_arrival = int(last_end + travel_to_dest)
        else:
            # No charges — direct travel (should never happen for a valid plan, but guard it)
            total_dist = abs(positions[bus.destination] - positions[bus.origin])
            travel = (total_dist / speed) * 60.0
            candidate_arrival = int(bus.departure_min + travel)

        arrivals.append(candidate_arrival)

        if not arrivals or not departures:
            return 0.0

        # Makespan = how long the whole operation takes
        makespan = max(arrivals) - min(departures)
        return weight * makespan
