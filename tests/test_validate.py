from __future__ import annotations

from dataclasses import replace

import pytest

from scheduler.engine import schedule
from scheduler.loader import load_scenario
from scheduler.model import (
    BusPlan,
    Bus,
    ChargeEvent,
    Route,
    Scenario,
    Segment,
    ScheduleResult,
    Station,
    StationSlot,
    Weights,
    World,
)
from scheduler.validate import validate


def _make_scenario() -> Scenario:
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
    stations = {n: Station(n, 1) for n in ("A", "B", "C", "D")}
    world = World(speed_kmph=60, charge_minutes=25, battery_range_km=240)
    bus = Bus(
        id="bus-BK-01", operator="kpn",
        origin="Bengaluru", destination="Kochi",
        departure_min=1140, range_km=240.0,
    )
    return Scenario(
        name="test", world=world, route=route,
        stations=stations, weights=Weights(), buses=(bus,),
    )


def _valid_plan() -> BusPlan:
    return BusPlan(
        bus_id="bus-BK-01",
        operator="kpn",
        direction="BK",
        charge_events=[
            ChargeEvent("A", 1240, 1240, 0, 1265, 0),
            ChargeEvent("C", 1485, 1485, 0, 1510, 0),
        ],
        arrival_min=1730,
        total_wait=0,
    )


def _wrap(plan: BusPlan, extra_buses: tuple[Bus, ...] = ()) -> tuple[ScheduleResult, Scenario]:
    scenario = _make_scenario()
    if extra_buses:
        scenario = replace(scenario, buses=scenario.buses + extra_buses)

    plans = [plan]
    station_order: dict = {}
    for evt in plan.charge_events:
        station_order.setdefault(evt.station, []).append(
            StationSlot(plan.bus_id, plan.operator, evt.charger_index,
                        evt.start_min, evt.wait_min, evt.end_min)
        )

    result = ScheduleResult(
        bus_plans=plans,
        station_order=station_order,
        objective_breakdown={},
        total_objective=0.0,
    )
    return result, scenario


class TestValidateAcceptsValidSchedule:

    def test_valid_constructed_plan_returns_no_violations(self):
        result, scenario = _wrap(_valid_plan())
        assert validate(result, scenario) == []

    @pytest.mark.parametrize("path", [
        "data/scenarios/scenario_1.json",
        "data/scenarios/scenario_2.json",
        "data/scenarios/scenario_3.json",
        "data/scenarios/scenario_4.json",
        "data/scenarios/scenario_5.json",
    ])
    def test_all_real_scenarios_validate_clean(self, path):
        scenario = load_scenario(path)
        result = schedule(scenario)
        assert validate(result, scenario) == [], (
            f"Unexpected violations in {path}"
        )


class TestH1RangeViolation:

    def test_leg_within_range_passes(self):
        result, scenario = _wrap(_valid_plan())
        violations = validate(result, scenario)
        h1 = [v for v in violations if "H1" in v]
        assert h1 == []

    def test_leg_exceeds_reduced_range_is_caught(self):
        scenario = _make_scenario()
        tighter = replace(scenario, world=replace(scenario.world, battery_range_km=200.0))
        result, _ = _wrap(_valid_plan())
        violations = validate(result, tighter)
        h1 = [v for v in violations if "H1" in v or "range" in v.lower()]
        assert h1, f"Expected H1 violation with range=200, got {violations}"

    def test_boundary_at_exact_range_passes(self):
        scenario = _make_scenario()
        tight = replace(scenario, world=replace(scenario.world, battery_range_km=220.0))
        result, _ = _wrap(_valid_plan())
        violations = validate(result, tight)
        h1 = [v for v in violations if "H1" in v]
        assert h1 == [], f"Leg exactly at range should not trigger H1, got {h1}"


