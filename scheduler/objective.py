from __future__ import annotations

import math
from typing import Dict, Tuple

from scheduler.rules.registry import RuleRegistry, ScheduleContext


def score(
    ctx: ScheduleContext,
    registry: RuleRegistry,
) -> Tuple[bool, float, Dict[str, float]]:
    breakdown: Dict[str, float] = {}
    total = 0.0


    for rule in registry.hard_rules:
        contribution = rule.evaluate(ctx)
        breakdown[rule.name] = contribution
        if contribution == math.inf:
            return False, math.inf, breakdown


    for rule in registry.soft_rules:
        contribution = rule.evaluate(ctx)
        breakdown[rule.name] = contribution
        total += contribution

    return True, total, breakdown
