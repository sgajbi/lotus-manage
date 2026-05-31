from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import Any


def register_route_modules(module_names: Iterable[str]) -> None:
    for module_name in module_names:
        importlib.import_module(module_name)


def load_route_callable(module_name: str, callable_name: str) -> Any:
    return getattr(importlib.import_module(module_name), callable_name)
