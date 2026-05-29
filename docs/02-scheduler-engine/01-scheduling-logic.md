# Scheduling Logic

**Purpose.** Specify the end-to-end algorithm the engine runs, precisely enough to implement
without further questions.

## Inputs and outputs
Input: a validated `Scenario`. Output: a `ScheduleResult` containing one `BusPlan` per bus
(its full timeline) and a `station_order` mapping each station node to the ordered list of
buses that charged there, plus an `objective_breakdown` for transparency.

## Algorithm (deterministic event-driven greedy)
First, for each bus compute its **wait-free arrival** at every node it passes, using
`physics.base_arrival_minutes` (departure + cumulative travel time at constant speed). Second,
for each bus enumerate its **candidate plans** with `plans.candidate_plans` — every
range-feasible, route-ordered subset of its downstream stations (see the verified feasibility
sets in `00-requirements/01-requirements-analysis.md §4`). Third, sort buses by the
deterministic key **priority desc → departure asc → id asc**. Fourth, iterate buses in that
order and for each bus evaluate all its candidate plans: for a given plan, walk the bus along
its route, and at each chosen station call the station's `ChargerPool.reserve(arrival)` to get
the actual charge start, wait, and charger index; this yields a tentative timeline. Score the
**incremental** weighted objective contribution of committing this bus with this plan, given
all prior commitments, and **commit the lowest-cost feasible plan**, persisting its charger
reservations. Fifth, after all buses are committed, assemble `BusPlan` timelines and
`station_order`. Finally, run `validate` to assert no hard rule is violated.

## Why greedy with incremental scoring is correct enough
Because chargers serialise and buses arrive over time, an arrival-ordered greedy that commits
the locally cheapest feasible plan produces schedules that are sensible and explainable. The
weighted objective ensures weights actually steer choices (e.g. a high operator weight makes
the engine prefer plans that smooth a fleet's waits). Global optimality is not required; if it
becomes necessary, the `Strategy` seam allows a CP-SAT model that minimises the same objective.

## Edge handling
If a bus has **no** feasible plan (should not occur with given data, but possible if someone
sets an impossible range), the engine raises a clear, surfaced error rather than emitting an
invalid schedule. If two plans tie on cost, the tie-break prefers fewer charges, then
earlier-finishing, then lexicographic plan order — all deterministic.

## Extensibility
Adding a soft consideration (electricity cost, driver shifts) changes *only* the objective via
a new rule; the orchestration loop is unchanged because it already minimises "whatever the
registry scores". Adding chargers changes only the pool capacity. Adding a station changes only
the data and the candidate-plan search space.
