"""
scheduler/loader.py — Scenario discovery and hydration.

This module is the trust boundary for all incoming data.  After the loader
returns a Scenario, all downstream code (engine, rules, adapter) can assume:
  • All distances are positive.
  • All station nodes are intermediate route nodes.
  • All buses have valid operators and non-negative departure times.
  • Route segments are contiguous.

Any structural violation raises ValueError with an actionable message that
names the offending field (docs/04-api-contracts/02-validation-rules.md §input).

Public API (docs/04-api-contracts/01-internal-api-contracts.md):
    list_scenarios(directory) -> list[tuple[str, Path]]
    load_scenario(path)       -> Scenario
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

from scheduler.config import DEFAULTS
from scheduler.model import (
    Bus,
    Route,
    Scenario,
    Segment,
    Station,
    Weights,
    World,
)
from scheduler.logger import log


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def list_scenarios(directory: str | Path) -> List[Tuple[str, Path]]:
    """
    Discover all scenario JSON files in a directory, sorted by filename.

    Returns a list of (display_name, path) pairs where display_name comes from
    the "name" key inside the file.  Powers the Streamlit scenario dropdown.

    Args:
        directory: Path to the directory containing scenario JSON files.

    Returns:
        Sorted list of (name, path) tuples (sorted by filename for stability).

    Raises:
        FileNotFoundError: if directory does not exist.
    """
    base = Path(directory)
    if not base.exists():
        log.error("Scenarios directory not found", path=str(base.resolve()))
        raise FileNotFoundError(f"Scenarios directory not found: {base.resolve()}")

    result: List[Tuple[str, Path]] = []
    for path in sorted(base.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            name = raw.get("name", path.stem)
        except (json.JSONDecodeError, OSError):
            log.warn("Skipping unreadable scenario file", file=path.name)
            continue
        result.append((name, path))

    log.info("Scenarios discovered", count=len(result), directory=str(base))
    return result


# ---------------------------------------------------------------------------
# Loading and hydration
# ---------------------------------------------------------------------------

def load_scenario(path: str | Path) -> Scenario:
    """
    Parse, validate, and hydrate a scenario JSON file into an immutable Scenario.

    Three-stage validation happens here (docs/04-api-contracts/02-validation-rules.md):
      1. Structural JSON parse.
      2. Field-level validation with actionable ValueError messages.
      3. Semantic validation (route connectivity, station membership, etc.).

    Args:
        path: Path to a scenario JSON file.

    Returns:
        A fully-validated, immutable Scenario ready for the engine.

    Raises:
        ValueError:         if any field is invalid (with a descriptive message).
        FileNotFoundError:  if the file does not exist.
        json.JSONDecodeError: if the file is not valid JSON.
    """
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    # --- 1. World (physical constants; any key optional, fallback to DEFAULTS) ---
    world_raw = raw.get("world", {})
    world = World(
        speed_kmph=float(world_raw.get("speed_kmph", DEFAULTS["speed_kmph"])),
        charge_minutes=int(world_raw.get("charge_minutes", DEFAULTS["charge_minutes"])),
        battery_range_km=float(world_raw.get("battery_range_km", DEFAULTS["battery_range_km"])),
    )
    if world.speed_kmph <= 0:
        raise ValueError(f"world.speed_kmph must be > 0, got {world.speed_kmph}")
    if world.charge_minutes <= 0:
        raise ValueError(f"world.charge_minutes must be > 0, got {world.charge_minutes}")
    if world.battery_range_km <= 0:
        raise ValueError(f"world.battery_range_km must be > 0, got {world.battery_range_km}")

    # --- 2. Route (nodes + segments + derived positions map) ---
    route_raw = raw.get("route", {})
    nodes: List[str] = list(route_raw.get("nodes", []))
    if len(nodes) < 2:
        raise ValueError("route.nodes must have at least 2 nodes (origin and destination).")

    segments_raw = route_raw.get("segments", [])
    segments: List[Segment] = []
    # Build position map: cumulative distance from nodes[0]
    positions: dict[str, float] = {nodes[0]: 0.0}
    prev_node = nodes[0]
    running_distance = 0.0

    # Validate that segments connect nodes in declared order
    if len(segments_raw) != len(nodes) - 1:
        raise ValueError(
            f"route.segments count ({len(segments_raw)}) must equal "
            f"len(nodes) - 1 ({len(nodes) - 1})."
        )
    for i, seg_raw in enumerate(segments_raw):
        from_node = seg_raw.get("from", "")
        to_node = seg_raw.get("to", "")
        dist = float(seg_raw.get("distance_km", 0))
        if from_node != nodes[i]:
            raise ValueError(
                f"route.segments[{i}].from '{from_node}' does not match "
                f"expected '{nodes[i]}'."
            )
        if to_node != nodes[i + 1]:
            raise ValueError(
                f"route.segments[{i}].to '{to_node}' does not match "
                f"expected '{nodes[i+1]}'."
            )
        if dist <= 0:
            raise ValueError(
                f"route.segments[{i}] distance_km must be > 0, got {dist}."
            )
        segments.append(Segment(from_node=from_node, to_node=to_node, distance_km=dist))
        running_distance += dist
        positions[to_node] = running_distance
        prev_node = to_node

    route = Route(
        nodes=tuple(nodes),
        segments=tuple(segments),
        positions=positions,
    )

    # --- 3. Stations (only intermediate nodes; endpoints excluded) ---
    intermediate = set(nodes[1:-1])
    stations_raw = raw.get("stations", {})
    stations: dict[str, Station] = {}
    for node, stn_raw in stations_raw.items():
        if node not in intermediate:
            raise ValueError(
                f"stations key '{node}' is not an intermediate route node. "
                f"Intermediate nodes are: {sorted(intermediate)}."
            )
        num_chargers = int(stn_raw.get("num_chargers", 1))
        if num_chargers < 1:
            raise ValueError(
                f"stations['{node}'].num_chargers must be ≥ 1, got {num_chargers}."
            )
        stations[node] = Station(node=node, num_chargers=num_chargers)

    # All intermediate nodes must have a station entry
    for node in intermediate:
        if node not in stations:
            stations[node] = Station(node=node, num_chargers=1)  # default to 1

    # --- 4. Weights (with extra dict for forward compatibility) ---
    weights_raw = raw.get("weights", {})
    known_keys = {"individual", "operator", "overall"}
    extra_weights = {k: float(v) for k, v in weights_raw.items() if k not in known_keys}
    weights = Weights(
        individual=float(weights_raw.get("individual", 1.0)),
        operator=float(weights_raw.get("operator", 1.0)),
        overall=float(weights_raw.get("overall", 1.0)),
        extra=extra_weights,
    )

    # --- 5. Buses ---
    buses_raw = raw.get("buses", [])
    if not buses_raw:
        raise ValueError("scenario must contain at least one bus.")
    buses: List[Bus] = []
    for i, b in enumerate(buses_raw):
        bus_id = b.get("id", "")
        if not bus_id:
            raise ValueError(f"buses[{i}].id is missing or empty.")
        operator = b.get("operator", "")
        if not operator:
            raise ValueError(f"buses[{i}] (id='{bus_id}'): operator must not be empty.")
        origin = b.get("origin", "")
        destination = b.get("destination", "")
        if origin not in route.nodes:
            raise ValueError(f"buses[{i}] (id='{bus_id}'): origin '{origin}' not in route.")
        if destination not in route.nodes:
            raise ValueError(f"buses[{i}] (id='{bus_id}'): destination '{destination}' not in route.")
        departure_min = int(b.get("departure_min", -1))
        if departure_min < 0:
            raise ValueError(f"buses[{i}] (id='{bus_id}'): departure_min must be >= 0.")
        range_km = float(b.get("range_km", world.battery_range_km))
        if range_km <= 0:
            raise ValueError(f"buses[{i}] (id='{bus_id}'): range_km must be > 0, got {range_km}.")
        priority = int(b.get("priority", 0))
        buses.append(Bus(
            id=bus_id,
            operator=operator,
            origin=origin,
            destination=destination,
            departure_min=departure_min,
            range_km=range_km,
            priority=priority,
        ))

    scenario = Scenario(
        name=raw.get("name", path.stem),
        world=world,
        route=route,
        stations=stations,
        weights=weights,
        buses=tuple(buses),
    )

    log.info(
        "Scenario loaded",
        name=scenario.name,
        buses=len(scenario.buses),
        stations=len(scenario.intermediate_nodes),
        route="→".join(scenario.route.nodes),
        weights=f"ind={weights.individual} op={weights.operator} all={weights.overall}",
    )
    return scenario
