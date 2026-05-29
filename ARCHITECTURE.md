# ARCHITECTURE — Bus Charging Scheduler

This document covers the framework choice, data model, anticipated-change table, and all assumptions.  It is a required deliverable (R38–R41).

---

## 1. Framework choice and why

**Python + Streamlit, single process.**

The assignment fixes the stack; this is not a choice but a deliberate constraint.  Within that constraint:

- **Streamlit** provides the required scenario dropdown and three-view UI with minimal boilerplate, and deploys to Streamlit Community Cloud without a Dockerfile or custom server.
- **Python** standard library is sufficient for all scheduling logic — the engine uses only `itertools`, `dataclasses`, `statistics`, `math`, and `collections`.  No heavy solver dependency is needed at this scale.

### Why event-driven greedy (not CP-SAT / ILP)?

| Property | Greedy | CP-SAT |
|----------|--------|--------|
| Explainability | ✅ Every decision traceable to weights | ⚠ Opaque solver |
| Extensibility | ✅ New rule = new file, zero engine edit | ❌ New constraint = remodel |
| Dependency | ✅ stdlib only | ❌ `ortools` / solver install |
| Performance | ✅ O(buses × plans × stations), ms | ✅ Better at huge scale |
| Global optimality | ⚠ Locally optimal | ✅ Globally optimal |

**Verdict:** For 20 buses, 4 stations, and an explicit "rule extensibility" grade signal, greedy + pluggable weighted rule registry is the correct fit.  The `Strategy` interface makes swapping in CP-SAT a future no-op:

```python
class GreedyStrategy:          # today
    def solve(self, scenario): ...

class CpSatStrategy:           # future (if instance scale grows)
    def solve(self, scenario): ...
```

Rules, data model, and UI are unchanged by this swap.

---

## 2. Data structure design

**"A scenario is the data structure"** (R26).

All world state is encoded in JSON files in `data/scenarios/`.  There is no SQL database — flat JSON is diffable, version-controlled, and trivially shipped.  At runtime the loader hydrates each file into immutable Python dataclasses; the engine never mutates input state.

### Core entities

```
Scenario
├── World         (speed_kmph, charge_minutes, battery_range_km)
├── Route         (nodes, segments → derived positions dict)
├── stations      {node → Station(num_chargers)}
├── Weights       (individual, operator, overall, extra: dict)
└── buses         [Bus(id, operator, origin, dest, departure_min, range_km, priority)]

Output:
ScheduleResult
├── bus_plans     [BusPlan(bus_id, operator, direction, charge_events, arrival_min, total_wait)]
│                   charge_events: [ChargeEvent(station, arrive_min, start_min, wait_min, end_min, charger_index)]
├── station_order {node → [StationSlot sorted by start_min]}
├── objective_breakdown {rule_name → penalty}
└── total_objective
```

### Why every field is extensible

| Need | Field | Change type |
|------|-------|-------------|
| Add a station | `route.nodes`, `route.segments`, `stations` | Data only |
| Change a segment distance | `route.segments[i].distance_km` | Data only |
| Double chargers | `stations[node].num_chargers = 2` | Data only |
| New operator | `bus.operator` (string, set derived) | Data only |
| Add buses | append to `buses` list | Data only |
| Per-bus range | `bus.range_km` | Data only |
| Priority bus | `bus.priority` (field already present) | Data only |
| New soft objective | add key to `weights.extra` + new Rule file | Data + 1 file |
| New hard rule | new Rule file | 1 file only |
| Change speed | `world.speed_kmph` | Data only |
| Change charge time | `world.charge_minutes` | Data only |

---

## 3. Anticipated-changes table

| Change | How the design absorbs it | Engine rewrite? |
|--------|--------------------------|----------------|
| Add station E between D and Kochi | Add node to `route.nodes`, add segment, add to `stations` | **No** |
| Change A→B distance from 120 to 150 km | Edit `route.segments[1].distance_km` | **No** |
| Double chargers at station B | Set `stations["B"].num_chargers = 2` | **No** |
| Swap Flixbus buses to new operator | Edit `operator` field on affected buses | **No** |
| Add 10 more buses | Append to `buses` list | **No** |
| Add a second route sharing stations | Add new Scenario JSON, pools keyed by node auto-share | **No** |
| Priority buses (charge first) | Raise `bus.priority`; engine already sorts by priority DESC | **No** |
| Time-of-day electricity cost | Add `ElectricityCostRule` file (see README §How to add a rule) | **No** |
| Driver shift constraints | Add `DriverShiftRule` hard rule; add shift data to Bus/World | **No** |
| Variable speed / traffic | Make `world.speed_kmph` per-segment; update physics.py | **Minimal** |
| Partial charging (e.g. 50%) | Add `charge_fraction` field to World; update ChargerPool | **Minimal** |
| Per-bus battery range | `bus.range_km` field already present | **No** |
| New weighted soft objective | New Rule file + new weight key in scenario JSON | **No** |
| Bigger fleets (100 buses) | Engine is O(buses × plans × stations); linear | **No** |
| Replace greedy with CP-SAT | Swap `GreedyStrategy` for `CpSatStrategy` behind Strategy interface | **No engine edit** |

