# Rule Framework — Pluggable Constraints & Objectives

**Purpose.** Specify the extension mechanism that lets a new rule be added by *defining* it,
never by editing the engine — the explicitly graded scalability property.

## Abstraction
`Rule` is an abstract base with `name: str`, `kind: Literal['hard','soft']`, optional
`weight_key: str` (soft rules only), and `evaluate(ctx) -> float`. Hard rules return `0.0`
when satisfied and `math.inf` when violated. Soft rules return a non-negative penalty already
multiplied by `ctx.weights[self.weight_key]`. `ctx` (a `ScheduleContext`) exposes the
candidate/committed schedule, the scenario, and the merged weights.

## Registry and autodiscovery
`RuleRegistry` collects `Rule` instances. A `@register` decorator adds a rule on import, and
`discover()` imports every module in `scheduler/rules/` so that dropping a new file
auto-registers its rules. The engine and objective consume the registry **generically** and
never reference a concrete rule class by name. This is the mechanism that satisfies "add a new
rule without rewriting the engine".

## Adding a rule (canonical example)
To add a time-of-day electricity-cost objective: create `scheduler/rules/electricity.py` with
a `@register` `ElectricityCostRule(kind='soft', weight_key='electricity_cost')` whose
`evaluate` sums a per-minute tariff over each charge interval times the weight; then add
`"electricity_cost": <value>` to the scenarios' `weights`. No other file changes. The engine
immediately begins pricing electricity into plan selection.

## Adding a hard rule
A new hard rule (e.g. a station closed for maintenance window) is the same pattern with
`kind='hard'`, returning `inf` when a bus would charge in the closed window. The validator
will then also enforce it because it iterates all registered hard rules.

## Why this is safe
Rules are pure functions of `(schedule, scenario, weights)`; they have no engine internals as
dependencies, so they cannot break orchestration. They are independently unit-testable, which
keeps additions low-risk and fast — the property the live interview will probe.
