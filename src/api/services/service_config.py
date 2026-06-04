from __future__ import annotations

import os


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 1 else default


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = float(raw)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def env_non_negative_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def env_csv_set(name: str, default: set[str]) -> set[str]:
    value = os.getenv(name)
    if value is None:
        return set(default)
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed or set(default)


__all__ = [
    "env_flag",
    "env_csv_set",
    "env_float",
    "env_int",
    "env_non_negative_int",
]
