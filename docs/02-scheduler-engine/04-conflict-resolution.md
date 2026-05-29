# Conflict Resolution

**Purpose.** Specify how the engine resolves the central conflict: multiple buses wanting one
charger at overlapping times.

## Conflict definition
A conflict exists when two or more buses' desired charge intervals at the same station node
overlap and capacity (`num_chargers`) is insufficient to serve them simultaneously. With one
charger, any temporal overlap is a conflict.

## Resolution mechanism
Conflicts are resolved at **reservation time**, not after the fact. Because the engine commits
buses one at a time in deterministic order and each reservation records its busy interval, a
later bus that wants an occupied charger is automatically pushed to the earliest free slot,
accruing measured wait. There is never a state where two committed buses occupy one charger —
the `ChargerPool` makes that representationally impossible, and `ChargerExclusivityRule` plus
`validate` re-confirm it on the final schedule.

## Policy levers
The *order* in which conflicts resolve is governed by (a) the deterministic commit order and
(b) the weighted objective, which can make the engine prefer a plan that sidesteps a congested
station entirely. Thus conflict resolution is both **structural** (the pool enforces capacity)
and **economic** (the objective prices congestion so buses route around it when beneficial).

## Starvation and fairness
Because commit order respects departure time and the individual-wait penalty grows with queue
time, no bus is indefinitely deferred; deferring a bus raises the objective, discouraging it.
Raising the operator weight further protects fleets from internally lopsided waits. Priority
buses (field already present) can be added as a hard pre-emption or a strong soft term without
engine changes.

## Failure mode
If capacity and plan options cannot avoid a range violation for some bus (e.g. an
over-constrained custom scenario), the engine does not "resolve" by emitting an invalid
schedule; it raises a surfaced infeasibility error naming the bus, so the operator can adjust
data. Silent invalidity is prohibited by `validate`.
