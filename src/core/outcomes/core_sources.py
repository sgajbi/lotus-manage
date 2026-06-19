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


class CoreOutcomeSourceError(ValueError):
    """Raised when a lotus-core response cannot produce bounded outcome evidence."""


class _CoreSourceMetadata(TypedDict):
    product_name: str
    product_version: str
    as_of_date: str
    observed_at: str | None
    data_quality_status: str
    content_hash: str | None


class _ExecutionAcknowledgementPosture(TypedDict):
    acknowledgement_count: int
    supportability_state: str
    supportability_reason: str
    execution_intent_id: str
    order_reference_ids: list[str]
    missing_data_families: list[str]
    blocked_capabilities: list[str]


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


def realized_execution_acknowledgement_source_from_response(
    response: dict[str, Any],
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-core OMS acknowledgement posture without claiming execution support."""

    metadata = _core_metadata(response)
    portfolio_id = _read_required_text(response.get("portfolio_id"), "portfolio_id")
    posture = _execution_acknowledgement_posture(response, metadata=metadata)
    source_state, quality = _execution_acknowledgement_state_quality(
        posture["supportability_state"]
    )
    return DpmRealizedSourceSnapshot(
        dimension="EXECUTION_QUALITY",
        source_system="lotus-core",
        source_type="EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT",
        source_id=_execution_acknowledgement_source_id(
            metadata=metadata,
            portfolio_id=portfolio_id,
            posture=posture,
        ),
        value=Decimal(posture["acknowledgement_count"]),
        unit="acknowledgements",
        source_state=source_state,
        quality=quality,
        observed_at=metadata["observed_at"],
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["content_hash"],
        reason_codes=_execution_acknowledgement_reason_codes(
            metadata=metadata,
            posture=posture,
        ),
    )


def _execution_acknowledgement_posture(
    response: dict[str, Any],
    *,
    metadata: _CoreSourceMetadata,
) -> _ExecutionAcknowledgementPosture:
    supportability = _read_mapping(response.get("supportability"))
    return {
        "acknowledgement_count": _read_int(
            supportability.get("acknowledgement_count"),
            "supportability.acknowledgement_count",
        ),
        "supportability_state": (
            _read_text(supportability.get("state")) or metadata["data_quality_status"]
        ).upper(),
        "supportability_reason": (
            _read_text(supportability.get("reason")) or "EXTERNAL_OMS_ACKNOWLEDGEMENT_UNAVAILABLE"
        ),
        "execution_intent_id": _read_text(response.get("execution_intent_id")) or "none",
        "order_reference_ids": _read_text_list(response.get("order_reference_ids")),
        "missing_data_families": _read_text_list(supportability.get("missing_data_families")),
        "blocked_capabilities": _read_text_list(supportability.get("blocked_capabilities")),
    }


def _execution_acknowledgement_source_id(
    *,
    metadata: _CoreSourceMetadata,
    portfolio_id: str,
    posture: _ExecutionAcknowledgementPosture,
) -> str:
    order_basis = (
        ",".join(posture["order_reference_ids"]) if posture["order_reference_ids"] else "none"
    )
    return _source_id(
        product_name=metadata["product_name"],
        product_version=metadata["product_version"],
        portfolio_id=portfolio_id,
        as_of_date=metadata["as_of_date"],
        basis=(
            "external_order_execution_acknowledgement:"
            f"execution_intent={posture['execution_intent_id']}:orders={order_basis}"
        ),
        fingerprint=metadata["content_hash"],
    )


def _execution_acknowledgement_state_quality(
    supportability_state: str,
) -> tuple[Literal["BLOCKED", "DEGRADED"], Literal["MISSING", "UNAVAILABLE"]]:
    if supportability_state == "UNAVAILABLE":
        return "BLOCKED", "MISSING"
    return "DEGRADED", "UNAVAILABLE"


def _execution_acknowledgement_reason_codes(
    *,
    metadata: _CoreSourceMetadata,
    posture: _ExecutionAcknowledgementPosture,
) -> list[str]:
    return [
        "CORE_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
        f"CORE_PRODUCT_{metadata['product_name'].upper()}",
        f"CORE_PRODUCT_VERSION_{metadata['product_version'].upper()}",
        f"EXECUTION_ACKNOWLEDGEMENT_SUPPORTABILITY_{posture['supportability_state']}",
        posture["supportability_reason"],
        f"EXECUTION_ACKNOWLEDGEMENT_COUNT_{posture['acknowledgement_count']}",
        *_prefixed_reason_codes(
            "EXECUTION_ACKNOWLEDGEMENT_MISSING_DATA",
            posture["missing_data_families"],
        ),
        *_prefixed_reason_codes(
            "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY",
            posture["blocked_capabilities"],
        ),
        f"CORE_DATA_QUALITY_{metadata['data_quality_status'].upper()}",
    ]


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
