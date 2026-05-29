# Requirements Analysis — Line-by-Line Decode

**Purpose.** This document converts the assignment PDF into structured engineering
requirements so no contributor ever needs the PDF again. Each requirement is given an ID
(`R#`), the literal source intent, the engineering interpretation, and the implementation
implication. Treat every `MUST` as a hard acceptance gate.

## 1. Stack, hosting, and process model

The assignment fixes the stack: **Python + Streamlit**, **one repo, one process**.
Everything — scheduling logic, scenario loading, and UI — lives in a single Python process.
There is deliberately **no separate backend service, no database server, and no DevOps
pipeline to design**; Streamlit Community Cloud is the host and reads `requirements.txt`
to install dependencies automatically. The engineering implication is that "backend",
"API", and "database" in this project are *logical* layers inside one process, not network
services. We honour that separation cleanly in code structure (a pure-Python `scheduler`
package with zero Streamlit imports, consumed by a thin `app.py`) so the engine could later
be lifted into a real service without a rewrite, but we do **not** build network plumbing now.

- **R1 (MUST).** App is Python + Streamlit, single repo, single process.
- **R2 (MUST).** Hosted on Streamlit Community Cloud at a public URL.
- **R3 (MUST).** All dependencies install from `requirements.txt`.
- **R43 (SHOULD).** In-memory state only; no auth, no DB, no maps.

## 2. The physical world

Buses run a fixed corridor with four intermediate charging stations. The world is fully
numeric and deterministic: no traffic, no speed variation, identical buses. A bus departs
its origin **fully charged** with **240 km of range**. Travel time is derived purely from
distance using one consistent speed; we assume **60 km/h**, which makes a 100 km segment
take 100 minutes and a 120 km segment take 120 minutes. This assumption is documented and
lives in config, overridable per scenario.

- **R4 (MUST).** Route Bengaluru→A→B→C→D→Kochi, segment distances 100/120/100/120/100 km (total 540).
- **R5 (MUST).** Buses travel both directions and **share** the same physical chargers.
- **R6 (MUST).** Every bus starts full with 240 km range.
- **R7 (MUST).** Only A, B, C, D are scheduling stations; **endpoints are not** part of scheduling.
- **R8 (MUST).** Each station has exactly **one** charger (today).
- **R10 (MUST).** Travel time = distance ÷ consistent speed.

## 3. Buses and operators

Each scenario has 20 buses, 10 going Bengaluru→Kochi (`bus-BK-*`) and 10 going
Kochi→Bengaluru (`bus-KB-*`). Each bus has a fixed scheduled **departure time** from its
origin and belongs to one of three operators: **KPN, Freshbus, Flixbus**. Operators must be
derived from the data, never hardcoded, because "swap in a new operator" is an explicit
future test.

- **R11 (MUST).** 20 buses/scenario, 10 per direction.
- **R12 (MUST).** Each bus has a scheduled departure time from its origin.
- **R13 (MUST).** Three operators today; operator set is data-driven.

## 4. Charging plans and the range constraint

A bus can travel at most **240 km** on a full charge, and charging always refills to full.
Therefore, between any two consecutive charges — and between origin and the first charge,
and between the last charge and arrival — the distance **must not exceed 240 km**, or the
schedule is invalid. Because the full trip is 540 km, a through-bus **cannot** complete the
journey with fewer than **two** charges. The scheduler chooses *which* stations a bus uses.

**Concrete, verified feasibility (Bengaluru→Kochi).** Distances from origin: A=100, B=220,
C=320, D=440, Kochi=540. A bus cannot reach C (320) on a full charge, so its **first charge
must be at A or B**. The only valid **two-charge** plans are **{A,C}, {B,C}, {B,D}**.
({A,D} is invalid because A→D = 340 km > 240.) Three- and four-charge plans are also valid
and may be chosen when they reduce contention or wait. The Kochi→Bengaluru direction mirrors
this: first charge must be D or C, and valid two-charge plans are **{D,B}, {C,B}, {C,A}**.

- **R14 (MUST).** No leg (origin→first, charge→charge, last→arrival) may exceed range; else invalid.
- **R15 (MUST).** A through-trip requires ≥2 charges.
- **R19 (MUST).** Stations are visited in route order; no backtracking; no repeats.

## 5. Hard rules (always hold)

- **R16 (MUST).** One bus per charger at a time (one charger/station today; generalise to N).
- **R17 (MUST).** Charging is always exactly 25 minutes.
- **R18 (MUST).** A bus must never run out of range between consecutive charges.
- **R19 (MUST).** Route order only; no backtracking.

These are *feasibility* constraints. A schedule that violates any of them is not a worse
schedule — it is an **invalid** one and must be rejected by the engine and flagged by a
post-schedule validator.

## 6. Soft rules (optimise, weighted, tunable)

When the scheduler has freedom (which stations, who charges first), it balances three soft
objectives, each with a **tunable weight**:

1. **Individual (R20).** No single bus should wait too long.
2. **Operator (R21).** Each operator's fleet should run smoothly as a group.
3. **Overall (R22).** Total time across the whole network should be low.

- **R23 (MUST).** Weights are tunable from **one obvious place**, never hardcoded or scattered.
- **R28 (MUST).** Default weights are 1/1/1 for all scenarios **except Scenario 4**, where
  `operator = 2.0`.

## 7. The scalability mandate (the thing they "really care about")

The system must absorb change **without an engine rewrite**. Specifically: changing a weight
is a one-value edit; adding a new rule means *defining* a rule, not editing the engine; and
growing the world (more buses, stations, operators, routes) is data-only. The PDF lists
future asks explicitly — priority buses, time-of-day electricity costs, driver shifts,
multiple routes sharing stations — and the interview will throw curveballs: add a station,
double the chargers, swap an operator, change a segment distance, encode a fresh scenario,
add a new rule live. See `00-requirements/03-hidden-expectations.md`.

- **R24 (MUST).** Add a rule without rewriting the engine.
- **R25 (MUST).** Grow the world without a rewrite (data-driven).
- **R26 (MUST).** "A scenario **is** the data structure" — design the data model first.

## 8. Deliverables and outputs

The scheduler reads any scenario, uses the scenario's weights, decides each bus's charging
plan and the per-charger order, and computes each bus's timeline (when it charges where, how
long it waits, when it arrives). The UI must, at minimum: present a **scenario dropdown** at
the top, show the **scenario input**, a **per-bus timetable**, and a **per-station order**
view — and nothing more (no dashboards, maps, or animations).

- **R29–R31 (MUST).** Engine: read scenario → schedule → per-bus timeline.
- **R32–R37 (MUST).** UI: dropdown first, input view, per-bus timetable, per-station view, minimal.
- **R38–R41 (MUST).** Deliver hosted link, public repo, README, ARCHITECTURE.
- **R42 (MUST).** Document all assumptions.
- **R44 (MUST).** Correctness: respect range; different weights → different defensible schedules.

## Acceptance summary

A submission passes when: all 5 scenarios load from data files; every through-bus has ≥2
charges with no leg > 240 km; no charger ever serves two buses at once; the three views
render for all scenarios; changing the operator weight visibly changes Scenario 4; and the
docs honestly explain framework, data model, anticipated changes, and assumptions.
