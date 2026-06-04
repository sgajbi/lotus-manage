import os

from src.api.services.service_config import env_flag as _env_flag


def env_flag(name: str, default: bool) -> bool:
    return _env_flag(name, default)


def resolve_async_execution_mode() -> str:
    value = os.getenv("DPM_ASYNC_EXECUTION_MODE", "INLINE")
    normalized = value.strip().upper()
    if normalized in {"INLINE", "ACCEPT_ONLY"}:
        return normalized
    return "INLINE"


def async_operations_enabled() -> bool:
    return env_flag("DPM_ASYNC_OPERATIONS_ENABLED", True)


def async_manual_execution_enabled() -> bool:
    return env_flag("DPM_ASYNC_MANUAL_EXECUTION_ENABLED", True)


__all__ = [
    "async_manual_execution_enabled",
    "async_operations_enabled",
    "env_flag",
    "resolve_async_execution_mode",
]
