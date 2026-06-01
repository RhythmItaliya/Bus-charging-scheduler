from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class World:


    speed_kmph: float = 60.0


    charge_minutes: int = 25


    battery_range_km: float = 240.0


@dataclass(frozen=True)
class Segment:
    from_node: str
    to_node: str
    distance_km: float


@dataclass(frozen=True)
class Route:
    nodes: tuple[str, ...]
    segments: tuple[Segment, ...]


    positions: Dict[str, float] = field(default_factory=dict)

    def distance_between(self, from_node: str, to_node: str) -> float:
        return abs(self.positions[to_node] - self.positions[from_node])


@dataclass(frozen=True)
class Station:
    node: str
    num_chargers: int = 1


@dataclass(frozen=True)
class Bus:
    id: str
    operator: str
    origin: str
    destination: str
    departure_min: int


    range_km: float = 240.0
    priority: int = 0


@dataclass(frozen=True)
class Weights:
    individual: float = 1.0
    operator: float = 1.0
    overall: float = 1.0


    extra: Dict[str, float] = field(default_factory=dict)

    def get(self, key: str, default: float = 1.0) -> float:
        known = {"individual": self.individual, "operator": self.operator,
                 "overall": self.overall}
        return known.get(key, self.extra.get(key, default))


@dataclass(frozen=True)
class Scenario:
    name: str
    world: World
    route: Route
    stations: Dict[str, Station]
    weights: Weights
    buses: tuple[Bus, ...]

    @property
    def operators(self) -> set[str]:
        return {b.operator for b in self.buses}

    @property
    def intermediate_nodes(self) -> list[str]:
        return list(self.route.nodes[1:-1])


@dataclass
class ChargeEvent:
    station: str
    arrive_min: int
    start_min: int
    wait_min: int
    end_min: int
    charger_index: int


@dataclass
class BusPlan:
    bus_id: str
    operator: str
    direction: str
    charge_events: List[ChargeEvent]
    arrival_min: int
    total_wait: int


@dataclass
class StationSlot:
    bus_id: str
    operator: str
    charger_index: int
    start_min: int
    wait_min: int
    end_min: int


@dataclass
class ScheduleResult:
    bus_plans: List[BusPlan]
    station_order: Dict[str, List[StationSlot]]
    objective_breakdown: Dict[str, float]
    total_objective: float
