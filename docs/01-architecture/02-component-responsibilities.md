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
Streamlit shell: dropdown, weight sliders, three tabbed views, startup validation banner.
**Depends on:** `loader`, `engine`, `validate`, `adapters`. **The only file importing
Streamlit.**
