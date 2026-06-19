"""Source-owned lotus-core realized evidence adapters for RFC-0042."""

from decimal import Decimal
from typing import Any, Literal

from src.core.outcomes.core_source_common import (
    CoreOutcomeSourceError,
    _core_as_of_date,
    _core_content_hash,
    _core_data_quality_status,
    _core_metadata,
    _core_observed_at,
    _decimal_value,
    _prefixed_reason_codes,
    _primary_reason,
    _read_int,
    _read_mapping,
    _read_required_text,
    _read_text,
    _read_text_list,
    _source_id,
    _source_quality,
    _source_state,
)
from src.core.outcomes.core_source_execution import (
    _execution_acknowledgement_posture,
    _execution_acknowledgement_reason_codes,
    _execution_acknowledgement_source_id,
    _execution_acknowledgement_state_quality,
    realized_execution_acknowledgement_source_from_response,
)
from src.core.outcomes.models import OutcomeDimension
from src.core.outcomes.models import DpmRealizedSourceSnapshot

TransactionLedgerOutcomeMeasure = Literal[
    "trade_fee",
    "withholding_tax_amount",
    "realized_fx_pnl",
    "cashflow_amount",
]
CashflowProjectionOutcomeMeasure = Literal[
    "total_net_cashflow",
    "booked_total_net_cashflow",
    "projected_settlement_total_cashflow",
]
RealizedTaxSummaryOutcomeMeasure = Literal[
    "total_tax_amount",
    "withholding_tax_amount",
    "other_tax_deductions_amount",
    "reporting_currency_total_tax_amount",
]

