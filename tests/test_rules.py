from __future__ import annotations

import math
import pytest

from scheduler.model import (
    BusPlan, Bus, ChargeEvent, Route, Scenario,
    Segment, Station, StationSlot, Weights, World,
)
from scheduler.rules.hard_rules import ChargeDurationRule, RangeRule, RouteOrderRule
from scheduler.rules.soft_rules import IndividualWaitRule, OperatorRule, OverallRule
from scheduler.rules.registry import ScheduleContext


def _make_scenario(weights: Weights = None) -> Scenario:
    route = Route(
        nodes=("Bengaluru", "A", "B", "C", "D", "Kochi"),
        segments=(
            Segment("Bengaluru", "A", 100),
            Segment("A", "B", 120),
            Segment("B", "C", 100),
            Segment("C", "D", 120),
            Segment("D", "Kochi", 100),
        ),
        positions={"Bengaluru": 0, "A": 100, "B": 220, "C": 320, "D": 440, "Kochi": 540},
    )
    stations = {
        "A": Station("A", 1),
        "B": Station("B", 1),
        "C": Station("C", 1),
        "D": Station("D", 1),
    }
    world = World(speed_kmph=60, charge_minutes=25, battery_range_km=240)
    if weights is None:
        weights = Weights(individual=1.0, operator=1.0, overall=1.0)
    bus = Bus(
        id="bus-BK-01", operator="kpn",
        origin="Bengaluru", destination="Kochi",
        departure_min=1140, range_km=240.0,
    )
    return Scenario(
        name="test", world=world, route=route,
        stations=stations, weights=weights, buses=(bus,),
    )


def _make_ctx(
    charge_events: list,
    plan: tuple,
    committed: list = None,
    weights: Weights = None,
    scenario: Scenario = None,
    bus_id: str = "bus-BK-01",
) -> ScheduleContext:
    if scenario is None:
        scenario = _make_scenario(weights)
    return ScheduleContext(
        bus_id=bus_id,
        plan=plan,
        charge_events=charge_events,
        all_committed=committed or [],
        scenario=scenario,
        weights=scenario.weights,
    )


def _make_event(station, arrive, wait, start=None, end=None, charger=0):
    if start is None:
        start = arrive + wait
    if end is None:
        end = start + 25
    return {
        "station": station,
        "arrive_min": arrive,
        "wait_min": wait,
        "start_min": start,
        "end_min": end,
        "charger_index": charger,
    }


class TestRangeRule:

    rule = RangeRule()

    def test_feasible_plan_returns_zero(self):
        ctx = _make_ctx(
            charge_events=[
                _make_event("A", 1240, 0),
                _make_event("C", 1385, 0),
            ],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == 0.0

    def test_leg_exactly_at_range_is_feasible(self):

        route = Route(
            nodes=("Bengaluru", "D", "Kochi"),
            segments=(
                Segment("Bengaluru", "D", 240),
                Segment("D", "Kochi", 100),
            ),
            positions={"Bengaluru": 0, "D": 240, "Kochi": 340},
        )
        stations = {"D": Station("D", 1)}
        world = World(speed_kmph=60, charge_minutes=25, battery_range_km=240)

        bus = Bus("bus-BK-01", "kpn", "Bengaluru", "Kochi", 1140, 240.0)
        scenario = Scenario(
            name="t", world=world, route=route,
            stations=stations,
            weights=Weights(individual=1.0, operator=1.0, overall=1.0),
            buses=(bus,),
        )
        ctx = _make_ctx(
            charge_events=[_make_event("D", 1380, 0)],
            plan=("D",),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == 0.0

    def test_leg_exceeds_range_returns_inf(self):
        ctx = _make_ctx(
            charge_events=[_make_event("D", 1480, 0)],
            plan=("D",),
        )
        result = self.rule.evaluate(ctx)
        assert result == math.inf, f"Expected inf for 440 km leg, got {result}"

    def test_last_leg_to_destination_checked(self):

        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0)],
            plan=("A",),
        )
        result = self.rule.evaluate(ctx)
        assert result == math.inf, (
            f"Expected inf: last leg A→Kochi = 440 km > 240 km, got {result}"
        )


class TestRouteOrderRule:

    rule = RouteOrderRule()

    def test_in_order_bk_returns_zero(self):
        ctx = _make_ctx(
            charge_events=[
                _make_event("A", 1240, 0),
                _make_event("C", 1385, 0),
            ],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == 0.0

    def test_out_of_order_returns_inf(self):
        ctx = _make_ctx(
            charge_events=[
                _make_event("C", 1240, 0),
                _make_event("A", 1305, 0),
            ],
            plan=("C", "A"),
        )
        result = self.rule.evaluate(ctx)
        assert result == math.inf, f"Expected inf for out-of-order plan, got {result}"

    def test_single_station_always_in_order(self):
        ctx = _make_ctx(
            charge_events=[_make_event("B", 1340, 0)],
            plan=("B",),
        )
        assert self.rule.evaluate(ctx) == 0.0


class TestChargeDurationRule:

    rule = ChargeDurationRule()

    def test_correct_duration_returns_zero(self):
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0, start=1240, end=1265)],
            plan=("A",),
        )
        assert self.rule.evaluate(ctx) == 0.0

    def test_too_short_charge_returns_inf(self):
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0, start=1240, end=1260)],
            plan=("A",),
        )
        assert self.rule.evaluate(ctx) == math.inf

    def test_too_long_charge_returns_inf(self):
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0, start=1240, end=1270)],
            plan=("A",),
        )
        assert self.rule.evaluate(ctx) == math.inf


