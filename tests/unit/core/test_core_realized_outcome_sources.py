import pytest

from src.core.outcomes import (
    CoreOutcomeSourceError,
    assemble_realized_outcome_snapshot,
    realized_cash_movement_source_from_cash_movement_summary_response,
    realized_cashflow_projection_source_from_cashflow_projection_response,
    realized_cash_source_from_cash_balances_response,
    realized_execution_acknowledgement_source_from_response,
    realized_tax_summary_source_from_realized_tax_summary_response,
    realized_transaction_source_from_transaction_ledger_response,
    unavailable_core_cashflow_projection_source,
    unavailable_core_cash_source,
)
from src.core.outcomes.core_sources import (
    _cash_movement_bucket_matches,
    _cash_movement_buckets,
    _transaction_cashflow_value,
    _transaction_fx_pnl_value,
)
from tests.unit.core.test_realized_outcome_sources import _window


def _cash_balances_response() -> dict[str, object]:
    return {
        "product_name": "HoldingsAsOf",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "portfolio_currency": "USD",
        "reporting_currency": "SGD",
        "resolved_as_of_date": "2026-05-06",
        "generated_at": "2026-05-06T01:12:00Z",
        "as_of_date": "2026-05-06",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-06T01:10:00Z",
        "source_batch_fingerprint": "sha256:holdings-as-of-cash",
        "snapshot_id": "pss_cash_001",
        "totals": {
            "cash_account_count": 2,
            "total_balance_portfolio_currency": "152500.25",
            "total_balance_reporting_currency": "205875.34",
        },
        "cash_accounts": [],
    }


def _transaction_ledger_response() -> dict[str, object]:
    return {
        "product_name": "TransactionLedgerWindow",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "reporting_currency": "SGD",
        "as_of_date": "2026-05-06",
        "generated_at": "2026-05-06T01:20:00Z",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-06T01:18:00Z",
        "source_batch_fingerprint": "sha256:transaction-ledger",
        "snapshot_id": "txn_window_001",
        "total": 2,
        "skip": 0,
        "limit": 50,
        "transactions": [
            {
                "transaction_id": "TXN-FX-001",
                "transaction_date": "2026-04-03T09:30:00Z",
                "settlement_date": "2026-04-05T00:00:00Z",
                "transaction_type": "FX_FORWARD",
                "instrument_id": "FX_EUR_USD",
                "security_id": "FX_EUR_USD",
                "quantity": "1000000",
                "price": "1.095",
                "gross_transaction_amount": "1095000",
                "trade_fee": "18.50",
                "trade_fee_reporting_currency": "24.98",
                "trade_currency": "USD",
                "currency": "USD",
                "withholding_tax_amount": None,
                "withholding_tax_amount_reporting_currency": None,
                "realized_fx_pnl_local": "1250.00",
                "realized_fx_pnl_base": "1250.00",
                "realized_total_pnl_local": "1250.00",
                "realized_total_pnl_base": "1250.00",
                "cashflow": {
                    "amount": "-1095000.00",
                    "currency": "USD",
                    "classification": "TRADE_SETTLEMENT",
                    "timing": "SETTLED",
                    "is_position_flow": True,
                    "is_portfolio_flow": False,
                    "calculation_type": "TRANSACTION_DERIVED",
                },
            },
            {
                "transaction_id": "TXN-INT-001",
                "transaction_date": "2026-04-10T09:30:00Z",
                "settlement_date": "2026-04-10T00:00:00Z",
                "transaction_type": "INTEREST",
                "instrument_id": "BOND_US_TSY_10Y",
                "security_id": "BOND_US_TSY_10Y",
                "quantity": "0",
                "price": "0",
                "gross_transaction_amount": "125.00",
                "trade_fee": None,
                "trade_currency": "USD",
                "currency": "USD",
                "withholding_tax_amount": "15.25",
                "withholding_tax_amount_reporting_currency": "20.59",
                "net_interest_amount": "109.75",
                "net_interest_amount_reporting_currency": "148.16",
                "cashflow": {
                    "amount": "109.75",
                    "currency": "USD",
                    "classification": "INCOME",
                    "timing": "SETTLED",
                    "is_position_flow": False,
                    "is_portfolio_flow": True,
                    "calculation_type": "TRANSACTION_DERIVED",
                },
            },
        ],
    }


