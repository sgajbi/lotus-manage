from typing import cast

from src.api.services import construction_source_analytics_posture
from src.api.services.construction_source_analytics_posture import (
    required_source_products,
    source_analytics_posture,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod


def test_source_analytics_posture_exports_expected_helpers() -> None:
    assert construction_source_analytics_posture.__all__ == [
        "required_source_products",
        "source_analytics_posture",
    ]


def test_source_analytics_posture_keeps_risk_method_source_product_required() -> None:
    required_products = required_source_products(method=ConstructionMethod.RISK_AWARE)
    posture = source_analytics_posture(
        method=ConstructionMethod.RISK_AWARE,
        authority_context=ConstructionAuthorityContext(),
    )

    risk_metrics = next(
        item for item in required_products if item["source_product_name"] == "RiskMetricsReport"
    )
    performance_products = [
        item for item in required_products if item["source_system"] == "lotus-performance"
    ]

    assert posture["risk_required_for_method"] is True
    assert posture["performance_required_for_method"] is False
    assert risk_metrics["required_for_ready"] is True
    assert all(item["required_for_ready"] is False for item in performance_products)


def test_source_analytics_posture_blocks_local_risk_performance_methodology_claims() -> None:
    required_products = required_source_products(method=ConstructionMethod.REGIME_STRESS_AWARE)
    posture = source_analytics_posture(
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        authority_context=ConstructionAuthorityContext(),
    )

    regime_pack = next(
        item
        for item in required_products
        if item["source_product_name"] == "RegimeScenarioPackEvaluation"
    )

    assert regime_pack["required_for_ready"] is True
    assert "LOCAL_TRACKING_ERROR_CALCULATION" in posture["blocked_capabilities"]
    assert "LOCAL_PERFORMANCE_ATTRIBUTION_CALCULATION" in posture["blocked_capabilities"]
    assert "RISK_PERFORMANCE_METHODOLOGY_REMAINS_SOURCE_OWNED" in posture["reason_codes"]


def test_source_analytics_posture_reuses_required_source_products() -> None:
    posture = source_analytics_posture(
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        authority_context=ConstructionAuthorityContext(),
    )

    assert cast(list[dict[str, object]], posture["required_source_products"]) == (
        required_source_products(method=ConstructionMethod.REGIME_STRESS_AWARE)
    )