class TestH2RouteOrderViolation:

    def test_in_order_plan_passes(self):
        result, scenario = _wrap(_valid_plan())
        h2 = [v for v in validate(result, scenario) if "H2" in v]
        assert h2 == []

    def test_reversed_stations_detected(self):
        bad = BusPlan(
            bus_id="bus-BK-01",
            operator="kpn",
            direction="BK",
            charge_events=[
                ChargeEvent("C", 1460, 1460, 0, 1485, 0),
                ChargeEvent("A", 1705, 1705, 0, 1730, 0),
            ],
            arrival_min=2170,
            total_wait=0,
        )
        result, scenario = _wrap(bad)
        violations = validate(result, scenario)
        h2 = [v for v in violations if "H2" in v or "order" in v.lower()]
        assert h2, f"Expected H2 route-order violation, got {violations}"

    def test_single_station_always_passes_h2(self):
        one_stop = BusPlan(
            bus_id="bus-BK-01",
            operator="kpn",
            direction="BK",
            charge_events=[
                ChargeEvent("B", 1360, 1360, 0, 1385, 0),
            ],
            arrival_min=1705,
            total_wait=0,
        )
        result, scenario = _wrap(one_stop)
        h2 = [v for v in validate(result, scenario) if "H2" in v]
        assert h2 == []


class TestH3ChargerExclusivity:

    def test_non_overlapping_buses_pass(self):
        bus2 = Bus(
            id="bus-BK-02", operator="kpn",
            origin="Bengaluru", destination="Kochi",
            departure_min=1290, range_km=240.0,
        )


        plan2 = BusPlan(
            bus_id="bus-BK-02", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1390, 1390, 0, 1415, 0),
                ChargeEvent("C", 1535, 1535, 0, 1560, 0),
            ],
            arrival_min=1760, total_wait=0,
        )
        scenario = replace(_make_scenario(), buses=_make_scenario().buses + (bus2,))
        station_order = {
            "A": [
                StationSlot("bus-BK-01", "kpn", 0, 1240, 0, 1265),
                StationSlot("bus-BK-02", "kpn", 0, 1390, 0, 1415),
            ],
            "C": [
                StationSlot("bus-BK-01", "kpn", 0, 1485, 0, 1510),
                StationSlot("bus-BK-02", "kpn", 0, 1535, 0, 1560),
            ],
        }
        result = ScheduleResult(
            bus_plans=[_valid_plan(), plan2],
            station_order=station_order,
            objective_breakdown={}, total_objective=0.0,
        )
        h3 = [v for v in validate(result, scenario) if "H3" in v]
        assert h3 == []

    def test_overlapping_at_same_station_is_detected(self):
        bus2 = Bus(
            id="bus-BK-02", operator="kpn",
            origin="Bengaluru", destination="Kochi",
            departure_min=1145, range_km=240.0,
        )
        plan2 = BusPlan(
            bus_id="bus-BK-02", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1245, 1245, 0, 1270, 0),
                ChargeEvent("C", 1490, 1490, 0, 1515, 0),
            ],
            arrival_min=1735, total_wait=0,
        )
        scenario = replace(_make_scenario(), buses=_make_scenario().buses + (bus2,))
        station_order = {
            "A": [
                StationSlot("bus-BK-01", "kpn", 0, 1240, 0, 1265),
                StationSlot("bus-BK-02", "kpn", 0, 1245, 0, 1270),
            ],
            "C": [
                StationSlot("bus-BK-01", "kpn", 0, 1485, 0, 1510),
                StationSlot("bus-BK-02", "kpn", 0, 1490, 0, 1515),
            ],
        }
        result = ScheduleResult(
            bus_plans=[_valid_plan(), plan2],
            station_order=station_order,
            objective_breakdown={}, total_objective=0.0,
        )
        violations = validate(result, scenario)
        h3 = [v for v in violations if "H3" in v or "simultaneous" in v.lower()]
        assert h3, f"Expected H3 charger-exclusivity violation, got {violations}"

    def test_two_chargers_allows_overlap(self):
        bus2 = Bus(
            id="bus-BK-02", operator="kpn",
            origin="Bengaluru", destination="Kochi",
            departure_min=1145, range_km=240.0,
        )

        two_charger_scenario = _make_scenario()
        new_stations = {n: Station(n, 2) for n in ("A", "B", "C", "D")}
        two_charger_scenario = replace(
            two_charger_scenario,
            stations=new_stations,
            buses=two_charger_scenario.buses + (bus2,),
        )
        plan2 = BusPlan(
            bus_id="bus-BK-02", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1245, 1245, 0, 1270, 0),
                ChargeEvent("C", 1490, 1490, 0, 1515, 0),
            ],
            arrival_min=1735, total_wait=0,
        )
        station_order = {
            "A": [
                StationSlot("bus-BK-01", "kpn", 0, 1240, 0, 1265),
                StationSlot("bus-BK-02", "kpn", 1, 1245, 0, 1270),
            ],
            "C": [
                StationSlot("bus-BK-01", "kpn", 0, 1485, 0, 1510),
                StationSlot("bus-BK-02", "kpn", 0, 1490, 0, 1515),
            ],
        }
        result = ScheduleResult(
            bus_plans=[_valid_plan(), plan2],
            station_order=station_order,
            objective_breakdown={}, total_objective=0.0,
        )
        violations = validate(result, two_charger_scenario)
        h3 = [v for v in violations if "H3" in v]
        assert h3 == [], f"Two-charger station should not trigger H3, got {h3}"


