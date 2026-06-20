"""Shared lotus-core outcome source parsing helpers."""

from decimal import Decimal, InvalidOperation
from typing import Any, Literal, TypedDict


class CoreOutcomeSourceError(ValueError):
    """Raised when a lotus-core response cannot produce bounded outcome evidence."""


class _CoreSourceMetadata(TypedDict):
    product_name: str
    product_version: str
    as_of_date: str
    observed_at: str | None
    data_quality_status: str
    content_hash: str | None


def _core_metadata(response: dict[str, Any]) -> _CoreSourceMetadata:
    return {
        "product_name": _core_product_name(response),
        "product_version": _core_product_version(response),
        "as_of_date": _core_as_of_date(response),
        "observed_at": _core_observed_at(response),
        "data_quality_status": _core_data_quality_status(response),
        "content_hash": _core_content_hash(response),
    }


def _core_product_name(response: dict[str, Any]) -> str:
    return _read_required_text(response.get("product_name"), "product_name")


def _core_product_version(response: dict[str, Any]) -> str:
    return _read_required_text(response.get("product_version"), "product_version")


def _core_as_of_date(response: dict[str, Any]) -> str:
    return _read_required_text(
        response.get("as_of_date") or response.get("resolved_as_of_date"),
        "as_of_date",
    )


def _core_observed_at(response: dict[str, Any]) -> str | None:
    latest_evidence = _read_text(response.get("latest_evidence_timestamp"))
    generated_at = _read_text(response.get("generated_at"))
    return latest_evidence or generated_at


def _core_data_quality_status(response: dict[str, Any]) -> str:
    return (_read_text(response.get("data_quality_status")) or "UNKNOWN").upper()


def _core_content_hash(response: dict[str, Any]) -> str | None:
    return (
        _read_text(response.get("source_batch_fingerprint"))
        or _read_text(response.get("snapshot_id"))
        or _read_text(response.get("correlation_id"))
    )


def _source_id(
    *,
    product_name: str,
    product_version: str,
    portfolio_id: str,
    as_of_date: str,
    basis: str,
    fingerprint: str | None,
) -> str:
    suffix = fingerprint or "no-source-fingerprint"
    return f"{product_name}:{product_version}:{portfolio_id}:{as_of_date}:{basis}:{suffix}"


def _source_state(data_quality_status: str) -> Literal["READY", "DEGRADED"]:
    if data_quality_status in {"COMPLETE", "READY", "OK"}:
        return "READY"
    if data_quality_status in {"UNAVAILABLE", "ERROR"}:
        return "DEGRADED"
    return "DEGRADED"


def _source_quality(
    data_quality_status: str,
) -> Literal["COMPLETE", "STALE", "PARTIAL", "UNAVAILABLE"]:
    if data_quality_status in {"COMPLETE", "READY", "OK"}:
        return "COMPLETE"
    if data_quality_status in {"STALE"}:
        return "STALE"
    if data_quality_status in {"PARTIAL", "INCOMPLETE"}:
        return "PARTIAL"
    return "UNAVAILABLE"


def _primary_reason(data_quality_status: str) -> str:
    if data_quality_status in {"COMPLETE", "READY", "OK"}:
        return "CORE_SOURCE_READY"
    return "CORE_SOURCE_DEGRADED"


def _read_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _read_required_text(value: Any, field_name: str) -> str:
    text = _read_text(value)
    if text is None:
        raise CoreOutcomeSourceError(f"lotus-core cash response is missing {field_name}")
    return text


def _read_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _read_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise CoreOutcomeSourceError(f"lotus-core response contains non-integer {field_name}")
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise CoreOutcomeSourceError(
            f"lotus-core response contains non-integer {field_name}"
        ) from exc
    if parsed < 0:
        raise CoreOutcomeSourceError(f"lotus-core response contains negative {field_name}")
    return parsed


def _prefixed_reason_codes(prefix: str, values: list[str]) -> list[str]:
    return [f"{prefix}_{value.upper()}" for value in values]


def _decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise CoreOutcomeSourceError(
            "lotus-core cash response contains a non-numeric cash balance total"
        ) from exc
