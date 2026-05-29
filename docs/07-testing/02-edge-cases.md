# Edge Cases

**Purpose.** Catalogue edge cases an autonomous agent must handle so none is discovered late.

## Range and feasibility edges
A bus whose first reachable station forces a specific plan (BK cannot reach C unfuelled, so the
first charge is A or B). A custom scenario with an impossibly small range (e.g. 90 km) yields
**no** feasible plan — the engine must surface infeasibility, not crash or emit garbage. A
bus that could legally skip an optional charge: the engine may use more than the minimum charges
when it lowers cost, which is permitted by the spec.

**Valid 2-charge BK plans are exactly `{A,C}`, `{B,C}`, `{B,D}`.** The plan `{A,D}` is
infeasible because leg A→D = 340 km > 240 km range. `test_plans.py` asserts this set directly.

## Contention edges
All buses converging on the inner stations B and C (Scenario 5): the allocator must serialise
correctly and waits must accumulate without overlap. Simultaneous arrivals from opposite
directions at the same node: deterministic tie-break (priority DESC → departure ASC → id ASC)
decides order; both must be served, never double-booked. `test_charger.py` covers this.

## Data encoding edges

> ⚠ **Scenario operator encoding:** The BK fleet and KB fleet use **different** operator rotations.
> BK starts kpn/freshbus/flixbus; KB starts **freshbus/flixbus/kpn**.
> Copying BK operators onto KB rows is the most common mistake. Always verify against
> `docs/03-data-model/02-scenario-schema.md` which has the full tables.

Missing optional fields (`range_km`, `priority`, partial `world`): defaults fill in. Additional
unknown `weights` keys: accepted and ignored unless a rule consumes them. A station listed that
is an endpoint or not on the route: rejected by validation. Zero or negative distances: rejected.

## Rule test edges
Every rule unit test must use a `ScheduleContext` whose `bus_id` matches a bus id actually
present in `ctx.scenario.buses`. A mismatch causes a `StopIteration` in the engine's id lookup.
The fix is to create the `Bus` and the `Scenario` together with the same id string, then pass
`scenario` explicitly to `_make_ctx`. See `test_rules.py` for the canonical pattern.

## Scaling edges
Doubling chargers at one station (`num_chargers=2`): concurrency allowed, no code change. Adding
a station E or changing a segment distance: candidate-plan search adapts automatically. Adding
buses beyond 20: linear slowdown only; no structural limit.

## Time edges
Departures near midnight wrap: encode as minutes from midnight; if a future scenario crosses
midnight, allow `departure_min > 1440` rather than wrapping, and document it. Equal departure
times: tie-break by bus id (lexicographic ascending).

## UI edges
A scenario that produces a validation violation (should never happen with shipped data, but a
custom one might): the UI blocks the views and shows the violation rather than rendering a
misleading timetable. The validation banner appears above all tabs so it is never missed.
