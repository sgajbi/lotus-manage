from __future__ import annotations

import importlib
from collections.abc import Iterable


def register_route_modules(module_names: Iterable[str]) -> None:
    for module_name in module_names:
        importlib.import_module(module_name)
