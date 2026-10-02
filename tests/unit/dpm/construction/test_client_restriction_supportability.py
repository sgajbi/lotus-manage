from datetime import date

import pytest

from src.api.request_models import RebalanceRequest
from src.api.services.construction_client_restriction_supportability import (
    active_applicable_restrictions,
    client_restriction_reason_codes,
    client_restriction_status,
    restriction_has_scope,
    restriction_matches_instrument,
    restriction_matches_intent,
    restriction_matches_shelf,
    shelf_country_code,
    shelf_entries_by_instrument,
    violated_client_restrictions,
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
        as_of_date=date(2026, 6, 1),
    )
    sell_restrictions = active_applicable_restrictions(
        restrictions=restrictions,
        trade_side="SELL",
        as_of_date=date(2026, 6, 1),
    )

    assert [restriction.restriction_code for restriction in buy_restrictions] == ["ACTIVE_BUY"]
    assert [restriction.restriction_code for restriction in sell_restrictions] == ["ACTIVE_SELL"]


def test_restriction_lifecycle_includes_effective_boundaries_only() -> None:
    restrictions = [
        _restriction_rule(
            restriction_code="CURRENT", effective_from="2026-06-01", effective_to="2026-06-30"
        ),
        _restriction_rule(restriction_code="FUTURE", effective_from="2026-07-01"),
        _restriction_rule(restriction_code="EXPIRED", effective_to="2026-05-31"),
    ]
    for as_of_date in (date(2026, 6, 1), date(2026, 6, 30)):
        assert [
            rule.restriction_code
            for rule in active_applicable_restrictions(
                restrictions=restrictions, trade_side="BUY", as_of_date=as_of_date
            )
        ] == ["CURRENT"]
    assert active_applicable_restrictions(
        restrictions=restrictions, trade_side="BUY", as_of_date=date(2026, 5, 31)
    ) == [restrictions[2]]


@pytest.mark.parametrize(
    ("rule_updates", "expected_missing"),
    [
        ({"instrument_ids": [], "asset_classes": ["EQUITY"]}, "asset_class_classification"),
        ({"instrument_ids": [], "issuer_ids": ["ISSUER_TECH"]}, "issuer_classification"),
        ({"instrument_ids": [], "country_codes": ["US"]}, "country_classification"),
    ],
)
def test_active_rule_with_missing_shelf_classification_degrades_instead_of_permitting(
    rule_updates, expected_missing
) -> None:
    base_request = _request()
    missing_shelf = base_request.shelf_entries[-1].model_copy(
        update={"asset_class": "UNKNOWN", "issuer_id": None, "attributes": {}}
    )
    request = base_request.model_copy(
        update={"shelf_entries": [*base_request.shelf_entries[:-1], missing_shelf]}
    )
    result = _trade_result()
    context = AuthoritativeClientRestrictionContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_restriction_1",
        client_id="client-1",
        as_of_date="2026-06-01",
        restriction_count=1,
        restrictions=[_restriction_rule(**rule_updates)],
    )

    assert (
        client_restriction_status(request=request, result=result, context=context)
        == ConstructionMethodStatus.DEGRADED
    )
    assert f"MISSING_{expected_missing.upper()}" in client_restriction_reason_codes(
        request=request, result=result, context=context
    )


def test_verified_empty_profile_is_ready_but_reported_missing_family_is_not() -> None:
    request = _request()
    result = _trade_result()
    context = AuthoritativeClientRestrictionContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_restriction_1",
        client_id="client-1",
        as_of_date="2026-06-01",
        restriction_count=0,
        restrictions=[],
    )

    assert (
        client_restriction_status(request=request, result=result, context=context)
        == ConstructionMethodStatus.READY
    )
    missing = context.model_copy(update={"missing_data_families": ["client_restrictions"]})
    assert (
        client_restriction_status(request=request, result=result, context=missing)
        == ConstructionMethodStatus.DEGRADED
    )


@pytest.mark.parametrize(
    ("rule_updates", "expected_sides"),
    [
        ({"instrument_ids": ["EQ_B"]}, ["BUY"]),
        ({"instrument_ids": ["EQ_A"], "applies_to_buy": False, "applies_to_sell": True}, ["SELL"]),
        ({"instrument_ids": ["UNRELATED"]}, []),
        ({"instrument_ids": [], "restriction_scope": "client"}, ["BUY"]),
        ({"instrument_ids": [], "issuer_ids": ["ISSUER_TECH"]}, ["BUY"]),
        ({"instrument_ids": [], "country_codes": ["US"]}, ["BUY"]),
        ({"instrument_ids": [], "asset_classes": ["EQUITY"]}, ["BUY"]),
    ],
)
def test_hard_rule_buy_sell_global_and_scoped_applicability(rule_updates, expected_sides) -> None:
    context = AuthoritativeClientRestrictionContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        portfolio_id="pf_restriction_1",
        client_id="client-1",
        as_of_date="2026-06-01",
        restriction_count=1,
        restrictions=[_restriction_rule(**rule_updates)],
    )
    violations = violated_client_restrictions(
        request=_request(), result=_trade_result(), context=context
    )

    assert [intent.side for intent, _ in violations] == expected_sides


def test_shelf_entries_by_instrument_indexes_request_shelf_entries() -> None:
    entries_by_instrument = shelf_entries_by_instrument(request=_request())

    assert entries_by_instrument["EQ_B"].issuer_id == "ISSUER_TECH"
    assert entries_by_instrument["EQ_B"].attributes["country_of_risk"] == "US"


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


def test_restriction_match_helpers_keep_scope_predicates_explicit() -> None:
    intent = next(intent for intent in _trade_result().intents if intent.instrument_id == "EQ_B")
    shelf = shelf_entry(
        "EQ_B",
        status="APPROVED",
        asset_class="EQUITY",
        issuer_id="ISSUER_TECH",
    ).model_copy(update={"attributes": {"country": "SG"}})

    assert not restriction_has_scope(_restriction_rule(instrument_ids=[]))
    assert restriction_has_scope(_restriction_rule(instrument_ids=["EQ_B"]))
    assert restriction_matches_instrument(
        intent=intent,
        restriction=_restriction_rule(instrument_ids=["EQ_B"]),
    )
    assert restriction_matches_shelf(
        shelf=shelf,
        restriction=_restriction_rule(instrument_ids=[], issuer_ids=["ISSUER_TECH"]),
    )
    assert shelf_country_code(shelf) == "SG"
