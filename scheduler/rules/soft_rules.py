from __future__ import annotations

import statistics
from typing import Dict, List

from scheduler.rules.registry import Rule, ScheduleContext, register


@register
class IndividualWaitRule(Rule):

    name = "IndividualWaitRule"
    kind = "soft"
    weight_key = "individual"

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)


        committed_wait = sum(plan.total_wait for plan in ctx.all_committed)


        candidate_wait = sum(e["wait_min"] for e in ctx.charge_events)

        total_wait = committed_wait + candidate_wait
        return weight * total_wait


@register
class OperatorRule(Rule):

    name = "OperatorRule"
    kind = "soft"
    weight_key = "operator"

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)


        op_waits: Dict[str, List[int]] = {}


        for plan in ctx.all_committed:
            op_waits.setdefault(plan.operator, []).append(plan.total_wait)


        candidate_bus = next(b for b in ctx.scenario.buses if b.id == ctx.bus_id)
        candidate_wait = sum(e["wait_min"] for e in ctx.charge_events)
        op_waits.setdefault(candidate_bus.operator, []).append(candidate_wait)


        total_variance = 0.0
        for waits in op_waits.values():
            if len(waits) > 1:
                total_variance += statistics.variance(waits)

        return weight * total_variance


@register
class OverallRule(Rule):

    name = "OverallRule"
    kind = "soft"
    weight_key = "overall"

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)


        departures = [b.departure_min for b in ctx.scenario.buses]


        arrivals = [plan.arrival_min for plan in ctx.all_committed]


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

            total_dist = abs(positions[bus.destination] - positions[bus.origin])
            travel = (total_dist / speed) * 60.0
            candidate_arrival = int(bus.departure_min + travel)

        arrivals.append(candidate_arrival)

        if not arrivals or not departures:
            return 0.0


        makespan = max(arrivals) - min(departures)
        return weight * makespan
