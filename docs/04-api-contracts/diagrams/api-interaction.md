# Diagram — API Interaction (internal call sequence)

```mermaid
sequenceDiagram
    participant UI  as app.py (Streamlit)
    participant L   as loader.py
    participant E   as engine.py
    participant V   as validate.py
    participant A   as adapters.py

    UI->>L: list_scenarios(dir)
    L-->>UI: [(name, path)…]

    UI->>L: load_scenario(selected_path)
    Note over L: Stage 1 — World constants
    Note over L: Stage 2 — Route connectivity
    Note over L: Stage 3 — Stations / Weights / Buses
    L-->>UI: Scenario (or raises ValueError)

    UI->>E: schedule(scenario)  [st.cache_data]
    Note over E: 1. Init ChargerPools
    Note over E: 2. Sort buses (priority→departure→id)
    Note over E: 3. Greedy loop: plans→simulate→score→commit
    Note over E: 4. Assemble station_order
    Note over E: 5. Compute objective_breakdown
    Note over E: 6. validate() post-schedule (defence in depth)
    E-->>UI: ScheduleResult

    UI->>V: validate(result, scenario)
    Note over V: H1 range, H2 order, H3 exclusivity, H4 duration, R15
    V-->>UI: [] (clean) or [violation strings…]

    UI->>A: to_input_table(scenario)
    A-->>UI: DataFrame (bus roster)
    UI->>A: to_bus_table(result, scenario)
    A-->>UI: DataFrame (per-bus timetable)
    UI->>A: to_station_table(result, node) × 4
    A-->>UI: DataFrame (per-station order)

    UI-->>UI: render validation banner + 4 tabs
```

## Public API contracts

| Function | Signature | Returns | Raises |
|----------|-----------|---------|--------|
| `list_scenarios` | `(directory: str\|Path) → list[tuple[str, Path]]` | Sorted `(name, path)` pairs | `FileNotFoundError` |
| `load_scenario` | `(path: str\|Path) → Scenario` | Fully validated `Scenario` | `ValueError`, `FileNotFoundError`, `json.JSONDecodeError` |
| `schedule` | `(scenario: Scenario) → ScheduleResult` | Complete committed schedule | `ValueError` (no plan), `RuntimeError` (validation failed) |
| `validate` | `(result: ScheduleResult, scenario: Scenario) → list[str]` | Empty = valid; non-empty = violations | — |
| `to_input_table` | `(scenario) → pd.DataFrame` | Bus roster with HH:MM departure | — |
| `to_bus_table` | `(result, scenario) → pd.DataFrame` | Per-bus charging timetable | — |
| `to_station_table` | `(result, node) → pd.DataFrame` | Charge order at one station | — |
