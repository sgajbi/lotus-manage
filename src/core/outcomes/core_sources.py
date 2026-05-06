"""Source-owned lotus-core realized evidence adapters for RFC-0042."""

from decimal import Decimal, InvalidOperation
from typing import Any, Literal, TypedDict

from src.core.outcomes.models import OutcomeDimension
from src.core.outcomes.models import DpmRealizedSourceSnapshot

TransactionLedgerOutcomeMeasure = Literal[
    "trade_fee",
    "withholding_tax_amount",
    "realized_fx_pnl",
    "cashflow_amount",
]
CashflowProjectionOutcomeMeasure = Literal["total_net_cashflow"]


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


def realized_transaction_source_from_transaction_ledger_response(
    response: dict[str, Any],
    *,
    transaction_id: str,
    measure: TransactionLedgerOutcomeMeasure,
) -> DpmRealizedSourceSnapshot:
    """Adapt a lotus-core transaction row without aggregating ledger truth locally."""

    metadata = _core_metadata(response)
    portfolio_id = _read_required_text(response.get("portfolio_id"), "portfolio_id")
    transaction = _find_transaction(response=response, transaction_id=transaction_id)
    if not transaction:
        raise CoreOutcomeSourceError(
            f"lotus-core transaction ledger response is missing transaction_id {transaction_id}"
        )

    value, unit, value_reason = _transaction_measure_value(
        response=response,
        transaction=transaction,
        measure=measure,
    )
    source_id = _source_id(
        product_name=metadata["product_name"],
        product_version=metadata["product_version"],
        portfolio_id=portfolio_id,
        as_of_date=metadata["as_of_date"],
        basis=f"transaction:{transaction_id}:{measure}",
        fingerprint=metadata["content_hash"],
    )
    return DpmRealizedSourceSnapshot(
        dimension=_transaction_dimension(measure),
        source_system="lotus-core",
        source_type="TRANSACTION_LEDGER_WINDOW",
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
            f"TRANSACTION_MEASURE_{measure.upper()}",
            f"TRANSACTION_ID_{transaction_id}",
            "TRANSACTION_TYPE_"
            f"{(_read_text(transaction.get('transaction_type')) or 'UNKNOWN').upper()}",
            value_reason,
            f"CORE_DATA_QUALITY_{metadata['data_quality_status'].upper()}",
        ],
    )


