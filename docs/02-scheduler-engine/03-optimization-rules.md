# Optimization Rules — Exact Metric Definitions

**Purpose.** Pin down the soft objective metrics so they are implemented identically by any
agent and so weight tuning behaves predictably.

## Common context
For each bus `b`, the schedule yields `wait(b)` (total charger queue minutes), `arrival(b)`
(final arrival minute), and `t0(b)` (departure minute). Operators partition buses into fleets
`g`. Weights `w_ind, w_op, w_all` come from `scenario.weights` (defaults 1.0).

## Individual wait — `IndividualWaitRule` (key `individual`)
`penalty = w_ind · Σ_b wait(b)`. Rationale: directly penalises queueing so no single bus is
parked at a charger for long. Documented alternative (toggle in code, not default):
`w_ind · max_b wait(b)` to target the worst case specifically.

## Operator fairness — `OperatorRule` (key `operator`)
Default: `penalty = w_op · Σ_g Var_{b∈g}(wait(b))`, the sum across operators of the variance
of per-bus wait inside each fleet. Variance is chosen because it penalises *uneven* treatment
within an operator — exactly what "each operator's fleet runs smoothly as a group" means — and
because it is what makes Scenario 4 (operator-heavy KPN, `operator = 2.0`) reshuffle visibly
when the weight changes. Documented alternative: `Σ_g Σ_{b∈g} wait(b)` (total fleet wait).

## Overall network time — `OverallRule` (key `overall`)
Default: `penalty = w_all · makespan`, where `makespan = max_b arrival(b) − min_b t0(b)`.
Rationale: compresses the whole operation. Documented alternative: total person-time
`Σ_b (arrival(b) − t0(b))`.

## Aggregation
`objective.score` returns `(feasible, total, breakdown)` where `total = penalty_individual +
penalty_operator + penalty_overall` and `breakdown` is `{rule_name: contribution}`. Hard rule
failure sets `feasible = False` and `total = inf`. The breakdown is surfaced for explainability
and is the evidence used to defend "different weights → different schedules".

## Weight-sensitivity guarantee
Because each penalty is multiplied by its weight before summation, raising one weight strictly
increases that term's influence on `argmin` plan selection. The test `test_weights` asserts
Scenario 4's `station_order` and `breakdown` differ between `operator = 1.0` and `operator =
2.0`, satisfying R28/R44.
