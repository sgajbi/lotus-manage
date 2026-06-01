from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_esg_supportability import (
    client_restriction_reason_codes,
    client_restriction_status,
    restriction_matches_intent,
    sustainability_preference_reason_codes,
    sustainability_preference_status,
)
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
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
    valid_api_payload,
)


def _request() -> RebalanceRequest:
    request = RebalanceRequest.model_validate(valid_api_payload())
    return request.model_copy(
        update={
            "shelf_entries": [
                *request.shelf_entries,
                shelf_entry(
                    "EQ_B",
                    status="APPROVED",
                    asset_class="EQUITY",
                    issuer_id="ISSUER_TECH",
                ).model_copy(update={"attributes": {"country_of_risk": "US"}}),
            ]
        }
    )


def _trade_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_esg_1",
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
        request_hash="hash-esg",
        correlation_id="corr-esg",
    )


def _restriction_rule(**updates) -> AuthoritativeClientRestrictionRule:
    values = {
        "restriction_scope": "instrument",
        "restriction_code": "NO_BUY_EQ_B",
        "restriction_status": "ACTIVE",
        "restriction_source": "CLIENT_PROFILE",
        "applies_to_buy": True,
        "applies_to_sell": False,
        "instrument_ids": ["EQ_B"],
        "effective_from": "2026-01-01",
        "restriction_version": 1,
    }
    values.update(updates)
    return AuthoritativeClientRestrictionRule(**values)


def test_client_restriction_supportability_blocks_matching_active_buy_rule() -> None:
    request = _request()
    result = _trade_result()
    context = AuthoritativeClientRestrictionContext(
        supportability_status=ConstructionMethodStatus.DEGRADED,
        source_system="lotus-core",
        portfolio_id="pf_esg_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date="2026-06-01",
        restriction_count=1,
        missing_data_families=["issuer_classification"],
        restrictions=[_restriction_rule()],
        reason_codes=["CLIENT_RESTRICTION_PROFILE_READY"],
    )

    reason_codes = client_restriction_reason_codes(
        request=request,
        result=result,
        context=context,
    )

    assert (
        client_restriction_status(request=request, result=result, context=context)
        == ConstructionMethodStatus.BLOCKED
    )
    assert "CLIENT_RESTRICTION_VIOLATION_NO_BUY_EQ_B" in reason_codes
    assert "MISSING_ISSUER_CLASSIFICATION" in reason_codes


def test_restriction_matching_uses_default_asset_issuer_and_country_scopes() -> None:
    intent = next(intent for intent in _trade_result().intents if intent.instrument_id == "EQ_B")
    shelf = shelf_entry(
        "EQ_B",
        status="APPROVED",
        asset_class="EQUITY",
        issuer_id="ISSUER_TECH",
    ).model_copy(update={"attributes": {"country_of_risk": "US"}})

    assert restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=_restriction_rule(instrument_ids=[]),
    )
    assert restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=_restriction_rule(instrument_ids=[], asset_classes=["EQUITY"]),
    )
    assert restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=_restriction_rule(instrument_ids=[], issuer_ids=["ISSUER_TECH"]),
    )
    assert restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=_restriction_rule(instrument_ids=[], country_codes=["US"]),
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
