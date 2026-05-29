# Constraints & Rules — Formal Specification

**Purpose.** Give the engine implementer a mathematically precise statement of every hard
and soft rule, expressed so it can be coded and unit-tested directly. Notation: a bus `b`
has origin `o(b)`, destination `d(b)`, departure minute `t0(b)`, and range `R(b)` (default
240). The route defines node positions `pos(n)` as cumulative distance from the bus's origin.
A **plan** `P(b)` is an ordered list of station nodes where `b` charges.

## Hard constraints (feasibility — violation ⇒ reject)

### H1 — Range constraint (R14, R18)
For the sequence `[o(b), P(b)..., d(b)]` with positions `x0 < x1 < ... < xk`, every leg
must satisfy `x_{i+1} − x_i ≤ R(b)`. Implementation: `RangeRule.evaluate` returns `inf` if
any leg exceeds range, else `0`. Test with the verified feasibility sets in
`01-requirements-analysis.md §4`.

### H2 — Route order, no backtracking (R19)
`P(b)` must be a strictly increasing subsequence of the bus's downstream station nodes (in
the bus's travel direction). No node repeats. Implementation: `RouteOrderRule`.

### H3 — Charger exclusivity (R16)
At any station node `n` with `c(n)` chargers, the number of buses whose charge intervals
`[start, start+25)` overlap at `n` must never exceed `c(n)`. Today `c(n)=1`, so charges at a
station strictly serialise. Implementation: `ChargerExclusivityRule` + the `ChargerPool`
resource allocator (see `02-scheduler-engine/02-charging-allocation-strategy.md`).

### H4 — Fixed charge duration (R17)
Every charge interval has length exactly `world.charge_minutes` (25). No partial charging.
Implementation: `ChargeDurationRule`.

## Soft objectives (cost — lower is better, weighted)

Each soft rule returns a non-negative penalty already multiplied by its weight, read by key
from `scenario.weights`. The total objective is the sum.

### S1 — Individual wait (R20), weight key `individual`
`penalty_individual = w_ind · Σ_b wait(b)` where `wait(b)` is the total minutes `b` spends
queuing for chargers (sum over its charge stops of `actual_start − arrival`). A `max`
variant (penalise the worst-waiting bus) is documented as an alternative; default is `Σ`.

### S2 — Operator fairness (R21), weight key `operator`
`penalty_operator = w_op · Σ_g f(g)` over operators `g`, where `f(g)` measures within-fleet
roughness. Default metric: total fleet wait `Σ_{b∈g} wait(b)`; alternative: variance of
per-bus wait inside the fleet (penalises uneven treatment within an operator). The variance
form is what makes raising the operator weight visibly reshuffle Scenario 4.

### S3 — Overall network time (R22), weight key `overall`
`penalty_overall = w_all · makespan`, where `makespan = max_b arrival(b) − min_b t0(b)`.
Alternative: `Σ_b (arrival(b) − t0(b))` (total person-time). Default: makespan.

> **All three metrics are documented in `02-scheduler-engine/03-optimization-rules.md` with
> exact formulas and must be implemented as separate, individually testable `Rule` subclasses.**

## Tunability requirement (R23)
Weights live **only** in the scenario file (`weights` object) and a UI sidebar that defaults
to those values. No weight literal appears in engine code. The objective function looks up
`ctx.weights[rule.weight_key]`, defaulting missing keys to `1.0`. Adding a new weighted term
is: (a) add a key to the scenario `weights`, (b) drop in a `Rule` that reads that key.

## Determinism requirement
Given identical scenario + weights, the engine must produce an identical schedule. Tie-breaks
are ordered: **priority desc → departure asc → bus id asc**. This guarantees reproducible
demos and stable tests.
