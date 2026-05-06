import pytest

from src.core.outcomes import (
    RiskOutcomeSourceError,
    assemble_realized_outcome_snapshot,
    realized_concentration_source_from_concentration_response,
    realized_drawdown_source_from_drawdown_response,
    realized_historical_attribution_source_from_attribution_response,
    realized_rolling_risk_source_from_rolling_response,
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


def _drawdown_response() -> dict[str, object]:
    return {
        "source_service": "lotus-risk",
        "input_mode": "stateful",
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
                "summary": {
                    "max_drawdown": -0.084211,
                    "max_drawdown_peak_date": "2026-01-11",
                    "max_drawdown_trough_date": "2026-02-03",
                    "max_drawdown_recovery_date": "2026-02-19",
                    "is_recovered": True,
                    "days_to_trough": 16,
                    "days_to_recovery": 11,
                    "time_under_water_days": 27,
                    "average_drawdown": -0.041208,
                    "ulcer_index": 0.053901,
                    "drawdown_at_risk_95": -0.101552,
                    "conditional_drawdown_at_risk_95": -0.117884,
                },
                "relative_to_benchmark": {
                    "max_drawdown": -0.026414,
                    "max_drawdown_peak_date": "2026-01-04",
                    "max_drawdown_trough_date": "2026-02-15",
                    "max_drawdown_recovery_date": "2026-02-28",
                    "is_recovered": True,
                    "days_to_trough": 12,
                    "days_to_recovery": 10,
                    "time_under_water_days": 21,
                },
                "relative_to_benchmark_context": {
                    "requested": True,
                    "applied": True,
                    "reason": "APPLIED",
                    "aligned_observation_count": 61,
                },
                "episodes": [],
                "error": None,
            }
        },
        "metadata": {
            "contract_version": "v1",
            "methodology_version": "drawdown.v1",
            "request_fingerprint": "sha256:drawdown-request",
            "source_services": ["lotus-risk", "lotus-performance"],
            "upstream_request_fingerprints": {
                "lotus-performance:/integration/returns/series": "sha256:returns-series"
            },
            "include_underwater_series": False,
            "include_episode_list": True,
            "include_benchmark": True,
            "missing_benchmark_policy": "IGNORE",
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


def _concentration_response() -> dict[str, object]:
    return {
        "source_service": "lotus-risk",
        "input_mode": "stateful",
        "risk_proxy": {
            "hhi_current": 1345.677131,
            "hhi_proposed": 1410.218372,
            "hhi_delta": 64.541241,
        },
        "single_position_concentration": {
            "top_position_weight_current": 0.1245,
            "top_position_weight_proposed": 0.142,
            "top_position_weight_delta": 0.0175,
            "top_n_cumulative_weight_current": 0.4123,
            "top_n_cumulative_weight_proposed": 0.4551,
            "top_n_cumulative_weight_delta": 0.0428,
            "top_n": 10,
            "top_position_current": {
                "security_id": "FO_FUND_PIMCO_INC",
                "security_name": "PIMCO GIS Income Fund",
                "weight": 0.1245,
            },
            "top_position_proposed": {
                "security_id": "FO_FUND_PIMCO_INC",
                "security_name": "PIMCO GIS Income Fund",
                "weight": 0.142,
            },
        },
        "issuer_concentration": {
            "hhi_current": 3200.0,
            "hhi_proposed": 3475.0,
            "hhi_delta": 275.0,
            "top_issuer_weight_current": 0.18,
            "top_issuer_weight_proposed": 0.21,
            "top_issuer_weight_delta": 0.03,
            "coverage_status": "complete",
            "covered_position_count_current": 30,
            "covered_position_count_proposed": 31,
            "total_position_count_current": 30,
            "total_position_count_proposed": 31,
            "uncovered_position_count_current": 0,
            "uncovered_position_count_proposed": 0,
            "coverage_ratio_current": 1.0,
            "coverage_ratio_proposed": 1.0,
            "note": None,
            "top_issuer_current": {
                "issuer_id": "ULTIMATE_PIMCO",
                "issuer_name": "Pacific Investment Management Company LLC",
                "weight": 0.18,
            },
            "top_issuer_proposed": {
                "issuer_id": "ULTIMATE_PIMCO",
                "issuer_name": "Pacific Investment Management Company LLC",
                "weight": 0.21,
            },
        },
        "valuation_context": {
            "portfolio_currency": "USD",
            "reporting_currency": "USD",
            "position_basis": "market_value_base",
            "weight_basis": "total_market_value_base",
        },
        "metadata": {
            "contract_version": "v1",
            "methodology_version": "concentration.v1",
            "request_fingerprint": "sha256:concentration-request",
            "as_of_date": "2026-05-06",
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "issuer_grouping_level": "ultimate_parent",
            "enrichment_policy": "merge_caller_then_core",
            "include_cash_positions": True,
            "include_zero_quantity_positions": False,
            "source_services": ["lotus-risk", "lotus-core"],
            "upstream_request_fingerprints": {
                "lotus-core:/integration/holdings/as-of": "sha256:holdings-as-of"
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


def _rolling_response() -> dict[str, object]:
    return {
        "source_service": "lotus-risk",
        "input_mode": "stateful",
        "scope": {
            "as_of_date": "2026-05-06",
            "reporting_currency": "USD",
            "net_or_gross": "NET",
        },
        "results": {
            "YTD": {
                "start_date": "2026-01-02",
                "end_date": "2026-05-06",
                "series_count": 64,
                "benchmark_series_count": 64,
                "aligned_benchmark_series_count": 61,
                "risk_free_series_count": 64,
                "aligned_risk_free_series_count": 61,
                "window_lengths_requested": [21],
                "window_count_requested": 1,
                "window_lengths_emitted": [21],
                "window_count_emitted": 1,
                "benchmark_context": {
                    "requested": True,
                    "available": True,
                    "aligned": True,
                    "reason": "APPLIED",
                },
                "risk_free_context": {
                    "requested": True,
                    "available": True,
                    "aligned": True,
                    "reason": "APPLIED",
                },
                "window_results": [
                    {
                        "window_length": 21,
                        "metric_summaries": {
                            "ROLLING_VOLATILITY": {
                                "total_point_count": 64,
                                "computed_point_count": 44,
                                "coverage_ratio": 0.6875,
                                "min_observations_required": 21,
                                "warmup_point_count": 20,
                                "non_computed_point_count": 20,
                                "post_warmup_gap_point_count": 0,
                                "latest_observation_date": "2026-05-06",
                                "latest": 0.12538011,
                                "average": 0.11844792,
                                "minimum": 0.09122408,
                                "maximum": 0.16651142,
                                "p05": 0.09540187,
                                "p50": 0.11793054,
                                "p95": 0.15541828,
                            },
                            "ROLLING_BETA": {
                                "total_point_count": 64,
                                "computed_point_count": 44,
                                "coverage_ratio": 0.6875,
                                "min_observations_required": 21,
                                "warmup_point_count": 20,
                                "non_computed_point_count": 20,
                                "post_warmup_gap_point_count": 0,
                                "latest_observation_date": "2026-05-06",
                                "latest": 0.41862514,
                                "average": 0.04185233,
                                "minimum": -0.32108851,
                                "maximum": 0.41862514,
                                "p05": -0.24148062,
                                "p50": 0.05739184,
                                "p95": 0.31680427,
                            },
                            "ROLLING_SHARPE": {
                                "total_point_count": 64,
                                "computed_point_count": 44,
                                "coverage_ratio": 0.6875,
                                "min_observations_required": 21,
                                "warmup_point_count": 20,
                                "non_computed_point_count": 20,
                                "post_warmup_gap_point_count": 0,
                                "latest_observation_date": "2026-05-06",
                                "latest": 0.8123,
                                "average": 0.7211,
                                "minimum": 0.301,
                                "maximum": 1.041,
                                "p05": 0.402,
                                "p50": 0.709,
                                "p95": 0.998,
                            },
                        },
                        "metric_series_context": {
                            "requested": False,
                            "included": False,
                            "emitted_point_count": 0,
                            "reason": "OMITTED_BY_REQUEST",
                        },
                        "metric_series": None,
                    }
                ],
                "quality_flags": [],
                "error": None,
            }
        },
        "metadata": {
            "contract_version": "v1",
            "methodology_version": "rolling_metrics.v1",
            "request_fingerprint": "sha256:rolling-request",
            "annualization_basis": 252,
            "requested_metrics": [
                "ROLLING_VOLATILITY",
                "ROLLING_BETA",
                "ROLLING_SHARPE",
            ],
            "window_lengths_requested": [21],
            "window_count_requested": 1,
            "alignment_policy": "INNER_JOIN",
            "min_observations_policy": "STRICT",
            "include_time_series": False,
            "benchmark_context": {
                "requested": True,
                "requested_metrics": ["ROLLING_BETA"],
            },
            "risk_free_context": {
                "requested": True,
                "requested_metrics": ["ROLLING_SHARPE"],
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


def _historical_attribution_response() -> dict[str, object]:
    return {
        "source_service": "lotus-risk",
        "input_mode": "stateful",
        "scope": {
            "as_of_date": "2026-05-06",
            "reporting_currency": "USD",
            "net_or_gross": "NET",
        },
        "results": {
            "YTD": {
                "start_date": "2026-01-02",
                "end_date": "2026-05-06",
                "attribution_sets": [
                    {
                        "attribution_type": "ACTIVE_RISK",
                        "metric": "TRACKING_ERROR",
                        "grouping_dimension": "SECTOR",
                        "total_value": 0.0642,
                        "reconciled_sum": 0.0638,
                        "residual": 0.0004,
                        "contributors": [
                            {
                                "group_key": "SECTOR_TECH",
                                "group_label": "Technology",
                                "weight_average": 0.245,
                                "marginal_contribution": 0.0911,
                                "component_contribution": 0.0223,
                                "percent_contribution": 0.3474,
                            },
                            {
                                "group_key": "SECTOR_HEALTH",
                                "group_label": "Healthcare",
                                "weight_average": 0.184,
                                "marginal_contribution": -0.0312,
                                "component_contribution": -0.0057,
                                "percent_contribution": -0.0888,
                            },
                        ],
                        "quality_flags": [],
                    }
                ],
                "error": None,
            }
        },
        "metadata": {
            "contract_version": "v1",
            "methodology_version": "historical_attribution.v1",
            "request_fingerprint": "sha256:risk-attribution-request",
            "covariance_method": "EMPIRICAL",
            "annualization_basis": 252,
            "requested_attribution_types": ["ACTIVE_RISK"],
            "requested_metrics": ["TRACKING_ERROR"],
            "requested_grouping_dimensions": ["SECTOR"],
            "min_observations_policy": "STRICT",
            "stateful_active_risk_supported_grouping_dimensions": [
                "POSITION",
                "SECTOR",
                "ASSET_CLASS",
            ],
            "stateful_active_risk_gated_grouping_dimensions": ["ISSUER"],
            "stateful_active_risk_gate_reason": "benchmark issuer exposure semantics unavailable",
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


def test_concentration_adapter_wraps_source_owned_hhi_without_recalculation() -> None:
    source = realized_concentration_source_from_concentration_response(_concentration_response())

    assert source.dimension == "RISK_REDUCTION"
    assert source.source_system == "lotus-risk"
    assert source.source_type == "CONCENTRATION_RESPONSE"
    assert source.source_id == "sha256:concentration-request:hhi_current"
    assert str(source.value) == "1345.677131"
    assert source.unit == "hhi"
    assert source.as_of_date == "2026-05-06"
    assert source.content_hash == "sha256:concentration-request"
    assert source.reason_codes == [
        "RISK_SOURCE_READY",
        "RISK_SUPPORTABILITY_READY",
        "RISK_REASON_CALCULATION_COMPLETE",
        "RISK_CONCENTRATION_MEASURE_HHI_CURRENT",
        "RISK_CONCENTRATION_INPUT_MODE_STATEFUL",
        "RISK_CONCENTRATION_ISSUER_COVERAGE_COMPLETE",
    ]


def test_rolling_risk_adapter_wraps_source_owned_latest_volatility() -> None:
    source = realized_rolling_risk_source_from_rolling_response(_rolling_response())

    assert source.dimension == "RISK_REDUCTION"
    assert source.source_system == "lotus-risk"
    assert source.source_type == "ROLLING_RISK_METRICS_REPORT"
    assert source.source_id == ("sha256:rolling-request:YTD:rolling:21:ROLLING_VOLATILITY:latest")
    assert str(source.value) == "0.12538011"
    assert source.unit == "ratio"
    assert source.observed_at == "2026-05-06"
    assert source.as_of_date == "2026-05-06"
    assert source.content_hash == "sha256:rolling-request"
    assert source.reason_codes == [
        "RISK_SOURCE_READY",
        "RISK_SUPPORTABILITY_READY",
        "RISK_REASON_CALCULATION_COMPLETE",
        "RISK_PERIOD_YTD",
        "RISK_ROLLING_METRIC_ROLLING_VOLATILITY",
        "RISK_ROLLING_STATISTIC_LATEST",
        "RISK_ROLLING_WINDOW_21",
        "RISK_ROLLING_INPUT_MODE_STATEFUL",
        "RISK_ROLLING_CONTEXT_NOT_REQUIRED",
    ]


def test_rolling_risk_adapter_wraps_source_owned_beta_percentile() -> None:
    source = realized_rolling_risk_source_from_rolling_response(
        _rolling_response(),
        metric="ROLLING_BETA",
        statistic="p95",
        window_length=21,
    )

    assert source.source_id == "sha256:rolling-request:YTD:rolling:21:ROLLING_BETA:p95"
    assert str(source.value) == "0.31680427"
    assert "RISK_ROLLING_BENCHMARK_APPLIED" in source.reason_codes


def test_rolling_risk_source_can_make_rfc42_risk_dimension_ready() -> None:
    source = realized_rolling_risk_source_from_rolling_response(_rolling_response())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    risk = snapshot.realized_values["RISK_REDUCTION"]
    assert snapshot.supportability.state == "READY"
    assert risk.value == source.value
    assert risk.source_refs[0].source_type == "ROLLING_RISK_METRICS_REPORT"
    assert risk.supportability.reason_codes[0] == "SOURCE_READY"


def test_historical_attribution_adapter_wraps_source_owned_total_value() -> None:
    source = realized_historical_attribution_source_from_attribution_response(
        _historical_attribution_response()
    )

    assert source.dimension == "RISK_REDUCTION"
    assert source.source_system == "lotus-risk"
    assert source.source_type == "HISTORICAL_RISK_ATTRIBUTION"
    assert source.source_id == (
        "sha256:risk-attribution-request:YTD:historical-attribution:"
        "ACTIVE_RISK:TRACKING_ERROR:SECTOR:total_value"
    )
    assert str(source.value) == "0.0642"
    assert source.unit == "ratio"
    assert source.observed_at == "2026-05-06"
    assert source.as_of_date == "2026-05-06"
    assert source.content_hash == "sha256:risk-attribution-request"
    assert source.reason_codes == [
        "RISK_SOURCE_READY",
        "RISK_SUPPORTABILITY_READY",
        "RISK_REASON_CALCULATION_COMPLETE",
        "RISK_PERIOD_YTD",
        "RISK_ATTRIBUTION_TYPE_ACTIVE_RISK",
        "RISK_ATTRIBUTION_METRIC_TRACKING_ERROR",
        "RISK_ATTRIBUTION_GROUPING_SECTOR",
        "RISK_ATTRIBUTION_MEASURE_TOTAL_VALUE",
        "RISK_ATTRIBUTION_INPUT_MODE_STATEFUL",
        (
            "RISK_ATTRIBUTION_STATEFUL_ACTIVE_RISK_SUPPORT_SUPPORTED_3_GATED_1_"
            "REASON_BENCHMARK_ISSUER_EXPOSURE_SEMANTICS_UNAVAILABLE"
        ),
        "RISK_ATTRIBUTION_SET_LEVEL",
        "RISK_ATTRIBUTION_QUALITY_FLAGS_0",
        "RISK_ATTRIBUTION_PERIOD_OK",
    ]


def test_historical_attribution_adapter_wraps_source_owned_contributor_value() -> None:
    source = realized_historical_attribution_source_from_attribution_response(
        _historical_attribution_response(),
        measure="contributor_component_contribution",
        contributor_group_key="SECTOR_TECH",
    )

    assert source.source_id == (
        "sha256:risk-attribution-request:YTD:historical-attribution:"
        "ACTIVE_RISK:TRACKING_ERROR:SECTOR:contributor_component_contribution:SECTOR_TECH"
    )
    assert str(source.value) == "0.0223"
    assert "RISK_ATTRIBUTION_CONTRIBUTOR_SECTOR_TECH" in source.reason_codes


def test_historical_attribution_source_can_make_rfc42_risk_dimension_ready() -> None:
    source = realized_historical_attribution_source_from_attribution_response(
        _historical_attribution_response()
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    risk = snapshot.realized_values["RISK_REDUCTION"]
    assert snapshot.supportability.state == "READY"
    assert risk.value == source.value
    assert risk.source_refs[0].source_type == "HISTORICAL_RISK_ATTRIBUTION"


def test_concentration_adapter_wraps_single_position_weight() -> None:
    source = realized_concentration_source_from_concentration_response(
        _concentration_response(),
        measure="top_position_weight_current",
    )

    assert source.source_id == "sha256:concentration-request:top_position_weight_current"
    assert str(source.value) == "0.1245"
    assert source.unit == "ratio"
    assert "RISK_CONCENTRATION_MEASURE_TOP_POSITION_WEIGHT_CURRENT" in source.reason_codes


def test_concentration_adapter_wraps_issuer_concentration_with_complete_coverage() -> None:
    source = realized_concentration_source_from_concentration_response(
        _concentration_response(),
        measure="issuer_hhi_current",
    )

    assert source.source_state == "READY"
    assert source.quality == "COMPLETE"
    assert str(source.value) == "3200.0"
    assert source.unit == "hhi"
    assert "RISK_CONCENTRATION_ISSUER_COVERAGE_COMPLETE" in source.reason_codes


def test_concentration_adapter_degrades_issuer_measure_when_coverage_is_partial() -> None:
    response = _concentration_response()
    issuer = response["issuer_concentration"]
    assert isinstance(issuer, dict)
    issuer["coverage_status"] = "partial"
    issuer["coverage_ratio_current"] = 0.833333
    issuer["uncovered_position_count_current"] = 5
    issuer["note"] = "issuer_id missing in lotus-core instrument_enrichment"

    source = realized_concentration_source_from_concentration_response(
        response,
        measure="issuer_hhi_current",
    )
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "PARTIAL"
    assert str(source.value) == "3200.0"
    assert snapshot.supportability.state == "DEGRADED"
    assert "RISK_CONCENTRATION_ISSUER_COVERAGE_PARTIAL" in source.reason_codes


def test_concentration_adapter_degrades_issuer_measure_when_coverage_is_missing() -> None:
    response = _concentration_response()
    issuer = response["issuer_concentration"]
    assert isinstance(issuer, dict)
    del issuer["coverage_status"]

    source = realized_concentration_source_from_concentration_response(
        response,
        measure="issuer_coverage_ratio_current",
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "PARTIAL"
    assert str(source.value) == "1.0"
    assert "RISK_CONCENTRATION_ISSUER_COVERAGE_UNKNOWN" in source.reason_codes


def test_concentration_source_can_make_rfc42_risk_dimension_ready() -> None:
    source = realized_concentration_source_from_concentration_response(
        _concentration_response(),
        measure="top_position_weight_proposed",
    )

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    risk = snapshot.realized_values["RISK_REDUCTION"]
    assert snapshot.supportability.state == "READY"
    assert risk.value == source.value
    assert risk.source_refs[0].source_type == "CONCENTRATION_RESPONSE"
    assert risk.supportability.reason_codes[0] == "SOURCE_READY"


def test_drawdown_response_adapter_wraps_source_owned_max_drawdown() -> None:
    source = realized_drawdown_source_from_drawdown_response(_drawdown_response())

    assert source.dimension == "RISK_REDUCTION"
    assert source.source_system == "lotus-risk"
    assert source.source_type == "DRAWDOWN_RESPONSE"
    assert source.source_id == "sha256:drawdown-request:YTD:max_drawdown"
    assert str(source.value) == "-0.084211"
    assert source.unit == "ratio"
    assert source.content_hash == "sha256:drawdown-request"
    assert source.reason_codes == [
        "RISK_SOURCE_READY",
        "RISK_SUPPORTABILITY_READY",
        "RISK_REASON_CALCULATION_COMPLETE",
        "RISK_PERIOD_YTD",
        "RISK_DRAWDOWN_MEASURE_MAX_DRAWDOWN",
        "RISK_DRAWDOWN_ABSOLUTE",
    ]


def test_drawdown_response_adapter_wraps_source_owned_relative_max_drawdown() -> None:
    source = realized_drawdown_source_from_drawdown_response(
        _drawdown_response(),
        measure="relative_max_drawdown",
    )

    assert source.source_type == "DRAWDOWN_RESPONSE"
    assert source.source_id == "sha256:drawdown-request:YTD:relative_max_drawdown"
    assert str(source.value) == "-0.026414"
    assert "RISK_DRAWDOWN_MEASURE_RELATIVE_MAX_DRAWDOWN" in source.reason_codes
    assert "RISK_DRAWDOWN_RELATIVE_APPLIED" in source.reason_codes


def test_risk_metrics_report_adapter_supports_explicit_metric() -> None:
    source = realized_risk_source_from_risk_metrics_report(
        _risk_metrics_report(),
        metric="VAR",
    )

    assert str(source.value) == "-1.775"
    assert source.unit == "percentage_point"
    assert source.source_id.endswith(":YTD:VAR")
    assert "RISK_METRIC_VAR" in source.reason_codes


def test_drawdown_source_can_make_rfc42_risk_dimension_ready() -> None:
    source = realized_drawdown_source_from_drawdown_response(_drawdown_response())

    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    risk = snapshot.realized_values["RISK_REDUCTION"]
    assert snapshot.supportability.state == "READY"
    assert risk.value == source.value
    assert risk.source_refs[0].source_type == "DRAWDOWN_RESPONSE"
    assert risk.supportability.reason_codes[0] == "SOURCE_READY"


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


def test_relative_drawdown_not_applied_preserves_degraded_source_posture() -> None:
    response = _drawdown_response()
    results = response["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    ytd["relative_to_benchmark_context"] = {
        "requested": True,
        "applied": False,
        "reason": "BENCHMARK_UNAVAILABLE",
        "aligned_observation_count": 0,
    }
    ytd["relative_to_benchmark"] = None

    source = realized_drawdown_source_from_drawdown_response(
        response,
        measure="relative_max_drawdown",
    )
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "UNAVAILABLE"
    assert snapshot.supportability.state == "DEGRADED"
    assert snapshot.realized_values["RISK_REDUCTION"].value is None
    assert snapshot.realized_values["RISK_REDUCTION"].supportability.reason_codes[:2] == [
        "RISK_SOURCE_UNAVAILABLE",
        "RISK_SOURCE_DEGRADED",
    ]
    assert "RISK_DRAWDOWN_RELATIVE_BENCHMARK_UNAVAILABLE" in source.reason_codes


def test_rolling_risk_benchmark_unavailable_preserves_degraded_source_posture() -> None:
    response = _rolling_response()
    results = response["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    ytd["benchmark_context"] = {
        "requested": True,
        "available": False,
        "aligned": False,
        "reason": "BENCHMARK_UNAVAILABLE",
    }
    window = ytd["window_results"][0]  # type: ignore[index]
    assert isinstance(window, dict)
    summaries = window["metric_summaries"]
    assert isinstance(summaries, dict)
    beta = summaries["ROLLING_BETA"]
    assert isinstance(beta, dict)
    beta["latest"] = None

    source = realized_rolling_risk_source_from_rolling_response(
        response,
        metric="ROLLING_BETA",
    )
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "UNAVAILABLE"
    assert source.value is None
    assert snapshot.supportability.state == "DEGRADED"
    assert "RISK_ROLLING_BENCHMARK_BENCHMARK_UNAVAILABLE" in source.reason_codes


def test_rolling_risk_free_unavailable_preserves_degraded_source_posture() -> None:
    response = _rolling_response()
    results = response["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    ytd["risk_free_context"] = {
        "requested": True,
        "available": False,
        "aligned": False,
        "reason": "RISK_FREE_UNAVAILABLE",
    }
    window = ytd["window_results"][0]  # type: ignore[index]
    assert isinstance(window, dict)
    summaries = window["metric_summaries"]
    assert isinstance(summaries, dict)
    sharpe = summaries["ROLLING_SHARPE"]
    assert isinstance(sharpe, dict)
    sharpe["latest"] = None

    source = realized_rolling_risk_source_from_rolling_response(
        response,
        metric="ROLLING_SHARPE",
    )

    assert source.source_state == "DEGRADED"
    assert source.quality == "UNAVAILABLE"
    assert source.value is None
    assert "RISK_ROLLING_RISK_FREE_RISK_FREE_UNAVAILABLE" in source.reason_codes


def test_historical_attribution_quality_flags_preserve_degraded_source_posture() -> None:
    response = _historical_attribution_response()
    results = response["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    attribution_set = ytd["attribution_sets"][0]  # type: ignore[index]
    assert isinstance(attribution_set, dict)
    attribution_set["quality_flags"] = ["grouping:SECTOR:weight_not_sum_to_one"]

    source = realized_historical_attribution_source_from_attribution_response(response)

    assert source.source_state == "DEGRADED"
    assert source.quality == "PARTIAL"
    assert source.value is not None
    assert "RISK_ATTRIBUTION_QUALITY_FLAGS_1" in source.reason_codes


def test_historical_attribution_period_error_blocks_ready_claim() -> None:
    response = _historical_attribution_response()
    results = response["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    ytd["error"] = "Insufficient aligned observations"
    ytd["attribution_sets"] = []

    source = realized_historical_attribution_source_from_attribution_response(response)
    snapshot = assemble_realized_outcome_snapshot(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        review_window=_window(),
        source_snapshots=[source],
        required_dimensions=["RISK_REDUCTION"],
    )

    assert source.source_state == "BLOCKED"
    assert source.quality == "MISSING"
    assert source.value is None
    assert snapshot.supportability.state == "BLOCKED"
    assert "RISK_ATTRIBUTION_PERIOD_ERROR_INSUFFICIENT_ALIGNED_OBSERVATIONS" in source.reason_codes


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


def test_degraded_rolling_risk_preserves_source_owner_supportability() -> None:
    response = _rolling_response()
    metadata = response["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {
        "state": "stale",
        "reason": "stale_source_observations",
        "freshness_bucket": "stale",
    }

    source = realized_rolling_risk_source_from_rolling_response(response)

    assert source.source_state == "DEGRADED"
    assert source.quality == "STALE"
    assert source.value is not None
    assert source.reason_codes[:3] == [
        "RISK_SOURCE_DEGRADED",
        "RISK_SUPPORTABILITY_STALE",
        "RISK_REASON_STALE_SOURCE_OBSERVATIONS",
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


def test_permission_blocked_rolling_risk_blocks_ready_claim() -> None:
    response = _rolling_response()
    metadata = response["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {
        "state": "permission_blocked",
        "reason": "permission_blocked",
        "freshness_bucket": "unknown",
    }

    source = realized_rolling_risk_source_from_rolling_response(response)
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


def test_degraded_drawdown_response_preserves_source_owner_supportability() -> None:
    response = _drawdown_response()
    metadata = response["metadata"]
    assert isinstance(metadata, dict)
    metadata["calculation_supportability"] = {
        "state": "stale",
        "reason": "stale_source_observations",
        "freshness_bucket": "stale",
    }

    source = realized_drawdown_source_from_drawdown_response(response)

    assert source.source_state == "DEGRADED"
    assert source.quality == "STALE"
    assert source.value is not None
    assert source.reason_codes[:3] == [
        "RISK_SOURCE_DEGRADED",
        "RISK_SUPPORTABILITY_STALE",
        "RISK_REASON_STALE_SOURCE_OBSERVATIONS",
    ]


def test_risk_adapter_rejects_report_without_trust_fingerprint() -> None:
    malformed = _risk_metrics_report()
    metadata = malformed["metadata"]
    assert isinstance(metadata, dict)
    del metadata["request_fingerprint"]

    with pytest.raises(RiskOutcomeSourceError, match="request_fingerprint"):
        realized_risk_source_from_risk_metrics_report(malformed)


def test_drawdown_adapter_rejects_response_without_trust_fingerprint() -> None:
    malformed = _drawdown_response()
    metadata = malformed["metadata"]
    assert isinstance(metadata, dict)
    del metadata["request_fingerprint"]

    with pytest.raises(RiskOutcomeSourceError, match="request_fingerprint"):
        realized_drawdown_source_from_drawdown_response(malformed)


def test_concentration_adapter_rejects_response_without_trust_fingerprint() -> None:
    malformed = _concentration_response()
    metadata = malformed["metadata"]
    assert isinstance(metadata, dict)
    del metadata["request_fingerprint"]

    with pytest.raises(RiskOutcomeSourceError, match="request_fingerprint"):
        realized_concentration_source_from_concentration_response(malformed)


def test_rolling_adapter_rejects_response_without_trust_fingerprint() -> None:
    malformed = _rolling_response()
    metadata = malformed["metadata"]
    assert isinstance(metadata, dict)
    del metadata["request_fingerprint"]

    with pytest.raises(RiskOutcomeSourceError, match="request_fingerprint"):
        realized_rolling_risk_source_from_rolling_response(malformed)


def test_historical_attribution_adapter_rejects_response_without_trust_fingerprint() -> None:
    malformed = _historical_attribution_response()
    metadata = malformed["metadata"]
    assert isinstance(metadata, dict)
    del metadata["request_fingerprint"]

    with pytest.raises(RiskOutcomeSourceError, match="request_fingerprint"):
        realized_historical_attribution_source_from_attribution_response(malformed)


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


def test_drawdown_adapter_rejects_missing_ready_max_drawdown_value() -> None:
    malformed = _drawdown_response()
    results = malformed["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    summary = ytd["summary"]
    assert isinstance(summary, dict)
    summary["max_drawdown"] = None

    with pytest.raises(RiskOutcomeSourceError, match="numeric max_drawdown value"):
        realized_drawdown_source_from_drawdown_response(malformed)


def test_concentration_adapter_rejects_missing_ready_measure_value() -> None:
    malformed = _concentration_response()
    risk_proxy = malformed["risk_proxy"]
    assert isinstance(risk_proxy, dict)
    risk_proxy["hhi_current"] = None

    with pytest.raises(RiskOutcomeSourceError, match="numeric hhi_current value"):
        realized_concentration_source_from_concentration_response(malformed)


def test_rolling_adapter_rejects_missing_ready_metric_value() -> None:
    malformed = _rolling_response()
    results = malformed["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    window = ytd["window_results"][0]  # type: ignore[index]
    assert isinstance(window, dict)
    summaries = window["metric_summaries"]
    assert isinstance(summaries, dict)
    volatility = summaries["ROLLING_VOLATILITY"]
    assert isinstance(volatility, dict)
    volatility["latest"] = None

    with pytest.raises(RiskOutcomeSourceError, match="ROLLING_VOLATILITY latest value"):
        realized_rolling_risk_source_from_rolling_response(malformed)


def test_historical_attribution_adapter_rejects_missing_ready_set_value() -> None:
    malformed = _historical_attribution_response()
    results = malformed["results"]
    assert isinstance(results, dict)
    ytd = results["YTD"]
    assert isinstance(ytd, dict)
    attribution_set = ytd["attribution_sets"][0]  # type: ignore[index]
    assert isinstance(attribution_set, dict)
    attribution_set["total_value"] = None

    with pytest.raises(RiskOutcomeSourceError, match="total_value value"):
        realized_historical_attribution_source_from_attribution_response(malformed)


def test_historical_attribution_contributor_measure_requires_group_key() -> None:
    with pytest.raises(RiskOutcomeSourceError, match="contributor_group_key"):
        realized_historical_attribution_source_from_attribution_response(
            _historical_attribution_response(),
            measure="contributor_component_contribution",
        )
