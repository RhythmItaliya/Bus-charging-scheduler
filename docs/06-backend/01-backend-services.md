# Backend Services

**Purpose.** Describe the "backend" — the in-process services that do the real work — and
their operational contracts. These are logical services inside one process, not network daemons.

## Loader service
Owns scenario discovery and hydration. Reads `data/scenarios/`, parses and validates JSON,
returns immutable `Scenario` objects. It is the trust boundary: after the loader, all data is
guaranteed structurally valid. It is pure and side-effect-free aside from reading files.

## Scheduling service (engine)
The core compute service. Given a `Scenario`, it deterministically produces a `ScheduleResult`.
It is stateless between calls, holds no global mutable state, imports no UI, and is runnable
headless via `python -m scheduler.engine <path>`. Its determinism and purity make it safe to
cache and to lift into a future REST worker unchanged.

## Validation service
Re-checks invariants on engine output. Runs at app startup and in tests. Treated as a separate
service so that engine logic and verification logic cannot accidentally share a bug.

## Adapter service
Transforms engine output into presentation-ready DataFrames. It is the only place that knows
about HH:MM formatting and column naming, keeping the engine format-agnostic (minutes only).

## Operational properties
All services are synchronous, in-memory, and idempotent. There is no shared database, no
background worker, and no inter-service network. Scaling is achieved by the engine's linear
behaviour and by caching; horizontal scaling (if ever needed) is achieved by replicating the
stateless engine behind a load balancer once extracted — no code change to the engine itself.
