"""
tests/test_charger.py — Charger exclusivity invariant tests.

Covers:
  • ChargerPool serialises charges correctly: no simultaneous charges with 1 slot.
  • num_chargers=2 permits overlap of two buses.
  • Across a full scheduled scenario, no station has more concurrent charges than
    its num_chargers value.

References:
    docs/07-testing/01-testing-plan.md (test_charger.py requirements)
    docs/00-requirements/02-constraints-and-rules.md (H3)
    scheduler/resources.py
"""

import pytest
from scheduler.resources import ChargerPool
from scheduler.loader import load_scenario
from scheduler.engine import schedule
from scheduler.validate import validate


class TestChargerPool:
    """Unit tests for the ChargerPool reservation mechanism."""

    def test_first_bus_has_no_wait_if_charger_free(self):
        """A bus arriving when the charger is free starts immediately."""
        pool = ChargerPool(node="A", num_chargers=1, charge_minutes=25)
        start, wait, charger_idx = pool.reserve(arrive_min=1240)
        assert start == 1240
        assert wait == 0
        assert charger_idx == 0

    def test_second_bus_queues_behind_first(self):
        """With 1 charger, a second bus arriving before the first finishes must wait."""
        pool = ChargerPool(node="A", num_chargers=1, charge_minutes=25)
        # First bus: starts at 1240, finishes at 1265
        start1, wait1, _ = pool.reserve(arrive_min=1240)
        assert start1 == 1240
        assert wait1 == 0

        # Second bus arrives at 1245 (while first is still charging, finishes at 1265)
        start2, wait2, _ = pool.reserve(arrive_min=1245)
        assert start2 == 1265   # must wait for first to finish
        assert wait2 == 1265 - 1245

    def test_two_chargers_allow_overlap(self):
        """With 2 chargers, two buses can charge simultaneously."""
        pool = ChargerPool(node="B", num_chargers=2, charge_minutes=25)
        start1, wait1, idx1 = pool.reserve(arrive_min=1300)
        start2, wait2, idx2 = pool.reserve(arrive_min=1300)
        # Both start at the same time (no wait)
        assert start1 == 1300
        assert start2 == 1300
        assert wait1 == 0
        assert wait2 == 0
        # They use different charger slots
        assert idx1 != idx2

    def test_snapshot_restore_allows_rollback(self):
        """Snapshot and restore leave pool state unchanged after a tentative reserve."""
        pool = ChargerPool(node="C", num_chargers=1, charge_minutes=25)
        snap = pool.snapshot()
        pool.reserve(arrive_min=1300)  # tentative reserve
        pool.restore(snap)             # roll back

        # After rollback, a new reserve should behave as if the first never happened
        start, wait, _ = pool.reserve(arrive_min=1300)
        assert start == 1300
        assert wait == 0

    def test_bus_arriving_after_charger_frees_has_no_wait(self):
        """Bus arriving well after first finishes should have no wait."""
        pool = ChargerPool(node="D", num_chargers=1, charge_minutes=25)
        pool.reserve(arrive_min=1240)  # finishes at 1265
        start, wait, _ = pool.reserve(arrive_min=1270)  # arrives after
        assert start == 1270
        assert wait == 0


class TestChargerExclusivityAcrossSchedule:
    """Integration tests: charger exclusivity invariant on full scenarios."""

    @pytest.mark.parametrize("scenario_path", [
        "data/scenarios/scenario_1.json",
        "data/scenarios/scenario_2.json",
        "data/scenarios/scenario_3.json",
        "data/scenarios/scenario_4.json",
        "data/scenarios/scenario_5.json",
    ])
    def test_no_station_exceeds_charger_capacity(self, scenario_path):
        """
        For every scheduled scenario, no station serves more buses simultaneously
        than its num_chargers value.  This is the H3 invariant.
        """
        scenario = load_scenario(scenario_path)
        result = schedule(scenario)
        violations = validate(result, scenario)

        charger_violations = [v for v in violations if "H3" in v or "simultaneous" in v]
        assert charger_violations == [], (
            f"Charger exclusivity violations in {scenario_path}:\n"
            + "\n".join(charger_violations)
        )

    def test_two_chargers_allows_concurrency_in_custom_scenario(self):
        """
        If num_chargers=2 at a station, two buses can charge simultaneously.
        Verify the pool reflects this — concurrency is NOT a violation.
        """
        pool = ChargerPool(node="B", num_chargers=2, charge_minutes=25)
        start1, wait1, idx1 = pool.reserve(1300)
        start2, wait2, idx2 = pool.reserve(1300)
        # Both buses start at same time (no wait, 2 chargers available)
        assert wait1 == 0
        assert wait2 == 0
        assert start1 == start2 == 1300