def _cashflow_projection_response() -> dict[str, object]:
    return {
        "product_name": "PortfolioCashflowProjection",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-05-06",
        "range_start_date": "2026-05-06",
        "range_end_date": "2026-05-16",
        "include_projected": True,
        "portfolio_currency": "USD",
        "generated_at": "2026-05-06T02:00:00Z",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-06T01:58:00Z",
        "source_batch_fingerprint": (
            "cashflow_projection:PB_SG_GLOBAL_BAL_001:2026-05-06:2026-05-16:include_projected=true"
        ),
        "points": [
            {
                "projection_date": "2026-05-06",
                "booked_net_cashflow": "0",
                "projected_settlement_cashflow": "0",
                "net_cashflow": "0",
                "projected_cumulative_cashflow": "0",
            },
            {
                "projection_date": "2026-05-10",
                "booked_net_cashflow": "0",
                "projected_settlement_cashflow": "-25000.00",
                "net_cashflow": "-25000.00",
                "projected_cumulative_cashflow": "-25000.00",
            },
        ],
        "total_net_cashflow": "-25000.00",
        "booked_total_net_cashflow": "0",
        "projected_settlement_total_cashflow": "-25000.00",
        "projection_days": 10,
    }


def _realized_tax_summary_response() -> dict[str, object]:
    return {
        "product_name": "PortfolioRealizedTaxSummary",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "base_currency": "USD",
        "reporting_currency": "SGD",
        "as_of_date": "2026-05-06",
        "start_date": "2026-04-01",
        "end_date": "2026-05-06",
        "generated_at": "2026-05-06T02:15:00Z",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-06T02:14:00Z",
        "source_batch_fingerprint": "realized_tax_summary:PB_SG_GLOBAL_BAL_001:2026-05-06",
        "source_transaction_count": 28,
        "tax_evidence_transaction_count": 3,
        "currency_totals": [
            {
                "currency": "USD",
                "source_transaction_count": 3,
                "withholding_tax_amount": "125.50",
                "other_tax_deductions_amount": "12.75",
                "total_tax_amount": "138.25",
            }
        ],
        "reporting_currency_total_tax_amount": "188.02",
        "reason_codes": ["PORTFOLIO_REALIZED_TAX_SUMMARY_READY"],
    }


def _cash_movement_summary_response() -> dict[str, object]:
    return {
        "product_name": "PortfolioCashMovementSummary",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-05-06",
        "start_date": "2026-04-01",
        "end_date": "2026-05-06",
        "generated_at": "2026-05-06T02:30:00Z",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": "2026-05-06T02:28:00Z",
        "source_batch_fingerprint": "cash_movement_summary:PB_SG_GLOBAL_BAL_001:2026-04-01:2026-05-06",
        "cashflow_count": 3,
        "notes": (
            "Summary aggregates latest cashflow rows only; it is not a forecast, "
            "funding recommendation, treasury instruction, or OMS acknowledgement."
        ),
        "buckets": [
            {
                "classification": "CASHFLOW_IN",
                "timing": "SETTLED",
                "currency": "USD",
                "is_position_flow": False,
                "is_portfolio_flow": True,
                "cashflow_count": 2,
                "total_amount": "12500.00",
                "movement_direction": "INFLOW",
            },
            {
                "classification": "TRADE_SETTLEMENT",
                "timing": "SETTLED",
                "currency": "USD",
                "is_position_flow": True,
                "is_portfolio_flow": False,
                "cashflow_count": 1,
                "total_amount": "-3500.00",
                "movement_direction": "OUTFLOW",
            },
        ],
    }


def _external_order_execution_acknowledgement_response() -> dict[str, object]:
    return {
        "product_name": "ExternalOrderExecutionAcknowledgement",
        "product_version": "v1",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "client_id": "CIF_SG_000184",
        "mandate_id": "MANDATE_PB_SG_GLOBAL_BAL_001",
        "as_of_date": "2026-05-06",
        "execution_intent_id": "intent_rebalance_001",
        "order_reference_ids": ["ORD-001", "ORD-002"],
        "acknowledgements": [],
        "supportability": {
            "state": "UNAVAILABLE",
            "reason": "EXTERNAL_OMS_SOURCE_NOT_INGESTED",
            "acknowledgement_count": 0,
            "missing_data_families": ["external_oms_order_execution_acknowledgement"],
            "blocked_capabilities": [
                "order_generation",
                "venue_routing",
                "best_execution",
                "oms_acknowledgement",
                "fills",
                "settlement",
                "execution_status_certification",
                "autonomous_execution_action",
            ],
        },
        "lineage": {
            "source_system": "external-bank-oms",
            "integration_status": "not_ingested",
            "runtime_posture": "fail_closed",
        },
        "data_quality_status": "MISSING",
        "latest_evidence_timestamp": None,
        "source_batch_fingerprint": "sha256:external-order-execution-acknowledgement",
    }


