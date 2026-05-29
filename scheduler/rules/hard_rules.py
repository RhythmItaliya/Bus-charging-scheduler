"""
scheduler/rules/hard_rules.py — Hard constraint rules (feasibility gates).

All four hard rules from the spec are implemented here.  Any rule that returns
math.inf causes the candidate plan to be rejected as infeasible.

Hard rules:
  H1 — RangeRule          : no leg may exceed battery range.
  H2 — RouteOrderRule     : stations visited in route order, no backtracking.
  H3 — ChargerExclusivity : enforced structurally by ChargerPool; this rule
                             double-checks the committed schedule in validate().
  H4 — ChargeDurationRule : every charge is exactly world.charge_minutes long.

References:
    docs/00-requirements/02-constraints-and-rules.md  (H1–H4 formal spec)
    docs/02-scheduler-engine/05-rule-framework.md     (Rule ABC contract)
    docs/07-testing/01-testing-plan.md                (test_rules.py)
"""

from __future__ import annotations

import math

from scheduler.rules.registry import Rule, ScheduleContext, register


@register
class RangeRule(Rule):
    """
    H1 — Range constraint.

    Returns math.inf if ANY leg in the candidate plan exceeds the bus's range.
    The legs are: origin→first_charge, each charge→next_charge, last_charge→dest.

    This is the primary hard feasibility filter and is the rule that makes a
    through-trip require ≥2 charges (a bus cannot travel 540 km on 240 km range).

    Ref: docs/00-requirements/02-constraints-and-rules.md §H1
    """

    name = "RangeRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:
        """Return 0.0 if all legs are within range; math.inf otherwise."""
        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        positions = ctx.scenario.route.positions

        # Build the full position sequence: origin → plan stations → destination
        stops = [bus.origin] + list(ctx.plan) + [bus.destination]
        for i in range(len(stops) - 1):
            leg = abs(positions[stops[i + 1]] - positions[stops[i]])
            if leg > bus.range_km:
                return math.inf  # H1 violated

        return 0.0


@register
class RouteOrderRule(Rule):
    """
    H2 — Route order and no-backtracking constraint.

    Verifies that the plan's stations form a strictly increasing subsequence of
    the bus's downstream route nodes.  No node may appear twice, and no bus may
    visit a station that lies behind its travel direction.

    Ref: docs/00-requirements/02-constraints-and-rules.md §H2
    """

    name = "RouteOrderRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:
        """Return 0.0 if stations are in strict route order; math.inf otherwise."""
        if not ctx.plan:
            return 0.0  # empty plan is trivially ordered

        positions = ctx.scenario.route.positions
        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        origin_pos = positions[bus.origin]
        dest_pos = positions[bus.destination]
        forward = dest_pos > origin_pos  # True for BK, False for KB

        prev_pos = origin_pos
        for node in ctx.plan:
            if node not in positions:
                return math.inf  # unknown node
            pos = positions[node]
            if forward and pos <= prev_pos:
                return math.inf  # H2 violated: not strictly increasing
            if not forward and pos >= prev_pos:
                return math.inf  # H2 violated: not strictly decreasing
            prev_pos = pos

        # Also check destination is in the correct direction
        if forward and dest_pos <= prev_pos:
            return math.inf
        if not forward and dest_pos >= prev_pos:
            return math.inf

        return 0.0


@register
class ChargeDurationRule(Rule):
    """
    H4 — Fixed charge duration.

    Verifies that every charge event in the candidate plan has an end_min that
    equals start_min + world.charge_minutes.  The ChargerPool already guarantees
    this, so this rule acts as a double-check used by the validator.

    Ref: docs/00-requirements/02-constraints-and-rules.md §H4
    """

    name = "ChargeDurationRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:
        """Return 0.0 if all charge events have the correct duration; inf otherwise."""
        expected = ctx.scenario.world.charge_minutes
        for event in ctx.charge_events:
            duration = event["end_min"] - event["start_min"]
            if duration != expected:
                return math.inf  # H4 violated

        return 0.0
