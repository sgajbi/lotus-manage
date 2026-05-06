import pytest

from src.core.outcomes import (
    PerformanceOutcomeSourceError,
    assemble_realized_outcome_snapshot,
    realized_active_performance_source_from_workspace_summary,
    realized_attribution_source_from_attribution_response,
    realized_contribution_source_from_contribution_response,
    realized_mwr_source_from_workspace_summary,
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
                },
                "active": {
                    "net": {
                        "period_return": {"base": 0.41},
                        "cumulative_return": {"base": 0.61},
                        "annualized_return": {"base": 0.61},
                    },
                    "gross": {
                        "period_return": {"base": 0.44},
                        "cumulative_return": {"base": 0.64},
                        "annualized_return": {"base": 0.64},
                    },
                },
                "money_weighted_return": {
                    "input_mode": "stateful",
                    "method": "XIRR",
                    "period_return": 2.93,
                    "cumulative_return": 3.27,
                    "annualized_return": 3.27,
                    "economics": {
                        "begin_market_value": 1000000.0,
                        "end_market_value": 1054100.0,
                        "beginning_cash_flow": 25000.0,
                        "ending_cash_flow": -5000.0,
                        "fees": -350.0,
                        "net_cash_flow": 20000.0,
                        "flow_adjusted_end_market_value": 1034100.0,
                    },
                    "start_date": "2026-01-02",
                    "end_date": "2026-05-06",
                    "notes": [
                        "Stateful workspace MWR summary resolved from source-owned economics."
                    ],
                },
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


def _contribution_response() -> dict[str, object]:
    return {
        "calculation_id": "0d000004-1111-4222-8333-abcdefabcdef",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "input_mode": "stateful",
        "results_by_period": {
            "YTD": {
                "total_portfolio_return": 3.41,
                "total_contribution": 3.39,
                "position_contributions": [
                    {
                        "position_id": "FO_FUND_PIMCO_INC",
                        "total_contribution": 1.42,
                        "average_weight": 12.45,
                        "total_return": 11.405622,
                        "local_contribution": 1.2,
                        "fx_contribution": 0.22,
                    }
                ],
                "timeseries": [{"date": "2026-05-06", "total_contribution": 0.18}],
                "summary": {
                    "portfolio_contribution": 3.39,
                    "coverage_mv_pct": 99.2,
                    "weighting_scheme": "average_weight",
                    "local_contribution": 3.11,
                    "fx_contribution": 0.28,
                },
            }
        },
        "calculation_supportability": {
            "state": "ready",
            "reason": "calculation_complete",
            "freshness_bucket": "current",
            "input_row_count": 64,
            "resolved_period_count": 1,
            "benchmark_row_count": 0,
        },
        "meta": {
            "calculation_id": "0d000004-1111-4222-8333-abcdefabcdef",
            "calculation_hash": "sha256:contribution",
            "periods": {"master_start": "2026-01-02", "master_end": "2026-05-06"},
        },
        "diagnostics": {"effective_period_start": "2026-01-02", "notes": []},
        "audit": {
            "sum_of_parts_vs_total_bp": 0.2,
            "residual_applied_bp": 0.2,
            "counts": {"input_rows": 64, "position_count": 11},
        },
    }


