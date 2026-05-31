"""
tests/test_loader.py — Unit tests for the loader (the trust boundary).

The loader is the only place that reads files and validates raw input.
After it returns a Scenario, all downstream code trusts the data.
So these tests verify every branch of the 3-stage validation:
  Stage 1 — World constants
  Stage 2 — Route connectivity
  Stage 3 — Stations, weights, buses

References:
    scheduler/loader.py
    docs/04-api-contracts/02-validation-rules.md
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scheduler.loader import list_scenarios, load_scenario


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, data: dict) -> Path:
    """Write data as JSON to a temp file and return the path."""
    p = tmp_path / "scenario.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _base() -> dict:
    """
    Minimal valid scenario dict.
    Uses a 3-node route (Bengaluru → A → Kochi) to keep tests focused.
    """
    return {
        "name": "Test",
        "world": {
            "speed_kmph": 60,
            "charge_minutes": 25,
            "battery_range_km": 240,
        },
        "route": {
            "nodes": ["Bengaluru", "A", "Kochi"],
            "segments": [
                {"from": "Bengaluru", "to": "A", "distance_km": 100},
                {"from": "A", "to": "Kochi", "distance_km": 240},
            ],
        },
        "stations": {"A": {"num_chargers": 1}},
        "weights": {"individual": 1.0, "operator": 1.0, "overall": 1.0},
        "buses": [
            {
                "id": "b1", "operator": "kpn",
                "origin": "Bengaluru", "destination": "Kochi",
                "departure_min": 1140,
            }
        ],
    }


# ---------------------------------------------------------------------------
# list_scenarios
# ---------------------------------------------------------------------------

class TestListScenarios:

    def test_finds_five_real_scenarios(self):
        """The data/scenarios directory contains exactly 5 scenario files."""
        result = list_scenarios("data/scenarios")
        assert len(result) == 5

    def test_returns_name_path_tuples(self):
        """Each element is a (str, Path) pair."""
        result = list_scenarios("data/scenarios")
        for name, path in result:
            assert isinstance(name, str)
            assert isinstance(path, Path)

    def test_sorted_by_filename(self):
        """Files are returned in filename-alphabetical order (scenario_1 before scenario_2)."""
        result = list_scenarios("data/scenarios")
        filenames = [p.name for _, p in result]
        assert filenames == sorted(filenames)

    def test_names_come_from_json_name_field(self):
        """Display names come from the JSON 'name' key, not from the filename."""
        result = list_scenarios("data/scenarios")
        names = [name for name, _ in result]
        assert any("Scenario" in n for n in names)

    def test_missing_directory_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            list_scenarios("data/nonexistent_xyz")

    def test_empty_directory_returns_empty_list(self, tmp_path):
        result = list_scenarios(tmp_path)
        assert result == []

    def test_invalid_json_file_is_skipped(self, tmp_path):
        (tmp_path / "bad.json").write_text("NOT VALID JSON {{", encoding="utf-8")
        result = list_scenarios(tmp_path)
        assert result == []

    def test_valid_and_invalid_files_coexist(self, tmp_path):
        (tmp_path / "good.json").write_text(
            json.dumps({"name": "Good"}), encoding="utf-8"
        )
        (tmp_path / "bad.json").write_text("INVALID", encoding="utf-8")
        result = list_scenarios(tmp_path)
        assert len(result) == 1
        assert result[0][0] == "Good"

    def test_missing_name_key_falls_back_to_stem(self, tmp_path):
        (tmp_path / "my_test.json").write_text(
            json.dumps({"buses": []}), encoding="utf-8"
        )
        result = list_scenarios(tmp_path)
        assert result[0][0] == "my_test"


# ---------------------------------------------------------------------------
# load_scenario — Stage 1: World constants
# ---------------------------------------------------------------------------

class TestLoadScenarioWorld:

    def test_valid_scenario_loads_correctly(self, tmp_path):
        s = load_scenario(_write(tmp_path, _base()))
        assert s.world.speed_kmph == 60
        assert s.world.charge_minutes == 25
        assert s.world.battery_range_km == 240

    def test_missing_world_block_uses_all_defaults(self, tmp_path):
        data = _base()
        del data["world"]
        s = load_scenario(_write(tmp_path, data))
        assert s.world.speed_kmph == 60     # from DEFAULTS
        assert s.world.charge_minutes == 25
        assert s.world.battery_range_km == 240

    def test_speed_zero_raises(self, tmp_path):
        data = _base()
        data["world"]["speed_kmph"] = 0
        with pytest.raises(ValueError, match="speed_kmph"):
            load_scenario(_write(tmp_path, data))

    def test_speed_negative_raises(self, tmp_path):
        data = _base()
        data["world"]["speed_kmph"] = -10
        with pytest.raises(ValueError, match="speed_kmph"):
            load_scenario(_write(tmp_path, data))

    def test_charge_minutes_zero_raises(self, tmp_path):
        data = _base()
        data["world"]["charge_minutes"] = 0
        with pytest.raises(ValueError, match="charge_minutes"):
            load_scenario(_write(tmp_path, data))

    def test_battery_range_zero_raises(self, tmp_path):
        data = _base()
        data["world"]["battery_range_km"] = 0
        with pytest.raises(ValueError, match="battery_range_km"):
            load_scenario(_write(tmp_path, data))

    def test_partial_world_override_keeps_other_defaults(self, tmp_path):
        data = _base()
        data["world"] = {"speed_kmph": 80}   # only override speed
        s = load_scenario(_write(tmp_path, data))
        assert s.world.speed_kmph == 80
        assert s.world.charge_minutes == 25  # still default
        assert s.world.battery_range_km == 240


# ---------------------------------------------------------------------------
# load_scenario — Stage 2: Route
# ---------------------------------------------------------------------------

class TestLoadScenarioRoute:

    def test_positions_computed_correctly(self, tmp_path):
        s = load_scenario(_write(tmp_path, _base()))
        assert s.route.positions["Bengaluru"] == 0.0
        assert s.route.positions["A"] == 100.0
        assert s.route.positions["Kochi"] == 340.0

    def test_fewer_than_two_nodes_raises(self, tmp_path):
        data = _base()
        data["route"]["nodes"] = ["Bengaluru"]
        data["route"]["segments"] = []
        with pytest.raises(ValueError, match="nodes"):
            load_scenario(_write(tmp_path, data))

    def test_segment_count_mismatch_raises(self, tmp_path):
        data = _base()
        data["route"]["segments"] = []   # 0 segments for 3 nodes (need 2)
        with pytest.raises(ValueError, match="segments"):
            load_scenario(_write(tmp_path, data))

    def test_segment_from_field_mismatch_raises(self, tmp_path):
        data = _base()
        data["route"]["segments"][0]["from"] = "WRONG_NODE"
        with pytest.raises(ValueError, match="from"):
            load_scenario(_write(tmp_path, data))

    def test_segment_to_field_mismatch_raises(self, tmp_path):
        data = _base()
        data["route"]["segments"][0]["to"] = "WRONG_NODE"
        with pytest.raises(ValueError, match="to"):
            load_scenario(_write(tmp_path, data))

    def test_segment_distance_zero_raises(self, tmp_path):
        data = _base()
        data["route"]["segments"][0]["distance_km"] = 0
        with pytest.raises(ValueError, match="distance_km"):
            load_scenario(_write(tmp_path, data))

    def test_segment_distance_negative_raises(self, tmp_path):
        data = _base()
        data["route"]["segments"][0]["distance_km"] = -50
        with pytest.raises(ValueError, match="distance_km"):
            load_scenario(_write(tmp_path, data))

    def test_full_route_nodes_tuple(self, tmp_path):
        s = load_scenario(_write(tmp_path, _base()))
        assert s.route.nodes == ("Bengaluru", "A", "Kochi")

    def test_intermediate_nodes_excludes_endpoints(self, tmp_path):
        s = load_scenario(_write(tmp_path, _base()))
        assert s.intermediate_nodes == ["A"]


# ---------------------------------------------------------------------------
# load_scenario — Stage 3a: Stations
# ---------------------------------------------------------------------------

class TestLoadScenarioStations:

    def test_endpoint_as_station_raises(self, tmp_path):
        data = _base()
        data["stations"]["Bengaluru"] = {"num_chargers": 1}
        with pytest.raises(ValueError, match="intermediate"):
            load_scenario(_write(tmp_path, data))

    def test_zero_chargers_raises(self, tmp_path):
        data = _base()
        data["stations"]["A"]["num_chargers"] = 0
        with pytest.raises(ValueError, match="num_chargers"):
            load_scenario(_write(tmp_path, data))

    def test_negative_chargers_raises(self, tmp_path):
        data = _base()
        data["stations"]["A"]["num_chargers"] = -1
        with pytest.raises(ValueError, match="num_chargers"):
            load_scenario(_write(tmp_path, data))

    def test_missing_station_entry_gets_default_one_charger(self, tmp_path):
        data = _base()
        del data["stations"]["A"]
        s = load_scenario(_write(tmp_path, data))
        assert s.stations["A"].num_chargers == 1

    def test_explicit_multi_charger_station(self, tmp_path):
        data = _base()
        data["stations"]["A"]["num_chargers"] = 3
        s = load_scenario(_write(tmp_path, data))
        assert s.stations["A"].num_chargers == 3


# ---------------------------------------------------------------------------
# load_scenario — Stage 3b: Weights
# ---------------------------------------------------------------------------

class TestLoadScenarioWeights:

    def test_default_weights_when_missing(self, tmp_path):
        data = _base()
        del data["weights"]
        s = load_scenario(_write(tmp_path, data))
        assert s.weights.individual == 1.0
        assert s.weights.operator == 1.0
        assert s.weights.overall == 1.0

    def test_custom_weights_applied(self, tmp_path):
        data = _base()
        data["weights"] = {"individual": 2.5, "operator": 0.5, "overall": 3.0}
        s = load_scenario(_write(tmp_path, data))
        assert s.weights.individual == 2.5
        assert s.weights.operator == 0.5
        assert s.weights.overall == 3.0

    def test_extra_weight_stored_in_extra_dict(self, tmp_path):
        data = _base()
        data["weights"]["electricity_cost"] = 1.5
        s = load_scenario(_write(tmp_path, data))
        assert s.weights.extra["electricity_cost"] == 1.5

    def test_weight_get_returns_extra(self, tmp_path):
        data = _base()
        data["weights"]["custom_key"] = 2.0
        s = load_scenario(_write(tmp_path, data))
        assert s.weights.get("custom_key") == 2.0

    def test_weight_get_returns_default_for_unknown_key(self, tmp_path):
        s = load_scenario(_write(tmp_path, _base()))
        assert s.weights.get("nonexistent", 99.0) == 99.0


# ---------------------------------------------------------------------------
# load_scenario — Stage 3c: Buses
# ---------------------------------------------------------------------------

class TestLoadScenarioBuses:

    def test_empty_bus_list_raises(self, tmp_path):
        data = _base()
        data["buses"] = []
        with pytest.raises(ValueError, match="bus"):
            load_scenario(_write(tmp_path, data))

    def test_missing_bus_id_raises(self, tmp_path):
        data = _base()
        del data["buses"][0]["id"]
        with pytest.raises(ValueError, match="id"):
            load_scenario(_write(tmp_path, data))

    def test_empty_bus_id_raises(self, tmp_path):
        data = _base()
        data["buses"][0]["id"] = ""
        with pytest.raises(ValueError, match="id"):
            load_scenario(_write(tmp_path, data))

    def test_missing_operator_raises(self, tmp_path):
        data = _base()
        del data["buses"][0]["operator"]
        with pytest.raises(ValueError, match="operator"):
            load_scenario(_write(tmp_path, data))

    def test_empty_operator_raises(self, tmp_path):
        data = _base()
        data["buses"][0]["operator"] = ""
        with pytest.raises(ValueError, match="operator"):
            load_scenario(_write(tmp_path, data))

    def test_origin_not_in_route_raises(self, tmp_path):
        data = _base()
        data["buses"][0]["origin"] = "Mumbai"
        with pytest.raises(ValueError, match="origin"):
            load_scenario(_write(tmp_path, data))

    def test_destination_not_in_route_raises(self, tmp_path):
        data = _base()
        data["buses"][0]["destination"] = "Chennai"
        with pytest.raises(ValueError, match="destination"):
            load_scenario(_write(tmp_path, data))

    def test_negative_departure_min_raises(self, tmp_path):
        data = _base()
        data["buses"][0]["departure_min"] = -1
        with pytest.raises(ValueError, match="departure_min"):
            load_scenario(_write(tmp_path, data))

    def test_zero_departure_is_valid(self, tmp_path):
        data = _base()
        data["buses"][0]["departure_min"] = 0
        s = load_scenario(_write(tmp_path, data))
        assert s.buses[0].departure_min == 0

    def test_zero_range_km_raises(self, tmp_path):
        data = _base()
        data["buses"][0]["range_km"] = 0
        with pytest.raises(ValueError, match="range_km"):
            load_scenario(_write(tmp_path, data))

    def test_missing_range_km_defaults_to_world_battery_range(self, tmp_path):
        s = load_scenario(_write(tmp_path, _base()))
        assert s.buses[0].range_km == 240.0

    def test_custom_range_km_applied(self, tmp_path):
        data = _base()
        data["buses"][0]["range_km"] = 300.0
        s = load_scenario(_write(tmp_path, data))
        assert s.buses[0].range_km == 300.0

    def test_priority_defaults_to_zero(self, tmp_path):
        s = load_scenario(_write(tmp_path, _base()))
        assert s.buses[0].priority == 0

    def test_bus_count_matches_scenario_1(self):
        s = load_scenario("data/scenarios/scenario_1.json")
        assert len(s.buses) == 20

    def test_operators_property_reflects_bus_list(self, tmp_path):
        data = _base()
        data["buses"].append({
            "id": "b2", "operator": "freshbus",
            "origin": "Bengaluru", "destination": "Kochi",
            "departure_min": 1155,
        })
        s = load_scenario(_write(tmp_path, data))
        assert s.operators == {"kpn", "freshbus"}
