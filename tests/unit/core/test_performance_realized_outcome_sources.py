import pytest

from src.core.outcomes import (
    PerformanceOutcomeSourceError,
    assemble_realized_outcome_snapshot,
    realized_performance_source_from_workspace_summary,
    unavailable_performance_source,
)
from tests.unit.core.test_realized_outcome_sources import _window


def _workspace_summary() -> dict[str, object]:
    return {
        "calculation_id": "0d000003-1111-4222-8333-abcdefabcdef",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "input_mode": "stateful",
        "results_by_period": {
            "YTD": {
                "portfolio_twr": {
                    "net": {
                        "summary": {
                            "period_return": {"base": 2.41, "local": 2.12, "fx": 0.29},
                            "cumulative_return": {"base": 3.41, "local": 3.18, "fx": 0.23},
                            "annualized_return": {"base": 3.41, "local": 3.18, "fx": 0.23},
                        },
                        "breakdowns": {},
                    },
                    "gross": {
                        "summary": {
                            "period_return": {"base": 2.44, "local": 2.15, "fx": 0.29},
                            "cumulative_return": {"base": 3.44, "local": 3.21, "fx": 0.23},
                            "annualized_return": {"base": 3.44, "local": 3.21, "fx": 0.23},
                        },
                        "breakdowns": {},
                    },
                }
            }
        },
        "meta": {
            "calculation_id": "0d000003-1111-4222-8333-abcdefabcdef",
            "calculation_hash": "sha256:workspace-summary",
            "periods": {"master_start": "2026-01-02", "master_end": "2026-05-06"},
        },
        "diagnostics": {"effective_period_start": "2026-01-02", "notes": []},
        "audit": {"counts": {"input_rows": 64}},
    }


def test_performance_workspace_summary_adapter_wraps_source_truth_without_recalculation() -> None:
    source = realized_performance_source_from_workspace_summary(_workspace_summary())

    assert source.dimension == "PERFORMANCE"
    assert source.source_system == "lotus-performance"
    assert source.source_type == "WORKSPACE_SUMMARY_TWR_RETURN"
    assert source.source_id == "0d000003-1111-4222-8333-abcdefabcdef:YTD:net:cumulative_return"
    assert str(source.value) == "0.0341"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:workspace-summary"
    assert source.reason_codes == [
        "PERFORMANCE_SOURCE_READY",
        "PERFORMANCE_PERIOD_YTD",
        "PERFORMANCE_BASIS_NET",
        "PERFORMANCE_MEASURE_CUMULATIVE_RETURN",
    ]


def test_performance_workspace_summary_adapter_supports_explicit_basis_and_measure() -> None:
    source = realized_performance_source_from_workspace_summary(
        _workspace_summary(),
        basis="gross",
        return_measure="period_return",
    )

    assert str(source.value) == "0.0244"
    assert source.source_id.endswith(":YTD:gross:period_return")
    assert "PERFORMANCE_BASIS_GROSS" in source.reason_codes
    assert "PERFORMANCE_MEASURE_PERIOD_RETURN" in source.reason_codes


def test_performance_source_can_make_rfc42_performance_dimension_ready() -> None:
    source = realized_performance_source_from_workspace_summary(_workspace_summary())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    performance = snapshot.realized_values["PERFORMANCE"]
    assert snapshot.supportability.state == "READY"
    assert performance.value == source.value
    assert performance.source_refs[0].source_system == "lotus-performance"
    assert performance.supportability.reason_codes[0] == "SOURCE_READY"


def test_missing_performance_source_still_reports_not_supported_without_local_clone() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[],
        required_dimensions=["PERFORMANCE"],
    )

    assert snapshot.supportability.state == "NOT_SUPPORTED"
    assert snapshot.realized_values["PERFORMANCE"].supportability.reason_codes == [
        "PERFORMANCE_OUTCOME_NOT_SUPPORTED"
    ]


def test_unavailable_performance_source_preserves_degraded_owner_posture() -> None:
    source = unavailable_performance_source(
        source_id="performance-down:YTD:net:cumulative_return",
        reason_code="PERFORMANCE_WORKSPACE_SUMMARY_UNAVAILABLE",
        as_of_date="2026-05-06",
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    performance = snapshot.realized_values["PERFORMANCE"]
    assert snapshot.supportability.state == "DEGRADED"
    assert performance.value is None
    assert performance.supportability.reason_codes[:2] == [
        "PERFORMANCE_SOURCE_UNAVAILABLE",
        "PERFORMANCE_WORKSPACE_SUMMARY_UNAVAILABLE",
    ]


def test_performance_adapter_rejects_malformed_source_payload() -> None:
    malformed = _workspace_summary()
    del malformed["results_by_period"]

    with pytest.raises(PerformanceOutcomeSourceError, match="numeric base return"):
        realized_performance_source_from_workspace_summary(malformed)
