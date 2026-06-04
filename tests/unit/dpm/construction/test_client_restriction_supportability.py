from src.api.request_models import RebalanceRequest
from src.api.services.construction_client_restriction_supportability import (
    active_applicable_restrictions,
    client_restriction_reason_codes,
    client_restriction_status,
    restriction_matches_intent,
)
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
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
            portfolio_id="pf_restriction_1",
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
        request_hash="hash-restriction",
        correlation_id="corr-restriction",
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
        portfolio_id="pf_restriction_1",
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


def test_client_restriction_supportability_degrades_without_source_profile() -> None:
    request = _request()
    result = _trade_result()

    assert (
        client_restriction_status(request=request, result=result, context=None)
        == ConstructionMethodStatus.DEGRADED
    )
    assert client_restriction_reason_codes(request=request, result=result, context=None) == [
        "CLIENT_RESTRICTION_PROFILE_UNAVAILABLE"
    ]


def test_client_restriction_supportability_ignores_inactive_and_non_applicable_rules() -> None:
    request = _request()
    result = _trade_result()
    context = AuthoritativeClientRestrictionContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_restriction_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date="2026-06-01",
        restriction_count=2,
        missing_data_families=[],
        restrictions=[
            _restriction_rule(restriction_status="INACTIVE"),
            _restriction_rule(restriction_code="SELL_ONLY_EQ_B", applies_to_buy=False),
        ],
        reason_codes=["CLIENT_RESTRICTION_PROFILE_READY"],
    )

    assert (
        client_restriction_status(request=request, result=result, context=context)
        == ConstructionMethodStatus.READY
    )
    assert client_restriction_reason_codes(request=request, result=result, context=context) == [
        "CLIENT_RESTRICTION_PROFILE_APPLIED",
        "CLIENT_RESTRICTION_PROFILE_READY",
    ]


def test_active_applicable_restrictions_filter_status_and_trade_side() -> None:
    restrictions = [
        _restriction_rule(
            restriction_code="ACTIVE_BUY", applies_to_buy=True, applies_to_sell=False
        ),
        _restriction_rule(
            restriction_code="ACTIVE_SELL", applies_to_buy=False, applies_to_sell=True
        ),
        _restriction_rule(restriction_code="INACTIVE_BUY", restriction_status="INACTIVE"),
        _restriction_rule(restriction_code="BUY_DISABLED", applies_to_buy=False),
    ]

    buy_restrictions = active_applicable_restrictions(
        restrictions=restrictions,
        trade_side="BUY",
    )
    sell_restrictions = active_applicable_restrictions(
        restrictions=restrictions,
        trade_side="SELL",
    )

    assert [restriction.restriction_code for restriction in buy_restrictions] == ["ACTIVE_BUY"]
    assert [restriction.restriction_code for restriction in sell_restrictions] == ["ACTIVE_SELL"]


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
