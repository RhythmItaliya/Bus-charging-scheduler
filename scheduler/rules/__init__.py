import importlib

from scheduler.rules.registry import RuleRegistry, get_registry, register


importlib.import_module("scheduler.rules._discover")

__all__ = ["RuleRegistry", "register", "get_registry"]
