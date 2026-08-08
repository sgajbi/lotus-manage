from __future__ import annotations

from decimal import Decimal

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSet,
    ConstructionComparisonMetrics,
)
from src.core.construction.vocabulary import ConstructionMethod, ConstructionMethodStatus
from src.core.waves import DpmRebalanceWaveItem, DpmWaveSourceRef
from src.core.waves import source_analytics as source_analytics_module
from src.core.waves.source_analytics import (
    aggregate_wave_source_analytics,
    build_source_analytics_from_alternative_set,
)


def test_build_source_analytics_from_alternative_set_preserves_source_owned_evidence() -> None:
    alternative_set = ConstructionAlternativeSet(
        alternative_set_id="cas_source_analytics_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of="2026-05-19",
        status=ConstructionMethodStatus.DEGRADED,
        alternatives=[
            _alternative(
                "alt_1",
                {
                    "authority_context": {
                        "risk_context": {
                            "supportability_status": "READY",
                            "source_system": "lotus-risk",
                            "source_product_name": "ConcentrationRiskReport",
                            "source_product_version": "v1",
                            "source_id": "risk-concentration-001",
                            "content_hash": "sha256:risk-001",
                            "tracking_error": Decimal("0.042"),
                            "maximum_drawdown": Decimal("-0.125"),
                            "stress_contribution_count": 7,
                            "attribution_contributor_count": 5,
                            "concentration_hhi_delta": Decimal("125.5"),
                            "reason_codes": ["LOTUS_RISK_CONCENTRATION_READY"],
                        },
                        "performance_context": {
                            "supportability_status": "DEGRADED",
                            "source_system": "lotus-performance",
                            "source_product_name": "PerformanceBenchmarkContext",
                            "source_product_version": "v1",
                            "source_id": "perf-benchmark-001",
                            "benchmark_id": "BMK_GLOBAL_BAL",
                            "active_return": Decimal("-0.018"),
                            "benchmark_relative_return": Decimal("-0.018"),
                            "contribution_total_return": Decimal("0.021"),
                            "attribution_selection": Decimal("-0.006"),
                            "currency_attribution_total": Decimal("0.0025"),
                            "reason_codes": ["PERFORMANCE_BENCHMARK_PARTIAL"],
                        },
                    }
                },
            )
        ],
    )

    analytics = build_source_analytics_from_alternative_set(alternative_set)

    assert analytics["risk"]["supportability_state"] == "READY"
    assert analytics["risk"]["source_refs"][0]["source_type"] == "ConcentrationRiskReport"
    assert analytics["risk"]["source_measures"] == {
        "attribution_contributor_count": ["5"],
        "concentration_hhi_delta": ["125.5"],
        "maximum_drawdown": ["-0.125"],
        "stress_contribution_count": ["7"],
        "tracking_error": ["0.042"],
    }
    assert analytics["performance"]["supportability_state"] == "DEGRADED"
    assert analytics["performance"]["source_measures"] == {
        "active_return": ["-0.018"],
        "attribution_selection": ["-0.006"],
        "benchmark_id": ["BMK_GLOBAL_BAL"],
        "benchmark_relative_return": ["-0.018"],
        "contribution_total_return": ["0.021"],
        "currency_attribution_total": ["0.0025"],
    }


def test_aggregate_wave_source_analytics_deduplicates_refs_and_counts_posture() -> None:
    source_analytics = {
        "risk": {
            "supportability_state": "READY",
            "source_systems": ["lotus-risk"],
            "source_refs": [
                {
                    "source_system": "lotus-risk",
                    "source_type": "ConcentrationRiskReport",
                    "source_id": "risk-concentration-001",
                    "source_version": "v1",
                    "supportability_state": "READY",
                }
            ],
            "reason_codes": ["LOTUS_RISK_CONCENTRATION_READY"],
            "source_measures": {"tracking_error": ["0.042"]},
        }
    }
    items = [
        _wave_item("dwi_001", source_analytics),
        _wave_item("dwi_002", source_analytics),
        _wave_item(
            "dwi_003",
            {
                "risk": {
                    **source_analytics["risk"],
                    "supportability_state": "DEGRADED",
                    "reason_codes": ["LOTUS_RISK_CONCENTRATION_PARTIAL"],
                }
            },
        ),
    ]

    summary = aggregate_wave_source_analytics(items)[0]

    assert summary.source_family == "RISK"
    assert summary.supportability_state == "DEGRADED"
    assert summary.item_count == 3
    assert summary.ready_item_count == 2
    assert summary.degraded_item_count == 1
    assert summary.source_refs == [
        DpmWaveSourceRef(
            source_system="lotus-risk",
            source_type="ConcentrationRiskReport",
            source_id="risk-concentration-001",
            source_version="v1",
            supportability_state="READY",
        )
    ]
    assert summary.reason_codes == [
        "LOTUS_RISK_CONCENTRATION_PARTIAL",
        "LOTUS_RISK_CONCENTRATION_READY",
    ]


