# Requirements Traceability Matrix

**Purpose.** Prove every requirement maps to a design artefact and code module, so an AI
agent can confirm nothing is dropped. Columns: requirement → doc that specifies it → code
module that implements it → test that verifies it.

| Req | Specified in | Implemented in | Verified by |
|---|---|---|---|
| R1 one process | 00/01 §1 | `app.py`, `scheduler/` | manual run |
| R2 hosted | 08/01 | Streamlit Cloud | hosted smoke test |
| R3 requirements.txt | 08/01 | `requirements.txt` | clean venv install |
| R4 route/segments | 03/02 | `model.Route` | `test_physics` |
| R5 bidirectional share | 02/02 | `ChargerPool` per node | `test_charger` |
| R6 full start / 240 | 03/02 | `Bus.range_km` | `test_plans` |
| R7 endpoints not scheduled | 02/01 | plan generator | `test_plans` |
| R8 1 charger | 03/02 | `Station.num_chargers` | `test_charger` |
| R10 travel time | 02/01 | `physics.travel_minutes` | `test_physics` |
| R11 20 buses | 03/02 | scenario files | `test_e2e` |
| R12 departure | 03/02 | `Bus.departure_min` | `test_e2e` |
| R13 operators data-driven | 03/01 | derived set | `test_e2e` |
| R14 range per leg | 00/02 H1 | `RangeRule` | `test_plans`, `test_rules` (H1 violating+satisfying) |
| R15 ≥2 charges | 00/01 §4 | plan generator | `test_plans`, `test_e2e` |
| R16 charger exclusivity | 00/02 H3 | `ChargerPool` + validator | `test_charger` |
| R17 25-min charge | 00/02 H4 | `ChargeDurationRule` | `test_rules` (H4 violating+satisfying) |
| R18 never run out | 00/02 H1 | `RangeRule` + validator | `test_e2e`, `test_rules` |
| R19 route order | 00/02 H2 | `RouteOrderRule` | `test_plans`, `test_rules` (H2 in/out of order) |
| R20 individual wait | 00/02 S1 | `IndividualWaitRule` | `test_rules` (S1 zero/nonzero, weight scaling) |
| R21 operator fairness | 00/02 S2 | `OperatorRule` | `test_rules` (S2 variance), `test_weights` |
| R22 overall time | 00/02 S3 | `OverallRule` | `test_rules` (S3 makespan, weight×2) |
| R23 weight tunability | 02/03 | `weights` + objective | `test_weights` |
| R24 add rule no rewrite | 02/05 | rule autodiscovery | code review (live) |
| R25 grow world | 03/01, 00/03 | data-driven model | live curveballs |
| R26 data structure first | 03/01 | scenario schema | review |
| R28 S4 operator=2.0 | 03/02 | `scenario_4.json` | `test_weights` |
| R29 read scenario | 06/01 | `loader.load_scenario` | `test_e2e` |
| R30 plan + order | 02/01 | `engine.schedule` | `test_e2e` |
| R31 per-bus timeline | 02/01 | `BusPlan` | `test_e2e` |
| R32 dropdown first | 05/01 | `app.py` selectbox | hosted smoke |
| R33 input view | 05/02 | `to_input_table` | hosted smoke |
| R34 per-bus timetable | 05/02 | `to_bus_table` | hosted smoke |
| R35 per-station view | 05/02 | `to_station_table` | hosted smoke |
| R36 minimal UI | 05/01 | `app.py` | review |
| R37 land on dropdown | 05/01 | `app.py` | hosted smoke |
| R38 hosted link | 11/01 | deploy | submission |
| R39 public repo | 11/01 | GitHub | submission |
| R40 README | 11/01 | `README.md` | review |
| R41 ARCHITECTURE | 01/* | `ARCHITECTURE.md` | review |
| R42 assumptions | 00/01, 07/02 | `ARCHITECTURE.md §6` | review |
| R44 correctness | 07/01 | validator + test suite | `test_e2e`, `test_weights`, `test_rules` |

## Test file summary

| Test file | Tests | What it covers |
|-----------|-------|----------------|
| `test_physics.py` | 18 | Travel time, arrival, HH:MM formatting |
| `test_plans.py` | 9 | Feasibility sets, route order, KB mirror |
| `test_charger.py` | 11 | Pool unit, H3 invariant all 5 scenarios |
| `test_e2e.py` | 33 | All 5 scenarios: validate==[], ≥2 charges, determinism |
| `test_rules.py` | 23 | H1/H2/H4 violating+satisfying; S1/S2/S3 penalty+weight scaling |
| `test_weights.py` | 4 | R28/R44: operator weight changes breakdown + score |
| **Total** | **103** | **All requirements R1–R44 covered** |
