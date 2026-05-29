# API Contracts (Internal + Forward-Looking REST)

**Purpose.** Define the function-level contracts between layers (the real "API" of this
single-process app) and a forward-looking REST surface for when the engine is extracted.

## Internal contracts (authoritative today)
- `loader.list_scenarios(dir) -> list[tuple[name, path]]`. Powers the dropdown. Pure read.
- `loader.load_scenario(path) -> Scenario`. Parse+validate+build. Raises `ValueError`.
- `engine.schedule(scenario: Scenario) -> ScheduleResult`. Pure, deterministic, no I/O, no
  Streamlit. Idempotent for identical input.
- `validate.validate(result, scenario) -> list[Violation]`. `[]` means valid.
- `adapters.to_input_table(scenario) -> DataFrame`,
  `adapters.to_bus_table(result, scenario) -> DataFrame`,
  `adapters.to_station_table(result, node) -> DataFrame`. Formatting only.

These contracts are the seam: `app.py` is the only caller that crosses from presentation into
the engine, and it does so through exactly these functions.

## Forward-looking REST contract (not built now)
If the engine becomes a service, the natural surface is:
`GET /scenarios` → list; `GET /scenarios/{name}` → scenario JSON;
`POST /schedule` with body `{scenario, weights_override?}` → `ScheduleResult` JSON;
`POST /validate` → violations. Because `engine.schedule` is already a pure function of a
`Scenario`, each endpoint is a thin wrapper. Auth, rate limiting, and idempotency keys would be
added at that layer; today they are out of scope (public read-only demo).

## Versioning
The scenario schema carries an implicit version via its shape; if breaking changes are needed,
add a top-level `"schema_version"` and branch in the loader. Output objects should add fields
additively to preserve backward compatibility for any consumer.