def test_cash_balances_adapter_wraps_source_total_without_recalculation() -> None:
    source = realized_cash_source_from_cash_balances_response(_cash_balances_response())

    assert source.dimension == "CASH_RESIDUAL"
    assert source.source_system == "lotus-core"
    assert source.source_type == "HOLDINGS_AS_OF_CASH_BALANCE"
    assert source.source_id == (
        "HoldingsAsOf:v1:PB_SG_GLOBAL_BAL_001:2026-05-06:reporting:sha256:holdings-as-of-cash"
    )
    assert str(source.value) == "205875.34"
    assert source.unit == "SGD"
    assert source.observed_at == "2026-05-06T01:10:00Z"
    assert source.content_hash == "sha256:holdings-as-of-cash"
    assert source.reason_codes == [
        "CORE_SOURCE_READY",
        "CORE_PRODUCT_HOLDINGSASOF",
        "CORE_PRODUCT_VERSION_V1",
        "CASH_BASIS_REPORTING",
        "CORE_DATA_QUALITY_COMPLETE",
    ]


def test_cash_balances_adapter_supports_portfolio_currency_basis() -> None:
    source = realized_cash_source_from_cash_balances_response(
        _cash_balances_response(),
        currency_basis="portfolio",
    )

    assert str(source.value) == "152500.25"
    assert source.unit == "USD"
    assert source.source_id.endswith(":portfolio:sha256:holdings-as-of-cash")


def test_cash_source_can_make_rfc42_cash_dimension_ready() -> None:
    source = realized_cash_source_from_cash_balances_response(_cash_balances_response())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["CASH_RESIDUAL"],
    )

    cash = snapshot.realized_values["CASH_RESIDUAL"]
    assert snapshot.supportability.state == "READY"
    assert cash.value == source.value
    assert cash.source_refs[0].source_system == "lotus-core"
    assert cash.supportability.reason_codes[0] == "SOURCE_READY"


def test_transaction_ledger_adapter_wraps_source_owned_trade_fee() -> None:
    source = realized_transaction_source_from_transaction_ledger_response(
        _transaction_ledger_response(),
        transaction_id="TXN-FX-001",
        measure="trade_fee",
    )

    assert source.dimension == "COST"
    assert source.source_system == "lotus-core"
    assert source.source_type == "TRANSACTION_LEDGER_WINDOW"
    assert source.source_id == (
        "TransactionLedgerWindow:v1:PB_SG_GLOBAL_BAL_001:2026-05-06:"
        "transaction:TXN-FX-001:trade_fee:sha256:transaction-ledger"
    )
    assert str(source.value) == "24.98"
    assert source.unit == "SGD"
    assert source.observed_at == "2026-05-06T01:18:00Z"
    assert source.as_of_date == "2026-05-06"
    assert source.content_hash == "sha256:transaction-ledger"
    assert source.reason_codes == [
        "CORE_SOURCE_READY",
        "CORE_PRODUCT_TRANSACTIONLEDGERWINDOW",
        "CORE_PRODUCT_VERSION_V1",
        "TRANSACTION_MEASURE_TRADE_FEE",
        "TRANSACTION_ID_TXN-FX-001",
        "TRANSACTION_TYPE_FX_FORWARD",
        "TRANSACTION_VALUE_TRADE_FEE_REPORTING",
        "CORE_DATA_QUALITY_COMPLETE",
    ]


def test_transaction_ledger_adapter_wraps_withholding_tax() -> None:
    source = realized_transaction_source_from_transaction_ledger_response(
        _transaction_ledger_response(),
        transaction_id="TXN-INT-001",
        measure="withholding_tax_amount",
    )

    assert source.dimension == "TAX"
    assert str(source.value) == "20.59"
    assert source.unit == "SGD"
    assert "TRANSACTION_VALUE_WITHHOLDING_TAX_REPORTING" in source.reason_codes


def test_transaction_ledger_adapter_wraps_realized_fx_pnl() -> None:
    source = realized_transaction_source_from_transaction_ledger_response(
        _transaction_ledger_response(),
        transaction_id="TXN-FX-001",
        measure="realized_fx_pnl",
    )

    assert source.dimension == "FX_RESIDUAL"
    assert str(source.value) == "1250.00"
    assert source.unit == "USD"
    assert "TRANSACTION_VALUE_REALIZED_FX_PNL_BASE" in source.reason_codes


def test_transaction_ledger_adapter_wraps_linked_cashflow_amount() -> None:
    source = realized_transaction_source_from_transaction_ledger_response(
        _transaction_ledger_response(),
        transaction_id="TXN-INT-001",
        measure="cashflow_amount",
    )

    assert source.dimension == "CASH_RESIDUAL"
    assert str(source.value) == "109.75"
    assert source.unit == "USD"
    assert "TRANSACTION_VALUE_CASHFLOW_AMOUNT" in source.reason_codes


