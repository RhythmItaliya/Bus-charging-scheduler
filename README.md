# Bus Charging Scheduler

A Python + Streamlit application that schedules electric bus charging stops along the Bengaluru–A–B–C–D–Kochi corridor.  Built as a take-home assignment; deadline **June 2**.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bus-charging-scheduler-gxy2aoipfkggccvrevanu6.streamlit.app)

**Live app:** [https://bus-charging-scheduler-gxy2aoipfkggccvrevanu6.streamlit.app](https://bus-charging-scheduler-gxy2aoipfkggccvrevanu6.streamlit.app)

**GitHub:** [https://github.com/RhythmItaliya/Bus-charging-scheduler](https://github.com/RhythmItaliya/Bus-charging-scheduler)

---

## Problem summary

- Route: Bengaluru → A → B → C → D → Kochi | segments 100/120/100/120/100 km (total 540 km).
- Every bus starts fully charged with **240 km range**; each charge always restores to full in **25 minutes**.
- 20 buses per scenario (10 each way), 4 charging stations (A, B, C, D), 1 charger per station.
- The scheduler decides **which stations each bus charges at** and **in what order** to minimise a weighted combination of individual wait, operator fairness, and network makespan.

---

## Run locally

```bash
# Clone and enter the repo
git clone https://github.com/RhythmItaliya/Bus-charging-scheduler.git
cd Bus-charging-scheduler

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## How to change a weight

### Via the UI (recommended for exploration)

Use the three sliders in the left sidebar.  Dragging **Operator Fairness** up in Scenario 4 will visibly reshuffle the per-station charge order.  The **Reset** button restores the scenario's file defaults.

### Via the scenario JSON (for permanent changes / new scenarios)

Edit the `weights` object in any file under `data/scenarios/`:

```json
{
  "weights": {
    "individual": 1.0,
    "operator": 2.0,   ← change this value
    "overall": 1.0
  }
}
```

The engine reads weights by key via `ctx.weights.get(key, default=1.0)`.  No engine code changes are needed — this is the design's core tunability guarantee (R23).

---

## How to add a new rule

1. Create a file in `scheduler/rules/`, e.g. `scheduler/rules/electricity.py`.
2. Define a `Rule` subclass and decorate it with `@register`:

```python
# scheduler/rules/electricity.py
from scheduler.rules.registry import Rule, ScheduleContext, register

@register
class ElectricityCostRule(Rule):
    """Penalises charging during peak electricity tariff window (18:00–22:00)."""
    name = "ElectricityCostRule"
    kind = "soft"
    weight_key = "electricity_cost"

    PEAK_START = 1080   # 18:00 in minutes
    PEAK_END   = 1320   # 22:00 in minutes
    PEAK_RATE  = 2.0    # cost multiplier per minute

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)
        penalty = 0.0
        for evt in ctx.charge_events:
            if self.PEAK_START <= evt["start_min"] < self.PEAK_END:
                penalty += self.PEAK_RATE * ctx.scenario.world.charge_minutes
        return weight * penalty
```

3. Add `"electricity_cost": 1.0` to the scenario's `weights` object.
4. Done — the engine autodiscovers the file and prices electricity into plan selection.  No other file changes.

---

## Project layout

```
bus-charging-scheduler/
├── app.py                  ← Streamlit UI (only file with Streamlit imports)
├── requirements.txt        ← streamlit + pandas only
├── pytest.ini              ← test configuration
├── ARCHITECTURE.md         ← design decisions, data model, change-foresight table
├── scheduler/              ← pure-Python engine (zero Streamlit imports)
│   ├── config.py           ← centralised defaults (speed, range, charge time)
│   ├── model.py            ← immutable domain dataclasses
│   ├── physics.py          ← travel-time arithmetic
│   ├── loader.py           ← scenario JSON parser + 3-stage validation
│   ├── plans.py            ← candidate plan enumeration (range-feasibility)
│   ├── resources.py        ← ChargerPool (reservation + snapshot/restore)
│   ├── objective.py        ← aggregate rule scorer
│   ├── engine.py           ← deterministic greedy scheduler (main algorithm)
│   ├── validate.py         ← post-schedule invariant checker
│   ├── adapters.py         ← engine output → pandas DataFrames
│   └── rules/
│       ├── registry.py     ← Rule ABC + @register decorator
│       ├── hard_rules.py   ← H1 RangeRule, H2 RouteOrderRule, H4 ChargeDurationRule
│       ├── soft_rules.py   ← S1 IndividualWaitRule, S2 OperatorRule, S3 OverallRule
│       └── _discover.py    ← auto-imports all rule files on package import
├── data/
│   └── scenarios/
│       ├── scenario_1.json ← Even spacing (15 min intervals)
│       ├── scenario_2.json ← Bunched start (8 min intervals then spaced)
│       ├── scenario_3.json ← Asymmetric (10 BK, 4 KB)
│       ├── scenario_4.json ← Operator-heavy (KPN 8/10, operator weight=2.0)
│       └── scenario_5.json ← Worst-case convergence (8 min both ends)
├── tests/
│   ├── test_physics.py     ← travel time, HH:MM formatting
│   ├── test_plans.py       ← feasibility enumeration, verified BK/KB sets
│   ├── test_charger.py     ← charger pool unit + H3 invariant across scenarios
│   ├── test_rules.py       ← per-rule: H1/H2/H4 violations; S1/S2/S3 penalty + weight scaling
│   ├── test_e2e.py         ← all 5 scenarios: validate()==[], ≥2 charges, determinism
│   └── test_weights.py     ← Scenario 4: operator weight changes schedule (R28/R44)
├── docs/                   ← 47 markdown engineering blueprints
│   ├── 00-requirements/    ← requirements analysis, constraints, traceability
│   ├── 01-architecture/    ← system architecture, component responsibilities, ADRs
│   ├── 02-scheduler-engine/← scheduling logic, allocation, optimisation, rules
│   ├── 03-data-model/      ← domain model, scenario schema, output schema
│   ├── 04-api-contracts/   ← internal API + validation rules
│   ├── 05-frontend/        ← Streamlit flow + component acceptance
│   ├── 06-backend/         ← in-process service responsibilities
│   ├── 07-testing/         ← test plan + edge cases
│   ├── 08-devops/          ← deployment strategy
│   ├── 09-security/        ← threat model
│   ├── 10-observability/   ← decision transparency
│   └── 11-submission/      ← checklist + interview prep
└── planning/               ← task tracker + docs plan
```

---

## The five scenarios

| # | Name | Buses | Weights | Key test |
|---|------|-------|---------|----------|
| 1 | Even Spacing | 10 BK + 10 KB, 15 min apart | 1/1/1 | Baseline |
| 2 | Bunched Start | 8 min apart then spaced | 1/1/1 | Contention at B,C |
| 3 | Asymmetric | 10 BK, 4 KB only | 1/1/1 | Lopsided charger demand |
| 4 | Operator-Heavy | KPN = 8/10 BK, operator=2.0 | 1/**2**/1 | Weight reshuffles order |
| 5 | Worst-Case | 8 min both ends, 20 buses | 1/1/1 | Maximum convergence |

---

## Run tests

```bash
pytest
```

All **103 tests** pass green for a correct implementation.  Key assertions:
- `validate() == []` for all five scenarios.
- Every through-bus has ≥ 2 charge events.
- Each hard rule (H1/H2/H4) returns `math.inf` for a violating case and `0` for a satisfying one.
- Each soft rule (S1/S2/S3) returns higher penalty for worse inputs; weight×2 doubles the penalty.
- Scenario 4 with `operator=2.0` produces a different objective score than `operator=1.0`.

---

## Assumptions

All assumptions are documented in `ARCHITECTURE.md §Assumptions`.  Key ones:
- Speed: constant **60 km/h** (no traffic, no variation).
- Charging: always to **full** in exactly **25 minutes**.
- Buses do **not** charge at endpoints (Bengaluru, Kochi).
- Greedy: locally optimal per-bus plan given prior commitments; not globally optimal.
- Tie-break: priority DESC → departure ASC → bus ID ASC (deterministic).
