# Frontend Flow (Streamlit)

**Purpose.** Specify the UI so it satisfies every UI requirement (dropdown first, input view,
per-bus timetable, per-station view, nothing more) and makes correctness eyeball-able.

## Package structure

All rendering logic lives in the `frontend/` package — `app.py` is a thin orchestrator
(~100 lines) that only wires data from the engine to the UI. No Streamlit calls exist outside
`app.py` and `frontend/`.

```
frontend/
├── __init__.py      # package docstring
├── icons.py         # SVG icon library (ICONS dict) + icon() helper — no emoji
├── styles.py        # inject_css() — one call; all CSS in one place
├── sidebar.py       # render_sidebar() → (path, w_ind, w_op, w_all)
└── tabs.py          # render_input_tab(), render_bus_tab(), render_station_tab()
                     # shared helpers: _icon_header, _icon_label, _metric_col
```

## Startup sequence

```
st.set_page_config()       ← must be first Streamlit call
inject_css()               ← injects all CSS incl. tab SVG ::before icons
render_sidebar()           ← scenario dropdown + weight sliders → returns selections
_cached_schedule(path, w…) ← load → override weights → schedule → validate (cached)
validation banner          ← SVG icon + coloured div (no emoji)
st.tabs(["Input", "Per-Bus Timetable", "Per-Station Order"])
render_input_tab(…)
render_bus_tab(…)
render_station_tab(…)
```

## The three views

The **Input** tab shows a readable table of buses (id, operator, direction, departure HH:MM)
plus a compact summary of world/route/stations/active weights, and an expander with the raw
scenario JSON. The **Per-Bus Timetable** tab shows one row per bus per charge stop with
arrive/start/wait/end in HH:MM; non-zero waits are yellow (≤ 30 min) or red (> 30 min).
Four summary metrics (total wait, max wait, makespan, bus count) appear below the table.
The **Per-Station** tab shows, for each of A/B/C/D, the ordered list of buses that charged
there with charger index, start, wait, and end — letting a reviewer judge whether the order
is sensible given the weights.

## SVG icon approach

- **Inline body icons** — `icon(name, label)` in `frontend/icons.py` injects
  `vertical-align:middle` into each SVG so it sits flush on the text baseline.
- **Tab icons** — CSS `::before` pseudo-elements with SVG data-URIs on
  `[data-testid="stTab"]:nth-of-type(n)` because `st.tabs()` only accepts plain text labels.
- **No emoji anywhere** in the rendered page.

## Caching and responsiveness

`load_scenario` + `schedule` are wrapped in `st.cache_data` keyed by scenario path plus the
three active weights, so re-selecting a scenario is instant and recomputation happens only
when the scenario or a weight changes.

## Deliberate omissions

No metrics dashboards, maps, or animations — the spec forbids them. The UI's only job is:
pick a scenario → see the input → see what the scheduler decided.
