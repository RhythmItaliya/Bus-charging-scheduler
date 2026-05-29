# Design Decisions (ADR-style)

Each decision records context, the decision, and consequences, so they can be defended.

## ADR-1 — Event-driven greedy + pluggable weighted rule registry
**Context.** Small instance, need easy rule addition and weight tuning, must be explainable.
**Decision.** Process buses in deterministic order; for each, pick the feasible plan +
charger reservation that minimises the weighted objective given prior commitments. Rules are
auto-discovered units; the engine never names them. **Consequences.** Trivial to add rules,
trivial to tune weights, fully explainable per-term breakdown; not globally optimal, but
acceptable and defensible. Mitigation: `Strategy` interface allows a CP-SAT replacement.

## ADR-2 — Scenario file as the single world description
**Context.** "A scenario is your data structure"; many announced curveballs are world changes.
**Decision.** One JSON file fully describes a world (world constants, route, stations,
weights, buses). **Consequences.** Add station / change distance / double chargers / swap
operator / new scenario are all data edits. No engine code path branches on specific values.

## ADR-3 — Engine has zero Streamlit dependency
**Context.** Reusability and testability; possible future service extraction.
**Decision.** `scheduler` package imports no UI library. **Consequences.** Engine runs
headless (`python -m scheduler.engine file.json`), is unit-testable, and can be wrapped in a
REST handler later with no change.

## ADR-4 — Charger pool keyed by physical node
**Context.** Bidirectional buses share chargers; future multiple routes share stations.
**Decision.** Resource pools are keyed by station node, not by route or direction.
**Consequences.** Cross-direction and cross-route contention resolve automatically.

## ADR-5 — Weights are data, looked up by key
**Context.** Tunability is explicitly graded; new objectives anticipated.
**Decision.** `weights` is an open dict in the scenario; the objective reads
`weights[rule.weight_key]` with default 1.0. **Consequences.** New weighted term = new key +
new rule; weight change = one value.

## ADR-6 — Deterministic tie-breaking
**Context.** Reproducible demos and stable tests.
**Decision.** Order by priority desc → departure asc → id asc. **Consequences.** Identical
inputs always yield identical schedules.