__all__ = [
    "CoreOutcomeSourceError",
    "realized_cash_source_from_cash_balances_response",
    "realized_transaction_source_from_transaction_ledger_response",
    "realized_cashflow_projection_source_from_cashflow_projection_response",
    "realized_tax_summary_source_from_realized_tax_summary_response",
    "realized_cash_movement_source_from_cash_movement_summary_response",
    "realized_execution_acknowledgement_source_from_response",
    "unavailable_core_cash_source",
    "unavailable_core_cashflow_projection_source",
    "_cash_movement_bucket_matches",
    "_cash_movement_buckets",
    "_core_as_of_date",
    "_core_content_hash",
    "_core_data_quality_status",
    "_core_metadata",
    "_core_observed_at",
    "_currency_total_matches",
    "_currency_total_rows",
    "_execution_acknowledgement_posture",
    "_execution_acknowledgement_reason_codes",
    "_execution_acknowledgement_source_id",
    "_execution_acknowledgement_state_quality",
    "_normalized_currency_filter",
    "_raise_on_invalid_currency_total_selection",
    "_transaction_cashflow_value",
    "_transaction_fx_pnl_value",
    "_transaction_reporting_money",
    "_transaction_source_currency",
]


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

    selected_cashflow = response.get(measure)
    if selected_cashflow is None:
        raise CoreOutcomeSourceError(
            f"lotus-core cashflow projection response is missing {measure}"
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
        value=_decimal_value(selected_cashflow),
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


def realized_tax_summary_source_from_realized_tax_summary_response(
    response: dict[str, Any],
    *,
    measure: RealizedTaxSummaryOutcomeMeasure = "total_tax_amount",
    currency: str | None = None,
) -> DpmRealizedSourceSnapshot:
    """Adapt source-owned portfolio realized-tax totals without tax methodology locally."""

    metadata = _core_metadata(response)
    portfolio_id = _read_required_text(response.get("portfolio_id"), "portfolio_id")
    source_transaction_count = _read_int(
        response.get("source_transaction_count"),
        "source_transaction_count",
    )
    tax_evidence_transaction_count = _read_int(
        response.get("tax_evidence_transaction_count"),
        "tax_evidence_transaction_count",
    )

    if measure == "reporting_currency_total_tax_amount":
        value = response.get("reporting_currency_total_tax_amount")
        if value is None:
            raise CoreOutcomeSourceError(
                "lotus-core realized-tax summary response is missing "
                "reporting_currency_total_tax_amount"
            )
        selected_currency = _read_required_text(
            response.get("reporting_currency"), "reporting_currency"
        )
    else:
        currency_total = _select_currency_total(
            response=response,
            currency=currency,
        )
        value = currency_total.get(measure)
        if value is None:
            raise CoreOutcomeSourceError(
                f"lotus-core realized-tax summary response is missing {measure}"
            )
        selected_currency = _read_required_text(currency_total.get("currency"), "currency")

    source_id = _source_id(
        product_name=metadata["product_name"],
        product_version=metadata["product_version"],
        portfolio_id=portfolio_id,
        as_of_date=metadata["as_of_date"],
        basis=f"realized_tax_summary:{measure}:{selected_currency}",
        fingerprint=metadata["content_hash"],
    )
    return DpmRealizedSourceSnapshot(
        dimension="TAX",
        source_system="lotus-core",
        source_type="PORTFOLIO_REALIZED_TAX_SUMMARY",
        source_id=source_id,
        value=_decimal_value(value),
        unit=selected_currency,
        source_state=_source_state(metadata["data_quality_status"]),
        quality=_source_quality(metadata["data_quality_status"]),
        observed_at=metadata["observed_at"],
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["content_hash"],
        reason_codes=[
            _primary_reason(metadata["data_quality_status"]),
            f"CORE_PRODUCT_{metadata['product_name'].upper()}",
            f"CORE_PRODUCT_VERSION_{metadata['product_version'].upper()}",
            f"REALIZED_TAX_SUMMARY_MEASURE_{measure.upper()}",
            f"REALIZED_TAX_SUMMARY_CURRENCY_{selected_currency.upper()}",
            f"REALIZED_TAX_SOURCE_TRANSACTION_COUNT_{source_transaction_count}",
            f"REALIZED_TAX_EVIDENCE_TRANSACTION_COUNT_{tax_evidence_transaction_count}",
            *_prefixed_reason_codes(
                "REALIZED_TAX_SOURCE_REASON",
                _read_text_list(response.get("reason_codes")),
            ),
            f"CORE_DATA_QUALITY_{metadata['data_quality_status'].upper()}",
        ],
    )


def realized_cash_movement_source_from_cash_movement_summary_response(
    response: dict[str, Any],
    *,
    classification: str,
    timing: str,
    currency: str,
    is_position_flow: bool,
    is_portfolio_flow: bool,
) -> DpmRealizedSourceSnapshot:
    """Adapt a source-owned cash movement bucket without forecasting or local aggregation."""

    metadata = _core_metadata(response)
    portfolio_id = _read_required_text(response.get("portfolio_id"), "portfolio_id")
    bucket = _find_cash_movement_bucket(
        response=response,
        classification=classification,
        timing=timing,
        currency=currency,
        is_position_flow=is_position_flow,
        is_portfolio_flow=is_portfolio_flow,
    )
    if not bucket:
        raise CoreOutcomeSourceError(
            "lotus-core cash movement summary response is missing requested bucket"
        )

    bucket_cashflow_count = _read_int(bucket.get("cashflow_count"), "bucket.cashflow_count")
    total_cashflow_count = _read_int(response.get("cashflow_count"), "cashflow_count")
    movement_direction = _read_required_text(bucket.get("movement_direction"), "movement_direction")
    start_date = _read_required_text(response.get("start_date"), "start_date")
    end_date = _read_required_text(response.get("end_date"), "end_date")
    selected_currency = _read_required_text(bucket.get("currency"), "bucket.currency")
    source_id = _source_id(
        product_name=metadata["product_name"],
        product_version=metadata["product_version"],
        portfolio_id=portfolio_id,
        as_of_date=metadata["as_of_date"],
        basis=(
            "cash_movement_summary:"
            f"{classification}:{timing}:{selected_currency}:"
            f"position_flow={str(is_position_flow).lower()}:"
            f"portfolio_flow={str(is_portfolio_flow).lower()}"
        ),
        fingerprint=metadata["content_hash"],
    )
    return DpmRealizedSourceSnapshot(
        dimension="CASH_RESIDUAL",
        source_system="lotus-core",
        source_type="PORTFOLIO_CASH_MOVEMENT_SUMMARY",
        source_id=source_id,
        value=_decimal_value(bucket.get("total_amount")),
        unit=selected_currency,
        source_state=_source_state(metadata["data_quality_status"]),
        quality=_source_quality(metadata["data_quality_status"]),
        observed_at=metadata["observed_at"],
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["content_hash"],
        reason_codes=[
            _primary_reason(metadata["data_quality_status"]),
            f"CORE_PRODUCT_{metadata['product_name'].upper()}",
            f"CORE_PRODUCT_VERSION_{metadata['product_version'].upper()}",
            f"CASH_MOVEMENT_CLASSIFICATION_{classification.upper()}",
            f"CASH_MOVEMENT_TIMING_{timing.upper()}",
            f"CASH_MOVEMENT_CURRENCY_{selected_currency.upper()}",
            f"CASH_MOVEMENT_POSITION_FLOW_{str(is_position_flow).upper()}",
            f"CASH_MOVEMENT_PORTFOLIO_FLOW_{str(is_portfolio_flow).upper()}",
            f"CASH_MOVEMENT_DIRECTION_{movement_direction.upper()}",
            f"CASH_MOVEMENT_BUCKET_CASHFLOW_COUNT_{bucket_cashflow_count}",
            f"CASH_MOVEMENT_TOTAL_CASHFLOW_COUNT_{total_cashflow_count}",
            f"CASH_MOVEMENT_RANGE_{start_date}_TO_{end_date}",
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


def _select_currency_total(
    *,
    response: dict[str, Any],
    currency: str | None,
) -> dict[str, Any]:
    normalized_currency = _normalized_currency_filter(currency)
    matches = [
        total
        for total in _currency_total_rows(response)
        if _currency_total_matches(total, normalized_currency)
    ]
    _raise_on_invalid_currency_total_selection(
        matches=matches,
        normalized_currency=normalized_currency,
        requested_currency=currency,
    )
    return matches[0]


def _normalized_currency_filter(currency: str | None) -> str | None:
    return currency.upper() if isinstance(currency, str) else None


def _currency_total_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    totals = response.get("currency_totals")
    if not isinstance(totals, list) or not totals:
        raise CoreOutcomeSourceError(
            "lotus-core realized-tax summary response is missing currency_totals"
        )
    return [_read_mapping(total) for total in totals]


def _currency_total_matches(
    total: dict[str, Any],
    normalized_currency: str | None,
) -> bool:
    if normalized_currency is None:
        return True
    return (_read_text(total.get("currency")) or "").upper() == normalized_currency


def _raise_on_invalid_currency_total_selection(
    *,
    matches: list[dict[str, Any]],
    normalized_currency: str | None,
    requested_currency: str | None,
) -> None:
    if not matches:
        raise CoreOutcomeSourceError(
            f"lotus-core realized-tax summary response is missing currency {requested_currency}"
        )
    if normalized_currency is None and len(matches) != 1:
        raise CoreOutcomeSourceError(
            "lotus-core realized-tax summary response has multiple currencies; "
            "currency must be supplied"
        )


def _find_cash_movement_bucket(
    *,
    response: dict[str, Any],
    classification: str,
    timing: str,
    currency: str,
    is_position_flow: bool,
    is_portfolio_flow: bool,
) -> dict[str, Any]:
    for bucket in _cash_movement_buckets(response):
        bucket_mapping = _read_mapping(bucket)
        if _cash_movement_bucket_matches(
            bucket=bucket_mapping,
            classification=classification,
            timing=timing,
            currency=currency,
            is_position_flow=is_position_flow,
            is_portfolio_flow=is_portfolio_flow,
        ):
            return bucket_mapping
    return {}


def _cash_movement_buckets(response: dict[str, Any]) -> list[Any]:
    buckets = response.get("buckets")
    if not isinstance(buckets, list):
        return []
    return buckets


def _cash_movement_bucket_matches(
    *,
    bucket: dict[str, Any],
    classification: str,
    timing: str,
    currency: str,
    is_position_flow: bool,
    is_portfolio_flow: bool,
) -> bool:
    return (
        _cash_movement_bucket_text(bucket, "classification") == classification.upper()
        and _cash_movement_bucket_text(bucket, "timing") == timing.upper()
        and _cash_movement_bucket_text(bucket, "currency") == currency.upper()
        and bucket.get("is_position_flow") is is_position_flow
        and bucket.get("is_portfolio_flow") is is_portfolio_flow
    )


def _cash_movement_bucket_text(bucket: dict[str, Any], field_name: str) -> str:
    return (_read_text(bucket.get(field_name)) or "").upper()


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
        return _transaction_fx_pnl_value(transaction=transaction)
    return _transaction_cashflow_value(transaction=transaction)


def _transaction_money_value(
    *,
    response: dict[str, Any],
    transaction: dict[str, Any],
    reporting_field: str,
    source_field: str,
    source_currency_fields: tuple[str, str],
    reason: str,
) -> tuple[Decimal, str, str]:
    reporting_money = _transaction_reporting_money(
        response=response,
        transaction=transaction,
        reporting_field=reporting_field,
        reason=reason,
    )
    if reporting_money is not None:
        return reporting_money

    source_value = transaction.get(source_field)
    if source_value is None:
        raise CoreOutcomeSourceError(
            f"lotus-core transaction ledger response is missing {source_field}"
        )
    return (
        _decimal_value(source_value),
        _transaction_source_currency(
            transaction=transaction,
            source_currency_fields=source_currency_fields,
            fallback_currency="transaction_currency",
        ),
        f"{reason}_SOURCE",
    )


def _transaction_reporting_money(
    *,
    response: dict[str, Any],
    transaction: dict[str, Any],
    reporting_field: str,
    reason: str,
) -> tuple[Decimal, str, str] | None:
    reporting_value = transaction.get(reporting_field)
    reporting_currency = _read_text(response.get("reporting_currency"))
    if reporting_value is None or reporting_currency is None:
        return None
    return _decimal_value(reporting_value), reporting_currency, f"{reason}_REPORTING"


def _transaction_source_currency(
    *,
    transaction: dict[str, Any],
    source_currency_fields: tuple[str, str],
    fallback_currency: str,
) -> str:
    first_currency_field, fallback_currency_field = source_currency_fields
    return (
        _read_text(transaction.get(first_currency_field))
        or _read_text(transaction.get(fallback_currency_field))
        or fallback_currency
    )


def _transaction_fx_pnl_value(*, transaction: dict[str, Any]) -> tuple[Decimal, str, str]:
    value = transaction.get("realized_fx_pnl_base")
    if value is not None:
        return (
            _decimal_value(value),
            _transaction_source_currency(
                transaction=transaction,
                source_currency_fields=("currency", "currency"),
                fallback_currency="base_currency",
            ),
            "TRANSACTION_VALUE_REALIZED_FX_PNL_BASE",
        )
    local_value = transaction.get("realized_fx_pnl_local")
    if local_value is not None:
        return (
            _decimal_value(local_value),
            _transaction_source_currency(
                transaction=transaction,
                source_currency_fields=("trade_currency", "currency"),
                fallback_currency="local_currency",
            ),
            "TRANSACTION_VALUE_REALIZED_FX_PNL_LOCAL",
        )
    raise CoreOutcomeSourceError(
        "lotus-core transaction ledger response is missing realized_fx_pnl"
    )


def _transaction_cashflow_value(*, transaction: dict[str, Any]) -> tuple[Decimal, str, str]:
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


def _transaction_dimension(measure: TransactionLedgerOutcomeMeasure) -> OutcomeDimension:
    dimension_by_measure: dict[TransactionLedgerOutcomeMeasure, OutcomeDimension] = {
        "trade_fee": "COST",
        "withholding_tax_amount": "TAX",
        "realized_fx_pnl": "FX_RESIDUAL",
        "cashflow_amount": "CASH_RESIDUAL",
    }
    return dimension_by_measure[measure]
