# Observability

**Purpose.** Make scheduling decisions inspectable so any odd schedule can be explained — the
property that lets you defend output in the interview and debug regressions fast.

## Decision transparency
The single most valuable observability feature is the **objective breakdown**: every
`ScheduleResult` carries `objective_breakdown` (`{rule_name: contribution}`) and `total`,
so you can see exactly how much the individual, operator, and overall terms contributed and
why one plan beat another. Surface this in a debug expander in the UI and assert on it in tests.

## Structured logging
The engine logs, at debug level, each bus's considered plans with their costs and the chosen
plan, and each charger reservation (`node, requested, actual, wait, charger_index`). Logs are
plain Python `logging` to stdout, which Streamlit Cloud captures. Because the engine is
deterministic, a log line fully reconstructs any decision. Keep logs off the hot path at info
level to avoid noise; gate decision traces behind a `SCHEDULER_DEBUG` flag.

## Validation as a health signal
The startup `validate()` result is the app's health check: an empty violation list means the
last schedule is provably correct. A non-empty list is logged at error level with the specific
rule and subject, and shown as a banner. This converts silent correctness bugs into loud,
actionable signals.

## Metrics (lightweight)
Although the spec forbids a metrics *dashboard*, the engine can expose simple counters for its
own debugging — number of candidate plans evaluated, total reservations, makespan — printed in
the debug expander. These are diagnostic, not a user-facing dashboard.

## Future tracing
If the engine becomes a service, wrap `schedule` in a span carrying scenario name, bus count,
and objective total; the existing breakdown and logs map directly onto trace attributes with no
redesign.
