"""
scheduler/model.py — Immutable domain dataclasses for the Bus Charging Scheduler.

This module defines *every* data entity used by the engine, loader, and adapter
layers.  All classes are plain Python dataclasses, intentionally free of any
Streamlit, pandas, or database imports.

Design decisions (docs/03-data-model/01-data-model-design.md):
  • Immutable at runtime — the engine reads a Scenario and produces output
    objects; it never mutates input state.  This makes st.cache_data safe.
  • Every plausibly-changing world parameter is a named field with a config
    default, not a literal scattered through engine code.
  • Output objects (ChargeEvent, BusPlan, ScheduleResult) are plain dataclasses
    convertible to dicts, enabling JSON dumps for debugging and golden tests.

References:
    docs/03-data-model/01-data-model-design.md   (entities, field choices)
    docs/03-data-model/02-scenario-schema.md     (JSON ↔ dataclass mapping)
    docs/03-data-model/03-output-schema.md       (output contracts)
    docs/00-requirements/02-constraints-and-rules.md (H1–H4, S1–S3)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# World constants (physical parameters of the simulation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class World:
    """
    Physical constants shared across all buses in a scenario.

    All three fields default to DEFAULTS values from config.py; the scenario
    JSON may override any of them.  Keeping them here (not as module-level
    literals) means a scenario can simulate a faster bus or a longer charger
    session without touching engine code.
    """

    # Speed used to derive travel time: travel_min = distance_km / speed_kmph.
    # Assumption documented in ARCHITECTURE: 60 km/h, overridable.
    speed_kmph: float = 60.0

    # Duration of every charge session (hard rule H4: always exactly this).
    charge_minutes: int = 25

    # Maximum km between any two consecutive energy-restores (hard rule H1).
    battery_range_km: float = 240.0


# ---------------------------------------------------------------------------
# Route (ordered list of nodes + segments connecting them)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Segment:
    """
    A directed edge between two adjacent route nodes.

    Segments are stored in travel-direction order for the canonical (Bengaluru→
    Kochi) direction; the loader derives the reverse direction by reversing the
    list.
    """
    from_node: str
    to_node: str
    distance_km: float   # must be > 0 (validated by loader)


@dataclass(frozen=True)
class Route:
    """
    The full ordered route: a list of node names and the segments between them.

    nodes[0] and nodes[-1] are the route endpoints (Bengaluru, Kochi).
    nodes[1:-1] are the intermediate stations eligible for charging.

    The positions dictionary is derived by the loader and caches cumulative
    distance from nodes[0] for O(1) position lookup during plan enumeration.
    """
    nodes: tuple[str, ...]        # e.g. ("Bengaluru","A","B","C","D","Kochi")
    segments: tuple[Segment, ...]

    # Cumulative distance from nodes[0] for every node, e.g. A=100, B=220, …
    positions: Dict[str, float] = field(default_factory=dict)

    def distance_between(self, from_node: str, to_node: str) -> float:
        """Return cumulative distance between two route nodes (always positive)."""
        return abs(self.positions[to_node] - self.positions[from_node])


# ---------------------------------------------------------------------------
# Station (a physical charging node on the route)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Station:
    """
    A charging station at a route node.

    num_chargers defaults to 1 (today's world).  Setting num_chargers=2 is a
    data-only change that immediately allows two simultaneous charges at that
    node — no engine code changes (docs/07-testing/02-edge-cases.md).
    """
    node: str
    num_chargers: int = 1   # ≥1, validated by loader


# ---------------------------------------------------------------------------
# Bus (a single vehicle in the scenario)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Bus:
    """
    A single bus operating in the scenario.

    Fields are deliberately generous: range_km allows heterogeneous fleets,
    priority is a latent field for future priority-bus rules, both addressable
    as data-only changes (docs/03-data-model/01-data-model-design.md).
    """
    id: str              # e.g. "bus-BK-01"
    operator: str        # e.g. "kpn" — set derived from buses, never hardcoded
    origin: str          # departure node
    destination: str     # arrival node
    departure_min: int   # minutes from midnight (19:00 = 1140)

    # Optional overrides (loader fills in defaults if absent in JSON)
    range_km: float = 240.0   # per-bus range override; defaults to world.battery_range_km
    priority: int = 0         # higher = higher scheduling priority; default 0


# ---------------------------------------------------------------------------
# Weights (soft-objective multipliers — always data, never hardcoded)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Weights:
    """
    Soft-objective weight container.  An open dict so new objectives need only a
    new key in the JSON — no class changes.

    R23: weights live in ONE obvious place (the scenario file + sidebar UI).
    Engine code never contains a weight literal; it always calls
    ctx.weights.get(key, DEFAULT_WEIGHT).
    """
    individual: float = 1.0   # weight for S1 — individual wait penalty
    operator: float = 1.0     # weight for S2 — operator fairness penalty
    overall: float = 1.0      # weight for S3 — overall makespan penalty

    # Extra future objectives arrive here (e.g. "electricity_cost")
    extra: Dict[str, float] = field(default_factory=dict)

    def get(self, key: str, default: float = 1.0) -> float:
        """Look up a weight by key; returns default if unknown (R23)."""
        known = {"individual": self.individual, "operator": self.operator,
                 "overall": self.overall}
        return known.get(key, self.extra.get(key, default))


# ---------------------------------------------------------------------------
# Scenario (the complete world description — the "database")
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    """
    A fully-hydrated, validated scenario ready for the engine to consume.

    A Scenario *is* the data structure (R26).  Every field that would need to
    change for a new problem variant is here; the engine never looks elsewhere.
    """
    name: str
    world: World
    route: Route
    stations: Dict[str, Station]   # node → Station; only intermediate nodes
    weights: Weights
    buses: tuple[Bus, ...]

    @property
    def operators(self) -> set[str]:
        """Set of operator names, derived from buses — never hardcoded."""
        return {b.operator for b in self.buses}

    @property
    def intermediate_nodes(self) -> list[str]:
        """Route nodes eligible for charging (excludes endpoints)."""
        return list(self.route.nodes[1:-1])


# ---------------------------------------------------------------------------
# Output objects (produced by the engine, consumed by adapters / UI / tests)
# ---------------------------------------------------------------------------

@dataclass
class ChargeEvent:
    """
    One charge session for a bus at one station.

    Invariants (validated by validate.py):
      • end_min - start_min == world.charge_minutes  (hard rule H4)
      • wait_min == start_min - arrive_min           (definition)
      • Leg from previous event (or origin) ≤ range  (hard rule H1)

    Ref: docs/03-data-model/03-output-schema.md
    """
    station: str           # charging node
    arrive_min: int        # wall-clock minute the bus reaches this station
    start_min: int         # minute charging begins (≥ arrive_min)
    wait_min: int          # start_min − arrive_min (≥ 0)
    end_min: int           # start_min + charge_minutes
    charger_index: int     # which charger slot (0-based); 0 for single-charger stations


@dataclass
class BusPlan:
    """
    Complete timeline for a single bus in the scheduled scenario.

    Invariants:
      • len(charge_events) ≥ 2  for any through-bus (R15)
      • Legs between consecutive events respect range (H1)
      • total_wait == sum(e.wait_min for e in charge_events)

    Ref: docs/03-data-model/03-output-schema.md
    """
    bus_id: str
    operator: str
    direction: str                      # "BK" (Bengaluru→Kochi) or "KB"
    charge_events: List[ChargeEvent]    # in route order
    arrival_min: int                    # final arrival at destination
    total_wait: int                     # Σ wait_min across all charge events


@dataclass
class StationSlot:
    """
    One row in the per-station ordering view.

    Ref: docs/03-data-model/03-output-schema.md (station_order)
    """
    bus_id: str
    operator: str
    charger_index: int
    start_min: int
    wait_min: int
    end_min: int


@dataclass
class ScheduleResult:
    """
    The complete output of one call to engine.schedule(scenario).

    Fields:
      • bus_plans         — one BusPlan per bus, in commit order
      • station_order     — per-node sorted list of StationSlot (by start_min)
      • objective_breakdown — {rule_name: penalty} for transparency / testing
      • total_objective   — sum of all penalty terms

    Serialisable to dict/JSON for debugging, golden-file tests, and a future
    REST response body with no reshaping.

    Ref: docs/03-data-model/03-output-schema.md
    """
    bus_plans: List[BusPlan]
    station_order: Dict[str, List[StationSlot]]   # node → sorted slots
    objective_breakdown: Dict[str, float]
    total_objective: float