def _attribution_response() -> dict[str, object]:
    return {
        "calculation_id": "0d000005-1111-4222-8333-abcdefabcdef",
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "input_mode": "stateful",
        "model": "brinson_fachler",
        "linking": "carino",
        "results_by_period": {
            "YTD": {
                "levels": [
                    {
                        "dimension": "asset_class",
                        "parent_key": None,
                        "groups": [
                            {
                                "key": {"asset_class": "equity"},
                                "portfolio_weight_avg": 62.5,
                                "benchmark_weight_avg": 58.0,
                                "portfolio_return": 4.1,
                                "benchmark_return": 3.4,
                                "allocation": 0.12,
                                "selection": 0.31,
                                "interaction": 0.04,
                                "total_effect": 0.47,
                            }
                        ],
                        "totals": {
                            "allocation": 0.12,
                            "selection": 0.31,
                            "interaction": 0.04,
                            "total_effect": 0.47,
                        },
                        "allocation_total_pct": 0.12,
                        "selection_total_pct": 0.31,
                        "interaction_total_pct": 0.04,
                        "total_effect_pct": 0.47,
                    }
                ],
                "reconciliation": {
                    "total_active_return": 0.49,
                    "sum_of_effects": 0.47,
                    "residual": 0.02,
                },
                "currency_attribution": [
                    {
                        "currency": "USD",
                        "weight_portfolio_avg": 64.0,
                        "weight_benchmark_avg": 60.0,
                        "effects": {
                            "local_allocation": 0.03,
                            "local_selection": 0.05,
                            "currency_allocation": 0.02,
                            "currency_selection": 0.01,
                            "total_effect": 0.11,
                        },
                    }
                ],
            }
        },
        "benchmark_context": {
            "benchmark_id": "BMK_GLOBAL_60_40",
            "return_source": "calculated",
        },
        "calculation_supportability": {
            "state": "ready",
            "reason": "calculation_complete",
            "freshness_bucket": "current",
            "input_row_count": 128,
            "resolved_period_count": 1,
            "benchmark_row_count": 64,
        },
        "meta": {
            "calculation_id": "0d000005-1111-4222-8333-abcdefabcdef",
            "calculation_hash": "sha256:attribution",
            "periods": {"master_start": "2026-01-02", "master_end": "2026-05-06"},
        },
        "diagnostics": {"effective_period_start": "2026-01-02", "notes": []},
        "audit": {"counts": {"input_rows": 128, "benchmark_rows": 64}},
    }


def test_performance_workspace_summary_adapter_wraps_source_truth_without_recalculation() -> None:
    source = realized_performance_source_from_workspace_summary(_workspace_summary())

    assert source.dimension == "PERFORMANCE"
    assert source.source_system == "lotus-performance"
    assert source.source_type == "WORKSPACE_SUMMARY_TWR_RETURN"
    assert source.source_id == (
        "0d000003-1111-4222-8333-abcdefabcdef:YTD:twr:net:cumulative_return"
    )
    assert str(source.value) == "0.0341"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:workspace-summary"
    assert source.reason_codes == [
        "PERFORMANCE_SOURCE_READY",
        "PERFORMANCE_PERIOD_YTD",
        "PERFORMANCE_MEASURE_FAMILY_TWR",
        "PERFORMANCE_BASIS_NET",
        "PERFORMANCE_MEASURE_CUMULATIVE_RETURN",
    ]


def test_contribution_adapter_wraps_source_owned_total_contribution() -> None:
    source = realized_contribution_source_from_contribution_response(_contribution_response())

    assert source.dimension == "PERFORMANCE"
    assert source.source_system == "lotus-performance"
    assert source.source_type == "PERFORMANCE_CONTRIBUTION"
    assert source.source_id == (
        "0d000004-1111-4222-8333-abcdefabcdef:YTD:contribution:total_contribution"
    )
    assert str(source.value) == "0.0339"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:contribution"
    assert source.reason_codes == [
        "PERFORMANCE_SOURCE_READY",
        "PERFORMANCE_SUPPORTABILITY_READY",
        "PERFORMANCE_REASON_CALCULATION_COMPLETE",
        "PERFORMANCE_PERIOD_YTD",
        "PERFORMANCE_MEASURE_FAMILY_CONTRIBUTION",
        "PERFORMANCE_MEASURE_TOTAL_CONTRIBUTION",
        "PERFORMANCE_INPUT_MODE_STATEFUL",
    ]


