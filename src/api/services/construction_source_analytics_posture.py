from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod


def source_analytics_posture(
    *,
    method: ConstructionMethod,
    authority_context: ConstructionAuthorityContext,
) -> dict[str, object]:
    return {
        "product_family": "CONSTRUCTION_ALTERNATIVE_RISK_PERFORMANCE_CONTEXT",
        "risk_context_preservation": "SUPPORTED_WHEN_SUPPLIED",
        "performance_context_preservation": "SUPPORTED_WHEN_SUPPLIED",
        "risk_context_supplied": authority_context.risk_context is not None,
        "performance_context_supplied": authority_context.performance_context is not None,
        "risk_required_for_method": method == ConstructionMethod.RISK_AWARE,
        "performance_required_for_method": False,
        "required_source_products": required_source_products(method=method),
        "blocked_capabilities": [
            "LOCAL_TRACKING_ERROR_CALCULATION",
            "LOCAL_VOLATILITY_CALCULATION",
            "LOCAL_DRAWDOWN_CALCULATION",
            "LOCAL_STRESS_CONTRIBUTION_CALCULATION",
            "LOCAL_PERFORMANCE_ATTRIBUTION_CALCULATION",
            "LOCAL_BENCHMARK_RELATIVE_PERFORMANCE_CALCULATION",
        ],
        "reason_codes": [
            "SOURCE_ANALYTICS_CONTEXT_PRESERVED_WHEN_SUPPLIED",
            "RISK_PERFORMANCE_METHODOLOGY_REMAINS_SOURCE_OWNED",
        ],
    }


def required_source_products(method: ConstructionMethod) -> list[dict[str, object]]:
    return [
        {
            "source_system": "lotus-risk",
            "source_product_name": "RiskMetricsReport",
            "source_product_version": "v1",
            "required_for_ready": method == ConstructionMethod.RISK_AWARE,
        },
        {
            "source_system": "lotus-risk",
            "source_product_name": "DrawdownAnalyticsReport",
            "source_product_version": "v1",
            "required_for_ready": False,
        },
        {
            "source_system": "lotus-risk",
            "source_product_name": "HistoricalRiskAttribution",
            "source_product_version": "v1",
            "required_for_ready": False,
        },
        {
            "source_system": "lotus-risk",
            "source_product_name": "RegimeScenarioPackEvaluation",
            "source_product_version": "v1",
            "required_for_ready": method == ConstructionMethod.REGIME_STRESS_AWARE,
        },
        {
            "source_system": "lotus-performance",
            "source_product_name": "BenchmarkExposureContext",
            "source_product_version": "v1",
            "required_for_ready": False,
        },
        {
            "source_system": "lotus-performance",
            "source_product_name": "ContributionAnalytics",
            "source_product_version": "v1",
            "required_for_ready": False,
        },
        {
            "source_system": "lotus-performance",
            "source_product_name": "AttributionAnalytics",
            "source_product_version": "v1",
            "required_for_ready": False,
        },
    ]


__all__ = [
    "required_source_products",
    "source_analytics_posture",
]
