"""
Bus Charging Scheduler — Pure-Python scheduling engine.

This package contains zero Streamlit imports.  It is a headless, testable,
liftable engine that can be consumed by any presentation layer (today: Streamlit
app.py; tomorrow: a REST service worker).

Public surface (see docs/04-api-contracts/01-internal-api-contracts.md):
    loader.list_scenarios(dir) -> list[tuple[name, path]]
    loader.load_scenario(path) -> Scenario
    engine.schedule(scenario)  -> ScheduleResult
    validate.validate(result, scenario) -> list[Violation]
    adapters.to_input_table / to_bus_table / to_station_table -> DataFrame
"""
