from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.construction import (
    AuthoritativeClientRestrictionContext,
    AuthoritativePerformanceContext,
    AuthoritativeRegimeStressContext,
    AuthoritativeRiskContext,
    AuthoritativeSustainabilityPreferenceContext,
    AuthoritativeTransactionCostContext,
)
from src.core.proof_packs.source_analytics import (
    ProofPackAnalyticsFamily,
    _SOURCE_ANALYTICS_BUILDERS,
    source_analytics_for_context,
)


def _risk_context() -> dict[str, object]:
    return AuthoritativeRiskContext(
        supportability_status="READY",
        source_system="lotus-risk",
        source_id="risk-context-001",
    ).model_dump(mode="json", exclude_none=True)


def _performance_context() -> dict[str, object]:
    return AuthoritativePerformanceContext(
        supportability_status="READY",
        source_system="lotus-performance",
        source_id="performance-context-001",
    ).model_dump(mode="json", exclude_none=True)


def _transaction_cost_context() -> dict[str, object]:
    return AuthoritativeTransactionCostContext(
        supportability_status="READY",
        source_system="lotus-core",
        source_id="transaction-cost-context-001",
        as_of_date=date(2026, 5, 3),
        window_start_date=date(2026, 4, 3),
        window_end_date=date(2026, 5, 3),
        returned_curve_point_count=0,
    ).model_dump(mode="json", exclude_none=True)


def _client_restriction_context() -> dict[str, object]:
    return AuthoritativeClientRestrictionContext(
        supportability_status="READY",
        source_system="lotus-core",
        source_id="client-restriction-context-001",
        portfolio_id="pf_001",
        client_id="client_001",
        mandate_id="mandate_001",
        as_of_date=date(2026, 5, 3),
        restriction_count=0,
    ).model_dump(mode="json", exclude_none=True)


def _sustainability_preference_context() -> dict[str, object]:
    return AuthoritativeSustainabilityPreferenceContext(
        supportability_status="READY",
        source_system="lotus-core",
        source_id="sustainability-preference-context-001",
        portfolio_id="pf_001",
        client_id="client_001",
        mandate_id="mandate_001",
        as_of_date=date(2026, 5, 3),
        preference_count=0,
    ).model_dump(mode="json", exclude_none=True)


def _regime_stress_context() -> dict[str, object]:
    return AuthoritativeRegimeStressContext(
        supportability_status="READY",
        source_system="lotus-risk",
        scenario_pack_id="CIO_REGIME_2026_Q4",
        worst_case_loss_pct=Decimal("0.0600"),
        maximum_allowed_loss_pct=Decimal("0.1200"),
        cio_approval_ref="CIO-APPROVAL-2026-Q4",
        effective_from=date(2026, 10, 1),
        applicable_mandate_ids=["mandate_001"],
    ).model_dump(mode="json", exclude_none=True)


@pytest.mark.parametrize(
    ("family", "source_context", "expected_source_hash_key"),
    [
        ("risk", _risk_context(), "risk_context"),
        ("performance", _performance_context(), "performance_context"),
        ("transaction_cost", _transaction_cost_context(), "transaction_cost_context"),
        ("client_restriction", _client_restriction_context(), "client_restriction_context"),
        (
            "sustainability_preference",
            _sustainability_preference_context(),
            "sustainability_preference_context",
        ),
        ("regime_stress", _regime_stress_context(), "regime_stress_context"),
    ],
)
def test_source_analytics_for_context_dispatches_all_supported_families(
    family: ProofPackAnalyticsFamily,
    source_context: dict[str, object],
    expected_source_hash_key: str,
) -> None:
    analytics = source_analytics_for_context(source_context=source_context, family=family)

    assert analytics is not None
    assert analytics.family == family
    assert analytics.source_hash_key == expected_source_hash_key


def test_source_analytics_dispatch_registry_covers_supported_families() -> None:
    assert set(_SOURCE_ANALYTICS_BUILDERS) == {
        "risk",
        "performance",
        "transaction_cost",
        "client_restriction",
        "sustainability_preference",
        "regime_stress",
    }


def test_source_analytics_for_context_skips_empty_context_without_dispatch() -> None:
    assert source_analytics_for_context(source_context={}, family="risk") is None
