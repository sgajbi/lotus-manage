import pytest

from src.core.outcomes import (
    CoreOutcomeSourceError,
    assemble_realized_outcome_snapshot,
    realized_cash_source_from_cash_balances_response,
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
