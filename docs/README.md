# Bus Charging Scheduler — Engineering Documentation

> **Audience:** an autonomous AI software engineer (or a human engineer) who must
> build, extend, or operate this system **without re-reading the original spec**.
> This `docs/` tree is the single source of truth.
> Every constraint, design decision, and execution instruction lives here.

---

## What this project is (one paragraph)

Electric buses run a fixed 540 km corridor **Bengaluru → A → B → C → D → Kochi**
in both directions. Buses leave their origin with a full **240 km** battery.
Only the four intermediate stations **A, B, C, D** can charge buses;
each station has **one** charger. Charging is always to full and takes **25 minutes**.
A bus may never travel more than 240 km between charges, so every bus needs **at least 2 charges**.
When several buses want the same charger at once, a scheduler decides each bus's
**charging plan** (which stations) and the **queue order** at each station,
optimising three tunable weighted objectives: per-bus wait, operator fairness, overall makespan.
The deliverable is a single **Python + Streamlit** app.

---

## Canonical constants (memorise these before reading any code)

| Constant | Value | Where it lives |
|---|---|---|
| Battery range | 240 km | `world.battery_range_km`, `bus.range_km` |
| Charge time | 25 min, always to full | `world.charge_minutes` |
| Speed | 60 km/h (assumed constant) | `world.speed_kmph` |
| Route nodes | Bengaluru, A, B, C, D, Kochi | `route.nodes` |
| Segment distances (km) | 100, 120, 100, 120, 100 (= 540) | `route.segments` |
| Chargers per station | 1 | `stations[node].num_chargers` |
| Buses per scenario | 20 (10 each way) | `buses[]` |
| Operators | kpn, freshbus, flixbus | derived from bus data |
| Default weights | individual=1, operator=1, overall=1 | `weights` (Scenario 4: operator=2) |
| Clock encoding | minutes from midnight | 19:00 = 1140, 21:15 = 1275 |

> **Golden rule:** nothing about the *world* may be hardcoded in logic.
> The scenario JSON describes the world; the engine reads it.
> Any change expressible as a JSON edit must **not** require a code change.

---

## Architecture — layers and rules

```
app.py (Streamlit entry point — thin wiring layer only)
  │
  ├── frontend/sidebar.py    → render_sidebar() → (path, w_ind, w_op, w_all)
  ├── frontend/tabs.py       → render_input_tab / render_bus_tab / render_station_tab / render_architecture_tab
  ├── frontend/styles.py     → inject_css()
  └── frontend/icons.py      → icon(name, size, colour) → HTML string
           │
           ↓ calls
  scheduler/adapters.py      → to_input_table / to_bus_table / to_station_table → pd.DataFrame
           │                   (ONLY file allowed to import pandas)
           ↓ reads
  scheduler/engine.py        → schedule(scenario) → ScheduleResult
  scheduler/validate.py      → validate(result, scenario) → List[str]
  scheduler/loader.py        → load_scenario(path) → Scenario
           │
           ├── scheduler/plans.py       → candidate_plans(bus, scenario) → List[Plan]
           ├── scheduler/resources.py   → ChargerPool.reserve / snapshot / restore
           ├── scheduler/objective.py   → score(ctx, registry) → (feasible, total, breakdown)
           ├── scheduler/physics.py     → travel_minutes / minutes_to_hhmm
           ├── scheduler/model.py       → Scenario, World, Route, Bus, Weights, BusPlan, ChargeEvent
           ├── scheduler/config.py      → DEFAULTS dict, SCENARIOS_DIR
           └── scheduler/rules/
               ├── registry.py          → Rule ABC, RuleRegistry, @register, get_registry()
               ├── hard_rules.py        → RangeRule, RouteOrderRule, ChargeDurationRule
               ├── soft_rules.py        → IndividualWaitRule, OperatorRule, OverallRule
               └── _discover.py         → auto-imports all rule modules at package init

LAYER RULE: lower layers never import higher ones.
            scheduler/* has ZERO Streamlit imports.
```

---

## How to navigate this documentation

| Folder | Purpose — read this to understand… |
|--------|-------------------------------------|
| `00-requirements/` | Every constraint formalised, hidden expectations, traceability matrix |
| `01-architecture/` | System architecture, component responsibilities, design decisions, **configuration guide** |
| `02-scheduler-engine/` | Scheduling logic, charging allocation, optimisation rules, conflict resolution, pluggable rule framework |
| `03-data-model/` | Domain model, scenario JSON schema, output schema, **full class diagram** |
| `04-api-contracts/` | Internal module contracts, validation rules |
| `05-frontend/` | Streamlit UI flow and component acceptance criteria |
| `06-backend/` | Backend service (engine, loader, adapters) responsibilities |
| `07-testing/` | Test plan, invariants, edge cases |
| `08-devops/` | Deployment to Streamlit Community Cloud, CI |
| `09-security/` | Threat model (public read-only app), **security diagram** |
| `10-observability/` | Logging with rich, decision transparency |
| `11-submission/` | Interview prep guide + live demo scripts |

