# Hidden Expectations — What They Are Really Testing

**Purpose.** The PDF states requirements, but the *evaluation* is about judgement and
foresight. This document names the implicit expectations so the build optimises for what is
actually graded, and so the interview holds no surprises.

## 1. "Design the data structure first" is the real exam
The strongest signal is whether the **scenario data model** anticipated change. The graders
explicitly ask for a written list of changes you foresaw and how the design absorbs each
**without code edits**. Build the data model before any algorithm, and make the world entirely
data-driven. Every constant that could plausibly change (range, charge time, speed, segment
distances, charger counts, operator set, weights) must be a field, not a literal.

## 2. The interview curveballs are pre-announced
The PDF lists exactly what will be thrown live. The design must make each a **data-only** edit:

| Curveball | Must require | Where it changes |
|---|---|---|
| Add a station (e.g. E) | data only | `route.nodes`, `route.segments`, `stations` |
| Change a segment distance | data only | `route.segments[i].distance_km` |
| Double the chargers somewhere | data only | `stations[n].num_chargers` |
| Swap / add an operator | data only | `buses[].operator` (set derived) |
| Encode a fresh schedule | data only | new `scenario_*.json` |
| Per-bus battery range | data only | `buses[].range_km` |
| Priority buses | data only (+latent rule) | `buses[].priority` (field already exists) |
| Time-of-day electricity cost | new rule + weight key | drop `ElectricityCostRule`, add weight |
| Driver shifts | new rule + data | drop `DriverShiftRule`, add shift data |
| Multiple routes sharing stations | data + station as shared resource | multiple `route`s, station pool keyed by node |
| Add a new soft/hard rule live | new `Rule` file only | `scheduler/rules/` autodiscovery |

If any row above would force an engine edit, the design has failed the core test.

## 3. "Different weights → different schedules" must be demonstrable
Scenario 4 sets `operator = 2.0` deliberately so that tuning the operator weight up vs down
produces **visibly different** schedules. The optimisation must be genuinely weight-sensitive
(not a fixed greedy that ignores weights), and the UI should let a reviewer drag the weight
and watch the order change. If weights do not move the output, correctness is considered failed.

## 4. Explainability beats raw optimality
This is a take-home for a small instance (20 buses). A clean, **explainable, defensible**
scheduler (event-driven greedy + a transparent weighted objective with a per-term breakdown)
scores higher than an opaque optimal solver you cannot defend line-by-line. Keep the search
strategy swappable so a CP-SAT/ILP optimiser can replace greedy later without touching rules
or data — and *say so* in the architecture doc.

## 5. Honesty in docs is graded
The rubric rewards docs that are honest about what is done, not done, and next. Do not claim
a real database or REST API exists. State assumptions plainly (speed, metric definitions,
tie-breaks) and defend them.

## 6. Output sensibility is eyeballed
Reviewers will literally read the per-bus timetable and per-station order and ask "does this
look reasonable?" Through-buses must show ≥2 charges, waits must be plausible, and station
order must look consistent with the active weights. Build the UI to make this obvious
(highlight non-zero waits, show charge counts, sort stations by charge start).
