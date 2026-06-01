from decimal import Decimal

from src.api.services.construction_sustainability_supportability import (
    sustainability_preference_reason_codes,
    sustainability_preference_status,
)
from src.core.construction.models import (
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import EngineOptions, RebalanceResult
from src.core.rebalance.engine import run_simulation
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_sustainability_1",
            base_currency="USD",
            positions=[position("EQ_A", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[
                price("EQ_A", "100", "USD"),
                price("EQ_B", "100", "USD"),
            ]
        ),
        model=model_portfolio(
            targets=[
                target("EQ_A", "0.50"),
                target("EQ_B", "0.50"),
            ]
        ),
        shelf=[
            shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(),
        request_hash="hash-sustainability",
        correlation_id="corr-sustainability",
    )


def test_sustainability_supportability_marks_allocation_and_classification_review() -> None:
    result = _trade_result()
    context = AuthoritativeSustainabilityPreferenceContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_esg_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date="2026-06-01",
        preference_count=2,
        missing_data_families=[],
        preferences=[
            AuthoritativeSustainabilityPreference(
                preference_framework="BANK_SUSTAINABILITY",
                preference_code="MAX_EQUITY",
                preference_status="ACTIVE",
                preference_source="CLIENT_PROFILE",
                maximum_allocation=Decimal("0.50"),
                applies_to_asset_classes=["EQUITY"],
                effective_from="2026-01-01",
                preference_version=1,
            ),
            AuthoritativeSustainabilityPreference(
                preference_framework="BANK_SUSTAINABILITY",
                preference_code="EXCLUSION_REVIEW",
                preference_status="ACTIVE",
                preference_source="CLIENT_PROFILE",
                exclusion_codes=["THERMAL_COAL"],
                effective_from="2026-01-01",
                preference_version=1,
            ),
        ],
        reason_codes=["SUSTAINABILITY_PROFILE_READY"],
    )

    reason_codes = sustainability_preference_reason_codes(result=result, context=context)

    assert (
        sustainability_preference_status(result=result, context=context)
        == ConstructionMethodStatus.PENDING_REVIEW
    )
    assert "SUSTAINABILITY_ALLOCATION_REVIEW_MAX_EQUITY" in reason_codes
    assert "SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED" in reason_codes


def test_sustainability_supportability_degrades_without_source_profile() -> None:
    result = _trade_result()

    assert (
        sustainability_preference_status(result=result, context=None)
        == ConstructionMethodStatus.DEGRADED
    )
    assert sustainability_preference_reason_codes(result=result, context=None) == [
        "SUSTAINABILITY_PREFERENCE_PROFILE_UNAVAILABLE"
    ]


def test_sustainability_supportability_ignores_inactive_preferences() -> None:
    result = _trade_result()
    context = AuthoritativeSustainabilityPreferenceContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_sustainability_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date="2026-06-01",
        preference_count=1,
        missing_data_families=[],
        preferences=[
            AuthoritativeSustainabilityPreference(
                preference_framework="BANK_SUSTAINABILITY",
                preference_code="INACTIVE_EXCLUSION",
                preference_status="INACTIVE",
                preference_source="CLIENT_PROFILE",
                maximum_allocation=Decimal("0.10"),
                applies_to_asset_classes=["EQUITY"],
                exclusion_codes=["THERMAL_COAL"],
                effective_from="2026-01-01",
                preference_version=1,
            )
        ],
        reason_codes=["SUSTAINABILITY_PROFILE_READY"],
    )

    assert (
        sustainability_preference_status(result=result, context=context)
        == ConstructionMethodStatus.READY
    )
    assert sustainability_preference_reason_codes(result=result, context=context) == [
        "SUSTAINABILITY_PREFERENCE_PROFILE_APPLIED",
        "SUSTAINABILITY_PROFILE_READY",
    ]
