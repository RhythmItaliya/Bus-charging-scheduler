# Data Model Design ("Database")

**Purpose.** Define the domain model and persistence approach. There is no SQL database in
this project; persistence is **file-based** (scenario JSON) and runtime state is **in-memory**
typed objects. This document specifies both, plus the forward-looking schema were a real DB
ever introduced.

## Persistence approach and reasoning
The world is small, read-only at runtime, and version-controlled alongside code, so flat JSON
files in `data/scenarios/` are the correct "database": diffable, reviewable, trivially shipped,
and exactly matching the assignment's "a scenario is your data structure" framing. At runtime
the loader hydrates each file into immutable dataclasses; the engine never mutates input
state, only produces output objects. This immutability removes a whole class of bugs and makes
caching (`st.cache_data`) safe.

## Core entities and relationships
A `Scenario` aggregates one `World` (constants), one `Route` (ordered nodes + segments), a map
of `Station` (node → chargers), a `Weights` object, and a list of `Bus`. A `Bus` references an
operator (string, set derived from buses) and has origin/destination nodes that, against the
route, derive its direction and downstream stations. Output entities `ChargeEvent`, `BusPlan`,
and `ScheduleResult` are produced by the engine and consumed by the UI; they are not persisted.

## Field-level design choices for extensibility
Every plausibly-changing world parameter is a **field with a config default**, never a literal:
`World.speed_kmph/charge_minutes/battery_range_km`; `Station.num_chargers` (defaults 1, enables
"double the chargers"); `Bus.range_km` (per-bus override, enables heterogeneous fleets);
`Bus.priority` (defaults 0, latent for priority-bus rules); `Weights` as an **open dict**
(enables new objectives). The route is a list of nodes plus segment distances, so adding a
station or changing a distance is a data edit.

## Forward-looking relational schema (only if a DB is later needed)
Were this to scale to a service with a database, the natural schema is: `routes(id, name)`,
`segments(route_id, seq, from_node, to_node, distance_km)`, `stations(node, num_chargers)`,
`operators(id, name, attrs jsonb)`, `buses(id, scenario_id, operator_id, origin, destination,
departure_min, range_km, priority)`, `scenarios(id, name, route_id, weights jsonb)`, and
output tables `bus_plans` and `charge_events`. The JSON model maps 1:1 onto this, so migration
is mechanical. We deliberately do **not** build it now (YAGNI), but document it to show the
data model is DB-ready.

## Validation as part of the model
The loader validates structural invariants before the engine ever runs (see
`04-api-contracts/02-validation-rules.md`): positive distances, connected route, station nodes
are intermediate route nodes, non-empty operators, non-negative departures. Invalid data fails
fast with an actionable message rather than producing a subtly wrong schedule.
