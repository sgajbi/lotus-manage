import logging
from typing import Any, TypeVar

T = TypeVar("T")


def resolve_main_override(name: str) -> Any | None:
    try:
        from src.api import main as main_module
    except ImportError:
        return None
    return getattr(main_module, name, None)


def resolve_callable_override(name: str, default: T) -> T:
    override = resolve_main_override(name)
    return override or default


def resolve_logger(default: logging.Logger) -> logging.Logger | Any:
    return resolve_main_override("logger") or default


__all__ = [
    "resolve_callable_override",
    "resolve_logger",
    "resolve_main_override",
]