---

## Reading order for an AI build agent

If you need to build or extend this system from scratch, read in this order:

1. `docs/README.md` — this file (canonical constants + architecture)
2. `docs/00-requirements/01-requirements-analysis.md` — every requirement extracted
3. `docs/00-requirements/02-constraints-and-rules.md` — hard rules H1-H4, soft rules S1-S3
4. `docs/03-data-model/01-data-model-design.md` — data structure design
5. `docs/03-data-model/02-scenario-schema.md` — JSON schema spec
6. `docs/02-scheduler-engine/01-scheduling-logic.md` — greedy algorithm spec
7. `docs/02-scheduler-engine/05-rule-framework.md` — pluggable rule registry
8. `docs/01-architecture/01-system-architecture.md` — layer rules
9. `docs/05-frontend/01-frontend-flow.md` — UI flow
10. `docs/07-testing/01-testing-plan.md` — what tests to write

---

## Key data structures (quick reference for builders)

### Input: Scenario

```python
@dataclass(frozen=True)
class Scenario:
    name: str
    world: World          # speed_kmph, charge_minutes, battery_range_km
    route: Route          # nodes tuple, segments tuple, positions dict
    stations: Dict[str, Station]   # node → Station(num_chargers)
    weights: Weights      # individual, operator, overall, extra: dict
    buses: tuple[Bus, ...]

@dataclass(frozen=True)
class Bus:
    id: str               # "bus-BK-01"
    operator: str         # "kpn" | "freshbus" | "flixbus"
    origin: str           # "Bengaluru" | "Kochi"
    destination: str      # "Kochi" | "Bengaluru"
    departure_min: int    # minutes from midnight (19:00 = 1140)
    range_km: float       # default 240.0
    priority: int         # default 0 (higher = scheduled first)
```

### Output: ScheduleResult

```python
@dataclass
class ScheduleResult:
    bus_plans: List[BusPlan]
    station_order: Dict[str, List[StationSlot]]   # node → slots sorted by start_min
    objective_breakdown: Dict[str, float]         # rule_name → penalty
    total_objective: float

@dataclass
class ChargeEvent:
    station: str
    arrive_min: int
    start_min: int
    wait_min: int     # start_min - arrive_min (≥ 0)
    end_min: int      # start_min + world.charge_minutes
    charger_index: int
```

### JSON scenario file schema

```json
{
  "name": "Scenario 1 — Even Spacing",
  "world": { "speed_kmph": 60, "charge_minutes": 25, "battery_range_km": 240 },
  "route": {
    "nodes": ["Bengaluru", "A", "B", "C", "D", "Kochi"],
    "segments": [
      { "from": "Bengaluru", "to": "A", "distance_km": 100 },
      { "from": "A", "to": "B", "distance_km": 120 },
      { "from": "B", "to": "C", "distance_km": 100 },
      { "from": "C", "to": "D", "distance_km": 120 },
      { "from": "D", "to": "Kochi", "distance_km": 100 }
    ]
  },
  "stations": {
    "A": { "num_chargers": 1 },
    "B": { "num_chargers": 1 },
    "C": { "num_chargers": 1 },
    "D": { "num_chargers": 1 }
  },
  "weights": { "individual": 1.0, "operator": 1.0, "overall": 1.0 },
  "buses": [
    { "id": "bus-BK-01", "operator": "kpn", "origin": "Bengaluru",
      "destination": "Kochi", "departure_min": 1140 }
  ]
}
```

---

## Scheduling algorithm (step by step)

```
schedule(scenario) → ScheduleResult

1. Create ChargerPool for each station
   pool[A] = ChargerPool(node="A", num_chargers=1, charge_minutes=25)

2. Sort buses: priority DESC → departure_min ASC → id ASC

3. For each bus:
   a. candidate_plans(bus) → [("A","C"), ("B","C"), ("B","D")] for BK
   b. For each plan:
        snapshots = {node: pool.snapshot() for all nodes}
        events = _simulate_plan(bus, plan, pools)
           → for each station in plan:
               arrive = prev_end + (distance / speed) * 60
               start, wait, idx = pool.reserve(arrive)
               end = start + charge_minutes
        ctx = ScheduleContext(bus_id, plan, events, committed, scenario, weights)
        feasible, cost, breakdown = objective.score(ctx, registry)
           → hard rules: any returns inf → INFEASIBLE
           → soft rules: sum weighted penalties → cost
        pool.restore(snapshots)  ← ROLLBACK tentative reservation
   c. Commit lowest-cost feasible plan (re-simulate permanently)
   d. log.bus_committed(bus_id, plan, wait, arrival, operator)

4. Assemble station_order: {node → [StationSlot sorted by start_min]}

5. Compute objective_breakdown (aggregate over all committed plans)

6. validate(result, scenario) → check H1/H2/H3/H4/R15 → raise if any fail
```

---

## Valid charging plans for current route

**BK buses (Bengaluru → Kochi), positions: A=100, B=220, C=320, D=440, Kochi=540:**

