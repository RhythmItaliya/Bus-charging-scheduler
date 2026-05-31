# Testing Plan

**Purpose.** Define the test suite that guarantees correctness, scalability claims, and weight
sensitivity. Use pytest. The suite uses only the public loader/engine/validate/adapters API.

## Test pyramid

A broad base of **unit tests** (physics, plan feasibility, each rule, charger pool, loader
validation), a middle of **invariant tests** (charger exclusivity, post-schedule validator,
adapter output), and a thin top of **end-to-end tests** (each scenario schedules cleanly) plus
**behavioural tests** (weights change the schedule). Keep unit tests fast and pure so the suite
runs in seconds.

## Shared fixtures: `conftest.py`

Provides `build_scenario(weights, battery_range_km, include_kb, num_chargers)` and
`make_event(station, arrive, wait)` helpers plus `canonical_scenario` and
`canonical_scenario_with_kb` pytest fixtures. These are available to all test files through
pytest's automatic conftest discovery.

## Required test modules

### `test_physics.py` — 18 tests
Verifies travel time arithmetic (60 km/h over 100 km = 100 min, 120 km = 120 min), arrival
times in both BK and KB directions, a non-default speed (80 km/h), and `minutes_to_hhmm`
edge cases (midnight, 19:00, 21:15, wrap at 1440).

### `test_plans.py` — 9 tests
Verifies no candidate plan has a leg > 240 km; through-buses require ≥ 2 charges; the
**only** valid 2-charge BK plans are `{A,C}`, `{B,C}`, `{B,D}` (spec-verified — `{A,D}` is
infeasible at 340 km); route order is monotonically increasing in BK and decreasing in KB;
an impossible range (90 km) yields an empty plan list.

### `test_loader.py` — 50 tests  ← trust boundary validation
Verifies every branch of the 3-stage input validation in `loader.load_scenario()`.
This is the most critical test file because the loader is the only trust boundary.

**Stage 1 — World:** speed/charge/range must be > 0; missing `world` block uses `DEFAULTS`.

**Stage 2 — Route:** ≥ 2 nodes; segment count == `len(nodes) - 1`; `from`/`to` fields match
declared node order; `distance_km > 0`; positions are computed correctly.

**Stage 3 — Stations:** station nodes must be intermediate (not endpoints); `num_chargers ≥ 1`;
missing station entries default to 1 charger.

**Weights:** all keys optional (defaults=1.0); `extra` dict accepts forward-compatible keys.

**Buses:** `id` required and non-empty; `operator` required; `origin`/`destination` in route;
`departure_min ≥ 0`; `range_km > 0`; at least one bus required.

Also tests `list_scenarios()`: sorted filenames, invalid JSON skipped gracefully,
missing directory raises `FileNotFoundError`, missing `name` key falls back to stem.

### `test_rules.py` — 23 tests  ← full per-rule coverage
Each hard rule gets a **violating case** (returns `math.inf`) and a **satisfying case`**
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

**Implementation note:** Every rule test builds its `ScheduleContext` with a `bus_id` that
matches a bus actually present in `ctx.scenario.buses`. A mismatch causes `StopIteration`
from the id lookup in `RangeRule.evaluate`.

### `test_charger.py` — 11 tests
Asserts no station ever has more concurrent charges than `num_chargers`, that `num_chargers=2`
permits two buses to overlap without wait, that snapshot/restore leaves pool state clean, and
that the H3 invariant holds across all five scenarios via `validate()`.

### `test_validate.py` — 22 tests  ← post-schedule validator
Tests the `validate(result, scenario)` function **independently of the engine** using
crafted `ScheduleResult` and `BusPlan` objects:

- **H1 range:** reduce `battery_range_km` so A→C (220 km) exceeds limit → violation detected.
- **H2 route order:** BK bus charging C then A (backwards) → violation detected.
- **H3 charger exclusivity:** two buses overlapping at station A with 1 charger → violation.
  Two buses with 2-charger station → no violation.
- **H4 charge duration:** 20-min charge instead of 25 → violation detected.
- **wait_min consistency:** `wait_min=99` but `start-arrive=0` → inconsistency detected.
- **R15 through-bus:** BK bus with 0 charge events but 540 km trip → violation.
- All 5 real scenarios produce zero violations when scheduled by the engine.

### `test_adapters.py` — 31 tests
Verifies all three adapter functions against a real `ScheduleResult` from Scenario 1:

- **`to_input_table`:** one row per bus; required columns; HH:MM departure format; direction
  values `"BK (→ Kochi)"` / `"KB (→ Bengaluru)"`; operator uppercase; sorted by departure.
- **`to_bus_table`:** ≥ 1 row per bus; wait ≥ 0; `Charge Start`/`End` in HH:MM; `Final Arrival`
  and `Total Wait` appear exactly once per bus (on the last row); `Total Wait` matches plan.
- **`to_station_table`:** empty node returns empty DataFrame with correct columns; `Order` is
  sequential from 1; `Charger #` ≥ 1 (1-indexed); all 4 stations have rows in Scenario 1.

### `test_e2e.py` — 38 tests
Loads and schedules all five scenarios (5 parametrized × 6 assertion methods = 30 tests);
asserts `validate()==[]`, every through-bus has ≥ 2 charges, every bus has a positive
`arrival_min`, bus count matches scenario, `station_order` keys are valid intermediate nodes,
objective breakdown contains all three terms, and scheduling twice produces identical results
(5 determinism tests). Also smoke-tests the adapter layer (3 tests).

### `test_weights.py` — 4 tests
Runs Scenario 4 with `operator=1.0` vs `operator=2.0`; asserts the `OperatorRule` breakdown
term differs (and is exactly double at w=2), total objective differs, and `var@w=2 ≤ var@w=1`
(higher weight → scheduler steers toward lower variance). Also checks `individual` weight change
affects the `IndividualWaitRule` term.

## Determinism tests
Schedule the same scenario twice and assert byte-identical plan output (bus_id, arrival_min,
total_wait, stations). Covered in `test_e2e.py::TestDeterminism`.

## Coverage intent
Every hard rule: positive + negative case (rules + validate). Every soft rule: monotonicity +
weight scaling. Loader: every `ValueError` branch. Charger allocator: 1 and N chargers.
Adapters: every column, every format, every edge (empty station, no-charge row).
Every scenario end-to-end. Orchestration loop covered for free via e2e tests.

## Running the suite

```bash
pytest                           # all 206 tests, ~1.2 s
pytest tests/test_rules.py       # rules only (23 tests)
pytest tests/test_loader.py      # loader validation (50 tests)
pytest tests/test_validate.py    # validator (22 tests)
pytest tests/test_e2e.py         # e2e across all 5 scenarios (38 tests)
pytest tests/test_adapters.py    # adapter output (31 tests)
pytest -v --tb=short             # verbose with short tracebacks
BCS_LOG_LEVEL=ERROR pytest -q    # suppress rich scheduler output for clean CI
```

## Current test count (as of last run)

| Module | Tests | Layer |
|--------|-------|-------|
| `test_physics.py` | 18 | Unit |
| `test_plans.py` | 9 | Unit |
| `test_rules.py` | 23 | Unit |
| `test_charger.py` | 11 | Unit |
| `test_loader.py` | 50 | Unit (trust boundary) |
| `test_validate.py` | 22 | Invariant |
| `test_adapters.py` | 31 | Invariant |
| `test_e2e.py` | 38 | End-to-end |
| `test_weights.py` | 4 | Behavioural |
| `conftest.py` | — | Shared fixtures |
| **Total** | **206** | |
