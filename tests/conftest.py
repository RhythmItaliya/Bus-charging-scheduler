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


def build_scenario(
    weights: Weights | None = None,
    battery_range_km: float = 240.0,
    include_kb: bool = False,
    num_chargers: int = 1,
) -> Scenario:
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


def make_event(
    station: str,
    arrive: int,
    wait: int,
    start: int | None = None,
    end: int | None = None,
    charger: int = 0,
) -> dict:
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


@pytest.fixture
def canonical_scenario() -> Scenario:
    return build_scenario()


@pytest.fixture
def canonical_scenario_with_kb() -> Scenario:
    return build_scenario(include_kb=True)
