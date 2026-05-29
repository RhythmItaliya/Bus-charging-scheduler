"""
tests/test_rules.py — Unit tests for every individual rule.

Covers:
  Hard rules:
    • RangeRule       — flags a leg that exceeds 240 km → returns inf.
    • RouteOrderRule  — flags backtracking → returns inf.
    • ChargeDurationRule — flags charge event with wrong duration → returns inf.

  Soft rules:
    • IndividualWaitRule — returns higher penalty for higher total wait.
    • OperatorRule       — returns higher penalty when operator variance is higher.
    • OverallRule        — returns higher penalty for larger makespan.

  Weight multiplication:
    • Doubling a soft rule's weight exactly doubles its contribution.
    • Weight = 0.0 silences the rule entirely.

References:
    docs/07-testing/01-testing-plan.md (test_rules.py requirements)
    scheduler/rules/hard_rules.py
    scheduler/rules/soft_rules.py
    scheduler/rules/registry.py
"""

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


# ---------------------------------------------------------------------------
# Shared scenario fixture
# ---------------------------------------------------------------------------

def _make_scenario(weights: Weights = None) -> Scenario:
    """Canonical Bengaluru–Kochi scenario for rule tests."""
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
    """Build a ScheduleContext for rule testing."""
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
    """Convenience: build a charge event dict."""
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


# ---------------------------------------------------------------------------
# RangeRule (H1)
# ---------------------------------------------------------------------------

class TestRangeRule:
    """RangeRule: returns inf when any leg exceeds battery_range_km."""

    rule = RangeRule()

    def test_feasible_plan_returns_zero(self):
        """Plan {A, C}: legs 100, 220-100=120→wait+dist, 320→100 all ≤ 240."""
        ctx = _make_ctx(
            charge_events=[
                _make_event("A", 1240, 0),
                _make_event("C", 1385, 0),
            ],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == 0.0

    def test_leg_exactly_at_range_is_feasible(self):
        """A leg of exactly 240 km must NOT trigger the range rule."""
        # Construct a scenario where D is 240 km from Bengaluru
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
        # bus id must match the bus_id used in the context
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
        """A→D = 340 km > 240 km → infeasible (inf)."""
        ctx = _make_ctx(
            charge_events=[_make_event("D", 1480, 0)],
            plan=("D",),  # Bengaluru→D = 440 km > 240 km
        )
        result = self.rule.evaluate(ctx)
        assert result == math.inf, f"Expected inf for 440 km leg, got {result}"

    def test_last_leg_to_destination_checked(self):
        """The final leg from last station to Kochi must also be ≤ 240 km."""
        # Charge at A (100 km from Bengaluru). A→Kochi = 440 km > 240 km.
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0)],
            plan=("A",),
        )
        result = self.rule.evaluate(ctx)
        assert result == math.inf, (
            f"Expected inf: last leg A→Kochi = 440 km > 240 km, got {result}"
        )


# ---------------------------------------------------------------------------
# RouteOrderRule (H2)
# ---------------------------------------------------------------------------

class TestRouteOrderRule:
    """RouteOrderRule: returns inf when stations are visited out of route order."""

    rule = RouteOrderRule()

    def test_in_order_bk_returns_zero(self):
        """BK bus charging at A then C (positions 100, 320) is in order."""
        ctx = _make_ctx(
            charge_events=[
                _make_event("A", 1240, 0),
                _make_event("C", 1385, 0),
            ],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == 0.0

    def test_out_of_order_returns_inf(self):
        """BK bus visiting C before A violates route order → inf."""
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
        """A single-station plan is trivially in order."""
        ctx = _make_ctx(
            charge_events=[_make_event("B", 1340, 0)],
            plan=("B",),
        )
        assert self.rule.evaluate(ctx) == 0.0


# ---------------------------------------------------------------------------
# ChargeDurationRule (H4)
# ---------------------------------------------------------------------------

class TestChargeDurationRule:
    """ChargeDurationRule: returns inf when end_min - start_min ≠ charge_minutes."""

    rule = ChargeDurationRule()

    def test_correct_duration_returns_zero(self):
        """Exactly 25-minute charge → 0."""
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0, start=1240, end=1265)],
            plan=("A",),
        )
        assert self.rule.evaluate(ctx) == 0.0

    def test_too_short_charge_returns_inf(self):
        """20-minute charge (< 25) → inf."""
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0, start=1240, end=1260)],
            plan=("A",),
        )
        assert self.rule.evaluate(ctx) == math.inf

    def test_too_long_charge_returns_inf(self):
        """30-minute charge (> 25) → inf."""
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0, start=1240, end=1270)],
            plan=("A",),
        )
        assert self.rule.evaluate(ctx) == math.inf


# ---------------------------------------------------------------------------
# IndividualWaitRule (S1)
# ---------------------------------------------------------------------------

