"""
scheduler/rules/__init__.py — Rule registry package initialiser.

Importing this package triggers auto-discovery of all rule modules in this
directory, which self-register via the @register decorator.  The engine and
objective consume the registry generically and never reference a concrete rule
class by name — satisfying R24 (add a rule without rewriting the engine).

To add a new rule:
  1. Create a file in this directory (e.g. electricity.py).
  2. Define a Rule subclass decorated with @register.
  3. Nothing else. The engine picks it up automatically.

References:
    docs/02-scheduler-engine/05-rule-framework.md  (autodiscovery spec)
"""

from scheduler.rules.registry import RuleRegistry, register, get_registry  # noqa: F401

# Trigger auto-discovery AFTER registry is defined (avoids circular imports)
from scheduler.rules import _discover  # noqa: F401

__all__ = ["RuleRegistry", "register", "get_registry"]
