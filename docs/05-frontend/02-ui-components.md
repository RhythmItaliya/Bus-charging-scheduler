# UI Components

**Purpose.** Enumerate each UI component, its source module, data source, and acceptance behaviour.

## Package layout

| Module | Responsibility |
|--------|---------------|
| `frontend/icons.py` | `ICONS` dict (Heroicons SVGs) + `icon(name, label) → str` helper |
| `frontend/styles.py` | `inject_css()` — global CSS, `.icon-label` class, tab `::before` SVG icons |
| `frontend/sidebar.py` | `render_sidebar() → (path, w_ind, w_op, w_all)` |
| `frontend/tabs.py` | `render_input_tab`, `render_bus_tab`, `render_station_tab` + shared helpers |
| `app.py` | Thin orchestrator: page config → CSS → sidebar → schedule → banner → tabs |

---

## Scenario selector

A `st.selectbox` in `render_sidebar()`, bound to `list_scenarios()`. The **first and topmost
element** on every page load (R32). Changing selection invalidates the `@st.cache_data` key
and triggers a full reschedule.

## Weight controls

Three `st.slider`s (range 0.0–5.0, step 0.5) in `render_sidebar()`, defaulting to the
selected scenario's `weights` object. A **Reset weights** button calls `st.rerun()` which
re-reads the scenario defaults.

Acceptance: defaults match the scenario JSON; dragging `operator` up in Scenario 4 visibly
changes the per-station order and the objective breakdown.

## Validation banner

Rendered in `app.py` above all tabs. Uses `icon("check_circle")` (green) on success and
`icon("alert")` (red) on failure. **No emoji.** All icon strings come from `frontend/icons.py`.

## Tab icons

`st.tabs()` only accepts plain text labels. Tab SVG icons are injected via CSS
`::before` pseudo-elements using encoded SVG data-URIs in `frontend/styles.py`. This is
the only reliable pattern for SVG icons in Streamlit tab headers.

## Input tab (`render_input_tab`)

`st.dataframe(to_input_table(scenario))` + world/route/station/active-weight JSON summary +
raw-JSON expander + objective-breakdown expander.

Acceptance: reviewer can read the full input including active weights without leaving the tab.

## Per-Bus Timetable tab (`render_bus_tab`)

`st.dataframe(to_bus_table(result, scenario))` with `_highlight_wait` Styler function:
- Yellow background — wait 1–30 min  
- Red background — wait > 30 min

Four summary metrics below the table (Total Wait, Max Wait, Makespan, Bus Count) each
prefixed with an SVG icon via `_metric_col()` helper.

Acceptance: every through-bus shows ≥ 2 charges; all buses show a final arrival; waits
are visually distinct.

## Per-Station Order tab (`render_station_tab`)

One `st.expander` per intermediate node (A, B, C, D) with `to_station_table(result, node)`.
Station header uses `icon("map_pin")` inline SVG, no emoji.

Acceptance: order matches charge start times; charger index shown when `num_chargers > 1`.

## Shared rendering helpers (in `frontend/tabs.py`)

| Helper | Purpose |
|--------|---------|
| `_icon_header(level, icon_name, label)` | Renders h2/h3 with inline SVG icon |
| `_icon_label(icon_name, label, small)` | Renders span.icon-label with optional small font |
| `_metric_col(col, icon_name, label, value, sub)` | Icon label + `st.metric` in a column |
| `_highlight_wait(col)` | Pandas Styler — colours the Wait (min) column |
