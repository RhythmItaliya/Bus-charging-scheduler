# Output Schema

**Purpose.** Define the engine's output objects so the UI and tests bind to a stable contract.

## `ChargeEvent`
Fields: `station` (node), `arrive_min` (when the bus reaches the station), `start_min` (when
charging begins after any wait), `wait_min` (`start_min − arrive_min`), `end_min`
(`start_min + charge_minutes`), `charger_index` (which charger, for multi-charger stations).
Invariant: `end_min − start_min == world.charge_minutes`.

## `BusPlan`
Fields: `bus_id`, `operator`, `direction`, `charge_events: list[ChargeEvent]` in route order,
`arrival_min` (final arrival at destination), `total_wait` (`Σ wait_min`). Invariant: legs
between consecutive events (and origin/destination) respect range; next-event `arrive_min`
equals previous `end_min` plus travel time of the intervening segment(s).

## `ScheduleResult`
Fields: `bus_plans: list[BusPlan]`, `station_order: dict[node, list[StationSlot]]` where
`StationSlot` carries `bus_id`, `operator`, `charger_index`, `start_min`, `wait_min`,
`end_min` sorted by `start_min`; and `objective_breakdown: dict[str, float]` plus `total`.

## Serializability
All output objects are plain dataclasses convertible to dicts, enabling JSON dumps for
debugging, golden-file tests, and a future API response body with no reshaping.