def test_attribution_adapter_wraps_source_owned_active_return_reconciliation() -> None:
    source = realized_attribution_source_from_attribution_response(_attribution_response())

    assert source.dimension == "PERFORMANCE"
    assert source.source_system == "lotus-performance"
    assert source.source_type == "PERFORMANCE_ATTRIBUTION"
    assert source.source_id == (
        "0d000005-1111-4222-8333-abcdefabcdef:YTD:attribution:"
        "reconciliation_total_active_return:reconciliation"
    )
    assert str(source.value) == "0.0049"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:attribution"
    assert source.reason_codes == [
        "PERFORMANCE_SOURCE_READY",
        "PERFORMANCE_SUPPORTABILITY_READY",
        "PERFORMANCE_REASON_CALCULATION_COMPLETE",
        "PERFORMANCE_PERIOD_YTD",
        "PERFORMANCE_MEASURE_FAMILY_ATTRIBUTION",
        "PERFORMANCE_ATTRIBUTION_MEASURE_RECONCILIATION_TOTAL_ACTIVE_RETURN",
        "PERFORMANCE_ATTRIBUTION_SELECTOR_RECONCILIATION",
        "PERFORMANCE_INPUT_MODE_STATEFUL",
        "PERFORMANCE_ATTRIBUTION_MODEL_BRINSON_FACHLER",
        "PERFORMANCE_ATTRIBUTION_LINKING_CARINO",
        "PERFORMANCE_BENCHMARK_BMK_GLOBAL_60_40",
        "PERFORMANCE_BENCHMARK_RETURN_SOURCE_CALCULATED",
    ]


def test_attribution_adapter_wraps_source_owned_level_total() -> None:
    source = realized_attribution_source_from_attribution_response(
        _attribution_response(),
        measure="level_total_effect",
        level_dimension="asset_class",
    )

    assert source.source_id.endswith(":YTD:attribution:level_total_effect:level:asset_class")
    assert str(source.value) == "0.0047"
    assert "PERFORMANCE_ATTRIBUTION_LEVEL_ASSET_CLASS" in source.reason_codes


def test_attribution_adapter_wraps_source_owned_currency_effect() -> None:
    source = realized_attribution_source_from_attribution_response(
        _attribution_response(),
        measure="currency_total_effect",
        currency="USD",
    )

    assert source.source_id.endswith(":YTD:attribution:currency_total_effect:currency:usd")
    assert str(source.value) == "0.0011"
    assert "PERFORMANCE_ATTRIBUTION_CURRENCY_USD" in source.reason_codes


def test_source_owned_attribution_can_make_rfc42_performance_dimension_ready() -> None:
    source = realized_attribution_source_from_attribution_response(_attribution_response())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    performance = snapshot.realized_values["PERFORMANCE"]
    assert snapshot.supportability.state == "READY"
    assert performance.value == source.value
    assert performance.source_refs[0].source_type == "PERFORMANCE_ATTRIBUTION"
    assert performance.supportability.reason_codes[0] == "SOURCE_READY"


def test_contribution_adapter_wraps_source_owned_portfolio_return() -> None:
    source = realized_contribution_source_from_contribution_response(
        _contribution_response(),
        measure="total_portfolio_return",
    )

    assert source.source_id.endswith(":YTD:contribution:total_portfolio_return")
    assert str(source.value) == "0.0341"
    assert "PERFORMANCE_MEASURE_TOTAL_PORTFOLIO_RETURN" in source.reason_codes


def test_contribution_adapter_wraps_source_owned_summary_fx_contribution() -> None:
    source = realized_contribution_source_from_contribution_response(
        _contribution_response(),
        measure="summary_fx_contribution",
    )

    assert source.source_id.endswith(":YTD:contribution:summary_fx_contribution")
    assert str(source.value) == "0.0028"
    assert "PERFORMANCE_MEASURE_SUMMARY_FX_CONTRIBUTION" in source.reason_codes


def test_performance_workspace_summary_adapter_supports_explicit_basis_and_measure() -> None:
    source = realized_performance_source_from_workspace_summary(
        _workspace_summary(),
        basis="gross",
        return_measure="period_return",
    )

    assert str(source.value) == "0.0244"
    assert source.source_id.endswith(":YTD:twr:gross:period_return")
    assert "PERFORMANCE_BASIS_GROSS" in source.reason_codes
    assert "PERFORMANCE_MEASURE_PERIOD_RETURN" in source.reason_codes


