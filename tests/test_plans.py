"""
tests/test_plans.py — Unit tests for candidate plan enumeration.

Covers:
  • No candidate plan has a leg > 240 km.
  • Through-buses require ≥ 2 charges (since 540 km > 240 km range).
  • The ONLY valid 2-charge BK plans are {A,C}, {B,C}, {B,D}  (spec-verified).
  • Route order is preserved in every plan.
  • KB direction enumerates the mirrored station order.
  • An impossible range (e.g. 90 km) yields no feasible plans.

References:
    docs/07-testing/01-testing-plan.md (test_plans.py requirements)
    docs/00-requirements/01-requirements-analysis.md §4 (feasibility sets)
    scheduler/plans.py
"""

import pytest
from scheduler.loader import load_scenario
from scheduler.model import Bus, Scenario, Segment, Station, Weights, World, Route
from scheduler.plans import candidate_plans, downstream_stations


# ---------------------------------------------------------------------------
# Helper: build a minimal BK-direction Scenario programmatically
# ---------------------------------------------------------------------------

def _make_scenario(
    battery_range_km: float = 240.0,
    num_chargers: int = 1,
) -> Scenario:
    """Build the canonical Bengaluru–Kochi scenario for plan tests."""
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
        "A": Station("A", num_chargers),
        "B": Station("B", num_chargers),
        "C": Station("C", num_chargers),
        "D": Station("D", num_chargers),
    }
    world = World(speed_kmph=60, charge_minutes=25, battery_range_km=battery_range_km)
    weights = Weights(individual=1.0, operator=1.0, overall=1.0)
    bus_bk = Bus(
        id="bus-BK-01", operator="kpn",
        origin="Bengaluru", destination="Kochi",
        departure_min=1140, range_km=battery_range_km,
    )
    bus_kb = Bus(
        id="bus-KB-01", operator="kpn",
        origin="Kochi", destination="Bengaluru",
        departure_min=1140, range_km=battery_range_km,
    )
    return Scenario(
        name="test", world=world, route=route,
        stations=stations, weights=weights,
        buses=(bus_bk, bus_kb),
    )


class TestDownstreamStations:
    """Test which stations are eligible for each bus direction."""

    def test_bk_bus_has_all_four_stations(self):
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-BK-01")
        stations = downstream_stations(bus, scenario)
        assert stations == ["A", "B", "C", "D"]

    def test_kb_bus_has_all_four_stations_reversed(self):
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-KB-01")
        stations = downstream_stations(bus, scenario)
        assert stations == ["D", "C", "B", "A"]


class TestCandidatePlans:
    """Test range-feasibility filtering and completeness of plan enumeration."""

    def test_no_plan_exceeds_range(self):
        """Every leg in every candidate plan must be ≤ 240 km."""
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-BK-01")
        plans = candidate_plans(bus, scenario)
        positions = scenario.route.positions

        for plan in plans:
            stops = ["Bengaluru"] + list(plan) + ["Kochi"]
            stop_positions = [positions[n] for n in stops]
            for i in range(len(stop_positions) - 1):
                leg = abs(stop_positions[i + 1] - stop_positions[i])
                assert leg <= 240.0, (
                    f"Plan {plan} has leg {stops[i]}→{stops[i+1]} = {leg} km > 240 km"
                )

    def test_through_bus_requires_at_least_2_charges(self):
        """All feasible BK plans have ≥ 2 stations (since 540 km > 240 km range)."""
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-BK-01")
        plans = candidate_plans(bus, scenario)
        assert plans, "Should have at least one feasible plan"
        for plan in plans:
            assert len(plan) >= 2, f"Plan {plan} has fewer than 2 charges"

    def test_valid_two_charge_bk_plans_are_exactly_abc_bc_bd(self):
        """
        The only valid 2-charge BK plans are {A,C}, {B,C}, {B,D}.
        {A,D} is invalid because A→D = 340 km > 240 km.

        Spec reference: docs/00-requirements/01-requirements-analysis.md §4.
        """
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-BK-01")
        plans = candidate_plans(bus, scenario)
        two_charge_plans = {plan for plan in plans if len(plan) == 2}
        expected = {("A", "C"), ("B", "C"), ("B", "D")}
        assert two_charge_plans == expected, (
            f"Expected 2-charge plans {expected}, got {two_charge_plans}"
        )

    def test_ad_plan_is_not_feasible(self):
        """A→D = 340 km exceeds 240 km range — must be excluded."""
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-BK-01")
        plans = candidate_plans(bus, scenario)
        assert ("A", "D") not in plans, "Plan {A,D} is infeasible (leg A→D = 340 km)"

    def test_route_order_preserved_in_all_plans(self):
        """Plans must be strictly increasing in position (no backtracking)."""
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-BK-01")
        plans = candidate_plans(bus, scenario)
        positions = scenario.route.positions
        for plan in plans:
            pos_seq = [positions[n] for n in plan]
            for i in range(len(pos_seq) - 1):
                assert pos_seq[i] < pos_seq[i + 1], (
                    f"Plan {plan} is not in route order: {pos_seq}"
                )

    def test_kb_plans_are_in_reversed_order(self):
        """KB bus station order should be decreasing in original route positions."""
        scenario = _make_scenario()
        bus = next(b for b in scenario.buses if b.id == "bus-KB-01")
        plans = candidate_plans(bus, scenario)
        positions = scenario.route.positions
        assert plans, "KB bus should have feasible plans"
        for plan in plans:
            pos_seq = [positions[n] for n in plan]
            for i in range(len(pos_seq) - 1):
                assert pos_seq[i] > pos_seq[i + 1], (
                    f"KB Plan {plan} is not in reverse route order: {pos_seq}"
                )

    def test_impossible_range_yields_no_plans(self):
        """A bus with 90 km range cannot make any feasible plan (first station is 100 km away)."""
        scenario = _make_scenario(battery_range_km=90.0)
        bus = next(b for b in scenario.buses if b.id == "bus-BK-01")
        # Override range on the bus object
        from dataclasses import replace
        bus_90 = replace(bus, range_km=90.0)
        # Rebuild scenario with this bus
        from scheduler.model import Scenario as S
        s2 = S(
            name="impossible",
            world=scenario.world,
            route=scenario.route,
            stations=scenario.stations,
            weights=scenario.weights,
            buses=(bus_90, scenario.buses[1]),
        )
        plans = candidate_plans(bus_90, s2)
        assert plans == [], (
            f"Bus with 90 km range should have no feasible plans, got {plans}"
        )
