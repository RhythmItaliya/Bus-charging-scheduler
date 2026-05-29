# Interview Preparation

**Purpose.** Be ready to defend every decision and execute the announced live tasks instantly.

## Be ready to demo
Walk through two scenarios live, explaining the data structure and the framework choice. Show
the objective breakdown to explain *why* the scheduler chose a given plan. Show that dragging
the operator weight reshapes Scenario 4's objective score (OperatorRule term doubles when
weight goes 1.0→2.0). Have the app open at Scenario 5 to show maximum contention at B and C.

## Be ready to encode a fresh scenario
The interviewer will hand you a new departure schedule. Encoding means authoring one JSON file
in `data/scenarios/` per the schema in `docs/03-data-model/02-scenario-schema.md`.

**Key gotcha to avoid:** KB buses use a *different* operator rotation from BK buses
(freshbus/flixbus/kpn, not kpn/freshbus/flixbus). The schema doc has the full table — glance
at it before encoding. After writing the file, run `pytest tests/test_e2e.py` to confirm it
schedules cleanly. Practice this until it takes under 3 minutes.

## Be ready to extend data without code
Rehearse each announced curveball as a **data-only** edit:
- **Add station E** between D and Kochi: add to `route.nodes`, add segment `D→E` and `E→Kochi`,
  add `"E": { "num_chargers": 1 }` to `stations`. Zero code changes.
- **Double chargers at B**: set `"B": { "num_chargers": 2 }`. Zero code changes.
- **Change segment distance**: edit the number in `route.segments`. Zero code changes.
- **Swap operator**: edit `operator` field on the affected bus rows. Zero code changes.
- **Add new buses**: append to the `buses` list. Zero code changes.

Confirm beforehand with `pytest tests/test_e2e.py` that the modified scenario still validates.

## Be ready to add a rule live
Drop a new `Rule` subclass into `scheduler/rules/` (e.g. `electricity.py`), decorate with
`@register`, add its `weight_key` to the scenario's `weights` dict. The autodiscovery +
registry design makes this a 2-minute task. No orchestration or engine change.

Template:
```python
from scheduler.rules.registry import Rule, ScheduleContext, register

@register
class ElectricityCostRule(Rule):
    name = "ElectricityCostRule"
    kind = "soft"
    weight_key = "electricity_cost"
    PEAK_START = 1080  # 18:00
    PEAK_END   = 1320  # 22:00

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)
        return weight * sum(
            ctx.scenario.world.charge_minutes
            for e in ctx.charge_events
            if self.PEAK_START <= e["start_min"] < self.PEAK_END
        )
```

Then write a test in `test_rules.py` using the same pattern as the existing rule tests.

## Be ready to defend the architecture
Crisp answers for likely questions:

| Question | Answer |
|----------|--------|
| Why greedy over CP-SAT? | Explainability (every decision traceable to weights), extensibility (new rule = new file), stdlib only. CP-SAT seam documented via `Strategy` interface. |
| Why is the engine Streamlit-free? | Testability (103 tests run headless), reusability (CLI entry point), future REST lift-out. |
| Why are ChargerPools keyed by node? | Automatic cross-direction and multi-route sharing — BK and KB buses contend on the same physical charger. |
| Why are weights data, not code? | Tunability mandate (one obvious place). Field team changes weights via JSON edit or slider, never a deploy. |
| Why deterministic tie-break? | Reproducibility for demos, testing, and customer support. |
| How does adding station E work? | Data only — see "extend data" above. Plans module adapts because it reads `downstream_stations` from scenario.route at runtime. |

## Test suite as evidence
The 103-test suite is a live proof of correctness. Key tests to mention:
- `test_plans.py::test_valid_two_charge_bk_plans_are_exactly_abc_bc_bd` — proves the spec-
  verified feasibility set is correct.
- `test_rules.py::TestRangeRule::test_leg_exceeds_range_returns_inf` — proves H1 is enforced.
- `test_e2e.py::TestAllScenariosScheduleCleanly::test_no_validation_violations` — proves all
  five scenarios pass the post-schedule invariant checker.
- `test_weights.py::test_operator_weight_1_vs_2_produces_different_objective_score` — proves
  R28/R44: different weights → different defensible schedules.
