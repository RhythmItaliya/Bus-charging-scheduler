from __future__ import annotations

import pytest

from scheduler.adapters import to_bus_table, to_input_table, to_station_table
from scheduler.engine import schedule
from scheduler.loader import load_scenario


_SCENARIO = load_scenario("data/scenarios/scenario_1.json")
_RESULT = schedule(_SCENARIO)


class TestToInputTable:

    def test_row_count_equals_bus_count(self):
        df = to_input_table(_SCENARIO)
        assert len(df) == len(_SCENARIO.buses)

    def test_required_columns_present(self):
        df = to_input_table(_SCENARIO)
        assert {"Bus ID", "Operator", "Direction", "Departure", "Range (km)", "Priority"}\
            .issubset(set(df.columns))

    def test_departure_is_hhmm_format(self):
        df = to_input_table(_SCENARIO)
        for dep in df["Departure"]:
            assert isinstance(dep, str) and len(dep) == 5 and dep[2] == ":", (
                f"Expected HH:MM, got {dep!r}"
            )

    def test_direction_values_are_valid(self):
        df = to_input_table(_SCENARIO)
        valid = {"BK (→ Kochi)", "KB (→ Bengaluru)"}
        for d in df["Direction"]:
            assert d in valid, f"Unexpected direction value: {d!r}"

    def test_operator_is_uppercase(self):
        df = to_input_table(_SCENARIO)
        for op in df["Operator"]:
            assert op == op.upper(), f"Operator {op!r} is not uppercase"

    def test_sorted_by_departure_time(self):
        df = to_input_table(_SCENARIO)
        deps = list(df["Departure"])
        assert deps == sorted(deps), "Rows are not sorted by departure time"

    def test_range_km_is_positive(self):
        df = to_input_table(_SCENARIO)
        assert (df["Range (km)"] > 0).all()

    def test_priority_is_integer(self):
        df = to_input_table(_SCENARIO)
        for p in df["Priority"]:
            assert isinstance(p, (int,)), f"Priority {p!r} is not an int"


class TestToBusTable:

    def test_at_least_one_row_per_bus(self):
        df = to_bus_table(_RESULT, _SCENARIO)

        assert len(df) >= len(_RESULT.bus_plans)

    def test_required_columns_present(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        required = {"Bus ID", "Operator", "Dir", "Station", "Arrive",
                    "Wait (min)", "Charge Start", "Charge End",
                    "Final Arrival", "Total Wait"}
        assert required.issubset(set(df.columns))

    def test_wait_min_values_are_non_negative(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        assert (df["Wait (min)"] >= 0).all()

    def test_charge_start_is_hhmm(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        for val in df["Charge Start"]:
            assert len(val) == 5 and val[2] == ":", f"Expected HH:MM, got {val!r}"

    def test_charge_end_is_hhmm(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        for val in df["Charge End"]:
            assert len(val) == 5 and val[2] == ":", f"Expected HH:MM, got {val!r}"

    def test_final_arrival_on_last_row_only(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        for bus_id, group in df.groupby("Bus ID"):
            non_empty = group[group["Final Arrival"] != ""]
            assert len(non_empty) == 1, (
                f"{bus_id}: Final Arrival appears on {len(non_empty)} rows, expected 1"
            )

    def test_total_wait_on_last_row_only(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        for bus_id, group in df.groupby("Bus ID"):
            non_empty = group[group["Total Wait"] != ""]
            assert len(non_empty) == 1, (
                f"{bus_id}: Total Wait appears on {len(non_empty)} rows, expected 1"
            )

    def test_total_wait_matches_bus_plan(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        for bp in _RESULT.bus_plans:
            group = df[df["Bus ID"] == bp.bus_id]
            last_row = group[group["Total Wait"] != ""]
            assert len(last_row) == 1
            reported_wait = int(last_row["Total Wait"].iloc[0])
            assert reported_wait == bp.total_wait, (
                f"{bp.bus_id}: reported Total Wait {reported_wait} ≠ "
                f"expected {bp.total_wait}"
            )

    def test_direction_values_are_bk_or_kb(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        for d in df["Dir"]:
            assert d in ("BK", "KB"), f"Unexpected direction {d!r}"

    def test_station_values_are_intermediate_nodes(self):
        df = to_bus_table(_RESULT, _SCENARIO)
        intermediate = set(_SCENARIO.intermediate_nodes)
        for s in df["Station"]:
            if s != "—":
                assert s in intermediate, f"Unknown station {s!r} in bus table"


class TestToStationTable:

    def test_nonexistent_node_returns_empty_df(self):
        df = to_station_table(_RESULT, "ZZZZ")
        assert df.empty

    def test_empty_df_has_required_columns(self):
        df = to_station_table(_RESULT, "ZZZZ")
        required = {"Order", "Bus ID", "Operator", "Charger #",
                    "Arrive", "Wait (min)", "Charge Start", "Charge End"}
        assert required.issubset(set(df.columns))

    def test_station_a_has_rows(self):
        df = to_station_table(_RESULT, "A")
        assert len(df) > 0

    def test_order_column_is_sequential_from_one(self):
        df = to_station_table(_RESULT, "A")
        assert list(df["Order"]) == list(range(1, len(df) + 1))

    def test_charger_is_one_indexed(self):
        df = to_station_table(_RESULT, "A")
        assert (df["Charger #"] >= 1).all()

    def test_charge_start_is_hhmm(self):
        df = to_station_table(_RESULT, "A")
        for val in df["Charge Start"]:
            assert len(val) == 5 and val[2] == ":", f"Expected HH:MM, got {val!r}"

    def test_charge_end_is_hhmm(self):
        df = to_station_table(_RESULT, "A")
        for val in df["Charge End"]:
            assert len(val) == 5 and val[2] == ":", f"Expected HH:MM, got {val!r}"

    def test_wait_min_values_non_negative(self):
        df = to_station_table(_RESULT, "A")
        assert (df["Wait (min)"] >= 0).all()

    def test_row_count_matches_buses_that_used_station(self):
        df = to_station_table(_RESULT, "A")
        expected = len(_RESULT.station_order.get("A", []))
        assert len(df) == expected

    @pytest.mark.parametrize("node", ["A", "B", "C", "D"])
    def test_all_stations_return_valid_df(self, node):
        df = to_station_table(_RESULT, node)
        assert df is not None

        assert len(df) > 0, f"Station {node} has no charge records"