def test_aggregate_wave_source_analytics_rolls_up_families_independently() -> None:
    items = [
        _wave_item(
            "dwi_004",
            {
                "risk": {
                    "supportability_state": "BLOCKED",
                    "source_systems": ["lotus-risk"],
                    "source_refs": [
                        {
                            "source_system": "lotus-risk",
                            "source_type": "RiskAuthorityContext",
                            "source_id": "risk-context-004",
                            "supportability_state": "BLOCKED",
                        }
                    ],
                    "reason_codes": ["RISK_SOURCE_BLOCKED"],
                    "source_measures": {
                        "tracking_error": ["0.071"],
                        "stress_loss_pct": ["-0.13"],
                    },
                },
                "performance": {
                    "supportability_state": "PENDING_REVIEW",
                    "source_systems": ["lotus-performance"],
                    "source_refs": [
                        {
                            "source_system": "lotus-performance",
                            "source_type": "PerformanceAuthorityContext",
                            "source_id": "performance-context-004",
                            "supportability_state": "PENDING_REVIEW",
                        }
                    ],
                    "reason_codes": ["PERFORMANCE_REVIEW_REQUIRED"],
                    "source_measures": {
                        "active_return": ["-0.018"],
                        "benchmark_id": ["BMK_GLOBAL_BAL"],
                    },
                },
            },
        )
    ]

    summaries_by_family = {
        summary.source_family: summary for summary in aggregate_wave_source_analytics(items)
    }

    assert summaries_by_family["RISK"].supportability_state == "BLOCKED"
    assert summaries_by_family["RISK"].blocked_item_count == 1
    assert summaries_by_family["RISK"].source_measures == {
        "stress_loss_pct": ["-0.13"],
        "tracking_error": ["0.071"],
    }
    assert summaries_by_family["PERFORMANCE"].supportability_state == "PENDING_REVIEW"
    assert summaries_by_family["PERFORMANCE"].pending_review_item_count == 1
    assert summaries_by_family["PERFORMANCE"].source_measures == {
        "active_return": ["-0.018"],
        "benchmark_id": ["BMK_GLOBAL_BAL"],
    }


def test_family_item_source_analytics_skips_missing_and_non_mapping_diagnostics() -> None:
    items = [
        DpmRebalanceWaveItem(
            wave_item_id="dwi_missing",
            portfolio_id="PF_MISSING",
            state="SIMULATED",
            diagnostics={},
        ),
        DpmRebalanceWaveItem(
            wave_item_id="dwi_malformed",
            portfolio_id="PF_MALFORMED",
            state="SIMULATED",
            diagnostics={"source_analytics": "not-a-mapping"},
        ),
        _wave_item(
            "dwi_ready",
            {"risk": {"supportability_state": "READY"}},
        ),
    ]

    assert source_analytics_module._family_item_source_analytics(
        items=items,
        family="risk",
    ) == [{"supportability_state": "READY"}]


