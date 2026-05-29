# Validation Rules

**Purpose.** Centralise every validation so inputs fail fast and outputs are provably correct.

## Input validation (loader, before scheduling)
Reject and explain when: any segment distance ≤ 0; route nodes are not contiguous via
segments; a station node is an endpoint or absent from the route; an operator string is empty;
`departure_min` < 0; `num_chargers` < 1; `range_km` ≤ 0; or a required bus field is missing.
Each failure raises `ValueError` naming the offending entity (e.g. `"bus-BK-07: departure_min
must be >= 0"`). Input validation prevents the engine from ever seeing impossible worlds.

## Feasibility validation (plan generation)
`candidate_plans` returns only plans where every leg ≤ range and stations are in route order.
If a bus yields **zero** plans, that is surfaced as an infeasibility error (the data is
over-constrained); the engine must not emit a partial or invalid schedule.

## Output validation (post-schedule, defensive)
`validate(result, scenario)` re-runs **all** registered hard rules over the final committed
schedule and returns a list of `Violation(rule, subject, detail)`. The app calls this at
startup and shows a red banner if non-empty. Tests assert `validate(...) == []` for all five
scenarios. This guarantees the 240 km rule, charger exclusivity, 25-min duration, and route
order can never be silently broken.

## Why three validation stages
Input validation protects against bad data; feasibility validation protects against impossible
requests; output validation protects against engine bugs. Defence in depth means a regression
in the engine is caught immediately rather than shipping a plausible-looking wrong schedule.
