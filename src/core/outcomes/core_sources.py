"""Source-owned lotus-core realized evidence adapters for RFC-0042."""

from decimal import Decimal, InvalidOperation
from typing import Any, Literal, TypedDict

from src.core.outcomes.models import DpmRealizedSourceSnapshot


class CoreOutcomeSourceError(ValueError):
    """Raised when a lotus-core response cannot produce bounded outcome evidence."""


class _CoreSourceMetadata(TypedDict):
    product_name: str
    product_version: str
    as_of_date: str
    observed_at: str | None
    data_quality_status: str
    content_hash: str | None


def realized_cash_source_from_cash_balances_response(
    response: dict[str, Any],
    *,
    currency_basis: str = "reporting",
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-core cash balance totals without recalculating cash truth locally."""

    totals = _read_mapping(response.get("totals"))
    metadata = _core_metadata(response)
    if currency_basis == "portfolio":
        value = _decimal_value(totals.get("total_balance_portfolio_currency"))
        unit = _read_text(response.get("portfolio_currency")) or "portfolio_currency"
    elif currency_basis == "reporting":
        value = _decimal_value(totals.get("total_balance_reporting_currency"))
        unit = _read_text(response.get("reporting_currency")) or "reporting_currency"
    else:
        raise CoreOutcomeSourceError(
            "cash balance currency_basis must be 'portfolio' or 'reporting'"
        )

    source_id = _source_id(
        product_name=metadata["product_name"],
        product_version=metadata["product_version"],
        portfolio_id=_read_required_text(response.get("portfolio_id"), "portfolio_id"),
        as_of_date=metadata["as_of_date"],
        basis=currency_basis,
        fingerprint=metadata["content_hash"],
    )
    return DpmRealizedSourceSnapshot(
        dimension="CASH_RESIDUAL",
        source_system="lotus-core",
        source_type="HOLDINGS_AS_OF_CASH_BALANCE",
        source_id=source_id,
        value=value,
        unit=unit,
        source_state=_source_state(metadata["data_quality_status"]),
        quality=_source_quality(metadata["data_quality_status"]),
        observed_at=metadata["observed_at"],
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["content_hash"],
        reason_codes=[
            _primary_reason(metadata["data_quality_status"]),
            f"CORE_PRODUCT_{metadata['product_name'].upper()}",
            f"CORE_PRODUCT_VERSION_{metadata['product_version'].upper()}",
            f"CASH_BASIS_{currency_basis.upper()}",
            f"CORE_DATA_QUALITY_{metadata['data_quality_status'].upper()}",
        ],
    )


def unavailable_core_cash_source(
    *,
    source_id: str,
    reason_code: str,
    as_of_date: str | None = None,
) -> DpmRealizedSourceSnapshot:
    """Return bounded unavailable cash evidence when lotus-core cannot serve truth."""

    return DpmRealizedSourceSnapshot(
        dimension="CASH_RESIDUAL",
        source_system="lotus-core",
        source_type="HOLDINGS_AS_OF_CASH_BALANCE",
        source_id=source_id,
        value=None,
        unit="unknown",
        source_state="DEGRADED",
        quality="UNAVAILABLE",
        observed_at=None,
        as_of_date=as_of_date,
        content_hash=None,
        reason_codes=[reason_code],
    )


def _core_metadata(response: dict[str, Any]) -> _CoreSourceMetadata:
    product_name = _read_required_text(response.get("product_name"), "product_name")
    product_version = _read_required_text(response.get("product_version"), "product_version")
    as_of_date = _read_required_text(
        response.get("as_of_date") or response.get("resolved_as_of_date"),
        "as_of_date",
    )
    generated_at = _read_text(response.get("generated_at"))
    latest_evidence = _read_text(response.get("latest_evidence_timestamp"))
    data_quality_status = (_read_text(response.get("data_quality_status")) or "UNKNOWN").upper()
    content_hash = (
        _read_text(response.get("source_batch_fingerprint"))
        or _read_text(response.get("snapshot_id"))
        or _read_text(response.get("correlation_id"))
    )
    return {
        "product_name": product_name,
        "product_version": product_version,
        "as_of_date": as_of_date,
        "observed_at": latest_evidence or generated_at,
        "data_quality_status": data_quality_status,
        "content_hash": content_hash,
    }


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


def _decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise CoreOutcomeSourceError(
            "lotus-core cash response contains a non-numeric cash balance total"
        ) from exc
