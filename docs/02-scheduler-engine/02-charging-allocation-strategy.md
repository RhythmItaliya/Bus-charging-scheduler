# Charging Allocation Strategy

**Purpose.** Define exactly how a bus is assigned a charger and how "who goes first, who
waits" is decided — the heart of the contention problem.

## The resource model
Each station node owns a `ChargerPool(num_chargers, charge_minutes)`. The pool tracks, per
charger, the list of committed busy intervals `[start, start+25)`. The operation
`reserve(requested_start) → (actual_start, charger_index, wait)` finds the charger that can
serve the bus **earliest at or after** its `requested_start` (its wait-free arrival at that
station, adjusted for any earlier charging delays accumulated upstream). If at least one
charger is free at `requested_start`, the bus charges immediately with zero wait. If all are
busy, the bus is queued behind the charger that frees up soonest, and `wait = actual_start −
requested_start`. Today `num_chargers = 1`, so charges at a station strictly serialise; with
`num_chargers = 2` two buses can charge concurrently — and **no engine code changes**, only
the data field.

## Ordering policy
Order at a charger emerges from the order in which buses are *committed* by the engine, which
is the deterministic global order (priority → departure → id) intersected with actual arrival
times. Because the engine commits buses in this order and reserves greedily, an earlier-
departing bus that arrives first generally charges first, while the weighted objective can
override this when, for example, letting a slightly later bus charge first markedly reduces a
high-weighted operator's total wait. The per-station view exposes the resulting order so a
reviewer can sanity-check it against the weights.

## Cross-direction and cross-route sharing
Pools are keyed by **physical node**, so a Bengaluru→Kochi bus and a Kochi→Bengaluru bus that
both want station `B` at overlapping times contend on the *same* pool. When multiple routes are
introduced later, any route passing through `B` joins the same pool automatically — the
sharing requirement (R5) and the future multi-route ask are satisfied by this single decision.

## Interaction with plan choice
Allocation and plan choice are coupled: a bus's plan determines *which* pools it touches, and
each pool's current load determines the wait that plan incurs. The engine therefore prices
each candidate plan by simulating its reservations before committing, so it can avoid a
congested station in favour of an alternative feasible plan (e.g. choosing `{B,D}` over `{B,C}`
if `C` is saturated). This is why the feasibility set having multiple options per bus matters.
