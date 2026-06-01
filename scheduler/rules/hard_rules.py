from __future__ import annotations

import math

from scheduler.rules.registry import Rule, ScheduleContext, register


@register
class RangeRule(Rule):

    name = "RangeRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:

        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        positions = ctx.scenario.route.positions


        stops = [bus.origin] + list(ctx.plan) + [bus.destination]


        for i in range(len(stops) - 1):
            leg_km = abs(positions[stops[i + 1]] - positions[stops[i]])
            if leg_km > bus.range_km:


                return math.inf


        return 0.0


@register
class RouteOrderRule(Rule):

    name = "RouteOrderRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:

        if not ctx.plan:
            return 0.0

        positions = ctx.scenario.route.positions
        bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)

        origin_pos = positions[bus.origin]
        dest_pos = positions[bus.destination]
        forward = dest_pos > origin_pos


        prev_pos = origin_pos
        for node in ctx.plan:
            if node not in positions:
                return math.inf
            pos = positions[node]
            if forward and pos <= prev_pos:
                return math.inf
            if not forward and pos >= prev_pos:
                return math.inf
            prev_pos = pos


        if forward and dest_pos <= prev_pos:
            return math.inf
        if not forward and dest_pos >= prev_pos:
            return math.inf

        return 0.0


@register
class ChargeDurationRule(Rule):

    name = "ChargeDurationRule"
    kind = "hard"

    def evaluate(self, ctx: ScheduleContext) -> float:
        expected_duration = ctx.scenario.world.charge_minutes

        for event in ctx.charge_events:
            actual_duration = event["end_min"] - event["start_min"]
            if actual_duration != expected_duration:


                return math.inf

        return 0.0
