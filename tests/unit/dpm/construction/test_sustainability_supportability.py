from decimal import Decimal

from src.api.services.construction_sustainability_supportability import (
    _maximum_allocation_breached,
    _minimum_allocation_breached,
    _missing_sustainability_family_reason_codes,
    _preference_allocation_breached,
    _preference_allocation_weight,
    _sustainability_allocation_review_reason_codes,
    _sustainability_applied_reason_codes,
    _sustainability_classification_reason_codes,
    _sustainability_supportability_reason_codes,
    active_sustainability_preferences,
    allocation_weight_by_asset_class,
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


def test_allocation_weight_by_asset_class_projects_post_trade_weights() -> None:
    result = _trade_result()

    weight_by_asset_class = allocation_weight_by_asset_class(result=result)

    assert set(weight_by_asset_class) == {"cash", "equity"}
    assert weight_by_asset_class["equity"] > Decimal("0")


def test_sustainability_preference_allocation_weight_sums_target_asset_classes() -> None:
    preference = AuthoritativeSustainabilityPreference(
        preference_framework="BANK_SUSTAINABILITY",
        preference_code="MULTI_ASSET_MINIMUM",
        preference_status="ACTIVE",
        preference_source="CLIENT_PROFILE",
        applies_to_asset_classes=["EQUITY", "BOND"],
        minimum_allocation=Decimal("0.65"),
        effective_from="2026-01-01",
        preference_version=1,
    )

    assert _preference_allocation_weight(
        preference=preference,
        weight_by_asset_class={
            "equity": Decimal("0.40"),
            "bond": Decimal("0.20"),
            "cash": Decimal("0.40"),
        },
    ) == Decimal("0.60")


def test_sustainability_preference_allocation_threshold_helpers_are_strict() -> None:
    preference = AuthoritativeSustainabilityPreference(
        preference_framework="BANK_SUSTAINABILITY",
        preference_code="EQUITY_RANGE",
        preference_status="ACTIVE",
        preference_source="CLIENT_PROFILE",
        applies_to_asset_classes=["EQUITY"],
        minimum_allocation=Decimal("0.40"),
        maximum_allocation=Decimal("0.60"),
        effective_from="2026-01-01",
        preference_version=1,
    )

    assert _minimum_allocation_breached(preference=preference, weight=Decimal("0.39")) is True
    assert _minimum_allocation_breached(preference=preference, weight=Decimal("0.40")) is False
    assert _maximum_allocation_breached(preference=preference, weight=Decimal("0.61")) is True
    assert _maximum_allocation_breached(preference=preference, weight=Decimal("0.60")) is False


def test_sustainability_preference_allocation_breach_requires_asset_class_scope() -> None:
    preference = AuthoritativeSustainabilityPreference(
        preference_framework="BANK_SUSTAINABILITY",
        preference_code="CLASSIFICATION_ONLY",
        preference_status="ACTIVE",
        preference_source="CLIENT_PROFILE",
        maximum_allocation=Decimal("0.10"),
        effective_from="2026-01-01",
        preference_version=1,
    )

    assert (
        _preference_allocation_breached(
            preference=preference,
            weight_by_asset_class={"equity": Decimal("1.00")},
        )
        is False
    )


def test_sustainability_preference_allocation_breach_detects_minimum_and_maximum() -> None:
    minimum = AuthoritativeSustainabilityPreference(
        preference_framework="BANK_SUSTAINABILITY",
        preference_code="MIN_BOND",
        preference_status="ACTIVE",
        preference_source="CLIENT_PROFILE",
        applies_to_asset_classes=["BOND"],
        minimum_allocation=Decimal("0.30"),
        effective_from="2026-01-01",
        preference_version=1,
    )
    maximum = AuthoritativeSustainabilityPreference(
        preference_framework="BANK_SUSTAINABILITY",
        preference_code="MAX_EQUITY",
        preference_status="ACTIVE",
        preference_source="CLIENT_PROFILE",
        applies_to_asset_classes=["EQUITY"],
        maximum_allocation=Decimal("0.50"),
        effective_from="2026-01-01",
        preference_version=1,
    )

    assert _preference_allocation_breached(
        preference=minimum,
        weight_by_asset_class={"bond": Decimal("0.20")},
    )
    assert _preference_allocation_breached(
        preference=maximum,
        weight_by_asset_class={"equity": Decimal("0.60")},
    )


def test_sustainability_reason_code_helpers_project_review_families() -> None:
    preference = AuthoritativeSustainabilityPreference(
        preference_framework="BANK_SUSTAINABILITY",
        preference_code="MAX_EQUITY",
        preference_status="ACTIVE",
        preference_source="CLIENT_PROFILE",
        applies_to_asset_classes=["EQUITY"],
        maximum_allocation=Decimal("0.50"),
        effective_from="2026-01-01",
        preference_version=1,
    )

    assert _sustainability_supportability_reason_codes(ConstructionMethodStatus.READY) == []
    assert _sustainability_supportability_reason_codes(ConstructionMethodStatus.DEGRADED) == [
        "SUSTAINABILITY_PREFERENCE_PROFILE_DEGRADED"
    ]
    assert _missing_sustainability_family_reason_codes(["classification", "scores"]) == [
        "MISSING_CLASSIFICATION",
        "MISSING_SCORES",
    ]
    assert _sustainability_allocation_review_reason_codes([preference]) == [
        "SUSTAINABILITY_ALLOCATION_REVIEW_MAX_EQUITY"
    ]
    assert _sustainability_classification_reason_codes(True) == [
        "SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED"
    ]
    assert _sustainability_classification_reason_codes(False) == []
    assert _sustainability_applied_reason_codes(
        breaches=[],
        classification_review_required=False,
    ) == ["SUSTAINABILITY_PREFERENCE_PROFILE_APPLIED"]
    assert (
        _sustainability_applied_reason_codes(
            breaches=[preference],
            classification_review_required=False,
        )
        == []
    )


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


def test_active_sustainability_preferences_filters_source_status() -> None:
    context = AuthoritativeSustainabilityPreferenceContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_sustainability_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date="2026-06-01",
        preference_count=2,
        missing_data_families=[],
        preferences=[
            AuthoritativeSustainabilityPreference(
                preference_framework="BANK_SUSTAINABILITY",
                preference_code="ACTIVE_PREF",
                preference_status="ACTIVE",
                preference_source="CLIENT_PROFILE",
                effective_from="2026-01-01",
                preference_version=1,
            ),
            AuthoritativeSustainabilityPreference(
                preference_framework="BANK_SUSTAINABILITY",
                preference_code="INACTIVE_PREF",
                preference_status="INACTIVE",
                preference_source="CLIENT_PROFILE",
                effective_from="2026-01-01",
                preference_version=1,
            ),
        ],
        reason_codes=["SUSTAINABILITY_PROFILE_READY"],
    )

    assert [
        preference.preference_code
        for preference in active_sustainability_preferences(context=context)
    ] == ["ACTIVE_PREF"]