def test_transaction_source_can_make_rfc42_tax_dimension_ready() -> None:
    source = realized_transaction_source_from_transaction_ledger_response(
        _transaction_ledger_response(),
        transaction_id="TXN-INT-001",
        measure="withholding_tax_amount",
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["TAX"],
    )

    tax = snapshot.realized_values["TAX"]
    assert snapshot.supportability.state == "READY"
    assert tax.value == source.value
    assert tax.source_refs[0].source_type == "TRANSACTION_LEDGER_WINDOW"


def test_incomplete_cash_source_preserves_degraded_core_posture() -> None:
    response = _cash_balances_response()
    response["data_quality_status"] = "INCOMPLETE"

    source = realized_cash_source_from_cash_balances_response(response)
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["CASH_RESIDUAL"],
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "PARTIAL"
    assert snapshot.supportability.state == "DEGRADED"
    assert snapshot.realized_values["CASH_RESIDUAL"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "CORE_SOURCE_DEGRADED",
    ]


@pytest.mark.parametrize(
    ("data_quality_status", "expected_quality"),
    [
        ("STALE", "STALE"),
        ("ERROR", "UNAVAILABLE"),
    ],
)
def test_cash_source_preserves_non_ready_core_quality_states(
    data_quality_status: str,
    expected_quality: str,
) -> None:
    response = _cash_balances_response()
    response["data_quality_status"] = data_quality_status

    source = realized_cash_source_from_cash_balances_response(response)

    assert source.source_state == "DEGRADED"
    assert source.quality == expected_quality
    assert "CORE_SOURCE_DEGRADED" in source.reason_codes


def test_incomplete_transaction_ledger_preserves_degraded_core_posture() -> None:
    response = _transaction_ledger_response()
    response["data_quality_status"] = "INCOMPLETE"

    source = realized_transaction_source_from_transaction_ledger_response(
        response,
        transaction_id="TXN-FX-001",
        measure="trade_fee",
    )
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["COST"],
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "PARTIAL"
    assert snapshot.supportability.state == "DEGRADED"
    assert snapshot.realized_values["COST"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "CORE_SOURCE_DEGRADED",
    ]


def test_unavailable_core_cash_source_preserves_degraded_owner_posture() -> None:
    source = unavailable_core_cash_source(
        source_id="core-down:cash",
        reason_code="CORE_CASH_BALANCE_UNAVAILABLE",
        as_of_date="2026-05-06",
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["CASH_RESIDUAL"],
    )

    assert snapshot.supportability.state == "DEGRADED"
    assert snapshot.realized_values["CASH_RESIDUAL"].value is None
    assert snapshot.realized_values["CASH_RESIDUAL"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "CORE_CASH_BALANCE_UNAVAILABLE",
    ]


def test_cashflow_projection_adapter_wraps_source_total_without_forecasting() -> None:
    source = realized_cashflow_projection_source_from_cashflow_projection_response(
        _cashflow_projection_response()
    )

    assert source.dimension == "CASH_RESIDUAL"
    assert source.source_system == "lotus-core"
    assert source.source_type == "PORTFOLIO_CASHFLOW_PROJECTION"
    assert source.source_id == (
        "PortfolioCashflowProjection:v1:PB_SG_GLOBAL_BAL_001:2026-05-06:"
        "cashflow_projection:total_net_cashflow:2026-05-06:2026-05-16:"
        "include_projected=true:cashflow_projection:PB_SG_GLOBAL_BAL_001:"
        "2026-05-06:2026-05-16:include_projected=true"
    )
    assert str(source.value) == "-25000.00"
    assert source.unit == "USD"
    assert source.observed_at == "2026-05-06T01:58:00Z"
    assert source.as_of_date == "2026-05-06"
    assert source.content_hash == (
        "cashflow_projection:PB_SG_GLOBAL_BAL_001:2026-05-06:2026-05-16:include_projected=true"
    )
    assert source.reason_codes == [
        "CORE_SOURCE_READY",
        "CORE_PRODUCT_PORTFOLIOCASHFLOWPROJECTION",
        "CORE_PRODUCT_VERSION_V1",
        "CASHFLOW_PROJECTION_MEASURE_TOTAL_NET_CASHFLOW",
        "CASHFLOW_PROJECTION_RANGE_2026-05-06_TO_2026-05-16",
        "CASHFLOW_PROJECTION_INCLUDE_PROJECTED_TRUE",
        "CORE_DATA_QUALITY_COMPLETE",
    ]


def test_cashflow_projection_source_can_make_rfc42_cash_dimension_ready() -> None:
    source = realized_cashflow_projection_source_from_cashflow_projection_response(
        _cashflow_projection_response()
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["CASH_RESIDUAL"],
    )

    cash = snapshot.realized_values["CASH_RESIDUAL"]
    assert snapshot.supportability.state == "READY"
    assert cash.value == source.value
    assert cash.unit == "USD"
    assert cash.source_refs[0].source_type == "PORTFOLIO_CASHFLOW_PROJECTION"


