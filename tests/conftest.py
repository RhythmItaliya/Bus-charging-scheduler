"""
tests/conftest.py — Shared fixtures and helpers for all test modules.

Helpers defined here are available to every test file in this directory via
pytest's automatic conftest discovery.  They provide the canonical Bengaluru–Kochi
scenario and a charge-event factory used across multiple test files.
"""

from __future__ import annotations

import pytest

from scheduler.model import (
    Bus,
    BusPlan,
    ChargeEvent,
    Route,
    Scenario,
    Segment,
    Station,
    StationSlot,
    Weights,
    World,
)
from scheduler.rules.registry import ScheduleContext


# ---------------------------------------------------------------------------
# Scenario builder
# ---------------------------------------------------------------------------

def build_scenario(
    weights: Weights | None = None,
    battery_range_km: float = 240.0,
    include_kb: bool = False,
    num_chargers: int = 1,
) -> Scenario:
    """
    Build the canonical Bengaluru→Kochi scenario programmatically.

    Args:
        weights:          Custom Weights object; defaults to all-ones.
        battery_range_km: Battery range override (default 240 km).
        include_kb:       When True, adds one KB (Kochi→Bengaluru) bus.
        num_chargers:     Charger count for all stations (default 1).

    Returns:
        A ready-to-use Scenario with one BK bus (plus one KB if requested).
    """
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
    stations = {n: Station(n, num_chargers) for n in ("A", "B", "C", "D")}
    world = World(speed_kmph=60, charge_minutes=25, battery_range_km=battery_range_km)
    if weights is None:
        weights = Weights(individual=1.0, operator=1.0, overall=1.0)
    buses: list[Bus] = [
        Bus(id="bus-BK-01", operator="kpn", origin="Bengaluru",
            destination="Kochi", departure_min=1140, range_km=battery_range_km),
    ]
    if include_kb:
        buses.append(
            Bus(id="bus-KB-01", operator="kpn", origin="Kochi",
                destination="Bengaluru", departure_min=1140, range_km=battery_range_km)
        )
    return Scenario(
        name="test", world=world, route=route,
        stations=stations, weights=weights, buses=tuple(buses),
    )


# ---------------------------------------------------------------------------
# Charge-event factory
# ---------------------------------------------------------------------------

def make_event(
    station: str,
    arrive: int,
    wait: int,
    start: int | None = None,
    end: int | None = None,
    charger: int = 0,
) -> dict:
    """
    Build a charge-event dict (the shape used inside _simulate_plan and rules).

    Args:
        station: Station node name (e.g. "A").
        arrive:  Arrival minute.
        wait:    Wait minutes (start - arrive).
        start:   Charge-start minute; defaults to arrive + wait.
        end:     Charge-end minute; defaults to start + 25.
        charger: Charger slot index (0-indexed).
    """
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
# pytest fixtures (dependency-injected into test functions/methods)
# ---------------------------------------------------------------------------

@pytest.fixture
def canonical_scenario() -> Scenario:
    """Single BK bus, all-ones weights, 240 km range."""
    return build_scenario()


@pytest.fixture
def canonical_scenario_with_kb() -> Scenario:
    """One BK bus + one KB bus, all-ones weights."""
    return build_scenario(include_kb=True)
