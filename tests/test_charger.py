import pytest
from scheduler.resources import ChargerPool
from scheduler.loader import load_scenario
from scheduler.engine import schedule
from scheduler.validate import validate


class TestChargerPool:

    def test_first_bus_has_no_wait_if_charger_free(self):
        pool = ChargerPool(node="A", num_chargers=1, charge_minutes=25)
        start, wait, charger_idx = pool.reserve(arrive_min=1240)
        assert start == 1240
        assert wait == 0
        assert charger_idx == 0

    def test_second_bus_queues_behind_first(self):
        pool = ChargerPool(node="A", num_chargers=1, charge_minutes=25)

        start1, wait1, _ = pool.reserve(arrive_min=1240)
        assert start1 == 1240
        assert wait1 == 0


        start2, wait2, _ = pool.reserve(arrive_min=1245)
        assert start2 == 1265
        assert wait2 == 1265 - 1245

    def test_two_chargers_allow_overlap(self):
        pool = ChargerPool(node="B", num_chargers=2, charge_minutes=25)
        start1, wait1, idx1 = pool.reserve(arrive_min=1300)
        start2, wait2, idx2 = pool.reserve(arrive_min=1300)

        assert start1 == 1300
        assert start2 == 1300
        assert wait1 == 0
        assert wait2 == 0

        assert idx1 != idx2

    def test_snapshot_restore_allows_rollback(self):
        pool = ChargerPool(node="C", num_chargers=1, charge_minutes=25)
        snap = pool.snapshot()
        pool.reserve(arrive_min=1300)
        pool.restore(snap)


        start, wait, _ = pool.reserve(arrive_min=1300)
        assert start == 1300
        assert wait == 0

    def test_bus_arriving_after_charger_frees_has_no_wait(self):
        pool = ChargerPool(node="D", num_chargers=1, charge_minutes=25)
        pool.reserve(arrive_min=1240)
        start, wait, _ = pool.reserve(arrive_min=1270)
        assert start == 1270
        assert wait == 0


class TestChargerExclusivityAcrossSchedule:

    @pytest.mark.parametrize("scenario_path", [
        "data/scenarios/scenario_1.json",
        "data/scenarios/scenario_2.json",
        "data/scenarios/scenario_3.json",
        "data/scenarios/scenario_4.json",
        "data/scenarios/scenario_5.json",
    ])
    def test_no_station_exceeds_charger_capacity(self, scenario_path):
        scenario = load_scenario(scenario_path)
        result = schedule(scenario)
        violations = validate(result, scenario)

        charger_violations = [v for v in violations if "H3" in v or "simultaneous" in v]
        assert charger_violations == [], (
            f"Charger exclusivity violations in {scenario_path}:\n"
            + "\n".join(charger_violations)
        )

    def test_two_chargers_allows_concurrency_in_custom_scenario(self):
        pool = ChargerPool(node="B", num_chargers=2, charge_minutes=25)
        start1, wait1, idx1 = pool.reserve(1300)
        start2, wait2, idx2 = pool.reserve(1300)

        assert wait1 == 0
        assert wait2 == 0
        assert start1 == start2 == 1300