def test_realized_tax_summary_adapter_wraps_source_owned_portfolio_total() -> None:
    source = realized_tax_summary_source_from_realized_tax_summary_response(
        _realized_tax_summary_response()
    )

    assert source.dimension == "TAX"
    assert source.source_system == "lotus-core"
    assert source.source_type == "PORTFOLIO_REALIZED_TAX_SUMMARY"
    assert source.source_id == (
        "PortfolioRealizedTaxSummary:v1:PB_SG_GLOBAL_BAL_001:2026-05-06:"
        "realized_tax_summary:total_tax_amount:USD:"
        "realized_tax_summary:PB_SG_GLOBAL_BAL_001:2026-05-06"
    )
    assert str(source.value) == "138.25"
    assert source.unit == "USD"
    assert source.observed_at == "2026-05-06T02:14:00Z"
    assert source.reason_codes == [
        "CORE_SOURCE_READY",
        "CORE_PRODUCT_PORTFOLIOREALIZEDTAXSUMMARY",
        "CORE_PRODUCT_VERSION_V1",
        "REALIZED_TAX_SUMMARY_MEASURE_TOTAL_TAX_AMOUNT",
        "REALIZED_TAX_SUMMARY_CURRENCY_USD",
        "REALIZED_TAX_SOURCE_TRANSACTION_COUNT_28",
        "REALIZED_TAX_EVIDENCE_TRANSACTION_COUNT_3",
        "REALIZED_TAX_SOURCE_REASON_PORTFOLIO_REALIZED_TAX_SUMMARY_READY",
        "CORE_DATA_QUALITY_COMPLETE",
    ]


def test_realized_tax_summary_adapter_wraps_reporting_currency_total() -> None:
    source = realized_tax_summary_source_from_realized_tax_summary_response(
        _realized_tax_summary_response(),
        measure="reporting_currency_total_tax_amount",
    )

    assert source.dimension == "TAX"
    assert str(source.value) == "188.02"
    assert source.unit == "SGD"
    assert "REALIZED_TAX_SUMMARY_MEASURE_REPORTING_CURRENCY_TOTAL_TAX_AMOUNT" in (
        source.reason_codes
    )


def test_realized_tax_summary_source_can_make_rfc42_tax_dimension_ready() -> None:
    source = realized_tax_summary_source_from_realized_tax_summary_response(
        _realized_tax_summary_response()
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["TAX"],
    )

    tax = snapshot.realized_values["TAX"]
    assert snapshot.supportability.state == "READY"
    assert tax.value == source.value
    assert tax.source_refs[0].source_type == "PORTFOLIO_REALIZED_TAX_SUMMARY"


def test_cash_movement_summary_adapter_wraps_source_owned_bucket_total() -> None:
    source = realized_cash_movement_source_from_cash_movement_summary_response(
        _cash_movement_summary_response(),
        classification="TRADE_SETTLEMENT",
        timing="SETTLED",
        currency="USD",
        is_position_flow=True,
        is_portfolio_flow=False,
    )

    assert source.dimension == "CASH_RESIDUAL"
    assert source.source_system == "lotus-core"
    assert source.source_type == "PORTFOLIO_CASH_MOVEMENT_SUMMARY"
    assert source.source_id == (
        "PortfolioCashMovementSummary:v1:PB_SG_GLOBAL_BAL_001:2026-05-06:"
        "cash_movement_summary:TRADE_SETTLEMENT:SETTLED:USD:"
        "position_flow=true:portfolio_flow=false:"
        "cash_movement_summary:PB_SG_GLOBAL_BAL_001:2026-04-01:2026-05-06"
    )
    assert str(source.value) == "-3500.00"
    assert source.unit == "USD"
    assert source.observed_at == "2026-05-06T02:28:00Z"
    assert "CASH_MOVEMENT_DIRECTION_OUTFLOW" in source.reason_codes
    assert "CASH_MOVEMENT_BUCKET_CASHFLOW_COUNT_1" in source.reason_codes
    assert "CASH_MOVEMENT_TOTAL_CASHFLOW_COUNT_3" in source.reason_codes


def test_cash_movement_bucket_helpers_extract_and_match_source_buckets() -> None:
    response = _cash_movement_summary_response()

    buckets = _cash_movement_buckets(response)

    assert len(buckets) == 2
    assert _cash_movement_bucket_matches(
        bucket=buckets[1],
        classification="trade_settlement",
        timing="settled",
        currency="usd",
        is_position_flow=True,
        is_portfolio_flow=False,
    )
    assert not _cash_movement_bucket_matches(
        bucket=buckets[1],
        classification="trade_settlement",
        timing="settled",
        currency="sgd",
        is_position_flow=True,
        is_portfolio_flow=False,
    )
    assert _cash_movement_buckets({"buckets": "not-a-list"}) == []


