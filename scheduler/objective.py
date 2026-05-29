"""
scheduler/objective.py — Aggregate weighted objective scorer.

Consumes the rule registry generically to produce a (feasible, total, breakdown)
triple for any candidate plan.  The engine calls this during plan evaluation; the
breakdown is also surfaced in the UI for transparency and in tests for assertion.

Design: the objective module is intentionally thin — it only delegates to rules
and sums.  Adding new rules does not require editing this file.

References:
    docs/02-scheduler-engine/03-optimization-rules.md  (Aggregation section)
    docs/02-scheduler-engine/05-rule-framework.md      (rule framework)
    docs/02-scheduler-engine/01-scheduling-logic.md    (step 4: incremental scoring)
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from scheduler.rules.registry import RuleRegistry, ScheduleContext


def score(
    ctx: ScheduleContext,
    registry: RuleRegistry,
) -> Tuple[bool, float, Dict[str, float]]:
    """
    Evaluate all registered rules for a candidate plan and return a score tuple.

    Algorithm:
      1. Evaluate all hard rules first.  If any returns inf, the plan is
         infeasible → return (False, inf, breakdown).
      2. Sum soft rule penalties.  Each soft rule returns a penalty already
         multiplied by its weight from ctx.weights.
      3. Return (True, total_penalty, breakdown).

    Args:
        ctx:      The ScheduleContext for the candidate bus + plan.
        registry: The populated rule registry (from get_registry()).

    Returns:
        (feasible, total, breakdown) where:
          feasible  — False if any hard rule is violated.
          total     — sum of all soft penalties (inf if infeasible).
          breakdown — {rule.name: contribution} for transparency / testing.
    """
    breakdown: Dict[str, float] = {}
    total = 0.0

    # Hard rules — feasibility gates
    for rule in registry.hard_rules:
        contribution = rule.evaluate(ctx)
        breakdown[rule.name] = contribution
        if contribution == math.inf:
            return False, math.inf, breakdown

    # Soft rules — weighted penalties
    for rule in registry.soft_rules:
        contribution = rule.evaluate(ctx)
        breakdown[rule.name] = contribution
        total += contribution

    return True, total, breakdown