class TestH4ChargeDuration:

    def test_correct_duration_passes(self):
        result, scenario = _wrap(_valid_plan())
        h4 = [v for v in validate(result, scenario) if "H4" in v]
        assert h4 == []

    def test_short_charge_duration_detected(self):
        bad = BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1240, 1240, 0, 1260, 0),
                ChargeEvent("C", 1480, 1480, 0, 1505, 0),
            ],
            arrival_min=1725, total_wait=0,
        )
        result, scenario = _wrap(bad)
        violations = validate(result, scenario)
        h4 = [v for v in violations if "H4" in v or "duration" in v.lower()]
        assert h4, f"Expected H4 charge-duration violation, got {violations}"

    def test_long_charge_duration_detected(self):
        bad = BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1240, 1240, 0, 1270, 0),
                ChargeEvent("C", 1490, 1490, 0, 1515, 0),
            ],
            arrival_min=1735, total_wait=0,
        )
        result, scenario = _wrap(bad)
        violations = validate(result, scenario)
        h4 = [v for v in violations if "H4" in v or "duration" in v.lower()]
        assert h4, f"Expected H4 charge-duration violation, got {violations}"


class TestWaitMinConsistency:

    def test_consistent_wait_min_passes(self):
        result, scenario = _wrap(_valid_plan())
        wait_issues = [v for v in validate(result, scenario) if "wait_min" in v]
        assert wait_issues == []

    def test_wrong_wait_min_detected(self):
        bad = BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[
                ChargeEvent("A", 1240, 1240, 99, 1265, 0),
                ChargeEvent("C", 1485, 1485, 0, 1510, 0),
            ],
            arrival_min=1730, total_wait=99,
        )
        result, scenario = _wrap(bad)
        violations = validate(result, scenario)
        assert violations, f"Expected wait_min consistency violation, got none"


class TestR15ThroughBusMinCharges:

    def test_bus_with_two_charges_passes(self):
        result, scenario = _wrap(_valid_plan())
        r15 = [v for v in validate(result, scenario) if "through-bus" in v]
        assert r15 == []

    def test_through_bus_with_zero_charges_detected(self):
        no_charges = BusPlan(
            bus_id="bus-BK-01", operator="kpn", direction="BK",
            charge_events=[],
            arrival_min=1680, total_wait=0,
        )
        result = ScheduleResult(
            bus_plans=[no_charges],
            station_order={},
            objective_breakdown={}, total_objective=0.0,
        )
        scenario = _make_scenario()
        violations = validate(result, scenario)
        r15 = [v for v in violations if "through-bus" in v or "charge event" in v]
        assert r15, f"Expected R15 through-bus violation, got {violations}"
