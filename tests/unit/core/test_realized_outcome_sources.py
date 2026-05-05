from decimal import Decimal

from src.core.outcomes import (
    DpmOutcomeReviewWindow,
    DpmRealizedSourceSnapshot,
    assemble_realized_outcome_snapshot,
)


def _window() -> DpmOutcomeReviewWindow:
    return DpmOutcomeReviewWindow(
        start_at="2026-05-05T01:00:00Z",
        end_at="2026-05-06T01:00:00Z",
        as_of_date="2026-05-06",
        timezone="Asia/Singapore",
    )


def _source(
    *,
    dimension: str,
    source_system: str = "lotus-core",
    source_type: str = "POST_TRADE_SOURCE",
    source_id: str = "src_001",
    value: str | None = "0.0375",
    source_state: str = "READY",
    quality: str = "COMPLETE",
) -> DpmRealizedSourceSnapshot:
    return DpmRealizedSourceSnapshot(
        dimension=dimension,
        source_system=source_system,
        source_type=source_type,
        source_id=source_id,
        value=Decimal(value) if value is not None else None,
        unit="ratio",
        source_state=source_state,
        quality=quality,
        observed_at="2026-05-06T01:10:00Z",
        as_of_date="2026-05-06",
        content_hash=f"sha256:{source_id}",
        reason_codes=[f"{quality}_SOURCE"],
    )


def test_realized_snapshot_consumes_ready_source_owner_values_without_recalculation() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[
            _source(
                dimension="DRIFT_REDUCTION",
                source_system="lotus-core",
                source_type="POST_TRADE_HOLDINGS_DRIFT",
                source_id="core_drift_001",
                value="0.0375",
            ),
            _source(
                dimension="COST",
                source_system="lotus-core",
                source_type="BOOKED_TRANSACTION_COST",
                source_id="core_cost_001",
                value="126.50",
            ),
        ],
        required_dimensions=["DRIFT_REDUCTION", "COST"],
    )

    assert snapshot.supportability.state == "READY"
    assert snapshot.realized_values["DRIFT_REDUCTION"].value == Decimal("0.0375")
    assert snapshot.realized_values["COST"].value == Decimal("126.50")
    assert snapshot.source_hashes["core_drift_001"] == "sha256:core_drift_001"
    assert snapshot.quality_summary == {"COMPLETE": 2}


def test_missing_execution_quality_source_blocks_with_execution_reason() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[],
        required_dimensions=["EXECUTION_QUALITY"],
    )

    execution = snapshot.realized_values["EXECUTION_QUALITY"]
    assert snapshot.supportability.state == "BLOCKED"
    assert execution.supportability.state == "BLOCKED"
    assert execution.supportability.reason_codes == ["EXECUTION_EVIDENCE_BLOCKED"]
    assert execution.source_refs[0].source_system == "execution-owner"


def test_missing_risk_and_performance_contracts_are_not_supported_not_ready() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[],
        required_dimensions=["RISK_REDUCTION", "PERFORMANCE"],
    )

    assert snapshot.supportability.state == "NOT_SUPPORTED"
    assert snapshot.realized_values["RISK_REDUCTION"].supportability.reason_codes == [
        "RISK_OUTCOME_NOT_SUPPORTED"
    ]
    assert snapshot.realized_values["PERFORMANCE"].supportability.reason_codes == [
        "PERFORMANCE_OUTCOME_NOT_SUPPORTED"
    ]


def test_stale_source_is_degraded_and_preserves_source_lineage() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[
            _source(
                dimension="CASH_RESIDUAL",
                source_system="lotus-core",
                source_type="POST_TRADE_CASH_RESIDUAL",
                source_id="core_cash_001",
                value="0.0610",
                source_state="DEGRADED",
                quality="STALE",
            )
        ],
        required_dimensions=["CASH_RESIDUAL"],
    )

    cash = snapshot.realized_values["CASH_RESIDUAL"]
    assert snapshot.supportability.state == "DEGRADED"
    assert cash.value == Decimal("0.0610")
    assert cash.supportability.state == "DEGRADED"
    assert cash.source_freshness.freshness_state == "STALE"
    assert snapshot.source_lineage[0].source_id == "core_cash_001"


def test_conflicting_source_owner_values_block_dimension() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[
            _source(dimension="COST", source_id="core_cost_001", value="126.50"),
            _source(dimension="COST", source_id="core_cost_002", value="127.10"),
        ],
        required_dimensions=["COST"],
    )

    cost = snapshot.realized_values["COST"]
    assert snapshot.supportability.state == "BLOCKED"
    assert cost.value is None
    assert cost.supportability.reason_codes == ["SOURCE_EVIDENCE_INCOMPLETE", "SOURCE_CONFLICTING"]
    assert {ref.source_id for ref in cost.source_refs} == {"core_cost_001", "core_cost_002"}


def test_malformed_source_blocks_without_using_partial_value() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[
            _source(
                dimension="DRIFT_REDUCTION",
                source_id="core_drift_bad",
                value="0.0375",
                source_state="BLOCKED",
                quality="MALFORMED",
            )
        ],
        required_dimensions=["DRIFT_REDUCTION"],
    )

    drift = snapshot.realized_values["DRIFT_REDUCTION"]
    assert drift.value is None
    assert drift.supportability.state == "BLOCKED"
    assert drift.supportability.reason_codes[0] == "SOURCE_EVIDENCE_INCOMPLETE"