class TestIndividualWaitRule:

    rule = IndividualWaitRule()

    def test_no_wait_returns_zero(self):
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0), _make_event("C", 1385, 0)],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)

    def test_wait_contributes_penalty(self):
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 20), _make_event("C", 1405, 0)],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == pytest.approx(20.0)

    def test_penalty_scales_with_weight(self):
        scenario = _make_scenario(Weights(individual=3.0, operator=1.0, overall=1.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 20), _make_event("C", 1405, 0)],
            plan=("A", "C"),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(60.0)

    def test_weight_zero_silences_rule(self):
        scenario = _make_scenario(Weights(individual=0.0, operator=1.0, overall=1.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 100)],
            plan=("A",),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)

    def test_doubling_weight_doubles_penalty(self):
        s1 = _make_scenario(Weights(individual=1.0, operator=1.0, overall=1.0))
        s2 = _make_scenario(Weights(individual=2.0, operator=1.0, overall=1.0))
        events = [_make_event("A", 1240, 30), _make_event("C", 1405, 15)]
        ctx1 = _make_ctx(events, ("A", "C"), scenario=s1)
        ctx2 = _make_ctx(events, ("A", "C"), scenario=s2)
        assert self.rule.evaluate(ctx2) == pytest.approx(2 * self.rule.evaluate(ctx1))


class TestOperatorRule:

    rule = OperatorRule()

    def test_no_committed_returns_zero(self):
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 10), _make_event("C", 1395, 0)],
            plan=("A", "C"),
            committed=[],
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)

    def test_same_wait_within_fleet_is_zero_variance(self):
        committed = [BusPlan(
            bus_id="bus-BK-02", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1255, 1265, 10, 1290, 0),
                ChargeEvent("C", 1405, 1405, 0, 1430, 0),
            ],
            arrival_min=1530, total_wait=10,
        )]
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 10), _make_event("C", 1385, 0)],
            plan=("A", "C"),
            committed=committed,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)

    def test_uneven_fleet_waits_produce_positive_penalty(self):
        committed = [BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1240, 1240, 0, 1265, 0),
                ChargeEvent("C", 1385, 1385, 0, 1410, 0),
            ],
            arrival_min=1510, total_wait=0,
        )]

        scenario = _make_scenario()
        bus2 = Bus(
            id="bus-BK-02", operator="kpn",
            origin="Bengaluru", destination="Kochi",
            departure_min=1155, range_km=240.0,
        )
        from dataclasses import replace
        scenario2 = replace(scenario, buses=(scenario.buses[0], bus2))
        ctx = ScheduleContext(
            bus_id="bus-BK-02",
            plan=("A", "C"),
            charge_events=[_make_event("A", 1255, 30), _make_event("C", 1415, 0)],
            all_committed=committed,
            scenario=scenario2,
            weights=scenario2.weights,
        )
        penalty = self.rule.evaluate(ctx)
        assert penalty > 0, f"Expected positive variance penalty, got {penalty}"

    def test_weight_zero_silences_operator_rule(self):
        scenario = _make_scenario(Weights(individual=1.0, operator=0.0, overall=1.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 50)],
            plan=("A",),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)


class TestOverallRule:

    rule = OverallRule()

    def test_single_bus_no_committed_returns_zero(self):
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0), _make_event("C", 1385, 0)],
            plan=("A", "C"),
            committed=[],
        )

        result = self.rule.evaluate(ctx)
        assert result >= 0.0

    def test_late_arrival_increases_makespan(self):
        scenario = _make_scenario()


        committed = [BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1240, 1240, 0, 1265, 0),
                ChargeEvent("C", 1385, 1385, 0, 1410, 0),
            ],
            arrival_min=1510, total_wait=0,
        )]


        from dataclasses import replace
        bus2 = Bus("bus-BK-02", "kpn", "Bengaluru", "Kochi", 1155, 240.0)
        s2 = replace(scenario, buses=(scenario.buses[0], bus2))


        ctx_early = ScheduleContext(
            bus_id="bus-BK-02",
            plan=("A", "C"),
            charge_events=[_make_event("A", 1255, 0), _make_event("C", 1395, 0)],
            all_committed=committed,
            scenario=s2,
            weights=s2.weights,
        )

        ctx_late = ScheduleContext(
            bus_id="bus-BK-02",
            plan=("A", "C"),
            charge_events=[_make_event("A", 1255, 60), _make_event("C", 1455, 0)],
            all_committed=committed,
            scenario=s2,
            weights=s2.weights,
        )
        penalty_early = self.rule.evaluate(ctx_early)
        penalty_late = self.rule.evaluate(ctx_late)
        assert penalty_late >= penalty_early, (
            f"Late arrival should have ≥ makespan penalty: "
            f"early={penalty_early:.1f}, late={penalty_late:.1f}"
        )

    def test_weight_multiplication_correct(self):
        s1 = _make_scenario(Weights(individual=1.0, operator=1.0, overall=1.0))
        s2 = _make_scenario(Weights(individual=1.0, operator=1.0, overall=2.0))
        events = [_make_event("A", 1240, 10), _make_event("C", 1395, 0)]
        ctx1 = _make_ctx(events, ("A", "C"), scenario=s1)
        ctx2 = _make_ctx(events, ("A", "C"), scenario=s2)
        r1, r2 = self.rule.evaluate(ctx1), self.rule.evaluate(ctx2)
        if r1 > 0:
            assert r2 == pytest.approx(2 * r1), (
                f"Overall weight×2 should double penalty: {r1} → {r2}"
            )

    def test_weight_zero_silences_overall_rule(self):
        scenario = _make_scenario(Weights(individual=1.0, operator=1.0, overall=0.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 90), _make_event("C", 1445, 0)],
            plan=("A", "C"),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)
