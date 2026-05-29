"""
scheduler/rules/registry.py — Rule ABC, registry, and autodiscovery mechanism.

This module implements the extension point that satisfies R24: adding a new rule
requires only *defining* it (drop a file in rules/), never editing the engine.

Design:
  • Rule   — abstract base class with a standard interface.
  • RuleRegistry — collects Rule instances; consumed generically by objective.py.
  • @register    — decorator that adds a rule to the global registry on import.
  • get_registry() — returns the singleton registry (populated after discovery).

References:
    docs/02-scheduler-engine/05-rule-framework.md  (full specification)
    docs/00-requirements/02-constraints-and-rules.md (H1–H4, S1–S3)
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional


# ---------------------------------------------------------------------------
# ScheduleContext — the read-only bag the engine hands to each rule's evaluate()
# ---------------------------------------------------------------------------

class ScheduleContext:
    """
    Read-only view of the in-flight schedule used by all rules during scoring.

    Rules receive this context and MUST NOT mutate it.  It contains everything a
    rule needs to compute a penalty (or detect a hard violation) without coupling
    to engine internals.
    """

    def __init__(
        self,
        *,
        bus_id: str,
        plan: tuple,
        charge_events: list,       # list of provisional ChargeEvent-like dicts
        all_committed: list,       # list of committed BusPlan objects so far
        scenario: Any,             # Scenario object
        weights: Any,              # Weights object
    ) -> None:
        self.bus_id = bus_id
        self.plan = plan
        self.charge_events = charge_events
        self.all_committed = all_committed
        self.scenario = scenario
        self.weights = weights


# ---------------------------------------------------------------------------
# Rule — abstract base class
# ---------------------------------------------------------------------------

class Rule(ABC):
    """
    Abstract base for all hard and soft scheduling rules.

    Subclasses implement evaluate(ctx) to return:
      • Hard rules: 0.0 if satisfied, math.inf if violated.
      • Soft rules: a non-negative penalty already multiplied by the rule's weight.

    The engine and objective always consume rules through this interface,
    so any concrete class can be added without touching existing code.
    """

    # Human-readable name used in objective_breakdown and test assertions.
    name: str

    # 'hard' rules gate feasibility; 'soft' rules contribute to the objective.
    kind: Literal["hard", "soft"]

    # For soft rules: the key used to look up the weight from scenario.weights.
    # Hard rules do not need a weight_key.
    weight_key: Optional[str] = None

    @abstractmethod
    def evaluate(self, ctx: ScheduleContext) -> float:
        """
        Evaluate this rule given the current scheduling context.

        Returns:
            0.0  if hard rule is satisfied.
            inf  if hard rule is violated.
            ≥0   weighted penalty for soft rules (weight already applied).
        """
        ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class RuleRegistry:
    """
    Collection of all registered Rule instances.

    The engine and objective iterate over this generically.  Rules are stored
    in registration order, which is import order (stable after autodiscovery).
    """

    def __init__(self) -> None:
        self._rules: List[Rule] = []

    def add(self, rule: Rule) -> None:
        """Register a rule. Duplicate names are silently overwritten."""
        # Remove any existing rule with the same name (idempotent re-import)
        self._rules = [r for r in self._rules if r.name != rule.name]
        self._rules.append(rule)

    @property
    def hard_rules(self) -> List[Rule]:
        """All registered hard rules, in registration order."""
        return [r for r in self._rules if r.kind == "hard"]

    @property
    def soft_rules(self) -> List[Rule]:
        """All registered soft rules, in registration order."""
        return [r for r in self._rules if r.kind == "soft"]

    @property
    def all_rules(self) -> List[Rule]:
        """All rules, hard first then soft."""
        return self.hard_rules + self.soft_rules


# ---------------------------------------------------------------------------
# Module-level singleton registry + decorator
# ---------------------------------------------------------------------------

_registry = RuleRegistry()


def get_registry() -> RuleRegistry:
    """Return the global rule registry (populated after autodiscovery)."""
    return _registry


def register(rule_instance: Rule) -> Rule:
    """
    Decorator / function that registers a Rule instance in the global registry.

    Usage (as decorator on a class, instantiating with defaults):
        @register
        class MyRule(Rule):
            ...

    Or as a function call:
        register(MyRule())

    Returns the rule instance unchanged so the rule class can still be imported
    and used directly in tests.
    """
    if isinstance(rule_instance, type):
        # Called as a class decorator — instantiate with no args
        instance = rule_instance()
        _registry.add(instance)
        return rule_instance  # return the class so it's still usable
    _registry.add(rule_instance)
    return rule_instance