def test_cash_movement_summary_source_can_make_rfc42_cash_dimension_ready() -> None:
    source = realized_cash_movement_source_from_cash_movement_summary_response(
        _cash_movement_summary_response(),
        classification="CASHFLOW_IN",
        timing="SETTLED",
        currency="USD",
        is_position_flow=False,
        is_portfolio_flow=True,
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["CASH_RESIDUAL"],
    )

    cash = snapshot.realized_values["CASH_RESIDUAL"]
    assert snapshot.supportability.state == "READY"
    assert cash.value == source.value
    assert cash.source_refs[0].source_type == "PORTFOLIO_CASH_MOVEMENT_SUMMARY"


def test_external_order_execution_acknowledgement_adapter_preserves_fail_closed_posture() -> None:
    source = realized_execution_acknowledgement_source_from_response(
        _external_order_execution_acknowledgement_response()
    )

    assert source.dimension == "EXECUTION_QUALITY"
    assert source.source_system == "lotus-core"
    assert source.source_type == "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT"
    assert source.source_id == (
        "ExternalOrderExecutionAcknowledgement:v1:PB_SG_GLOBAL_BAL_001:2026-05-06:"
        "external_order_execution_acknowledgement:execution_intent=intent_rebalance_001:"
        "orders=ORD-001,ORD-002:sha256:external-order-execution-acknowledgement"
    )
    assert str(source.value) == "0"
    assert source.unit == "acknowledgements"
    assert source.source_state == "BLOCKED"
    assert source.quality == "MISSING"
    assert source.content_hash == "sha256:external-order-execution-acknowledgement"
    assert source.reason_codes[:6] == [
        "CORE_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
        "CORE_PRODUCT_EXTERNALORDEREXECUTIONACKNOWLEDGEMENT",
        "CORE_PRODUCT_VERSION_V1",
        "EXECUTION_ACKNOWLEDGEMENT_SUPPORTABILITY_UNAVAILABLE",
        "EXTERNAL_OMS_SOURCE_NOT_INGESTED",
        "EXECUTION_ACKNOWLEDGEMENT_COUNT_0",
    ]
    assert (
        "EXECUTION_ACKNOWLEDGEMENT_MISSING_DATA_EXTERNAL_OMS_ORDER_EXECUTION_ACKNOWLEDGEMENT"
        in source.reason_codes
    )
    assert "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_FILLS" in source.reason_codes
    assert "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_SETTLEMENT" in source.reason_codes


def test_external_order_execution_acknowledgement_blocks_rfc42_execution_dimension() -> None:
    source = realized_execution_acknowledgement_source_from_response(
        _external_order_execution_acknowledgement_response()
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["EXECUTION_QUALITY"],
    )

    execution_quality = snapshot.realized_values["EXECUTION_QUALITY"]
    assert snapshot.supportability.state == "BLOCKED"
    assert execution_quality.value is None
    assert execution_quality.unit == "acknowledgements"
    assert execution_quality.supportability.reason_codes[:2] == [
        "EXECUTION_EVIDENCE_BLOCKED",
        "CORE_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
    ]
    assert execution_quality.source_refs[0].source_type == (
        "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT"
    )
    assert snapshot.source_hashes[source.source_id] == (
        "sha256:external-order-execution-acknowledgement"
    )


@pytest.mark.parametrize(
    ("measure", "expected_value"),
    [
        ("booked_total_net_cashflow", "0"),
        ("projected_settlement_total_cashflow", "-25000.00"),
    ],
)
def test_cashflow_projection_adapter_wraps_source_owned_cash_movement_components(
    measure: str,
    expected_value: str,
) -> None:
    source = realized_cashflow_projection_source_from_cashflow_projection_response(
        _cashflow_projection_response(),
        measure=measure,  # type: ignore[arg-type]
    )

    assert source.dimension == "CASH_RESIDUAL"
    assert str(source.value) == expected_value
    assert source.unit == "USD"
    assert f"CASHFLOW_PROJECTION_MEASURE_{measure.upper()}" in source.reason_codes
    assert f"cashflow_projection:{measure}:2026-05-06:2026-05-16" in source.source_id


def test_incomplete_cashflow_projection_preserves_degraded_core_posture() -> None:
    response = _cashflow_projection_response()
    response["data_quality_status"] = "INCOMPLETE"

    source = realized_cashflow_projection_source_from_cashflow_projection_response(response)
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["CASH_RESIDUAL"],
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "PARTIAL"
    assert snapshot.supportability.state == "DEGRADED"
    assert snapshot.realized_values["CASH_RESIDUAL"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "CORE_SOURCE_DEGRADED",
    ]