---

## 4. How to change a weight (concrete before/after)

**Scenario 4 example — raise operator weight from 1.0 to 2.0:**

*File: `data/scenarios/scenario_4.json`*

```diff
  "weights": {
    "individual": 1.0,
-   "operator": 1.0,
+   "operator": 2.0,
    "overall": 1.0
  }
```

That is the **entire change**.  The engine reads weights by key:
```python
weight = ctx.weights.get("operator")   # → 2.0
penalty = weight * operator_variance   # → doubled
```

No engine code is touched.  Via the UI, drag the "Operator Fairness" slider to 2.0 for the same effect without editing any file.

---

## 5. How to add a rule (concrete example)

**New rule: penalise charging during peak electricity tariff (18:00–22:00).**

*Create file: `scheduler/rules/electricity.py`*

```python
from scheduler.rules.registry import Rule, ScheduleContext, register

@register
class ElectricityCostRule(Rule):
    name = "ElectricityCostRule"
    kind = "soft"
    weight_key = "electricity_cost"

    PEAK_START = 1080   # 18:00
    PEAK_END   = 1320   # 22:00
    PEAK_RATE  = 2.0    # cost multiplier per charging minute during peak

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)
        penalty = 0.0
        for evt in ctx.charge_events:
            if self.PEAK_START <= evt["start_min"] < self.PEAK_END:
                penalty += self.PEAK_RATE * ctx.scenario.world.charge_minutes
        return weight * penalty
```

*Add to any scenario JSON:*
```json
"weights": { "individual": 1.0, "operator": 1.0, "overall": 1.0, "electricity_cost": 1.0 }
```

**No other file changes.**  The autodiscovery mechanism in `scheduler/rules/_discover.py` imports the new file, `@register` adds the rule to the registry, and the objective scorer picks it up generically.

---

## 6. Assumptions

All assumptions are explicitly documented here per R42.

| Assumption | Value | Reasoning |
|------------|-------|-----------|
| Travel speed | 60 km/h constant | Assignment states "consistent speed"; 60 km/h makes 100 km = 100 min which is clean arithmetic. Overridable per scenario via `world.speed_kmph`. |
| Charge duration | Always exactly 25 minutes, always to full | Assignment specifies "25 minutes to charge"; no partial charging mentioned. Hard rule H4. |
| Charging at endpoints | Not permitted | R7 states "endpoints are not part of scheduling". |
| Decision timing | Instantaneous; no re-planning mid-trip | Buses commit to a plan at departure; no dynamic re-routing. |
| Tie-break order | priority DESC → departure_min ASC → bus_id ASC | Guarantees deterministic, reproducible schedules. |
| Individual wait metric | Sum of per-bus waits (Σ wait) | Default; max-based alternative documented in code. |
| Operator fairness metric | Sum of per-fleet within-fleet wait variance | Variance chosen because it penalises *uneven* treatment, which is what the spec means by "fleet runs smoothly". |
| Overall metric | Makespan (max arrival − min departure) | Compresses the total operation window. Total person-time alternative documented. |
| Infeasible bus | Engine raises ValueError with bus name | Silent invalidity is prohibited by design. The app surfaces the error. |
| Optional charges | A bus may take more than minimum charges | If adding a 3rd charge reduces cost, the engine may select it. Permitted by spec. |
| Multi-charger sharing | Pools keyed by physical node | Both directions and future routes using the same station contend on the same pool automatically. |
| Clock encoding | Minutes from midnight; values > 1440 allowed | Avoids midnight-wrap bugs. The UI converts to HH:MM display only. |

---

## 7. Layer dependency rule

```
app.py (Streamlit UI)
  └── scheduler/adapters.py (formatting only)
        └── scheduler/engine.py + validate.py + model.py
              └── scheduler/rules/* (pure functions of schedule context)
              └── scheduler/resources.py (ChargerPool)
              └── scheduler/plans.py (plan enumeration)
              └── scheduler/physics.py (travel arithmetic)
              └── scheduler/model.py (dataclasses)
              └── scheduler/config.py (defaults)

Lower layers NEVER import higher ones.
scheduler/* contains ZERO Streamlit imports.
```

This keeps the engine headless, testable via `pytest`, runnable via CLI, and liftable into a future REST service without a rewrite.
