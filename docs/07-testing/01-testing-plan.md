# Testing Plan

**Purpose.** Define the test suite that guarantees correctness, scalability claims, and weight
sensitivity. Use pytest. The suite uses only the public loader/engine/validate API.

## Test pyramid
A broad base of **unit tests** (physics, plan feasibility, each rule, charger pool), a middle
of **invariant tests** (charger exclusivity across full schedules), and a thin top of
**end-to-end tests** (each scenario schedules cleanly) plus **behavioural tests** (weights
change the schedule). Keep unit tests fast and pure so the suite runs in seconds.

## Required test modules

### `test_physics.py`
Verifies travel time arithmetic (60 km/h over 100 km = 100 min, 120 km = 120 min), arrival
times in both BK and KB directions, a non-default speed (80 km/h), and `minutes_to_hhmm`
edge cases (midnight, 19:00, 21:15, wrap at 1440).

### `test_plans.py`
Verifies no candidate plan has a leg > 240 km; through-buses require ≥ 2 charges; the
**only** valid 2-charge BK plans are `{A,C}`, `{B,C}`, `{B,D}` (spec-verified — `{A,D}` is
infeasible at 340 km); route order is monotonically increasing in BK and decreasing in KB;
an impossible range (90 km) yields an empty plan list.

### `test_rules.py`  ← full per-rule coverage
Each hard rule gets a **violating case** (returns `math.inf`) and a **satisfying case**
(returns 0.0):
- `RangeRule` (H1): a leg of 440 km returns inf; a leg of exactly 240 km returns 0.
- `RouteOrderRule` (H2): visiting C before A (backtracking) returns inf; A then C returns 0.
- `ChargeDurationRule` (H4): 20-min or 30-min charge returns inf; 25-min charge returns 0.

Each soft rule gets a **worse-vs-better** penalty comparison and **weight multiplication** checks:
- `IndividualWaitRule` (S1): zero wait → 0.0; 20 min wait × weight=1 → 20; weight=3 → 60;
  weight=0 silences; weight×2 = penalty×2.
- `OperatorRule` (S2): equal fleet waits → variance=0 → 0.0; unequal waits → positive penalty;
  weight=0 silences.
- `OverallRule` (S3): later arrival → ≥ earlier arrival penalty; weight×2 doubles contribution;
  weight=0 silences.

**Important implementation note:** Every rule test builds its `ScheduleContext` with a bus id
(`bus_id`) that matches a bus actually present in `ctx.scenario.buses`. A mismatch causes
`StopIteration` from the id lookup in `RangeRule.evaluate`. Always create scenario + bus
together with consistent ids.

### `test_charger.py`
Asserts no station ever has more concurrent charges than `num_chargers`, that `num_chargers=2`
permits two buses to overlap without wait, that snapshot/restore leaves pool state clean, and
that the H3 invariant holds across all five scenarios via `validate()`.

### `test_e2e.py`
Loads and schedules all five scenarios; asserts `validate()==[]`, every through-bus has ≥ 2
charges, every bus has a positive `arrival_min`, bus count matches scenario, objective breakdown
contains all three terms, and scheduling twice produces identical results (determinism).
Also smoke-tests the adapter layer.

### `test_weights.py`
Runs Scenario 4 with `operator=1.0` vs `operator=2.0`; asserts the `OperatorRule` breakdown
term differs (and is exactly double at w=2), total objective differs, and `var@w=2 ≤ var@w=1`
(higher weight → scheduler steers toward lower variance). Also checks `individual` weight change
affects the `IndividualWaitRule` term.

## Determinism tests
Schedule the same scenario twice and assert byte-identical plan output (bus_id, arrival_min,
total_wait, stations), proving deterministic tie-breaking. Covered in `test_e2e.py`.

## Coverage intent
Every hard rule: positive + negative case. Every soft rule: monotonicity + weight scaling.
Charger allocator: 1 and N chargers. Every scenario end-to-end. Orchestration loop covered
for free via e2e tests.

## Running the suite
```bash
pytest                      # all 103 tests, ~0.7 s
pytest tests/test_rules.py  # rules only (23 tests)
pytest tests/test_e2e.py    # e2e across all 5 scenarios
pytest -v --tb=short        # verbose with short tracebacks
```

## Current test count (as of last run)
| Module | Tests |
|--------|-------|
| test_charger.py | 11 |
| test_e2e.py | 33 |
| test_physics.py | 18 |
| test_plans.py | 9 |
| test_rules.py | 23 |
| test_weights.py | 4 |
| **Total** | **103** |