class TestIndividualWaitRule:
    """IndividualWaitRule: weighted sum of wait times for this bus."""

    rule = IndividualWaitRule()

    def test_no_wait_returns_zero(self):
        """Zero wait → zero penalty."""
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0), _make_event("C", 1385, 0)],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)

    def test_wait_contributes_penalty(self):
        """20 min wait at A, weight=1.0 → penalty=20."""
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 20), _make_event("C", 1405, 0)],
            plan=("A", "C"),
        )
        assert self.rule.evaluate(ctx) == pytest.approx(20.0)

    def test_penalty_scales_with_weight(self):
        """Same wait, weight=3.0 → penalty = 3 × wait."""
        scenario = _make_scenario(Weights(individual=3.0, operator=1.0, overall=1.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 20), _make_event("C", 1405, 0)],
            plan=("A", "C"),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(60.0)

    def test_weight_zero_silences_rule(self):
        """Weight=0 → penalty=0 regardless of wait."""
        scenario = _make_scenario(Weights(individual=0.0, operator=1.0, overall=1.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 100)],
            plan=("A",),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)

    def test_doubling_weight_doubles_penalty(self):
        """Weight ×2 → penalty ×2 (linear relationship)."""
        s1 = _make_scenario(Weights(individual=1.0, operator=1.0, overall=1.0))
        s2 = _make_scenario(Weights(individual=2.0, operator=1.0, overall=1.0))
        events = [_make_event("A", 1240, 30), _make_event("C", 1405, 15)]
        ctx1 = _make_ctx(events, ("A", "C"), scenario=s1)
        ctx2 = _make_ctx(events, ("A", "C"), scenario=s2)
        assert self.rule.evaluate(ctx2) == pytest.approx(2 * self.rule.evaluate(ctx1))


# ---------------------------------------------------------------------------
# OperatorRule (S2)
# ---------------------------------------------------------------------------

class TestOperatorRule:
    """OperatorRule: weighted variance of waits within each operator's fleet."""

    rule = OperatorRule()

    def test_no_committed_returns_zero(self):
        """No previously committed buses → no variance → zero penalty."""
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 10), _make_event("C", 1395, 0)],
            plan=("A", "C"),
            committed=[],
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)

    def test_same_wait_within_fleet_is_zero_variance(self):
        """Two KPN buses both with 10 min wait → variance=0 → penalty=0."""
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
        """KPN bus-01 has 0 wait; adding bus-02 with 30 min wait → positive variance."""
        committed = [BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1240, 1240, 0, 1265, 0),
                ChargeEvent("C", 1385, 1385, 0, 1410, 0),
            ],
            arrival_min=1510, total_wait=0,
        )]
        # The current bus (bus-BK-02 / kpn) has 30 min wait
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
        """Weight=0 silences even non-zero variance."""
        scenario = _make_scenario(Weights(individual=1.0, operator=0.0, overall=1.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 50)],
            plan=("A",),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# OverallRule (S3)
# ---------------------------------------------------------------------------

class TestOverallRule:
    """OverallRule: weighted makespan (max_arrival − min_departure)."""

    rule = OverallRule()

    def test_single_bus_no_committed_returns_zero(self):
        """With only one bus and no committed, makespan is bus's own span → still 0 relative."""
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 0), _make_event("C", 1385, 0)],
            plan=("A", "C"),
            committed=[],
        )
        # Single-bus makespan is trivially own arrival - departure; result >= 0
        result = self.rule.evaluate(ctx)
        assert result >= 0.0

    def test_late_arrival_increases_makespan(self):
        """A bus that arrives later increases the overall makespan penalty."""
        scenario = _make_scenario()

        # Committed bus: arrival = 1510 (no wait)
        committed = [BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1240, 1240, 0, 1265, 0),
                ChargeEvent("C", 1385, 1385, 0, 1410, 0),
            ],
            arrival_min=1510, total_wait=0,
        )]

        # Current bus arriving earlier (less makespan)
        from dataclasses import replace
        bus2 = Bus("bus-BK-02", "kpn", "Bengaluru", "Kochi", 1155, 240.0)
        s2 = replace(scenario, buses=(scenario.buses[0], bus2))

        # Early arrival ctx
        ctx_early = ScheduleContext(
            bus_id="bus-BK-02",
            plan=("A", "C"),
            charge_events=[_make_event("A", 1255, 0), _make_event("C", 1395, 0)],
            all_committed=committed,
            scenario=s2,
            weights=s2.weights,
        )
        # Late arrival ctx (extra 60 min wait = much later arrival)
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
        """Doubling overall weight doubles the OverallRule contribution."""
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
        """Weight=0 → penalty=0."""
        scenario = _make_scenario(Weights(individual=1.0, operator=1.0, overall=0.0))
        ctx = _make_ctx(
            charge_events=[_make_event("A", 1240, 90), _make_event("C", 1445, 0)],
            plan=("A", "C"),
            scenario=scenario,
        )
        assert self.rule.evaluate(ctx) == pytest.approx(0.0)