def test_performance_workspace_summary_adapter_wraps_source_owned_active_return() -> None:
    source = realized_active_performance_source_from_workspace_summary(
        _workspace_summary(),
        basis="gross",
        return_measure="period_return",
    )

    assert source.dimension == "PERFORMANCE"
    assert source.source_system == "lotus-performance"
    assert source.source_type == "WORKSPACE_SUMMARY_ACTIVE_RETURN"
    assert source.source_id == (
        "0d000003-1111-4222-8333-abcdefabcdef:YTD:active:gross:period_return"
    )
    assert str(source.value) == "0.0044"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:workspace-summary"
    assert source.reason_codes == [
        "PERFORMANCE_SOURCE_READY",
        "PERFORMANCE_PERIOD_YTD",
        "PERFORMANCE_MEASURE_FAMILY_ACTIVE",
        "PERFORMANCE_BASIS_GROSS",
        "PERFORMANCE_MEASURE_PERIOD_RETURN",
    ]


def test_performance_workspace_summary_adapter_wraps_source_owned_mwr_return() -> None:
    source = realized_mwr_source_from_workspace_summary(
        _workspace_summary(),
        return_measure="period_return",
    )

    assert source.dimension == "PERFORMANCE"
    assert source.source_system == "lotus-performance"
    assert source.source_type == "WORKSPACE_SUMMARY_MWR_RETURN"
    assert source.source_id == "0d000003-1111-4222-8333-abcdefabcdef:YTD:mwr:period_return:XIRR"
    assert str(source.value) == "0.0293"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:workspace-summary"
    assert source.reason_codes == [
        "PERFORMANCE_SOURCE_READY",
        "PERFORMANCE_PERIOD_YTD",
        "PERFORMANCE_MEASURE_FAMILY_MWR",
        "PERFORMANCE_MEASURE_PERIOD_RETURN",
        "PERFORMANCE_MWR_METHOD_XIRR",
        "PERFORMANCE_MWR_INPUT_MODE_STATEFUL",
    ]


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


def test_source_owned_active_return_can_make_rfc42_performance_dimension_ready() -> None:
    source = realized_active_performance_source_from_workspace_summary(_workspace_summary())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    performance = snapshot.realized_values["PERFORMANCE"]
    assert snapshot.supportability.state == "READY"
    assert performance.value == source.value
    assert performance.source_refs[0].source_type == "WORKSPACE_SUMMARY_ACTIVE_RETURN"
    assert performance.supportability.reason_codes[0] == "SOURCE_READY"


def test_source_owned_mwr_return_can_make_rfc42_performance_dimension_ready() -> None:
    source = realized_mwr_source_from_workspace_summary(_workspace_summary())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    performance = snapshot.realized_values["PERFORMANCE"]
    assert snapshot.supportability.state == "READY"
    assert performance.value == source.value
    assert performance.source_refs[0].source_type == "WORKSPACE_SUMMARY_MWR_RETURN"
    assert performance.supportability.reason_codes[0] == "SOURCE_READY"


def test_source_owned_contribution_can_make_rfc42_performance_dimension_ready() -> None:
    source = realized_contribution_source_from_contribution_response(_contribution_response())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    performance = snapshot.realized_values["PERFORMANCE"]
    assert snapshot.supportability.state == "READY"
    assert performance.value == source.value
    assert performance.source_refs[0].source_type == "PERFORMANCE_CONTRIBUTION"
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


def test_degraded_contribution_preserves_source_owner_supportability() -> None:
    response = _contribution_response()
    supportability = response["calculation_supportability"]
    assert isinstance(supportability, dict)
    supportability.update(
        {
            "state": "stale",
            "reason": "stale_source_observations",
            "freshness_bucket": "stale",
        }
    )

    source = realized_contribution_source_from_contribution_response(response)

    assert source.source_state == "DEGRADED"
    assert source.quality == "STALE"
    assert str(source.value) == "0.0339"
    assert source.reason_codes[:3] == [
        "PERFORMANCE_SOURCE_DEGRADED",
        "PERFORMANCE_SUPPORTABILITY_STALE",
        "PERFORMANCE_REASON_STALE_SOURCE_OBSERVATIONS",
    ]


def test_error_contribution_blocks_ready_claim() -> None:
    response = _contribution_response()
    supportability = response["calculation_supportability"]
    assert isinstance(supportability, dict)
    supportability.update(
        {
            "state": "error",
            "reason": "calculation_quality_issue",
            "freshness_bucket": "unknown",
        }
    )

    source = realized_contribution_source_from_contribution_response(response)
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    assert source.source_state == "BLOCKED"
    assert source.quality == "MISSING"
    assert snapshot.supportability.state == "BLOCKED"
    assert snapshot.realized_values["PERFORMANCE"].value is None
    assert snapshot.realized_values["PERFORMANCE"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "PERFORMANCE_SOURCE_BLOCKED",
    ]


