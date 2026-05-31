"""
scheduler/rules/hard_rules.py  —  Hard constraint rules (the rules that MUST always hold).

WHAT ARE HARD RULES?
  Hard rules are non-negotiable physical or safety constraints.
  If a hard rule returns math.inf, the candidate plan is REJECTED immediately —
  it does not matter how good the soft-objective score is.

  Think of hard rules as: "the schedule is simply ILLEGAL if any of these are broken."

PDF reference: Page 3, "Hard rules that must always hold"
  H1 — One bus per charger at a time (1 charger per station)
       → Enforced by ChargerPool (resources.py), not by a rule class
  H2 — Charging is always exactly 25 minutes
       → ChargeDurationRule below
  H3 — A bus must never run out of range between two consecutive charges
       → RangeRule below
  H4 — A bus visits stations in route order — no backtracking
       → RouteOrderRule below

HOW HARD RULES FIT IN THE SYSTEM:
  engine.py calls objective.score(ctx, registry)
  objective.score calls each hard rule's evaluate(ctx)
  If any hard rule returns math.inf → plan is INFEASIBLE → skip this plan
  If all hard rules return 0.0 → plan passes → move to soft rules

INTERVIEW TALKING POINT:
  "I modelled each hard rule as a separate class decorated with @register.
   The engine never imports hard_rules.py directly — it just asks the registry
   for all hard rules and runs them generically. To add a new hard rule,
   I just create a new file with @register. Zero engine changes."

HOW TO ADD A NEW HARD RULE (live demo for interview):
  1. Create a new file: scheduler/rules/my_rule.py
  2. Write:
       from scheduler.rules.registry import Rule, ScheduleContext, register

       @register
       class MyHardRule(Rule):
           name = "MyHardRule"
           kind = "hard"

           def evaluate(self, ctx: ScheduleContext) -> float:
               # check something
               if something_is_wrong:
                   return math.inf   # REJECT this plan
               return 0.0            # plan is OK
  3. That's it — the engine picks it up automatically.
"""

from __future__ import annotations

import math

from scheduler.rules.registry import Rule, ScheduleContext, register


# ─────────────────────────────────────────────────────────────────────────────
# H1 — Range Rule
# PDF reference: Page 3 — "A bus must never run out of range between
#                two consecutive charges (or between segments without a charge)"
# ─────────────────────────────────────────────────────────────────────────────

@register
class RangeRule(Rule):
    """
    Hard rule H1: No leg of the journey can exceed the bus's battery range.

    A "leg" is a continuous drive without charging:
      origin → first station, station → next station, last station → destination

    WHAT IT CHECKS:
      For each leg, measure the distance.
      If any leg > bus.range_km (240 km), return math.inf (INFEASIBLE).

    WHY THIS IS THE MOST IMPORTANT RULE:
      A 540 km trip with 240 km range REQUIRES at least 2 charges.
      Any plan with only 1 charge will fail this rule automatically.
      So this rule is what forces every bus to charge at least twice.

    PDF reference: Page 3 —
      "A bus must never run out of range between two consecutive charges"
      Page 2 — "Battery range: 240 km on a full charge"

    INTERVIEW TALKING POINT:
      "The RangeRule is the primary hard feasibility filter.
       It automatically enforces the minimum-2-charges requirement
       without any special case in the code — a plan with fewer charges
       just fails the 240 km range check."

    Returns:
      0.0      if all legs are within range (plan is feasible)
      math.inf if any leg exceeds range (plan is REJECTED)
    """

    name = "RangeRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:
        # Get this bus's data
        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        positions = ctx.scenario.route.positions

        # Build the full sequence of stops: [origin, station1, station2, ..., destination]
        # PDF reference: Page 2, "Charging plans" — "between any two consecutive charges"
        stops = [bus.origin] + list(ctx.plan) + [bus.destination]

        # Check every consecutive pair of stops
        for i in range(len(stops) - 1):
            leg_km = abs(positions[stops[i + 1]] - positions[stops[i]])
            if leg_km > bus.range_km:
                # This leg is too long — the bus would run out of battery.
                # Return math.inf to signal: this plan is PHYSICALLY IMPOSSIBLE.
                return math.inf

        # All legs are within range — this plan is feasible from a range perspective.
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# H2 — Route Order Rule
# PDF reference: Page 3 — "A bus visits stations in route order — no backtracking"
# ─────────────────────────────────────────────────────────────────────────────

