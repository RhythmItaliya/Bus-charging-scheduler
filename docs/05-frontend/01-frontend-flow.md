# Frontend Flow (Streamlit)

**Purpose.** Specify the UI so it satisfies every UI requirement (dropdown first, input view,
per-bus timetable, per-station view, nothing more) and makes correctness eyeball-able.

## Page composition
On load, `app.py` sets page config and immediately renders a `st.selectbox` of scenario names
from `list_scenarios()` — the **first and topmost element**, so a reviewer lands on the
dropdown. A sidebar exposes three weight sliders (`individual`, `operator`, `overall`)
defaulting to the selected scenario's weights, with a "reset to scenario defaults" button.
Selecting a scenario or moving a slider triggers a cached `load_scenario` + `schedule`, then a
startup `validate`; any violation renders a red `st.error` banner. The body uses `st.tabs` with
three tabs: **Input**, **Per-bus timetable**, **Per-station**.

## The three views
The **Input** tab shows a readable table of buses (id, operator, direction, departure HH:MM)
plus a compact summary of world/route/stations/active weights, and an expander with the raw
scenario JSON so reviewers see exactly what is fed in. The **Per-bus timetable** tab shows one
row (or expandable block) per bus with stations used, and arrive/start/wait/end at each stop in
HH:MM, the charge count, and final arrival; non-zero waits are highlighted so they are obvious.
The **Per-station** tab shows, for each of A/B/C/D, the ordered list of buses that charged
there with charger index, start, wait, and end — letting a reviewer judge whether the order is
sensible given the weights.

## Caching and responsiveness
`load_scenario` + `schedule` are wrapped in `st.cache_data` keyed by scenario name plus the
active weights, so re-selecting a scenario is instant and recomputation happens only when the
scenario or a weight changes. This keeps the demo snappy and scales to larger inputs.

## Deliberate omissions
No metrics dashboards, maps, or animations — the spec forbids them. The UI's only job is:
pick a scenario → see the input → see what the scheduler decided. Restraint here is itself a
graded signal.
