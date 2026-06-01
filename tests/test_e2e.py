import json
import pytest

from scheduler.adapters import to_bus_table, to_input_table, to_station_table
from scheduler.engine import schedule
from scheduler.loader import load_scenario
from scheduler.validate import validate


ALL_SCENARIOS = [
    "data/scenarios/scenario_1.json",
    "data/scenarios/scenario_2.json",
    "data/scenarios/scenario_3.json",
    "data/scenarios/scenario_4.json",
    "data/scenarios/scenario_5.json",
]


class TestAllScenariosScheduleCleanly:

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_no_validation_violations(self, path):
        scenario = load_scenario(path)
        result = schedule(scenario)
        violations = validate(result, scenario)
        assert violations == [], (
            f"Scenario {path} produced violations:\n" + "\n".join(violations)
        )

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_every_through_bus_has_at_least_2_charges(self, path):
        scenario = load_scenario(path)
        result = schedule(scenario)

        for bp in result.bus_plans:
            assert len(bp.charge_events) >= 2, (
                f"{bp.bus_id} (dir={bp.direction}) has only "
                f"{len(bp.charge_events)} charge event(s) — expected ≥ 2."
            )

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_every_bus_has_arrival_time(self, path):
        scenario = load_scenario(path)
        result = schedule(scenario)
        for bp in result.bus_plans:
            assert bp.arrival_min > 0, (
                f"{bp.bus_id} has invalid arrival_min={bp.arrival_min}"
            )

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_bus_count_matches_scenario(self, path):
        scenario = load_scenario(path)
        result = schedule(scenario)
        assert len(result.bus_plans) == len(scenario.buses), (
            f"Expected {len(scenario.buses)} bus plans, got {len(result.bus_plans)}"
        )

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_station_order_covers_expected_nodes(self, path):
        scenario = load_scenario(path)
        result = schedule(scenario)

        assert len(result.station_order) > 0, "station_order is empty — no buses were charged"

        for node in result.station_order:
            assert node in scenario.intermediate_nodes, (
                f"station_order contains '{node}' which is not an intermediate node"
            )

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_objective_breakdown_has_all_three_terms(self, path):
        scenario = load_scenario(path)
        result = schedule(scenario)
        bd = result.objective_breakdown
        assert "IndividualWaitRule" in bd
        assert "OperatorRule" in bd
        assert "OverallRule" in bd


class TestDeterminism:

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_schedule_is_deterministic(self, path):
        scenario = load_scenario(path)
        result1 = schedule(scenario)
        result2 = schedule(scenario)


        def plan_to_dict(bp):
            return {
                "bus_id": bp.bus_id,
                "arrival_min": bp.arrival_min,
                "total_wait": bp.total_wait,
                "stations": [e.station for e in bp.charge_events],
            }

        plans1 = sorted([plan_to_dict(bp) for bp in result1.bus_plans], key=lambda x: x["bus_id"])
        plans2 = sorted([plan_to_dict(bp) for bp in result2.bus_plans], key=lambda x: x["bus_id"])
        assert plans1 == plans2, f"Non-deterministic results for {path}"


class TestAdapterIntegration:

    def test_input_table_has_correct_row_count(self):
        scenario = load_scenario("data/scenarios/scenario_1.json")
        df = to_input_table(scenario)
        assert len(df) == len(scenario.buses)

    def test_bus_table_has_charge_events(self):
        scenario = load_scenario("data/scenarios/scenario_1.json")
        result = schedule(scenario)
        df = to_bus_table(result, scenario)
        assert len(df) > 0
        assert "Wait (min)" in df.columns
        assert "Bus ID" in df.columns

    def test_station_table_for_each_node(self):
        scenario = load_scenario("data/scenarios/scenario_1.json")
        result = schedule(scenario)
        for node in scenario.intermediate_nodes:
            df = to_station_table(result, node)

            assert df is not None
