# Component Responsibilities

**Purpose.** Give each module a single, testable responsibility and explicit dependencies so
an AI agent can implement them in isolation.

## `scheduler/config.py`
Holds only fallback world defaults (`speed_kmph=60`, `charge_minutes=25`,
`battery_range_km=240`) as a frozen dataclass. **Responsibility:** be the *only* place a
physical default literal appears. **Depends on:** nothing. **Forbidden:** route, stations,
operators, weights.

## `scheduler/model.py`
Defines `Segment`, `Route`, `Station`, `Bus`, `Weights`, `Scenario`, and output objects
`ChargeEvent`, `BusPlan`, `ScheduleResult`. **Responsibility:** typed, immutable domain
vocabulary and pure geometry helpers (`distance_between`, `cumulative_distance`,
`downstream_stations`). **Depends on:** `config`. **No I/O.**

## `scheduler/loader.py`
`load_scenario(path) → Scenario` and `list_scenarios(dir)`. **Responsibility:** parse JSON,
merge defaults, validate, build model objects. **Depends on:** `model`, `config`. Raises
`ValueError` with actionable messages.

## `scheduler/physics.py`
Pure travel-time and arrival-time functions. **Responsibility:** convert distance + speed to
minutes; compute wait-free arrival at each node. **Depends on:** `model`.

## `scheduler/plans.py`
`candidate_plans(bus, route, station_nodes, range_km)`. **Responsibility:** enumerate all
range-feasible, route-ordered charging plans for one bus. **Depends on:** `model`.

## `scheduler/rules/`
`base.py` (abstract `Rule`, `RuleRegistry`, autodiscovery), `hard_rules.py`, `soft_rules.py`.
**Responsibility:** encapsulate every constraint and objective as an independent unit.
**Depends on:** `model`. The engine depends on the registry, never on concrete rule classes.

## `scheduler/resources.py`
`ChargerPool(num_chargers, charge_minutes)` with `reserve(requested_start)`.
**Responsibility:** allocate charger time-slots, compute waits, generalise over N chargers.
**Depends on:** nothing but stdlib.

## `scheduler/objective.py`
`score(schedule, scenario, registry)`. **Responsibility:** combine hard feasibility and
weighted soft penalties into `(feasible, total, breakdown)`. **Depends on:** `rules`.

## `scheduler/engine.py`
`schedule(scenario) → ScheduleResult` via a swappable `Strategy`. **Responsibility:**
orchestrate plan choice + charger reservation + objective minimisation; build timelines and
station order. **Depends on:** `plans`, `resources`, `objective`, `model`.

## `scheduler/validate.py`
`validate(result, scenario) → list[Violation]`. **Responsibility:** defensive re-check of all
hard rules on the final schedule. **Depends on:** `rules`, `model`.

## `scheduler/adapters.py`
DataFrame builders + `minutes_to_hhmm`. **Responsibility:** all human formatting. **Depends
on:** `model`, pandas.

## `app.py`

Thin orchestrator (~100 lines): `set_page_config` → `inject_css` → `render_sidebar` →
`_cached_schedule` → validation banner → three `st.tabs`. **No rendering logic here.**
**Depends on:** `frontend/`, `scheduler/loader`, `scheduler/engine`, `scheduler/validate`,
`scheduler/model`.

## `frontend/icons.py`

`ICONS: dict[str, str]` of Heroicons SVGs + `icon(name, label) → str` helper.
**Responsibility:** single source of truth for all SVG icons; no emoji anywhere.
Injects `vertical-align:middle` into every SVG for baseline alignment.
**Depends on:** nothing (pure string functions).

## `frontend/styles.py`

`inject_css()` — one call injects all global CSS: `.icon-label` class, wait-cell colours,
metric card padding, and tab SVG `::before` icons via encoded data-URIs.
**Depends on:** `streamlit`.

## `frontend/sidebar.py`

`render_sidebar() → (selected_path, w_individual, w_operator, w_overall)`.
**Responsibility:** scenario dropdown (R32: first/topmost), weight sliders, reset button,
active-weight readout. Calls `st.stop()` on missing scenario data.
**Depends on:** `frontend/icons`, `scheduler/config`, `scheduler/loader`, `streamlit`.

## `frontend/tabs.py`

`render_input_tab`, `render_bus_tab`, `render_station_tab` + shared private helpers:
`_icon_header`, `_icon_label`, `_metric_col`, `_highlight_wait`.
**Responsibility:** all tab content rendering, zero duplicated markup.
**Depends on:** `frontend/icons`, `scheduler/adapters`, `scheduler/model`, `streamlit`.
