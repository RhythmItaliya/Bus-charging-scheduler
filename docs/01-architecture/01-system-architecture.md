# System Architecture

**Purpose.** Define the macro structure of the system, the layers, and how a single
Streamlit process is internally partitioned so that the engine is reusable and the world is
data-driven.

## Architectural style
The system is a **layered, single-process application** with a strict dependency direction:
UI depends on adapters, adapters depend on the engine, the engine depends on the domain model
and the rule framework, and the loader bridges scenario files into the domain model. The
**`scheduler` package contains zero Streamlit imports** — this is the single most important
structural rule, because it keeps the engine headless (testable, scriptable, and liftable
into a future service) while the Streamlit `app.py` stays a thin presentation shell.

## Layers and responsibilities
The **data layer** is file-based: scenario JSON files in `data/scenarios/` are the persistent
description of each world, loaded into in-memory domain objects at runtime. The **domain
model layer** (`scheduler/model.py`) holds immutable dataclasses for route, station, bus,
weights, scenario, and the output objects. The **rule framework layer**
(`scheduler/rules/`) holds the pluggable hard and soft rules, auto-discovered by a registry.
The **engine layer** (`scheduler/engine.py`, `plans.py`, `resources.py`, `objective.py`)
computes schedules. The **adapter layer** (`scheduler/adapters.py`) converts results into
DataFrames with human formatting. The **presentation layer** (`app.py` + `frontend/`)
renders the dropdown and three views; `app.py` is a thin orchestrator (~100 lines),
and all rendering logic lives in the `frontend/` package (`icons.py`, `styles.py`,
`sidebar.py`, `tabs.py`). The **validation layer** (`scheduler/validate.py`) double-checks invariants.

## Dependency rule
Lower layers never import higher ones. The engine must never import Streamlit, pandas display
helpers, or the adapter layer. This inversion is what makes "extract the engine into a REST
service" a future no-op rather than a rewrite.

## Why one process is correct here
The problem is small and synchronous; a request ("schedule this scenario") completes in
milliseconds. Network boundaries would add latency, failure modes, and deployment complexity
for zero benefit. The architecture therefore keeps everything in-process but **draws the
seams** (loader → engine → adapter → UI) exactly where a future service boundary would go.

## Scalability considerations
Bigger fleets scale linearly in the greedy strategy (`O(buses · plans · stations)`); the
plan enumeration is exponential only in the number of stations a single bus can use, which is
tiny and range-pruned. If instance size grows beyond greedy's comfort, swap `GreedyStrategy`
for a `CpSatStrategy` behind the same interface — rules, data model, and UI are unchanged.

## Future extensibility
Multiple routes sharing stations is handled by keying the `ChargerPool` on the **physical
station node**, not the route, so two routes that both pass through `B` contend on the same
pool automatically. New objectives are new `Rule` files. New world parameters are new scenario
fields with config defaults.