def test_unavailable_core_cashflow_projection_preserves_degraded_owner_posture() -> None:
    source = unavailable_core_cashflow_projection_source(
        source_id="core-down:cashflow-projection",
        reason_code="CORE_CASHFLOW_PROJECTION_UNAVAILABLE",
        as_of_date="2026-05-06",
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["CASH_RESIDUAL"],
    )

    assert snapshot.supportability.state == "DEGRADED"
    assert snapshot.realized_values["CASH_RESIDUAL"].value is None
    assert snapshot.realized_values["CASH_RESIDUAL"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "CORE_CASHFLOW_PROJECTION_UNAVAILABLE",
    ]


def test_cashflow_projection_adapter_rejects_missing_currency() -> None:
    malformed = _cashflow_projection_response()
    del malformed["portfolio_currency"]

    with pytest.raises(CoreOutcomeSourceError, match="portfolio_currency"):
        realized_cashflow_projection_source_from_cashflow_projection_response(malformed)


def test_cashflow_projection_adapter_rejects_missing_source_total() -> None:
    malformed = _cashflow_projection_response()
    del malformed["total_net_cashflow"]

    with pytest.raises(CoreOutcomeSourceError, match="total_net_cashflow"):
        realized_cashflow_projection_source_from_cashflow_projection_response(malformed)


def test_cashflow_projection_adapter_rejects_non_canonical_measure() -> None:
    with pytest.raises(CoreOutcomeSourceError, match="unsupported_measure"):
        realized_cashflow_projection_source_from_cashflow_projection_response(
            _cashflow_projection_response(),
            measure="unsupported_measure",  # type: ignore[arg-type]
        )


def test_cashflow_projection_adapter_rejects_missing_projection_posture() -> None:
    malformed = _cashflow_projection_response()
    del malformed["include_projected"]

    with pytest.raises(CoreOutcomeSourceError, match="include_projected"):
        realized_cashflow_projection_source_from_cashflow_projection_response(malformed)


def test_external_order_execution_acknowledgement_rejects_invalid_count() -> None:
    malformed = _external_order_execution_acknowledgement_response()
    supportability = malformed["supportability"]
    assert isinstance(supportability, dict)
    supportability["acknowledgement_count"] = -1

    with pytest.raises(CoreOutcomeSourceError, match="negative"):
        realized_execution_acknowledgement_source_from_response(malformed)


def test_cash_adapter_rejects_local_aggregation_request() -> None:
    with pytest.raises(CoreOutcomeSourceError, match="currency_basis"):
        realized_cash_source_from_cash_balances_response(
            _cash_balances_response(),
            currency_basis="tax",
        )


def test_cash_adapter_rejects_missing_source_total() -> None:
    malformed = _cash_balances_response()
    totals = malformed["totals"]
    assert isinstance(totals, dict)
    del totals["total_balance_reporting_currency"]

    with pytest.raises(CoreOutcomeSourceError, match="cash balance total"):
        realized_cash_source_from_cash_balances_response(malformed)


def test_transaction_adapter_rejects_missing_transaction_row() -> None:
    with pytest.raises(CoreOutcomeSourceError, match="transaction_id TXN-MISSING"):
        realized_transaction_source_from_transaction_ledger_response(
            _transaction_ledger_response(),
            transaction_id="TXN-MISSING",
            measure="trade_fee",
        )


def test_transaction_adapter_rejects_missing_source_measure() -> None:
    malformed = _transaction_ledger_response()
    transactions = malformed["transactions"]
    assert isinstance(transactions, list)
    txn = transactions[0]
    assert isinstance(txn, dict)
    txn["trade_fee"] = None
    txn["trade_fee_reporting_currency"] = None

    with pytest.raises(CoreOutcomeSourceError, match="trade_fee"):
        realized_transaction_source_from_transaction_ledger_response(
            malformed,
            transaction_id="TXN-FX-001",
            measure="trade_fee",
        )


def test_transaction_adapter_uses_source_trade_fee_when_reporting_value_is_absent() -> None:
    response = _transaction_ledger_response()
    del response["reporting_currency"]
    transactions = response["transactions"]
    assert isinstance(transactions, list)
    txn = transactions[0]
    assert isinstance(txn, dict)
    txn["trade_fee_reporting_currency"] = None

    source = realized_transaction_source_from_transaction_ledger_response(
        response,
        transaction_id="TXN-FX-001",
        measure="trade_fee",
    )

    assert str(source.value) == "18.50"
    assert source.unit == "USD"
    assert "TRANSACTION_VALUE_TRADE_FEE_SOURCE" in source.reason_codes


