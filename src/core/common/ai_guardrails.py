"""Shared guardrails for AI evidence handoff payloads."""

from __future__ import annotations

from typing import Any

AI_FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "account_number",
        "client_name",
        "client_id",
        "email",
        "phone",
        "raw_payload",
        "raw_request",
        "raw_response",
        "secret",
        "ssn",
        "token",
    }
)


def sanitize_for_ai(value: Any, removed: set[str]) -> Any:
    if isinstance(value, dict):
        return _sanitize_mapping_for_ai(value=value, removed=removed)
    if isinstance(value, list):
        return [sanitize_for_ai(item, removed) for item in value]
    return value


def _sanitize_mapping_for_ai(*, value: dict[Any, Any], removed: set[str]) -> dict[Any, Any]:
    sanitized: dict[Any, Any] = {}
    for key, item in value.items():
        if _is_forbidden_field_name(key):
            removed.add(str(key).lower())
            continue
        sanitized[key] = sanitize_for_ai(item, removed)
    return sanitized


def forbidden_field_names(value: Any) -> set[str]:
    if isinstance(value, dict):
        return _forbidden_mapping_field_names(value)
    if isinstance(value, list):
        return _forbidden_list_field_names(value)
    return set()


def _forbidden_mapping_field_names(value: dict[Any, Any]) -> set[str]:
    found: set[str] = set()
    for key, item in value.items():
        if _is_forbidden_field_name(key):
            found.add(str(key).lower())
        found.update(forbidden_field_names(item))
    return found


def _forbidden_list_field_names(value: list[Any]) -> set[str]:
    found: set[str] = set()
    for item in value:
        found.update(forbidden_field_names(item))
    return found


def _is_forbidden_field_name(key: Any) -> bool:
    return isinstance(key, str) and key.lower() in AI_FORBIDDEN_FIELD_NAMES
