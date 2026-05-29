"""
scheduler/rules/_discover.py — Autodiscovery import trigger.

Importing this module imports all rule submodules in the rules/ package so
that every @register-decorated rule is added to the global registry.

This is the mechanism that satisfies "drop a file in rules/ → engine picks it
up automatically" (docs/02-scheduler-engine/05-rule-framework.md).

Do not import concrete rule classes directly in engine or objective code —
always consume via get_registry() so new rules are picked up automatically.
"""

# Order matters only cosmetically; hard rules imported before soft rules so
# they appear first in registry.all_rules output.
from scheduler.rules import hard_rules  # noqa: F401
from scheduler.rules import soft_rules  # noqa: F401

# Future rule modules: just add an import here, OR rely on the dynamic scanner
# below which auto-imports any module in this directory.

import importlib
import pkgutil
import scheduler.rules as _pkg

for _info in pkgutil.iter_modules(_pkg.__path__):
    if _info.name.startswith("_"):
        continue  # skip __init__, _discover, registry itself
    if _info.name in ("registry", "hard_rules", "soft_rules"):
        continue  # already imported
    importlib.import_module(f"scheduler.rules.{_info.name}")