def test_transaction_adapter_uses_local_fx_pnl_when_base_value_is_absent() -> None:
    response = _transaction_ledger_response()
    transactions = response["transactions"]
    assert isinstance(transactions, list)
    txn = transactions[0]
    assert isinstance(txn, dict)
    txn["realized_fx_pnl_base"] = None

    source = realized_transaction_source_from_transaction_ledger_response(
        response,
        transaction_id="TXN-FX-001",
        measure="realized_fx_pnl",
    )

    assert str(source.value) == "1250.00"
    assert source.unit == "USD"
    assert "TRANSACTION_VALUE_REALIZED_FX_PNL_LOCAL" in source.reason_codes


def test_transaction_adapter_rejects_missing_fx_pnl_and_cashflow_amount() -> None:
    missing_fx = _transaction_ledger_response()
    transactions = missing_fx["transactions"]
    assert isinstance(transactions, list)
    fx_txn = transactions[0]
    assert isinstance(fx_txn, dict)
    fx_txn["realized_fx_pnl_base"] = None
    fx_txn["realized_fx_pnl_local"] = None

    with pytest.raises(CoreOutcomeSourceError, match="realized_fx_pnl"):
        realized_transaction_source_from_transaction_ledger_response(
            missing_fx,
            transaction_id="TXN-FX-001",
            measure="realized_fx_pnl",
        )

    missing_cashflow = _transaction_ledger_response()
    transactions = missing_cashflow["transactions"]
    assert isinstance(transactions, list)
    cash_txn = transactions[1]
    assert isinstance(cash_txn, dict)
    cash_txn["cashflow"] = {}

    with pytest.raises(CoreOutcomeSourceError, match="cashflow.amount"):
        realized_transaction_source_from_transaction_ledger_response(
            missing_cashflow,
            transaction_id="TXN-INT-001",
            measure="cashflow_amount",
        )


def test_transaction_value_helpers_select_fx_and_cashflow_source_values() -> None:
    transactions = _transaction_ledger_response()["transactions"]
    assert isinstance(transactions, list)
    fx_transaction = transactions[0]
    cashflow_transaction = transactions[1]
    assert isinstance(fx_transaction, dict)
    assert isinstance(cashflow_transaction, dict)

    fx_value, fx_unit, fx_reason = _transaction_fx_pnl_value(transaction=fx_transaction)
    assert str(fx_value) == str(fx_transaction["realized_fx_pnl_base"])
    assert fx_unit == "USD"
    assert fx_reason == "TRANSACTION_VALUE_REALIZED_FX_PNL_BASE"
    fx_transaction["realized_fx_pnl_base"] = None
    assert _transaction_fx_pnl_value(transaction=fx_transaction)[2] == (
        "TRANSACTION_VALUE_REALIZED_FX_PNL_LOCAL"
    )
    cashflow_value, cashflow_unit, cashflow_reason = _transaction_cashflow_value(
        transaction=cashflow_transaction
    )
    assert str(cashflow_value) == str(cashflow_transaction["cashflow"]["amount"])
    assert cashflow_unit == "USD"
    assert cashflow_reason == "TRANSACTION_VALUE_CASHFLOW_AMOUNT"


def test_transaction_adapter_treats_missing_transaction_list_as_source_gap() -> None:
    malformed = _transaction_ledger_response()
    malformed["transactions"] = None

    with pytest.raises(CoreOutcomeSourceError, match="transaction_id TXN-FX-001"):
        realized_transaction_source_from_transaction_ledger_response(
            malformed,
            transaction_id="TXN-FX-001",
            measure="trade_fee",
        )


def test_realized_tax_summary_adapter_rejects_ambiguous_currency_totals() -> None:
    response = _realized_tax_summary_response()
    totals = response["currency_totals"]
    assert isinstance(totals, list)
    totals.append(
        {
            "currency": "SGD",
            "source_transaction_count": 1,
            "withholding_tax_amount": "1",
            "other_tax_deductions_amount": "0",
            "total_tax_amount": "1",
        }
    )

    with pytest.raises(CoreOutcomeSourceError, match="currency must be supplied"):
        realized_tax_summary_source_from_realized_tax_summary_response(response)


def test_realized_tax_summary_adapter_rejects_missing_reporting_total() -> None:
    response = _realized_tax_summary_response()
    response["reporting_currency_total_tax_amount"] = None

    with pytest.raises(CoreOutcomeSourceError, match="reporting_currency_total_tax_amount"):
        realized_tax_summary_source_from_realized_tax_summary_response(
            response,
            measure="reporting_currency_total_tax_amount",
        )


def test_cash_movement_summary_adapter_rejects_missing_bucket() -> None:
    with pytest.raises(CoreOutcomeSourceError, match="missing requested bucket"):
        realized_cash_movement_source_from_cash_movement_summary_response(
            _cash_movement_summary_response(),
            classification="DIVIDEND",
            timing="SETTLED",
            currency="USD",
            is_position_flow=False,
            is_portfolio_flow=True,
        )
