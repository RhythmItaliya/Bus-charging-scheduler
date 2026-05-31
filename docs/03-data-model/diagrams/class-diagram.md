# Diagram — Full Python Class Diagram

All dataclasses, domain objects, rule classes, and runtime resources.
This is the canonical class reference for an AI agent or developer building or extending this project.

```mermaid
classDiagram
    %% ─────────────────────────────────────────
    %% DOMAIN MODEL (scheduler/model.py)
    %% ─────────────────────────────────────────
    class World {
        +float speed_kmph = 60.0
        +int   charge_minutes = 25
        +float battery_range_km = 240.0
    }

    class Segment {
        +str   from_node
        +str   to_node
        +float distance_km
    }

    class Route {
        +tuple~str~    nodes
        +tuple~Segment~ segments
        +dict~str_float~ positions
        +distance_between(from_node, to_node) float
    }

    class Station {
        +str node
        +int num_chargers = 1
    }

    class Bus {
        +str   id
        +str   operator
        +str   origin
        +str   destination
        +int   departure_min
        +float range_km = 240.0
        +int   priority = 0
    }

    class Weights {
        +float individual = 1.0
        +float operator   = 1.0
        +float overall    = 1.0
        +dict  extra
        +get(key, default) float
    }

    class Scenario {
        +str   name
        +World world
        +Route route
        +dict~str_Station~ stations
        +Weights weights
        +tuple~Bus~ buses
        +operators() set~str~
        +intermediate_nodes() list~str~
    }

    class ChargeEvent {
        +str station
        +int arrive_min
        +int start_min
        +int wait_min
        +int end_min
        +int charger_index
    }

    class BusPlan {
        +str  bus_id
        +str  operator
        +str  direction
        +list~ChargeEvent~ charge_events
        +int  arrival_min
        +int  total_wait
    }

    class StationSlot {
        +str bus_id
        +str operator
        +int charger_index
        +int start_min
        +int wait_min
        +int end_min
    }

    class ScheduleResult {
        +list~BusPlan~            bus_plans
        +dict~str_list~           station_order
        +dict~str_float~          objective_breakdown
        +float                    total_objective
    }

    %% ─────────────────────────────────────────
    %% RESOURCE ALLOCATOR (scheduler/resources.py)
    %% ─────────────────────────────────────────
    class ChargerPool {
        +str  node
        +int  num_chargers
        +int  charge_minutes
        -list _slot_free_at
        +reserve(arrive_min) tuple
        +snapshot() list
        +restore(state) None
    }

    %% ─────────────────────────────────────────
    %% RULE FRAMEWORK (scheduler/rules/)
    %% ─────────────────────────────────────────
    class Rule {
        <<abstract>>
        +str name
        +str kind
        +str weight_key
        +evaluate(ctx ScheduleContext) float
    }

    class RuleRegistry {
        -list _rules
        +add(rule Rule) None
        +hard_rules() list~Rule~
        +soft_rules() list~Rule~
        +all_rules() list~Rule~
    }

    class ScheduleContext {
        +str     bus_id
        +tuple   plan
        +list    charge_events
        +list    all_committed
        +Scenario scenario
        +Weights weights
    }

    class RangeRule {
        +name = "RangeRule"
        +kind = "hard"
        +evaluate(ctx) float
    }

    class RouteOrderRule {
        +name = "RouteOrderRule"
        +kind = "hard"
        +evaluate(ctx) float
    }

    class ChargeDurationRule {
        +name = "ChargeDurationRule"
        +kind = "hard"
        +evaluate(ctx) float
    }

    class IndividualWaitRule {
        +name       = "IndividualWaitRule"
        +kind       = "soft"
        +weight_key = "individual"
        +evaluate(ctx) float
    }

    class OperatorRule {
        +name       = "OperatorRule"
        +kind       = "soft"
        +weight_key = "operator"
        +evaluate(ctx) float
    }

    class OverallRule {
        +name       = "OverallRule"
        +kind       = "soft"
        +weight_key = "overall"
        +evaluate(ctx) float
    }

    %% ─────────────────────────────────────────
    %% RELATIONSHIPS
    %% ─────────────────────────────────────────

    Scenario "1" *-- "1" World        : has
    Scenario "1" *-- "1" Route        : has
    Scenario "1" *-- "1..*" Station   : has
    Scenario "1" *-- "1" Weights      : has
    Scenario "1" *-- "1..*" Bus       : contains

    Route "1" *-- "1..*" Segment      : ordered

    ScheduleResult "1" *-- "1..*" BusPlan      : contains
    ScheduleResult "1" *-- "0..*" StationSlot  : orders
    BusPlan        "1" *-- "1..*" ChargeEvent  : timeline

    Station "1" <-- ChargerPool       : allocates for

    RuleRegistry "1" o-- "0..*" Rule  : holds
    Rule <|-- RangeRule
    Rule <|-- RouteOrderRule
    Rule <|-- ChargeDurationRule
    Rule <|-- IndividualWaitRule
    Rule <|-- OperatorRule
    Rule <|-- OverallRule

    ScheduleContext --> Scenario       : reads
    ScheduleContext --> Weights        : reads
    Rule            --> ScheduleContext : evaluates with
```

## Field contracts

| Class | Invariant |
|-------|-----------|
| `ChargeEvent` | `wait_min == start_min - arrive_min` |
| `ChargeEvent` | `end_min  == start_min + world.charge_minutes` |
| `BusPlan`     | `total_wait == sum(e.wait_min for e in charge_events)` |
| `Route`       | `positions[nodes[0]] == 0.0`; positions are cumulative distances |
| `Bus`         | `range_km > 0`; `departure_min >= 0` |
| `Weights`     | All fields ≥ 0.0; `extra` may be empty |
| `ChargerPool` | `len(_slot_free_at) == num_chargers` at all times |

## Adding a new rule (live demo pattern)

```python
# scheduler/rules/electricity.py
from scheduler.rules.registry import Rule, ScheduleContext, register

@register
class ElectricityCostRule(Rule):
    name = "ElectricityCostRule"
    kind = "soft"
    weight_key = "electricity_cost"

    def evaluate(self, ctx: ScheduleContext) -> float:
        weight = ctx.weights.get(self.weight_key)
        night_charges = sum(
            1 for e in ctx.charge_events
            if 0 <= (e.start_min % 1440) < 360   # 00:00–06:00 is cheaper
        )
        # Penalise off-peak to incentivise daytime charging
        return weight * (len(ctx.charge_events) - night_charges)
```
Drop the file — `_discover.py` picks it up. Zero engine changes.