def realized_cashflow_projection_source_from_cashflow_projection_response(
    response: dict[str, Any],
    *,
    measure: CashflowProjectionOutcomeMeasure = "total_net_cashflow",
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-core cashflow projection output without forecasting locally."""

    metadata = _core_metadata(response)
    portfolio_id = _read_required_text(response.get("portfolio_id"), "portfolio_id")
    range_start_date = _read_required_text(response.get("range_start_date"), "range_start_date")
    range_end_date = _read_required_text(response.get("range_end_date"), "range_end_date")
    include_projected = response.get("include_projected")
    if not isinstance(include_projected, bool):
        raise CoreOutcomeSourceError(
            "lotus-core cashflow projection response is missing include_projected"
        )

    if measure != "total_net_cashflow":
        raise CoreOutcomeSourceError("cashflow projection measure must be 'total_net_cashflow'")

    total_net_cashflow = response.get("total_net_cashflow")
    if total_net_cashflow is None:
        raise CoreOutcomeSourceError(
            "lotus-core cashflow projection response is missing total_net_cashflow"
        )
    portfolio_currency = _read_required_text(
        response.get("portfolio_currency"),
        "portfolio_currency",
    )
    projection_basis = (
        f"cashflow_projection:{measure}:{range_start_date}:{range_end_date}:"
        f"include_projected={str(include_projected).lower()}"
    )
    source_id = _source_id(
        product_name=metadata["product_name"],
        product_version=metadata["product_version"],
        portfolio_id=portfolio_id,
        as_of_date=metadata["as_of_date"],
        basis=projection_basis,
        fingerprint=metadata["content_hash"],
    )
    return DpmRealizedSourceSnapshot(
        dimension="CASH_RESIDUAL",
        source_system="lotus-core",
        source_type="PORTFOLIO_CASHFLOW_PROJECTION",
        source_id=source_id,
        value=_decimal_value(total_net_cashflow),
        unit=portfolio_currency,
        source_state=_source_state(metadata["data_quality_status"]),
        quality=_source_quality(metadata["data_quality_status"]),
        observed_at=metadata["observed_at"],
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["content_hash"],
        reason_codes=[
            _primary_reason(metadata["data_quality_status"]),
            f"CORE_PRODUCT_{metadata['product_name'].upper()}",
            f"CORE_PRODUCT_VERSION_{metadata['product_version'].upper()}",
            f"CASHFLOW_PROJECTION_MEASURE_{measure.upper()}",
            f"CASHFLOW_PROJECTION_RANGE_{range_start_date}_TO_{range_end_date}",
            f"CASHFLOW_PROJECTION_INCLUDE_PROJECTED_{str(include_projected).upper()}",
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


def unavailable_core_cashflow_projection_source(
    *,
    source_id: str,
    reason_code: str,
    as_of_date: str | None = None,
) -> DpmRealizedSourceSnapshot:
    """Return bounded unavailable cashflow-projection evidence for source-owner gaps."""

    return DpmRealizedSourceSnapshot(
        dimension="CASH_RESIDUAL",
        source_system="lotus-core",
        source_type="PORTFOLIO_CASHFLOW_PROJECTION",
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


def _find_transaction(
    *,
    response: dict[str, Any],
    transaction_id: str,
) -> dict[str, Any]:
    transactions = response.get("transactions")
    if not isinstance(transactions, list):
        return {}
    for transaction in transactions:
        transaction_mapping = _read_mapping(transaction)
        if _read_text(transaction_mapping.get("transaction_id")) == transaction_id:
            return transaction_mapping
    return {}


def _transaction_measure_value(
    *,
    response: dict[str, Any],
    transaction: dict[str, Any],
    measure: TransactionLedgerOutcomeMeasure,
) -> tuple[Decimal, str, str]:
    if measure == "trade_fee":
        return _transaction_money_value(
            response=response,
            transaction=transaction,
            reporting_field="trade_fee_reporting_currency",
            source_field="trade_fee",
            source_currency_fields=("trade_currency", "currency"),
            reason="TRANSACTION_VALUE_TRADE_FEE",
        )
    if measure == "withholding_tax_amount":
        return _transaction_money_value(
            response=response,
            transaction=transaction,
            reporting_field="withholding_tax_amount_reporting_currency",
            source_field="withholding_tax_amount",
            source_currency_fields=("currency", "trade_currency"),
            reason="TRANSACTION_VALUE_WITHHOLDING_TAX",
        )
    if measure == "realized_fx_pnl":
        value = transaction.get("realized_fx_pnl_base")
        if value is not None:
            return (
                _decimal_value(value),
                _read_text(transaction.get("currency")) or "base_currency",
                "TRANSACTION_VALUE_REALIZED_FX_PNL_BASE",
            )
        local_value = transaction.get("realized_fx_pnl_local")
        if local_value is not None:
            return (
                _decimal_value(local_value),
                _read_text(transaction.get("trade_currency"))
                or _read_text(transaction.get("currency"))
                or "local_currency",
                "TRANSACTION_VALUE_REALIZED_FX_PNL_LOCAL",
            )
        raise CoreOutcomeSourceError(
            "lotus-core transaction ledger response is missing realized_fx_pnl"
        )

    cashflow = _read_mapping(transaction.get("cashflow"))
    cashflow_amount = cashflow.get("amount")
    if cashflow_amount is None:
        raise CoreOutcomeSourceError(
            "lotus-core transaction ledger response is missing cashflow.amount"
        )
    return (
        _decimal_value(cashflow_amount),
        _read_text(cashflow.get("currency")) or "cashflow_currency",
        "TRANSACTION_VALUE_CASHFLOW_AMOUNT",
    )


def _transaction_money_value(
    *,
    response: dict[str, Any],
    transaction: dict[str, Any],
    reporting_field: str,
    source_field: str,
    source_currency_fields: tuple[str, str],
    reason: str,
) -> tuple[Decimal, str, str]:
    reporting_value = transaction.get(reporting_field)
    reporting_currency = _read_text(response.get("reporting_currency"))
    if reporting_value is not None and reporting_currency is not None:
        return _decimal_value(reporting_value), reporting_currency, f"{reason}_REPORTING"

    source_value = transaction.get(source_field)
    if source_value is None:
        raise CoreOutcomeSourceError(
            f"lotus-core transaction ledger response is missing {source_field}"
        )
    first_currency_field, fallback_currency_field = source_currency_fields
    return (
        _decimal_value(source_value),
        _read_text(transaction.get(first_currency_field))
        or _read_text(transaction.get(fallback_currency_field))
        or "transaction_currency",
        f"{reason}_SOURCE",
    )


def _transaction_dimension(measure: TransactionLedgerOutcomeMeasure) -> OutcomeDimension:
    dimension_by_measure: dict[TransactionLedgerOutcomeMeasure, OutcomeDimension] = {
        "trade_fee": "COST",
        "withholding_tax_amount": "TAX",
        "realized_fx_pnl": "FX_RESIDUAL",
        "cashflow_amount": "CASH_RESIDUAL",
    }
    return dimension_by_measure[measure]


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
