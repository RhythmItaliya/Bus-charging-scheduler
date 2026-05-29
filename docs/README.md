# Bus Charging Scheduler — Engineering Documentation

> **Audience:** an autonomous AI software engineer (or a human engineer) who must
> build, extend, or operate this system **without re-reading the original PDF**.
> This `docs/` tree is the single source of truth. Every fact, constraint, decision,
> and execution instruction needed to ship the project lives here.

## What this project is (one paragraph)

Electric buses run a fixed 540 km corridor **Bengaluru → A → B → C → D → Kochi** in
both directions. Buses leave their origin with a full 240 km battery. Only the four
intermediate stations **A, B, C, D** can charge buses; each station today has **one**
charger. Charging is always to full and always takes **25 minutes**. A bus may never
travel more than 240 km between charges, so a 540 km trip needs **at least two charges**.
When several buses want the same charger at once, a **scheduler** decides each bus's
charging plan (which stations it uses) and the order in which buses use each charger,
optimising three tunable, weighted objectives: per-bus wait, per-operator fairness, and
overall network time. The deliverable is a single **Python + Streamlit** app that reads
data-defined scenarios and shows the schedule it produced.

## How to navigate this documentation

| Folder | Purpose |
|---|---|
| `00-requirements/` | **Start here.** Line-by-line decode of the assignment, every constraint formalised, hidden expectations, traceability matrix. |
| `01-architecture/` | System architecture, component responsibilities, design decisions, data flow. |
| `02-scheduler-engine/` | The core: scheduling logic, charging allocation, optimisation rules, conflict resolution, the pluggable rule framework. |
| `03-data-model/` | Domain data model ("database"), scenario file schema, output schema. |
| `04-api-contracts/` | Internal module contracts, forward-looking REST contract, validation rules, retry semantics. |
| `05-frontend/` | Streamlit UI flow and components. |
| `06-backend/` | Backend service responsibilities (engine, loader, adapters). |
| `07-testing/` | Test plan, invariants, edge cases. |
| `08-devops/` | Deployment to Streamlit Community Cloud, CI. |
| `09-security/` | Threat model and hardening (scoped to a public read-only app). |
| `10-observability/` | Logging, tracing, debuggability of scheduling decisions. |
| `11-submission/` | Final submission checklist and interview defence prep. |
| `PROJECT_PLAN.csv` | Master execution plan: every doc → code tasks → status. |

## Reading order for an AI build agent

1. `00-requirements/01-requirements-analysis.md`
2. `00-requirements/02-constraints-and-rules.md`
3. `03-data-model/01-data-model-design.md` + `02-scenario-schema.md`
4. `02-scheduler-engine/*` (logic → allocation → optimisation → conflict → rule framework)
5. `01-architecture/*`
6. `04-api-contracts/*`, `05-frontend/*`, `06-backend/*`
7. `07-testing/*`, `08-devops/*`, `10-observability/*`
8. `11-submission/*`

## Canonical constants (memorise these)

| Constant | Value | Source / overridable |
|---|---|---|
| Battery range | 240 km | per-scenario `world.battery_range_km`, per-bus `range_km` |
| Charge time | 25 min, always to full | per-scenario `world.charge_minutes` |
| Speed | 60 km/h (assumed) | per-scenario `world.speed_kmph` |
| Route | Bengaluru–A–B–C–D–Kochi | per-scenario `route` |
| Segments (km) | 100, 120, 100, 120, 100 (=540) | per-scenario `route.segments` |
| Chargers/station | 1 | per-scenario `stations[node].num_chargers` |
| Buses/scenario | 20 (10 each way) | scenario `buses` list |
| Operators | kpn, freshbus, flixbus | derived from data |
| Default weights | individual=1, operator=1, overall=1 | per-scenario `weights` (S4 operator=2) |

> **Golden rule for every contributor:** nothing about the *world* may be hardcoded in
> logic. The scenario file describes the world; the engine reads it. If a change can be
> expressed as editing a scenario file, it must **not** require touching code.