@register
class RouteOrderRule(Rule):
    """
    Hard rule H2: Buses must visit charging stations in the correct travel order.

    For BK buses (Bengaluru→Kochi), stations must be visited left→right:
      A (100km), then B (220km), then C (320km), then D (440km).
      A BK bus cannot charge at C and then go back to B.

    For KB buses (Kochi→Bengaluru), stations must be visited right→left:
      D (440km), then C (320km), then B (220km), then A (100km).

    WHY THIS MATTERS:
      In the real world, a bus cannot backtrack on the highway.
      Once it passes station B, it cannot go back to B.

    PDF reference: Page 3 —
      "A bus visits stations in route order — no backtracking"

    Returns:
      0.0      if stations are in correct order (plan is valid)
      math.inf if any backtracking detected (plan is REJECTED)
    """

    name = "RouteOrderRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:
        # An empty plan (no stations) trivially satisfies order — nothing to check
        if not ctx.plan:
            return 0.0

        positions = ctx.scenario.route.positions
        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)

        origin_pos = positions[bus.origin]
        dest_pos = positions[bus.destination]
        forward = dest_pos > origin_pos  # True for BK buses, False for KB buses

        # Walk through the plan and check each station is further along than the previous
        prev_pos = origin_pos
        for node in ctx.plan:
            if node not in positions:
                return math.inf  # unknown station name — reject
            pos = positions[node]
            if forward and pos <= prev_pos:
                return math.inf  # BK bus going backwards — INVALID
            if not forward and pos >= prev_pos:
                return math.inf  # KB bus going forwards — INVALID
            prev_pos = pos

        # Also check the destination is further along than the last station
        if forward and dest_pos <= prev_pos:
            return math.inf
        if not forward and dest_pos >= prev_pos:
            return math.inf

        return 0.0  # all stations are in correct travel order


# ─────────────────────────────────────────────────────────────────────────────
# H4 — Charge Duration Rule
# PDF reference: Page 2 — "Charging: always to full, takes 25 minutes (fixed)"
#                Page 3 — "Charging is always exactly 25 minutes"
# ─────────────────────────────────────────────────────────────────────────────

@register
class ChargeDurationRule(Rule):
    """
    Hard rule H4: Every charge session must be exactly world.charge_minutes long.

    In the real problem, charging always fills the battery to full and takes
    exactly 25 minutes. No partial charges, no shorter charges.

    WHY THIS IS A RULE AND NOT JUST CODE:
      The ChargerPool (resources.py) already sets end = start + charge_minutes,
      so in practice this rule should never fail. But we check it anyway as
      "defence in depth" — if there is ever an engine bug, this rule catches it
      during the post-schedule validation step.

    PDF reference: Page 2 — "Charging: always to full, takes 25 minutes (fixed)"
                   Page 3 — "Charging is always exactly 25 minutes"

    Returns:
      0.0      if all charge events have the correct duration
      math.inf if any charge event has wrong duration (should never happen normally)
    """

    name = "ChargeDurationRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:
        expected_duration = ctx.scenario.world.charge_minutes  # should be 25

        for event in ctx.charge_events:
            actual_duration = event["end_min"] - event["start_min"]
            if actual_duration != expected_duration:
                # This should never happen in a correct engine implementation.
                # If it does, there is a bug in _simulate_plan or ChargerPool.
                return math.inf

        return 0.0
