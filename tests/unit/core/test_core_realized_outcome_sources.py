import pytest

from src.core.outcomes import (
    CoreOutcomeSourceError,
    assemble_realized_outcome_snapshot,
    realized_cash_source_from_cash_balances_response,
    realized_transaction_source_from_transaction_ledger_response,
    unavailable_core_cash_source,
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
