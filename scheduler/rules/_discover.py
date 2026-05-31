"""
scheduler/rules/_discover.py — Autodiscovery import trigger.

Importing this module imports all rule submodules in the rules/ package so
that every @register-decorated rule is added to the global registry.

This is the mechanism that satisfies "drop a file in rules/ → engine picks it
up automatically" (docs/02-scheduler-engine/05-rule-framework.md).

Do not import concrete rule classes directly in engine or objective code —
always consume via get_registry() so new rules are picked up automatically.
"""

import importlib
import pkgutil

import scheduler.rules as _pkg

# Dynamically import every non-private, non-registry module in this package.
# Each module's @register decorators fire on import, populating the registry.
# "Drop a file with @register" → this loop picks it up — zero engine changes.
_SKIP = {"registry", "_discover"}

for _info in pkgutil.iter_modules(_pkg.__path__):
    if _info.name.startswith("_"):
        continue  # skip __init__ and this file
    if _info.name in _SKIP:
        continue
    importlib.import_module(f"scheduler.rules.{_info.name}")
