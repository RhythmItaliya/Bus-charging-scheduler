"""
scheduler/model.py  —  All data classes (the "shapes" of data in this project).

WHAT THIS FILE DOES:
  This file defines the shape of every piece of data used in the scheduler.
  Think of it like a blueprint — before we write any algorithm, we decide
  exactly what fields each object carries.

WHY DATACLASSES?
  Python dataclasses are simple containers with named fields.
  They are immutable (frozen=True), meaning no code can accidentally change them.
  This makes st.cache_data safe and makes testing easy.

PDF reference: Page 5 — "Designing your data structure (important)"
  "A scenario IS your data structure."
  "You design the actual data structure your scheduler and UI use."
  This is one of the strongest signals to the evaluators about how well
  you understood the problem.

INTERVIEW TALKING POINT:
  "I designed the data model first, before writing any algorithm.
   Every field that could change in the future is a named field here —
   not a magic number buried in code. For example, if the battery range
   changes from 240 km to 300 km, I only edit the JSON file."

HOW DATA FLOWS:
  JSON file  →  loader.py  →  Scenario (this file)  →  engine.py  →  ScheduleResult (this file)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# WORLD CONSTANTS
# PDF reference: Page 2, "Physical constants"
#   - Battery range: 240 km on a full charge
#   - Charging: always to full, takes 25 minutes (fixed)
#   - All buses travel at the same speed (no traffic, no variation)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class World:
    """
    The physical rules of the simulation world.
    These are the same for every bus in every scenario.

    INTERVIEW TALKING POINT:
      "I put all physical constants in one place — the World class.
       If tomorrow the assignment changes charge time from 25 to 30 minutes,
       I only edit one JSON field: world.charge_minutes.
       No code needs to change."

    PDF reference: Page 2, "Physical constants"
      Battery range = 240 km  →  battery_range_km
      Charging time = 25 min  →  charge_minutes
      Same speed for all buses →  speed_kmph (I chose 60 km/h, see ARCHITECTURE.md)
    """

    # How fast all buses travel.
    # PDF page 2: "All buses travel at the same speed (no traffic, no variation)"
    # I chose 60 km/h because: 100 km / 60 km/h = 100 min (clean math).
    # This is overridable per scenario in the JSON file.
    speed_kmph: float = 60.0

    # How long each charge takes.
    # PDF page 2: "Charging: always to full, takes 25 minutes (fixed)"
    # Hard rule H4: every charge is exactly this many minutes — not more, not less.
    charge_minutes: int = 25

    # Maximum km a bus can travel between two charges.
    # PDF page 2: "Battery range: 240 km on a full charge"
    # Hard rule H1: any leg longer than this is INVALID.
    battery_range_km: float = 240.0


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE
# PDF reference: Page 2, "The route" table
#   Bengaluru → A (100km) → B (120km) → C (100km) → D (120km) → Kochi (100km)
#   Total = 540 km
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Segment:
    """
    One road segment between two adjacent stations.
    Example: Segment("A", "B", 120.0) means A → B is 120 km.

    PDF reference: Page 2, route table:
      Bengaluru→A = 100 km
      A→B         = 120 km
      B→C         = 100 km
      C→D         = 120 km
      D→Kochi     = 100 km
    """
    from_node: str      # where this segment starts (e.g. "A")
    to_node: str        # where this segment ends   (e.g. "B")
    distance_km: float  # length of this road segment in km


@dataclass(frozen=True)
class Route:
    """
    The complete route: a list of stop names and the distances between them.

    INTERVIEW TALKING POINT:
      "I store the route as a list of nodes plus a positions dictionary.
       The positions dict maps each node to its cumulative distance from the
       start — e.g., A=100, B=220, C=320, D=440, Kochi=540.
       This makes range-checking instant: abs(pos[B] - pos[A]) = 120 km."

    PDF reference: Page 2, "The route"
      nodes = ["Bengaluru", "A", "B", "C", "D", "Kochi"]
      endpoints (Bengaluru, Kochi) = starting points, NOT charging stations
      intermediate nodes (A, B, C, D) = charging stations

    The positions dict is computed once by the loader (not in the JSON):
      positions = {"Bengaluru": 0, "A": 100, "B": 220, "C": 320, "D": 440, "Kochi": 540}
    """
    nodes: tuple[str, ...]        # all stop names in order, e.g. ("Bengaluru","A","B","C","D","Kochi")
    segments: tuple[Segment, ...] # the road segments connecting those stops

    # Cumulative km from nodes[0] — computed by loader, stored here for fast lookup.
    # Example: {"Bengaluru": 0, "A": 100, "B": 220, "C": 320, "D": 440, "Kochi": 540}
    positions: Dict[str, float] = field(default_factory=dict)

    def distance_between(self, from_node: str, to_node: str) -> float:
        """Return the km distance between any two nodes on the route."""
        return abs(self.positions[to_node] - self.positions[from_node])


# ─────────────────────────────────────────────────────────────────────────────
# STATION
# PDF reference: Page 1, "Each station has 1 charger"
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Station:
    """
    A physical charging station at one stop on the route.

    PDF reference: Page 1 —
      "Each station has 1 charger, so when multiple buses want to charge
       at the same station around the same time, the scheduler has to decide
       who goes first and who waits."

    FUTURE CHANGE (data only, no code change needed):
      If the assignment says "station B now has 2 chargers", just change:
        stations["B"].num_chargers = 2
      The ChargerPool (resources.py) automatically handles multiple charger slots.
    """
    node: str           # which stop this station is at (e.g. "A", "B", "C", "D")
    num_chargers: int = 1  # how many buses can charge at the same time (default 1)


# ─────────────────────────────────────────────────────────────────────────────
# BUS
# PDF reference: Page 2, "Buses"
#   "20 buses total per scenario — 10 going Bengaluru→Kochi, 10 going Kochi→Bengaluru"
#   "Each bus belongs to one of 3 operators: KPN, Freshbus, Flixbus"
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Bus:
    """
    One bus in the scenario.

    INTERVIEW TALKING POINT:
      "I gave Bus two extra fields beyond what the assignment required:
       range_km for per-bus battery range (some buses might have different batteries),
       and priority for 'VIP buses that always charge first'.
       Both are in the data model now, so adding them later is a JSON-only change."

    PDF reference: Page 2, "Buses"
      - 20 buses total (10 BK + 10 KB)
      - Each bus has a departure time (departure_min in minutes from midnight)
      - Each bus belongs to KPN, Freshbus, or Flixbus
      - "Each bus starts its trip with a full charge"

    Clock encoding: we use minutes from midnight.
      19:00 = 19×60 = 1140 minutes
      19:15 = 1155 minutes
      Why? Avoids midnight-wrap bugs (1440 + 60 = 1500 = 01:00 next day, still works).
    """
    id: str             # unique name, e.g. "bus-BK-01" (BK = Bengaluru→Kochi)
    operator: str       # "kpn", "freshbus", or "flixbus"  (PDF page 2)
    origin: str         # departure city, e.g. "Bengaluru" or "Kochi"
    destination: str    # arrival city,   e.g. "Kochi" or "Bengaluru"
    departure_min: int  # when the bus leaves, in minutes from midnight (19:00 = 1140)

    # Extra fields — not in the basic scenario but supported for future changes:
    range_km: float = 240.0  # battery range (default = world.battery_range_km)
    priority: int = 0        # scheduling priority: higher = charges first (default 0 = equal)


# ─────────────────────────────────────────────────────────────────────────────
# WEIGHTS
# PDF reference: Page 4, "What to optimize for" and "Don't hardcode them."
#   S1 Individual bus   — no single bus should wait too long
#   S2 Operator         — each operator's fleet should run smoothly as a group
#   S3 Overall          — total time across the whole network should be low
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Weights:
    """
    The three soft-objective weights — tunable numbers that change what the
    scheduler optimises for.

    INTERVIEW TALKING POINT:
      "The PDF specifically says 'These weights should be tunable — engineers
       will change them as we learn what matters operationally. Don't hardcode them.'
       So I never write weight values in Python code. Every weight is read from
       the scenario JSON file, and engineers can change them there — or by dragging
       the sliders in the Streamlit UI."

    PDF reference: Page 4, "What to optimize for"
      individual = weight for S1 (individual bus wait penalty)
      operator   = weight for S2 (operator fairness penalty)
      overall    = weight for S3 (overall makespan penalty)

    The 'extra' dict allows new weights to be added in the future.
    Example: add "electricity_cost": 1.5 to a scenario JSON and it just works.
    """
    individual: float = 1.0  # S1: multiplier for individual wait penalty
    operator: float = 1.0    # S2: multiplier for operator fairness penalty
    overall: float = 1.0     # S3: multiplier for network makespan penalty

    # Future weights go here — no class change needed, just add to scenario JSON.
    extra: Dict[str, float] = field(default_factory=dict)

    def get(self, key: str, default: float = 1.0) -> float:
        """
        Look up a weight by name. Returns default if the weight is not set.

        Usage in rules:  weight = ctx.weights.get("individual")  # → 1.0
        """
        known = {"individual": self.individual, "operator": self.operator,
                 "overall": self.overall}
        return known.get(key, self.extra.get(key, default))


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO  —  the main input to the scheduler
# PDF reference: Page 5, "A scenario IS your data structure."
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Scenario:
    """
    Everything the scheduler needs to know about one run of the problem.

    INTERVIEW TALKING POINT:
      "The assignment says 'A scenario IS your data structure.'
       So I designed one Scenario object that holds everything:
       the physical world constants, the route, the stations, the weights,
       and the list of buses. The engine receives a Scenario and produces
       a ScheduleResult. It never needs to read a file or talk to a database."

    PDF reference: Page 5 —
      "You decide what the file actually looks like, what fields it carries,
       and how the rest of the world (route, stations, weights, etc.) is represented."

    Structure:
      Scenario
      ├── World         → speed, charge time, battery range
      ├── Route         → nodes, segments, positions dict
      ├── stations      → {node: Station(num_chargers)}
      ├── Weights       → individual, operator, overall (+ extra)
      └── buses         → list of Bus objects
    """
    name: str                        # display name, e.g. "Scenario 1 — Even Spacing"
    world: World                     # physical constants (speed, charge time, range)
    route: Route                     # the full route with distances
    stations: Dict[str, Station]     # which nodes have chargers, and how many
    weights: Weights                 # soft-objective multipliers
    buses: tuple[Bus, ...]           # all buses in this scenario

    @property
    def operators(self) -> set[str]:
        """
        The set of all operator names in this scenario (derived from bus list).
        Example: {"kpn", "freshbus", "flixbus"}

        WHY A PROPERTY? — We never hardcode operator names anywhere.
          If a new operator "bluebus" is added to the JSON, this property
          automatically includes it. No code change needed.
        """
        return {b.operator for b in self.buses}

    @property
    def intermediate_nodes(self) -> list[str]:
        """
        The charging stations — the nodes between origin and destination.
        Example: ["A", "B", "C", "D"]

        PDF reference: Page 1 —
          "Only A, B, C, and D are scheduling charging stations —
           the endpoints are not part of the scheduling problem."
        """
        return list(self.route.nodes[1:-1])


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT OBJECTS  —  what the engine produces
# PDF reference: Page 9, "The scheduler" section
#   "Decides each bus's charging plan and the ORDER in which buses use each station"
#   "Computes, for each bus, the timeline: when it charges, how long it waits, arrival"
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChargeEvent:
    """
    One charge stop for one bus at one station.

    INTERVIEW TALKING POINT:
      "Each ChargeEvent records exactly what happened at one charging stop:
       when the bus arrived, how long it waited in the queue, when it started
       charging, and when it finished. The wait_min field is what the S1 soft
       rule penalises — longer waits = higher cost."

    PDF reference: Page 9 —
      "for each bus, show its full timeline:
       charging stations used, time at each, wait (if any), final arrival"

    Example for bus-BK-01 at station A:
      station     = "A"
      arrive_min  = 1240  (20:40 — departed 19:00 + 100 min travel)
      start_min   = 1240  (20:40 — no queue, charged immediately)
      wait_min    = 0     (no wait)
      end_min     = 1265  (21:05 — 20:40 + 25 min charge)
      charger_index = 0   (first charger slot, 0-indexed)
    """
    station: str          # which charging stop, e.g. "A"
    arrive_min: int       # when the bus got to this station (minutes from midnight)
    start_min: int        # when charging actually began (≥ arrive_min)
    wait_min: int         # how long the bus waited in the queue (start - arrive)
    end_min: int          # when charging finished (start + world.charge_minutes)
    charger_index: int    # which charger slot (0-indexed; 0 for single-charger stations)


@dataclass
class BusPlan:
    """
    The complete charging schedule for one bus from origin to destination.

    INTERVIEW TALKING POINT:
      "For every bus, the engine produces a BusPlan that contains the list
       of all charge stops in order, the final arrival time, and the total
       waiting time. This is what the Per-Bus Timetable tab shows."

    PDF reference: Page 9 —
      "per-bus timetable — for each bus, show its full timeline:
       charging stations used, time at each, wait (if any), final arrival"

    Invariants (always true for a valid BusPlan):
      len(charge_events) >= 2  (a 540 km trip needs at least 2 charges with 240 km range)
      total_wait == sum(e.wait_min for e in charge_events)
    """
    bus_id: str                       # e.g. "bus-BK-01"
    operator: str                     # e.g. "kpn"
    direction: str                    # "BK" (Bengaluru→Kochi) or "KB" (Kochi→Bengaluru)
    charge_events: List[ChargeEvent]  # all charge stops, in travel order
    arrival_min: int                  # when the bus reaches its destination
    total_wait: int                   # total minutes spent waiting in queues


@dataclass
class StationSlot:
    """
    One row in the per-station charging order view.

    PDF reference: Page 9 —
      "per-station view — for each of A, B, C, D,
       show the order in which buses charged there"

    The station_order dict in ScheduleResult is sorted by start_min,
    so StationSlot #1 is the first bus to charge, #2 is next, etc.
    """
    bus_id: str          # which bus used this charger
    operator: str        # which company operates this bus
    charger_index: int   # which charger slot (0-indexed)
    start_min: int       # when this bus started charging
    wait_min: int        # how long this bus waited before charging started
    end_min: int         # when this bus finished charging


@dataclass
class ScheduleResult:
    """
    The complete output of one call to engine.schedule(scenario).

    INTERVIEW TALKING POINT:
      "The engine returns one ScheduleResult that contains everything:
       the plan for every bus, the charge order at every station,
       and the objective score breakdown showing which penalty rule
       contributed how much. This makes the schedule fully explainable —
       you can always see why a particular bus waited."

    PDF reference: Page 9, "What to build — The scheduler"
      bus_plans     → per-bus timetable (per-bus tab)
      station_order → per-station ordering (per-station tab)

    This object is serialisable to JSON for debugging:
      import json, dataclasses
      json.dumps(dataclasses.asdict(result), indent=2)
    """
    bus_plans: List[BusPlan]                    # one BusPlan per bus
    station_order: Dict[str, List[StationSlot]] # node → slots sorted by start_min
    objective_breakdown: Dict[str, float]       # {rule_name: penalty}
    total_objective: float                      # sum of all penalties (lower = better)
