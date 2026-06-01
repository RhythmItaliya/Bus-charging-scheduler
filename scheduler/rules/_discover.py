import importlib
import pkgutil

import scheduler.rules as _pkg


_SKIP = {"registry", "_discover"}

for _info in pkgutil.iter_modules(_pkg.__path__):
    if _info.name.startswith("_"):
        continue
    if _info.name in _SKIP:
        continue
    importlib.import_module(f"scheduler.rules.{_info.name}")