def test_source_analytics_from_alternative_uses_enrichment_fallbacks() -> None:
    alternative_set = ConstructionAlternativeSet(
        alternative_set_id="cas_source_analytics_fallback",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of="2026-05-19",
        status=ConstructionMethodStatus.DEGRADED,
        alternatives=[],
    )

    analytics = source_analytics_module._source_analytics_from_alternative(
        alternative_set=alternative_set,
        alternative_diagnostics={
            "authority_context": {
                "risk_context": {
                    "source_product_name": "RiskAuthorityContext",
                    "tracking_error": Decimal("0.051"),
                }
            },
            "enrichment_summary": {
                "risk_status": "pending_review",
                "reason_codes": ["RISK_SOURCE_REVIEW_REQUIRED"],
            },
        },
        family="risk",
    )

    assert analytics == {
        "supportability_state": "PENDING_REVIEW",
        "source_systems": ["lotus-risk"],
        "source_refs": [
            {
                "source_system": "lotus-risk",
                "source_type": "RiskAuthorityContext",
                "source_id": "cas_source_analytics_fallback",
                "source_version": None,
                "supportability_state": "DEGRADED",
                "content_hash": None,
                "source_batch_fingerprint": None,
                "selection_basis": None,
            }
        ],
        "reason_codes": ["RISK_SOURCE_REVIEW_REQUIRED"],
        "source_measures": {"tracking_error": ["0.051"]},
    }


def test_source_analytics_from_alternative_skips_missing_source_context() -> None:
    alternative_set = ConstructionAlternativeSet(
        alternative_set_id="cas_source_analytics_missing",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of="2026-05-19",
        status=ConstructionMethodStatus.DEGRADED,
        alternatives=[],
    )

    assert (
        source_analytics_module._source_analytics_from_alternative(
            alternative_set=alternative_set,
            alternative_diagnostics={"authority_context": {"risk_context": "not-a-mapping"}},
            family="risk",
        )
        is None
    )


def test_analytics_source_ref_preserves_source_product_metadata() -> None:
    source_ref = source_analytics_module._analytics_source_ref(
        source_context={
            "source_product_name": "ConcentrationRiskReport",
            "source_product_version": "v1",
            "source_id": "risk-concentration-001",
            "supportability_status": "READY",
            "content_hash": "sha256:risk-001",
        },
        source_system="lotus-risk",
        family="risk",
        fallback_id="cas_source_analytics_001",
    )

    assert source_ref == DpmWaveSourceRef(
        source_system="lotus-risk",
        source_type="ConcentrationRiskReport",
        source_id="risk-concentration-001",
        source_version="v1",
        supportability_state="READY",
        content_hash="sha256:risk-001",
    )


def test_analytics_source_ref_defaults_missing_metadata_by_family() -> None:
    risk_ref = source_analytics_module._analytics_source_ref(
        source_context={},
        source_system="lotus-risk",
        family="risk",
        fallback_id="cas_source_analytics_001",
    )
    performance_ref = source_analytics_module._analytics_source_ref(
        source_context={"content_hash": ""},
        source_system="lotus-performance",
        family="performance",
        fallback_id="cas_source_analytics_001",
    )

    assert risk_ref.source_type == "RISK_AUTHORITY_CONTEXT"
    assert risk_ref.source_id == "cas_source_analytics_001"
    assert risk_ref.source_version is None
    assert risk_ref.supportability_state == "DEGRADED"
    assert risk_ref.content_hash is None
    assert performance_ref.source_type == "PERFORMANCE_AUTHORITY_CONTEXT"
    assert performance_ref.content_hash is None


def _alternative(
    alternative_id: str,
    diagnostics: dict[str, object],
) -> ConstructionAlternative:
    return ConstructionAlternative(
        alternative_id=alternative_id,
        method=ConstructionMethod.RISK_AWARE,
        method_status=ConstructionMethodStatus.DEGRADED,
        summary="Source-aware construction alternative.",
        objective_trace=[],
        constraint_trace=[],
        comparison_metrics=ConstructionComparisonMetrics(
            drift_before=Decimal("0.10"),
            drift_after=Decimal("0.05"),
            drift_reduction=Decimal("0.05"),
            turnover_weight=Decimal("0.02"),
            trade_count=1,
        ),
        diagnostics=diagnostics,
    )


def _wave_item(
    wave_item_id: str,
    source_analytics: dict[str, object],
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=wave_item_id,
        portfolio_id=f"PF_{wave_item_id}",
        state="SIMULATED",
        diagnostics={"source_analytics": source_analytics},
    )