def test_degraded_attribution_preserves_source_owner_supportability() -> None:
    response = _attribution_response()
    supportability = response["calculation_supportability"]
    assert isinstance(supportability, dict)
    supportability.update(
        {
            "state": "stale",
            "reason": "stale_source_observations",
            "freshness_bucket": "stale",
        }
    )

    source = realized_attribution_source_from_attribution_response(
        response,
        measure="level_total_effect",
        level_dimension="asset_class",
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "STALE"
    assert str(source.value) == "0.0047"
    assert source.reason_codes[:3] == [
        "PERFORMANCE_SOURCE_DEGRADED",
        "PERFORMANCE_SUPPORTABILITY_STALE",
        "PERFORMANCE_REASON_STALE_SOURCE_OBSERVATIONS",
    ]


def test_error_attribution_blocks_ready_claim() -> None:
    response = _attribution_response()
    supportability = response["calculation_supportability"]
    assert isinstance(supportability, dict)
    supportability.update(
        {
            "state": "error",
            "reason": "calculation_quality_issue",
            "freshness_bucket": "unknown",
        }
    )

    source = realized_attribution_source_from_attribution_response(response)
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["PERFORMANCE"],
    )

    assert source.source_state == "BLOCKED"
    assert source.quality == "MISSING"
    assert snapshot.supportability.state == "BLOCKED"
    assert snapshot.realized_values["PERFORMANCE"].value is None
    assert snapshot.realized_values["PERFORMANCE"].supportability.reason_codes[:2] == [
        "SOURCE_EVIDENCE_INCOMPLETE",
        "PERFORMANCE_SOURCE_BLOCKED",
    ]


def test_performance_adapter_rejects_malformed_source_payload() -> None:
    malformed = _workspace_summary()
    del malformed["results_by_period"]

    with pytest.raises(PerformanceOutcomeSourceError, match="numeric base return"):
        realized_performance_source_from_workspace_summary(malformed)


def test_active_performance_adapter_rejects_missing_source_active_return() -> None:
    malformed = _workspace_summary()
    period = malformed["results_by_period"]
    assert isinstance(period, dict)
    ytd = period["YTD"]
    assert isinstance(ytd, dict)
    del ytd["active"]

    with pytest.raises(PerformanceOutcomeSourceError, match="numeric active base return"):
        realized_active_performance_source_from_workspace_summary(malformed)


def test_mwr_adapter_rejects_missing_source_mwr_return() -> None:
    malformed = _workspace_summary()
    period = malformed["results_by_period"]
    assert isinstance(period, dict)
    ytd = period["YTD"]
    assert isinstance(ytd, dict)
    del ytd["money_weighted_return"]

    with pytest.raises(PerformanceOutcomeSourceError, match="numeric money-weighted return"):
        realized_mwr_source_from_workspace_summary(malformed)


def test_contribution_adapter_rejects_missing_ready_source_value() -> None:
    malformed = _contribution_response()
    results_by_period = malformed["results_by_period"]
    assert isinstance(results_by_period, dict)
    ytd = results_by_period["YTD"]
    assert isinstance(ytd, dict)
    ytd["total_contribution"] = None

    with pytest.raises(PerformanceOutcomeSourceError, match="numeric total_contribution"):
        realized_contribution_source_from_contribution_response(malformed)


def test_attribution_adapter_rejects_missing_ready_source_value() -> None:
    malformed = _attribution_response()
    results_by_period = malformed["results_by_period"]
    assert isinstance(results_by_period, dict)
    ytd = results_by_period["YTD"]
    assert isinstance(ytd, dict)
    reconciliation = ytd["reconciliation"]
    assert isinstance(reconciliation, dict)
    reconciliation["total_active_return"] = None

    with pytest.raises(
        PerformanceOutcomeSourceError,
        match="numeric attribution reconciliation_total_active_return",
    ):
        realized_attribution_source_from_attribution_response(malformed)
