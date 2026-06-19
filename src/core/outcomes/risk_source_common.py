"""Shared primitives for source-owned lotus-risk outcome adapters."""

from decimal import Decimal, InvalidOperation
from typing import Any, Literal

_RiskSourceState = Literal["READY", "DEGRADED", "BLOCKED", "NOT_SUPPORTED"]
_RiskSourceQuality = Literal[
    "COMPLETE",
    "STALE",
    "UNAVAILABLE",
    "PARTIAL",
    "MISSING",
    "NOT_SUPPORTED",
]
_RiskSourcePosture = tuple[_RiskSourceState, _RiskSourceQuality]


class RiskOutcomeSourceError(ValueError):
    """Raised when a lotus-risk response cannot produce bounded outcome evidence."""


def _supportability(metadata: dict[str, Any]) -> tuple[str, str]:
    supportability = _read_mapping(metadata.get("calculation_supportability"))
    return (
        _read_text(supportability.get("state")) or "ready",
        _read_text(supportability.get("reason")) or "calculation_complete",
    )


def _supportability_source_posture(
    supportability_state: str, *, include_stale: bool = True
) -> _RiskSourcePosture | None:
    if supportability_state == "unsupported":
        return "NOT_SUPPORTED", "NOT_SUPPORTED"
    if supportability_state == "permission_blocked":
        return "BLOCKED", "MISSING"
    if include_stale and supportability_state == "stale":
        return "DEGRADED", "STALE"
    return None


def _quality_for_degraded_value(value: Decimal | None) -> _RiskSourceQuality:
    return "PARTIAL" if value is not None else "UNAVAILABLE"


def _risk_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
) -> _RiskSourcePosture:
    supportability_posture = _supportability_source_posture(supportability_state)
    if supportability_posture is not None:
        return supportability_posture
    if supportability_state != "ready":
        return "DEGRADED", _quality_for_degraded_value(value)
    return "READY", "COMPLETE"


def _primary_reason(source_state: str) -> str:
    if source_state == "READY":
        return "RISK_SOURCE_READY"
    if source_state == "NOT_SUPPORTED":
        return "RISK_SOURCE_NOT_SUPPORTED"
    if source_state == "BLOCKED":
        return "RISK_SOURCE_BLOCKED"
    return "RISK_SOURCE_DEGRADED"


def _read_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _read_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise RiskOutcomeSourceError(
            "lotus-risk metrics report contains a non-numeric risk metric value"
        ) from exc