| Plan | Leg 1 | Leg 2 | Leg 3 | Valid? |
|------|-------|-------|-------|--------|
| A, C | 100 | 220 | 220 | ✓ |
| B, C | 220 | 100 | 220 | ✓ |
| B, D | 220 | 220 | 100 | ✓ |
| A, D | 100 | **340** | 100 | ✗ (H1) |

**KB buses (Kochi → Bengaluru), positions reversed: D=100, C=220, B=320, A=440, Bng=540:**

| Plan | Leg 1 | Leg 2 | Leg 3 | Valid? |
|------|-------|-------|-------|--------|
| D, C | 100 | 120 | 320 | ✓ (C→A=220, A→Bng=100) |
| D, B | 100 | 220 | 220 | ✓ |
| C, B | 220 | 100 | 220 | ✓ |
| C, A | 220 | 220 | 100 | ✓ |

---

## How rules work (pluggable registry)

Every rule is a class decorated with `@register` in `scheduler/rules/`.
The engine never imports rule classes directly — it calls `get_registry()`.

```python
from scheduler.rules.registry import Rule, ScheduleContext, register

@register
class MyNewRule(Rule):
    name = "MyNewRule"
    kind = "hard"    # or "soft"

    def evaluate(self, ctx: ScheduleContext) -> float:
        # ctx.bus_id, ctx.plan, ctx.charge_events, ctx.all_committed,
        # ctx.scenario, ctx.weights — all available here
        if hard_violation:
            return math.inf   # plan rejected
        return 0.0            # or: weight * penalty for soft rules
```

**That is the entire API for adding a rule.** No engine edits. No registry edits.
The `_discover.py` auto-imports all modules in `scheduler/rules/` at package init.

---

## Important: what must never be hardcoded

The following must always come from the scenario data, never from Python literals:

- `world.speed_kmph` — never `60` in physics calculations
- `world.charge_minutes` — never `25` in engine or rules
- `world.battery_range_km` — never `240` in range checks (use `bus.range_km`)
- operator names — never `if operator == "kpn"` — derive from bus data
- station names — never `["A","B","C","D"]` literals — read from `route.nodes`
- weight values — always via `ctx.weights.get(key)` — never literal multipliers

---

## Diagram index

Each section in `docs/` has a `diagrams/` subfolder. All diagrams are Mermaid-renderable.

| # | Diagram | File | Type |
|---|---------|------|------|
| 1 | Requirements map | `docs/00-requirements/diagrams/requirements-map.md` | flowchart |
| 2 | Full system architecture (layers) | `docs/01-architecture/diagrams/system-architecture.md` | flowchart |
| 3 | Component dependency graph | `docs/01-architecture/diagrams/component-dependency.md` | graph LR |
| 4 | End-to-end data flow | `docs/01-architecture/diagrams/data-flow.md` | flowchart |
| 5 | Scheduler workflow | `docs/02-scheduler-engine/diagrams/scheduler-workflow.md` | flowchart |
| 6 | Charging allocation (ChargerPool) | `docs/02-scheduler-engine/diagrams/charging-allocation-flow.md` | flowchart |
| 7 | Conflict resolution (sequence) | `docs/02-scheduler-engine/diagrams/conflict-resolution-flow.md` | sequenceDiagram |
| 8 | Optimisation decision | `docs/02-scheduler-engine/diagrams/optimization-decision-flow.md` | flowchart |
| 9 | State management (commit lifecycle) | `docs/02-scheduler-engine/diagrams/state-management-flow.md` | stateDiagram-v2 |
| 10 | **Full Python class diagram** | `docs/03-data-model/diagrams/class-diagram.md` | **classDiagram** |
| 11 | Entity-relationship | `docs/03-data-model/diagrams/entity-relationship.md` | erDiagram |
| 12 | Scenario data flow | `docs/03-data-model/diagrams/scenario-data-flow.md` | flowchart |
| 13 | API interaction sequence | `docs/04-api-contracts/diagrams/api-interaction.md` | sequenceDiagram |
| 14 | Error/retry flow | `docs/04-api-contracts/diagrams/retry-flow.md` | flowchart |
| 15 | UI navigation flow | `docs/05-frontend/diagrams/ui-navigation-flow.md` | flowchart |
| 16 | Render sequence | `docs/05-frontend/diagrams/render-sequence.md` | sequenceDiagram |
| 17 | Backend service sequence | `docs/06-backend/diagrams/backend-sequence.md` | sequenceDiagram |
| 18 | **Test pyramid (206 tests)** | `docs/07-testing/diagrams/test-pyramid.md` | flowchart |
| 19 | Deployment flow | `docs/08-devops/diagrams/deployment-flow.md` | flowchart |
| 20 | **Security threat model** | `docs/09-security/diagrams/security-model.md` | flowchart |
| 21 | Logging flow | `docs/10-observability/diagrams/logging-flow.md` | flowchart |
| 22 | **Config consumer map** | `docs/01-architecture/04-configuration-guide.md` | flowchart |

> **Bold** = newly added or significantly updated diagrams.
