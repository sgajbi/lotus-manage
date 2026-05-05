import pytest

from src.core.outcomes import (
    RiskOutcomeSourceError,
    assemble_realized_outcome_snapshot,
    realized_risk_source_from_risk_metrics_report,
    unavailable_risk_source,
)
from tests.unit.core.test_realized_outcome_sources import _window


def _risk_metrics_report() -> dict[str, object]:
    return {
        "scope": {
            "as_of_date": "2026-05-06",
            "reporting_currency": "USD",
            "net_or_gross": "NET",
        },
        "results": {
            "YTD": {
                "start_date": "2026-01-02",
                "end_date": "2026-05-06",
                "portfolio_observation_count": 64,
                "benchmark_observation_count": 64,
                "aligned_benchmark_observation_count": 61,
                "metrics": {
                    "VOLATILITY": {
                        "value": 0.079885986,
                        "details": {
                            "observation_count": 64,
                            "annualization_factor": 252,
                        },
                    },
                    "VAR": {
                        "value": -1.775,
                        "details": {
                            "method": "HISTORICAL",
                            "confidence": 0.95,
                            "horizon_days": 1,
                        },
                    },
                },
            }
        },
        "metadata": {
            "contract_version": "v1",
            "methodology_version": "risk.v1",
            "request_fingerprint": "sha256:risk-metrics-request",
            "source_services": ["lotus-risk", "lotus-performance"],
            "upstream_request_fingerprints": {
                "lotus-performance:/integration/returns/series": "sha256:returns-series"
            },
            "calculation_supportability": {
                "state": "ready",
                "reason": "calculation_complete",
                "freshness_bucket": "current",
                "degraded_metric_count": 0,
                "empty_period_count": 0,
                "evaluated_period_count": 1,
            },
        },
    }


def test_risk_metrics_report_adapter_wraps_source_truth_without_recalculation() -> None:
    source = realized_risk_source_from_risk_metrics_report(_risk_metrics_report())

    assert source.dimension == "RISK_REDUCTION"
    assert source.source_system == "lotus-risk"
    assert source.source_type == "RISK_METRICS_REPORT"
    assert source.source_id == "sha256:risk-metrics-request:YTD:VOLATILITY"
    assert str(source.value) == "0.079885986"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:risk-metrics-request"
    assert source.reason_codes == [
        "RISK_SOURCE_READY",
        "RISK_SUPPORTABILITY_READY",
        "RISK_REASON_CALCULATION_COMPLETE",
        "RISK_PERIOD_YTD",
        "RISK_METRIC_VOLATILITY",
    ]


def test_risk_metrics_report_adapter_supports_explicit_metric() -> None:
    source = realized_risk_source_from_risk_metrics_report(
        _risk_metrics_report(),
        metric="VAR",
    )

    assert str(source.value) == "-1.775"
    assert source.unit == "percentage_point"
    assert source.source_id.endswith(":YTD:VAR")
    assert "RISK_METRIC_VAR" in source.reason_codes


def test_risk_source_can_make_rfc42_risk_dimension_ready() -> None:
    source = realized_risk_source_from_risk_metrics_report(_risk_metrics_report())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    risk = snapshot.realized_values["RISK_REDUCTION"]
    assert snapshot.supportability.state == "READY"
    assert risk.value == source.value
    assert risk.source_refs[0].source_system == "lotus-risk"
    assert risk.supportability.reason_codes[0] == "SOURCE_READY"


def test_missing_risk_source_still_reports_not_supported_without_local_clone() -> None:
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[],
        required_dimensions=["RISK_REDUCTION"],
    )

    assert snapshot.supportability.state == "NOT_SUPPORTED"
    assert snapshot.realized_values["RISK_REDUCTION"].supportability.reason_codes == [
        "RISK_OUTCOME_NOT_SUPPORTED"
    ]


def test_unavailable_risk_source_preserves_degraded_owner_posture() -> None:
    source = unavailable_risk_source(
        source_id="risk-down:YTD:VOLATILITY",
        reason_code="RISK_METRICS_REPORT_UNAVAILABLE",
        as_of_date="2026-05-06",
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    risk = snapshot.realized_values["RISK_REDUCTION"]
    assert snapshot.supportability.state == "DEGRADED"
    assert risk.value is None
    assert risk.supportability.reason_codes[:2] == [
        "RISK_SOURCE_UNAVAILABLE",
        "RISK_METRICS_REPORT_UNAVAILABLE",
    ]


def test_degraded_risk_report_preserves_source_owner_supportability() -> None:
    report = _risk_metrics_report()
    metadata = report["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {
        "state": "degraded",
        "reason": "benchmark_unavailable",
        "freshness_bucket": "current",
    }

    source = realized_risk_source_from_risk_metrics_report(report)

    assert source.source_state == "DEGRADED"
    assert source.quality == "PARTIAL"
    assert source.value is not None
    assert source.reason_codes[:3] == [
        "RISK_SOURCE_DEGRADED",
        "RISK_SUPPORTABILITY_DEGRADED",
        "RISK_REASON_BENCHMARK_UNAVAILABLE",
    ]


def test_permission_blocked_risk_report_blocks_ready_claim() -> None:
    report = _risk_metrics_report()
    metadata = report["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {
        "state": "permission_blocked",
        "reason": "permission_blocked",
        "freshness_bucket": "unknown",
    }

    source = realized_risk_source_from_risk_metrics_report(report)
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    assert source.source_state == "BLOCKED"
    assert source.quality == "MISSING"
    assert snapshot.supportability.state == "BLOCKED"
    assert snapshot.realized_values["RISK_REDUCTION"].value is None
    assert snapshot.realized_values["RISK_REDUCTION"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "RISK_SOURCE_BLOCKED",
    ]


def test_risk_adapter_rejects_report_without_trust_fingerprint() -> None:
    malformed = _risk_metrics_report()
    metadata = malformed["metadata"]
    assert isinstance(metadata, dict)
    del metadata["request_fingerprint"]

    with pytest.raises(RiskOutcomeSourceError, match="request_fingerprint"):
        realized_risk_source_from_risk_metrics_report(malformed)


def test_risk_adapter_rejects_missing_ready_metric_value() -> None:
    malformed = _risk_metrics_report()
    results = malformed["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    metrics = ytd["metrics"]
    assert isinstance(metrics, dict)
    metrics["VOLATILITY"] = {"value": None}

    with pytest.raises(RiskOutcomeSourceError, match="numeric VOLATILITY value"):
        realized_risk_source_from_risk_metrics_report(malformed)
