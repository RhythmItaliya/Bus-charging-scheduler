from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Literal, Optional

from scheduler.logger import log


class ScheduleContext:

    def __init__(
        self,
        *,
        bus_id: str,
        plan: tuple,
        charge_events: list,
        all_committed: list,
        scenario: Any,
        weights: Any,
    ) -> None:
        self.bus_id = bus_id
        self.plan = plan
        self.charge_events = charge_events
        self.all_committed = all_committed
        self.scenario = scenario
        self.weights = weights


class Rule(ABC):


    name: str


    kind: Literal["hard", "soft"]


    weight_key: Optional[str] = None

    @abstractmethod
    def evaluate(self, ctx: ScheduleContext) -> float:
        ...


class RuleRegistry:

    def __init__(self) -> None:
        self._rules: List[Rule] = []

    def add(self, rule: Rule) -> None:

        self._rules = [r for r in self._rules if r.name != rule.name]
        self._rules.append(rule)
        log.debug("Rule registered", name=rule.name, kind=rule.kind)

    @property
    def hard_rules(self) -> List[Rule]:
        return [r for r in self._rules if r.kind == "hard"]

    @property
    def soft_rules(self) -> List[Rule]:
        return [r for r in self._rules if r.kind == "soft"]

    @property
    def all_rules(self) -> List[Rule]:
        return self.hard_rules + self.soft_rules


_registry = RuleRegistry()


def get_registry() -> RuleRegistry:
    hard = len(_registry.hard_rules)
    soft = len(_registry.soft_rules)
    log.debug("Rule registry ready", hard_rules=hard, soft_rules=soft, total=hard + soft)
    return _registry


def register(rule_instance: Rule) -> Rule:
    if isinstance(rule_instance, type):

        instance = rule_instance()
        _registry.add(instance)
        return rule_instance
    _registry.add(rule_instance)
    return rule_instance
