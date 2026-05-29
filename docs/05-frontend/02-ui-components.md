# UI Components

**Purpose.** Enumerate each UI component, its data source, and its acceptance behaviour.

## Scenario selector
A `st.selectbox` bound to `list_scenarios()`. Acceptance: present at top on first paint;
changing selection swaps all three views to the new scenario.

## Weight controls
Three `st.slider`s (range e.g. 0.0–5.0, step 0.5) plus a reset button. Source: scenario
weights. Acceptance: defaults match the scenario file; dragging `operator` up in Scenario 4
visibly changes the per-station order and the objective breakdown.

## Input table
`st.dataframe(to_input_table(scenario))` + world/route/station/weight summary + raw-JSON
expander. Acceptance: reviewer can read the full input including active weights.

## Per-bus timetable
`st.dataframe(to_bus_table(result, scenario))` with conditional highlight on non-zero waits and
a visible charge-count column. Acceptance: every through-bus shows ≥2 charges; all buses show a
final arrival; waits are legible.

## Per-station view
One `st.dataframe(to_station_table(result, node))` per node A/B/C/D. Acceptance: order matches
charge start times; charger index shown when `num_chargers > 1`.

## Validation banner
`st.error` rendered when `validate()` returns violations; otherwise nothing. Acceptance: clean
for all five scenarios.
