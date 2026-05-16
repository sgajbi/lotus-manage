from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.api.request_models import RebalanceRequest
import src.api.services.construction_service as construction_service
from src.core.construction import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    AuthoritativeCurrencyOverlayContext,
    AuthoritativeLiquidityCashflowProjection,
    AuthoritativeLiquidityContext,
    AuthoritativePerformanceContext,
    AuthoritativeRiskContext,
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
    AuthoritativeTransactionCostContext,
    AuthoritativeTransactionCostPoint,
    ConstructionAuthorityContext,
    ConstructionMethodStatus,
    estimate_transaction_cost,
    summarize_enrichment_posture,
)
from src.core.construction.repository import (
    ConstructionAlternativeSetNotFoundError,
    ConstructionIdempotencyConflictError,
)
from src.core.construction.vocabulary import ConstructionMethod
from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
    DpmResolvedSourceContext,
)
from src.core.models import EngineOptions, Money, RebalanceResult
from src.core.rebalance.engine import run_simulation
from src.infrastructure.construction import InMemoryConstructionRepository
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


def _trade_result(*, max_turnover_pct: Decimal | None = None) -> RebalanceResult:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_enrich_1",
        base_currency="USD",
        positions=[position("EQ_A", "10")],
        cash_balances=[cash("USD", "0")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("EQ_A", "100", "USD"),
            price("EQ_B", "100", "USD"),
        ]
    )
    model = model_portfolio(
        targets=[
            target("EQ_A", "0.50"),
            target("EQ_B", "0.50"),
        ]
    )
    shelf = [
        shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
    ]
    return run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(max_turnover_pct=max_turnover_pct),
        request_hash="hash_enrich_1",
        correlation_id="corr_enrich_1",
    )


def test_transaction_cost_estimate_is_labelled_local_and_reconciles_to_turnover_notional() -> None:
    result = _trade_result()

    cost = estimate_transaction_cost(result=result, basis_points=Decimal("10"))

    assert cost.currency == "USD"
    assert cost.amount == Decimal("1.00")


def test_enrichment_summary_blocks_required_tax_without_tax_impact() -> None:
    result = _trade_result()

    summary = summarize_enrichment_posture(result=result, tax_required=True)

    assert summary.tax_status == ConstructionMethodStatus.BLOCKED
    assert summary.cost_status == ConstructionMethodStatus.DEGRADED
    assert summary.risk_status == ConstructionMethodStatus.DEGRADED
    assert summary.performance_status == ConstructionMethodStatus.DEGRADED
    assert "TAX_LOTS_REQUIRED_BUT_NO_TAX_IMPACT" in summary.reason_codes
    assert "AUTHORITATIVE_TRANSACTION_COST_UNAVAILABLE" in summary.reason_codes
    assert "RISK_ENRICHMENT_UNAVAILABLE" in summary.reason_codes
    assert "PERFORMANCE_CONTEXT_UNAVAILABLE" in summary.reason_codes


def test_enrichment_summary_flags_missing_fx_and_cash_weight_sources() -> None:
    result = SimpleNamespace(
        tax_impact=None,
        diagnostics=SimpleNamespace(missing_fx_pairs=[("USD", "SGD")], dropped_intents=[]),
        after_simulated=SimpleNamespace(allocation_by_asset_class=[]),
    )

    summary = summarize_enrichment_posture(
        result=result,
        tax_required=False,
        risk_required=False,
        performance_required=False,
        authoritative_cost_available=True,
    )

    assert summary.fx_status == ConstructionMethodStatus.BLOCKED
    assert summary.liquidity_status == ConstructionMethodStatus.DEGRADED
    assert "FX_SOURCE_MISSING" in summary.reason_codes
    assert "CASH_WEIGHT_UNAVAILABLE" in summary.reason_codes


def test_construction_service_error_mapping_and_missing_set() -> None:
    with pytest.raises(ConstructionAlternativeSetNotFoundError):
        construction_service.get_construction_alternative_set(
            repository=InMemoryConstructionRepository(),
            alternative_set_id="missing",
        )

    conflict = construction_service.to_api_http_exception(
        ConstructionIdempotencyConflictError("CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT")
    )
    missing = construction_service.to_api_http_exception(
        ConstructionAlternativeSetNotFoundError("CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND")
    )
    unknown = construction_service.to_api_http_exception(RuntimeError("boom"))

    assert conflict.status_code == 409
    assert missing.status_code == 404
    assert unknown.status_code == 500
    assert unknown.detail == "RuntimeError"


def test_construction_service_supportability_helper_edges() -> None:
    request = RebalanceRequest.model_validate(valid_api_payload())
    result = _trade_result(max_turnover_pct=Decimal("0.01"))
    no_context = construction_service._authority_context_for_method(
        request=request,
        method=ConstructionMethod.LIQUIDITY_AWARE,
        result=result,
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=None,
        correlation_id="corr-helper",
    )
    risk_unavailable = construction_service._authority_context_for_method(
        request=request,
        method=ConstructionMethod.RISK_AWARE,
        result=result,
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_UnavailableRiskClient(),
        correlation_id="corr-helper",
    )
    liquidity_context = AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.99"),
        allowed_liquidity_tiers=["L1"],
        reason_codes=["LIQUIDITY_READY"],
    )

    assert no_context.liquidity_context is not None
    assert risk_unavailable.risk_context is None
    assert (
        construction_service._solver_method_status(result=result) == ConstructionMethodStatus.READY
    )
    assert (
        construction_service._liquidity_status(result=result, context=None)
        == ConstructionMethodStatus.DEGRADED
    )
    assert (
        construction_service._liquidity_status(result=result, context=liquidity_context)
        == ConstructionMethodStatus.PENDING_REVIEW
    )
    assert "LIQUIDITY_POLICY_CONTEXT_DERIVED" in construction_service._liquidity_reason_codes(
        result=result,
        context=None,
    )


def test_construction_as_of_date_uses_snapshot_identifier_date() -> None:
    request = RebalanceRequest.model_validate(valid_api_payload())
    request.market_data_snapshot.snapshot_id = "md_2026_05_06"

    assert (
        construction_service._construction_as_of_date(request=request).isoformat() == "2026-05-06"
    )


def test_cashflow_projection_context_marks_future_cash_pressure_pending() -> None:
    result = _trade_result()
    context = AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.03"),
        allowed_liquidity_tiers=["L1"],
        cashflow_projection=AuthoritativeLiquidityCashflowProjection(
            source_product_name="PortfolioCashflowProjection",
            source_product_version="v1",
            source_system="lotus-core",
            total_net_cashflow={"amount": "-50.00", "currency": "USD"},
            projection_start="2026-05-03",
            projection_end="2026-06-03",
            include_projected=True,
            source_batch_fingerprint="cashflow-projection:pf_enrich_1:2026-05-03",
            reason_codes=["CORE_CASHFLOW_PROJECTION_READY"],
        ),
        reason_codes=["LIQUIDITY_POLICY_READY"],
    )

    status = construction_service._liquidity_status(result=result, context=context)
    reason_codes = construction_service._liquidity_reason_codes(
        result=result,
        context=context,
    )

    assert status == ConstructionMethodStatus.PENDING_REVIEW
    assert "CORE_CASHFLOW_PROJECTION_READY" in reason_codes
    assert "CASHFLOW_PROJECTION_ADJUSTED_CASH_BELOW_POLICY" in reason_codes


def test_cashflow_projection_context_rejects_unusable_projection_posture() -> None:
    result = _trade_result()
    context = AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.03"),
        allowed_liquidity_tiers=["L1"],
        cashflow_projection=AuthoritativeLiquidityCashflowProjection(
            source_product_name="PortfolioCashflowProjection",
            source_product_version="v1",
            source_system="lotus-core",
            total_net_cashflow={"amount": "100.00", "currency": "SGD"},
            projection_start="2026-05-03",
            projection_end="2026-06-03",
            include_projected=False,
            data_quality_status=ConstructionMethodStatus.DEGRADED,
            reason_codes=["CORE_CASHFLOW_PROJECTION_STALE"],
        ),
        reason_codes=["LIQUIDITY_POLICY_READY"],
    )

    status = construction_service._liquidity_status(result=result, context=context)
    reason_codes = construction_service._liquidity_reason_codes(
        result=result,
        context=context,
    )

    assert status == ConstructionMethodStatus.DEGRADED
    assert "CASHFLOW_PROJECTION_CURRENCY_MISMATCH" in reason_codes
    assert "CASHFLOW_PROJECTION_PROJECTED_ROWS_NOT_INCLUDED" in reason_codes
    assert "CASHFLOW_PROJECTION_DEGRADED_BY_SOURCE" in reason_codes


def test_transaction_cost_context_marks_missing_observed_evidence_degraded() -> None:
    result = _trade_result()
    context = AuthoritativeTransactionCostContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        as_of_date="2026-05-03",
        window_start_date="2026-05-01",
        window_end_date="2026-05-03",
        returned_curve_point_count=1,
        curve_points=[
            AuthoritativeTransactionCostPoint(
                security_id="NOT_TRADED",
                transaction_type="BUY",
                currency="USD",
                observation_count=3,
                total_notional=Decimal("1000"),
                total_cost=Decimal("1"),
                average_cost_bps=Decimal("10"),
                min_cost_bps=Decimal("8"),
                max_cost_bps=Decimal("12"),
                first_observed_date="2026-05-01",
                last_observed_date="2026-05-03",
            )
        ],
        reason_codes=["TRANSACTION_COST_CURVE_READY"],
    )

    assert (
        construction_service._observed_transaction_cost_estimate(result=result, context=context)
        is None
    )
    assert (
        construction_service._transaction_cost_status(result=result, context=context)
        == ConstructionMethodStatus.DEGRADED
    )
    reason_codes = construction_service._transaction_cost_reason_codes(
        result=result,
        context=context,
    )

    assert "TRANSACTION_COST_CURVE_MISSING_TRADED_SECURITIES" in reason_codes
    assert "TRANSACTION_COST_ESTIMATE_UNAVAILABLE" in reason_codes


def test_transaction_cost_context_ignores_intents_without_base_notional() -> None:
    result = _trade_result()
    result = result.model_copy(
        update={
            "intents": [
                intent.model_copy(update={"notional_base": None}) for intent in result.intents
            ]
        }
    )
    context = AuthoritativeTransactionCostContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-core",
        as_of_date="2026-05-03",
        window_start_date="2026-05-01",
        window_end_date="2026-05-03",
        returned_curve_point_count=1,
        curve_points=[
            AuthoritativeTransactionCostPoint(
                security_id="EQ_B",
                transaction_type="BUY",
                currency="USD",
                observation_count=3,
                total_notional=Decimal("1000"),
                total_cost=Decimal("1"),
                average_cost_bps=Decimal("10"),
                min_cost_bps=Decimal("8"),
                max_cost_bps=Decimal("12"),
                first_observed_date="2026-05-01",
                last_observed_date="2026-05-03",
            )
        ],
        reason_codes=["TRANSACTION_COST_CURVE_READY"],
    )

    assert (
        construction_service._observed_transaction_cost_estimate(result=result, context=context)
        is None
    )


def test_client_restriction_context_applies_source_owned_restriction_scopes() -> None:
    request = RebalanceRequest.model_validate(valid_api_payload())
    result = _trade_result()
    context = AuthoritativeClientRestrictionContext(
        supportability_status=ConstructionMethodStatus.DEGRADED,
        source_system="lotus-core",
        portfolio_id="pf_enrich_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date="2026-05-03",
        restriction_count=4,
        missing_data_families=["issuer_classification"],
        restrictions=[
            AuthoritativeClientRestrictionRule(
                restriction_scope="instrument",
                restriction_code="NO_BUY_EQ_B",
                restriction_status="ACTIVE",
                restriction_source="CLIENT_PROFILE",
                applies_to_buy=True,
                applies_to_sell=False,
                instrument_ids=["EQ_B"],
                effective_from="2026-01-01",
                restriction_version=1,
            ),
            AuthoritativeClientRestrictionRule(
                restriction_scope="inactive",
                restriction_code="INACTIVE_RESTRICTION",
                restriction_status="INACTIVE",
                restriction_source="CLIENT_PROFILE",
                applies_to_buy=True,
                applies_to_sell=True,
                instrument_ids=["EQ_B"],
                effective_from="2026-01-01",
                restriction_version=1,
            ),
            AuthoritativeClientRestrictionRule(
                restriction_scope="sell_only",
                restriction_code="SELL_ONLY_RULE",
                restriction_status="ACTIVE",
                restriction_source="CLIENT_PROFILE",
                applies_to_buy=False,
                applies_to_sell=True,
                instrument_ids=["EQ_B"],
                effective_from="2026-01-01",
                restriction_version=1,
            ),
        ],
        reason_codes=["CLIENT_RESTRICTION_PROFILE_READY"],
    )

    assert (
        construction_service._client_restriction_status(
            request=request,
            result=result,
            context=context,
        )
        == ConstructionMethodStatus.BLOCKED
    )
    reason_codes = construction_service._client_restriction_reason_codes(
        request=request,
        result=result,
        context=context,
    )

    assert "CLIENT_RESTRICTION_PROFILE_DEGRADED" in reason_codes
    assert "MISSING_ISSUER_CLASSIFICATION" in reason_codes
    assert "CLIENT_RESTRICTION_VIOLATION_NO_BUY_EQ_B" in reason_codes


def test_restriction_scope_matching_handles_default_asset_issuer_and_country_rules() -> None:
    result = _trade_result()
    intent = next(intent for intent in result.intents if intent.instrument_id == "EQ_B")
    shelf = shelf_entry(
        "EQ_B",
        status="APPROVED",
        asset_class="EQUITY",
        issuer_id="ISSUER_TECH",
    ).model_copy(
        update={"attributes": {"country_of_risk": "US"}},
    )

    base_rule = {
        "restriction_scope": "scope",
        "restriction_code": "RULE",
        "restriction_status": "ACTIVE",
        "restriction_source": "CLIENT_PROFILE",
        "applies_to_buy": True,
        "applies_to_sell": True,
        "effective_from": "2026-01-01",
        "restriction_version": 1,
    }

    assert construction_service._restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=AuthoritativeClientRestrictionRule(**base_rule),
    )
    assert not construction_service._restriction_matches_intent(
        intent=intent,
        shelf=None,
        restriction=AuthoritativeClientRestrictionRule(
            **base_rule,
            asset_classes=["EQUITY"],
        ),
    )
    assert construction_service._restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=AuthoritativeClientRestrictionRule(
            **base_rule,
            asset_classes=["EQUITY"],
        ),
    )
    assert construction_service._restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=AuthoritativeClientRestrictionRule(
            **base_rule,
            issuer_ids=["ISSUER_TECH"],
        ),
    )
    assert construction_service._restriction_matches_intent(
        intent=intent,
        shelf=shelf,
        restriction=AuthoritativeClientRestrictionRule(
            **base_rule,
            country_codes=["US"],
        ),
    )


def test_sustainability_context_flags_allocation_and_classification_review() -> None:
    result = _trade_result()
    context = AuthoritativeSustainabilityPreferenceContext(
        supportability_status=ConstructionMethodStatus.DEGRADED,
        source_system="lotus-core",
        portfolio_id="pf_enrich_1",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date="2026-05-03",
        preference_count=3,
        missing_data_families=["issuer_esg_classification"],
        preferences=[
            AuthoritativeSustainabilityPreference(
                preference_framework="BANK_SUSTAINABILITY",
                preference_code="MIN_EQUITY",
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
            AuthoritativeSustainabilityPreference(
                preference_framework="BANK_SUSTAINABILITY",
                preference_code="INACTIVE_LIMIT",
                preference_status="INACTIVE",
                preference_source="CLIENT_PROFILE",
                maximum_allocation=Decimal("0.01"),
                applies_to_asset_classes=["EQUITY"],
                effective_from="2026-01-01",
                preference_version=1,
            ),
        ],
        reason_codes=["SUSTAINABILITY_PROFILE_READY"],
    )

    assert (
        construction_service._sustainability_preference_status(
            result=result,
            context=context,
        )
        == ConstructionMethodStatus.DEGRADED
    )
    reason_codes = construction_service._sustainability_preference_reason_codes(
        result=result,
        context=context,
    )

    assert "SUSTAINABILITY_PREFERENCE_PROFILE_DEGRADED" in reason_codes
    assert "MISSING_ISSUER_ESG_CLASSIFICATION" in reason_codes
    assert "SUSTAINABILITY_ALLOCATION_REVIEW_MIN_EQUITY" in reason_codes
    assert "SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED" in reason_codes


def test_source_context_lifts_client_restriction_and_sustainability_profiles() -> None:
    restriction_profile = DpmCoreClientRestrictionProfileResponse.model_validate(
        {
            "product_name": "ClientRestrictionProfile",
            "product_version": "v1",
            "portfolio_id": "pf_enrich_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "restrictions": [
                {
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
            ],
            "supportability": {
                "state": "INCOMPLETE",
                "reason": "CLIENT_RESTRICTION_PROFILE_INCOMPLETE",
                "restriction_count": 1,
                "missing_data_families": ["issuer_classification"],
            },
            "lineage": {"source_batch_fingerprint": "restriction-source-hash"},
            "data_quality_status": "INCOMPLETE",
        }
    )
    sustainability_profile = DpmCoreSustainabilityPreferenceProfileResponse.model_validate(
        {
            "product_name": "SustainabilityPreferenceProfile",
            "product_version": "v1",
            "portfolio_id": "pf_enrich_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "preferences": [
                {
                    "preference_framework": "BANK_SUSTAINABILITY",
                    "preference_code": "EXCLUSION_REVIEW",
                    "preference_status": "ACTIVE",
                    "preference_source": "CLIENT_PROFILE",
                    "exclusion_codes": ["THERMAL_COAL"],
                    "effective_from": "2026-01-01",
                    "preference_version": 1,
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "SUSTAINABILITY_PREFERENCE_PROFILE_READY",
                "preference_count": 1,
                "missing_data_families": [],
            },
            "lineage": {"source_batch_fingerprint": "sustainability-source-hash"},
            "data_quality_status": "READY",
        }
    )
    source_context = DpmResolvedSourceContext.model_construct(
        input_mode="stateful",
        source_system="lotus-core",
        stateful_context_hash="source-context-hash",
        context=SimpleNamespace(
            transaction_cost_curve=None,
            portfolio_cashflow_projection=None,
            client_restriction_profile=restriction_profile,
            sustainability_preference_profile=sustainability_profile,
        ),
    )

    context = construction_service._authority_context_with_source_products(
        authority_context=ConstructionAuthorityContext(),
        source_context=source_context,
    )

    assert context.client_restriction_context is not None
    assert (
        context.client_restriction_context.supportability_status == ConstructionMethodStatus.BLOCKED
    )
    assert context.client_restriction_context.content_hash
    assert context.sustainability_preference_context is not None
    assert (
        context.sustainability_preference_context.supportability_status
        == ConstructionMethodStatus.READY
    )
    assert context.sustainability_preference_context.content_hash
    assert (
        construction_service._source_status_to_method_status("INCOMPLETE")
        == ConstructionMethodStatus.BLOCKED
    )


def test_source_context_lifts_income_reserve_and_withdrawal_sources() -> None:
    income_schedule = DpmCoreClientIncomeNeedsScheduleResponse.model_validate(
        {
            "product_name": "ClientIncomeNeedsSchedule",
            "product_version": "v1",
            "portfolio_id": "pf_liquidity_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "schedules": [
                {
                    "schedule_id": "income-1",
                    "need_type": "RETIREMENT_INCOME",
                    "need_status": "ACTIVE",
                    "amount": "12000.00",
                    "currency": "USD",
                    "frequency": "MONTHLY",
                    "start_date": "2026-05-01",
                    "priority": 1,
                    "funding_policy": "BANK_POLICY_REF",
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "CLIENT_INCOME_NEEDS_READY",
                "schedule_count": 1,
                "missing_data_families": [],
            },
            "lineage": {"source_batch_fingerprint": "income-source-hash"},
        }
    )
    reserve_requirement = DpmCoreLiquidityReserveRequirementResponse.model_validate(
        {
            "product_name": "LiquidityReserveRequirement",
            "product_version": "v1",
            "portfolio_id": "pf_liquidity_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "requirements": [
                {
                    "reserve_requirement_id": "reserve-1",
                    "reserve_type": "CLIENT_RESERVE",
                    "reserve_status": "ACTIVE",
                    "required_amount": "50000.00",
                    "currency": "USD",
                    "horizon_days": 90,
                    "priority": 1,
                    "policy_source": "BANK_POLICY_REF",
                    "effective_from": "2026-05-01",
                    "requirement_version": 1,
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "LIQUIDITY_RESERVE_READY",
                "requirement_count": 1,
                "missing_data_families": [],
            },
            "lineage": {"source_batch_fingerprint": "reserve-source-hash"},
        }
    )
    planned_withdrawals = DpmCorePlannedWithdrawalScheduleResponse.model_validate(
        {
            "product_name": "PlannedWithdrawalSchedule",
            "product_version": "v1",
            "portfolio_id": "pf_liquidity_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "horizon_days": 365,
            "withdrawals": [
                {
                    "withdrawal_schedule_id": "wd-1",
                    "withdrawal_type": "CLIENT_DISTRIBUTION",
                    "withdrawal_status": "ACTIVE",
                    "amount": "25000.00",
                    "currency": "USD",
                    "scheduled_date": "2026-06-15",
                    "purpose_code": "CLIENT_REQUEST",
                }
            ],
            "supportability": {
                "state": "READY",
                "reason": "PLANNED_WITHDRAWALS_READY",
                "withdrawal_count": 1,
                "missing_data_families": [],
            },
            "lineage": {"source_batch_fingerprint": "withdrawal-source-hash"},
        }
    )
    source_context = DpmResolvedSourceContext.model_construct(
        input_mode="stateful",
        source_system="lotus-core",
        stateful_context_hash="source-context-hash",
        context=SimpleNamespace(
            transaction_cost_curve=None,
            portfolio_cashflow_projection=None,
            client_income_needs_schedule=income_schedule,
            liquidity_reserve_requirement=reserve_requirement,
            planned_withdrawal_schedule=planned_withdrawals,
            client_restriction_profile=None,
            sustainability_preference_profile=None,
        ),
    )

    context = construction_service._authority_context_with_source_products(
        authority_context=ConstructionAuthorityContext(),
        source_context=source_context,
    )

    liquidity_context = context.liquidity_context
    assert liquidity_context is not None
    assert liquidity_context.client_income_needs_schedule is not None
    assert liquidity_context.client_income_needs_schedule.schedule_count == 1
    assert liquidity_context.liquidity_reserve_requirement is not None
    assert liquidity_context.liquidity_reserve_requirement.maximum_horizon_days == 90
    assert liquidity_context.planned_withdrawal_schedule is not None
    assert liquidity_context.planned_withdrawal_schedule.withdrawal_count == 1
    reason_codes = summarize_enrichment_posture(
        result=_trade_result(),
        tax_required=False,
        risk_required=False,
        performance_required=False,
        liquidity_context=liquidity_context,
    ).reason_codes
    assert "CLIENT_INCOME_NEEDS_CONTEXT_PRESENT" in reason_codes
    assert "LIQUIDITY_RESERVE_CONTEXT_PRESENT" in reason_codes
    assert "PLANNED_WITHDRAWAL_CONTEXT_PRESENT" in reason_codes


def test_source_context_lifts_external_hedge_readiness_as_fail_closed_currency_context() -> None:
    readiness = DpmCoreExternalHedgeExecutionReadinessResponse.model_validate(
        {
            "product_name": "ExternalHedgeExecutionReadiness",
            "product_version": "v1",
            "portfolio_id": "pf_fx_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "reporting_currency": "USD",
            "exposure_currencies": ["EUR"],
            "readiness_checks": [],
            "supportability": {
                "state": "UNAVAILABLE",
                "reason": "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
                "missing_data_families": [
                    "external_currency_exposure",
                    "external_hedge_policy",
                ],
                "blocked_capabilities": ["hedge_advice", "oms_acknowledgement"],
            },
            "lineage": {"runtime_posture": "fail_closed"},
            "data_quality_status": "MISSING",
            "source_batch_fingerprint": "sha256:external-hedge-readiness",
        }
    )
    exposure = DpmCoreExternalCurrencyExposureResponse.model_validate(
        {
            "product_name": "ExternalCurrencyExposure",
            "product_version": "v1",
            "portfolio_id": "pf_fx_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "reporting_currency": "USD",
            "exposure_currencies": ["EUR"],
            "exposures": [],
            "supportability": {
                "state": "UNAVAILABLE",
                "reason": "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
                "exposure_count": 0,
                "missing_data_families": [
                    "external_currency_exposure",
                    "external_hedge_policy",
                ],
                "blocked_capabilities": ["fx_attribution", "treasury_instruction"],
            },
            "lineage": {"runtime_posture": "fail_closed"},
            "data_quality_status": "MISSING",
            "source_batch_fingerprint": "sha256:external-currency-exposure",
        }
    )
    hedge_policy = DpmCoreExternalHedgePolicyResponse.model_validate(
        {
            "product_name": "ExternalHedgePolicy",
            "product_version": "v1",
            "portfolio_id": "pf_fx_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "reporting_currency": "USD",
            "exposure_currencies": ["EUR"],
            "policy_rules": [],
            "supportability": {
                "state": "UNAVAILABLE",
                "reason": "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
                "policy_rule_count": 0,
                "missing_data_families": ["external_hedge_policy"],
                "blocked_capabilities": ["hedge_policy_approval", "counterparty_selection"],
            },
            "lineage": {"runtime_posture": "fail_closed"},
            "data_quality_status": "MISSING",
            "source_batch_fingerprint": "sha256:external-hedge-policy",
        }
    )
    fx_forward_curve = DpmCoreExternalFXForwardCurveResponse.model_validate(
        {
            "product_name": "ExternalFXForwardCurve",
            "product_version": "v1",
            "portfolio_id": "pf_fx_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "reporting_currency": "USD",
            "exposure_currencies": ["EUR"],
            "curve_points": [],
            "supportability": {
                "state": "UNAVAILABLE",
                "reason": "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
                "curve_point_count": 0,
                "missing_data_families": ["external_fx_forward_curve"],
                "blocked_capabilities": [
                    "forward_pricing",
                    "fx_valuation_methodology",
                    "best_execution",
                ],
            },
            "lineage": {"runtime_posture": "fail_closed"},
            "data_quality_status": "MISSING",
            "source_batch_fingerprint": "sha256:external-fx-forward-curve",
        }
    )
    source_context = DpmResolvedSourceContext.model_construct(
        input_mode="stateful",
        source_system="lotus-core",
        stateful_context_hash="source-context-hash",
        context=SimpleNamespace(
            transaction_cost_curve=None,
            portfolio_cashflow_projection=None,
            client_income_needs_schedule=None,
            liquidity_reserve_requirement=None,
            planned_withdrawal_schedule=None,
            external_hedge_execution_readiness=readiness,
            external_currency_exposure=exposure,
            external_hedge_policy=hedge_policy,
            external_fx_forward_curve=fx_forward_curve,
            client_restriction_profile=None,
            sustainability_preference_profile=None,
        ),
    )

    context = construction_service._authority_context_with_source_products(
        authority_context=ConstructionAuthorityContext(),
        source_context=source_context,
    )

    currency_context = context.currency_overlay_context
    assert currency_context is not None
    assert currency_context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert currency_context.source_system == "lotus-core"
    assert currency_context.source_product_name == "ExternalHedgeExecutionReadiness"
    assert currency_context.source_id == "sha256:external-hedge-readiness"
    assert currency_context.eligible_currencies == ["EUR"]
    assert "external_hedge_policy" in currency_context.missing_data_families
    assert "external_currency_exposure" in currency_context.missing_data_families
    assert "oms_acknowledgement" in currency_context.blocked_capabilities
    assert "fx_attribution" in currency_context.blocked_capabilities
    assert "hedge_policy_approval" in currency_context.blocked_capabilities
    assert "forward_pricing" in currency_context.blocked_capabilities
    assert currency_context.external_currency_exposure_source_product_name == (
        "ExternalCurrencyExposure"
    )
    assert currency_context.external_currency_exposure_source_id == (
        "sha256:external-currency-exposure"
    )
    assert currency_context.external_currency_exposure_count == 0
    assert currency_context.external_currency_exposure_rows == []
    assert currency_context.external_hedge_policy_source_product_name == "ExternalHedgePolicy"
    assert currency_context.external_hedge_policy_source_id == "sha256:external-hedge-policy"
    assert currency_context.external_hedge_policy_rule_count == 0
    assert currency_context.external_hedge_policy_rules == []
    assert currency_context.external_fx_forward_curve_source_product_name == (
        "ExternalFXForwardCurve"
    )
    assert currency_context.external_fx_forward_curve_source_id == (
        "sha256:external-fx-forward-curve"
    )
    assert currency_context.external_fx_forward_curve_point_count == 0
    assert currency_context.external_fx_forward_curve_points == []
    assert "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED" in currency_context.reason_codes
    assert "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED" in currency_context.reason_codes
    assert "EXTERNAL_HEDGE_POLICY_FAIL_CLOSED" in currency_context.reason_codes
    assert "EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED" in currency_context.reason_codes


def test_source_context_lifts_fx_forward_curve_when_it_is_the_only_currency_source() -> None:
    fx_forward_curve = DpmCoreExternalFXForwardCurveResponse.model_validate(
        {
            "product_name": "ExternalFXForwardCurve",
            "product_version": "v1",
            "portfolio_id": "pf_fx_1",
            "client_id": "client-1",
            "mandate_id": "mandate-1",
            "as_of_date": "2026-05-03",
            "reporting_currency": "USD",
            "exposure_currencies": ["USD"],
            "curve_points": [],
            "supportability": {
                "state": "UNAVAILABLE",
                "reason": "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
                "curve_point_count": 0,
                "missing_data_families": ["external_fx_forward_curve"],
                "blocked_capabilities": [
                    "forward_pricing",
                    "fx_valuation_methodology",
                    "best_execution",
                ],
            },
            "lineage": {"runtime_posture": "fail_closed"},
            "data_quality_status": "MISSING",
            "source_batch_fingerprint": "sha256:external-fx-forward-curve",
        }
    )
    source_context = DpmResolvedSourceContext.model_construct(
        input_mode="stateful",
        source_system="lotus-core",
        stateful_context_hash="source-context-hash",
        context=SimpleNamespace(
            transaction_cost_curve=None,
            portfolio_cashflow_projection=None,
            client_income_needs_schedule=None,
            liquidity_reserve_requirement=None,
            planned_withdrawal_schedule=None,
            external_hedge_execution_readiness=None,
            external_currency_exposure=None,
            external_hedge_policy=None,
            external_fx_forward_curve=fx_forward_curve,
            client_restriction_profile=None,
            sustainability_preference_profile=None,
        ),
    )

    context = construction_service._authority_context_with_source_products(
        authority_context=ConstructionAuthorityContext(),
        source_context=source_context,
    )

    currency_context = context.currency_overlay_context
    assert currency_context is not None
    assert currency_context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert currency_context.source_product_name is None
    assert currency_context.source_id is not None
    assert currency_context.source_id.startswith("sha256:")
    assert currency_context.eligible_currencies == ["USD"]
    assert currency_context.external_fx_forward_curve_source_product_name == (
        "ExternalFXForwardCurve"
    )
    assert currency_context.external_fx_forward_curve_point_count == 0
    assert currency_context.external_fx_forward_curve_points == []
    assert "forward_pricing" in currency_context.blocked_capabilities
    assert "best_execution" in currency_context.blocked_capabilities
    assert "external_fx_forward_curve" in currency_context.missing_data_families
    assert "EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED" in currency_context.reason_codes


def test_method_reason_codes_preserve_missing_currency_policy_context() -> None:
    payload = valid_api_payload()
    payload["portfolio_snapshot"]["base_currency"] = "SGD"
    payload["market_data_snapshot"]["prices"][0]["currency"] = "USD"
    payload["market_data_snapshot"]["fx_rates"] = []
    request = RebalanceRequest.model_validate(payload)
    result = _trade_result()
    enrichment = summarize_enrichment_posture(result=result, tax_required=False)

    reason_codes = construction_service._method_specific_reason_codes(
        request=request,
        method=ConstructionMethod.CURRENCY_OVERLAY,
        result=result,
        enrichment=enrichment,
        authority_context=ConstructionAuthorityContext(),
    )

    assert "CURRENCY_OVERLAY_POLICY_CONTEXT_MISSING" in reason_codes


def test_regime_context_unavailable_is_kept_source_safe() -> None:
    request = RebalanceRequest.model_validate(valid_api_payload())
    result = _trade_result()

    context = construction_service._authority_context_for_method(
        request=request,
        method=ConstructionMethod.REGIME_STRESS_AWARE,
        result=result,
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=_UnavailableRiskClient(),
        correlation_id="corr-regime",
    )

    assert context.regime_stress_context is None


def test_solver_and_liquidity_edges_surface_operational_evidence() -> None:
    result = _trade_result()
    warning_result = result.model_copy(
        update={
            "diagnostics": result.diagnostics.model_copy(
                update={"warnings": ["INFEASIBLE_CASH_CONSTRAINT"]}
            )
        }
    )
    blocked_result = result.model_copy(
        update={
            "diagnostics": result.diagnostics.model_copy(
                update={
                    "cash_ladder": [
                        {"date_offset": 1, "currency": "USD", "projected_balance": "-1.00"}
                    ],
                    "cash_ladder_breaches": [
                        {
                            "date_offset": 1,
                            "currency": "USD",
                            "projected_balance": "-1.00",
                            "allowed_floor": "0.00",
                            "reason_code": "SETTLEMENT_CASH_LADDER_BREACH",
                        }
                    ],
                    "insufficient_cash": [{"currency": "USD", "deficit": "1.00"}],
                }
            )
        }
    )
    liquidity_context = AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.03"),
        allowed_liquidity_tiers=["L1"],
        cashflow_projection=AuthoritativeLiquidityCashflowProjection(
            source_product_name="PortfolioCashflowProjection",
            source_product_version="v1",
            source_system="lotus-core",
            total_net_cashflow={"amount": "100.00", "currency": "USD"},
            projection_start="2026-05-03",
            projection_end="2026-06-03",
            include_projected=True,
            reason_codes=["CORE_CASHFLOW_PROJECTION_READY"],
        ),
        reason_codes=["LIQUIDITY_POLICY_READY"],
    )

    assert (
        construction_service._solver_method_status(result=warning_result)
        == ConstructionMethodStatus.BLOCKED
    )
    assert (
        construction_service._liquidity_status(result=blocked_result, context=liquidity_context)
        == ConstructionMethodStatus.BLOCKED
    )
    blocked_reason_codes = construction_service._liquidity_reason_codes(
        result=blocked_result,
        context=liquidity_context,
    )
    assert "SETTLEMENT_CASH_LADDER_BREACH" in blocked_reason_codes
    assert "LIQUIDITY_FUNDING_DEFICIT" in blocked_reason_codes

    zero_value_state = result.after_simulated.model_copy(
        update={"total_value": Money(amount=Decimal("0"), currency="USD")}
    )
    zero_value_result = result.model_copy(update={"after_simulated": zero_value_state})
    assert (
        construction_service._liquidity_status(
            result=zero_value_result,
            context=liquidity_context,
        )
        == ConstructionMethodStatus.DEGRADED
    )
    assert "CASHFLOW_PROJECTION_TOTAL_VALUE_UNAVAILABLE" in (
        construction_service._liquidity_reason_codes(
            result=zero_value_result,
            context=liquidity_context,
        )
    )

    no_cash_state = result.after_simulated.model_copy(
        update={
            "allocation_by_asset_class": [
                allocation
                for allocation in result.after_simulated.allocation_by_asset_class
                if allocation.key != "CASH"
            ]
        }
    )
    no_cash_result = result.model_copy(update={"after_simulated": no_cash_state})
    assert "CASHFLOW_PROJECTION_READY" not in construction_service._liquidity_reason_codes(
        result=no_cash_result,
        context=liquidity_context,
    )


def test_construction_service_currency_overlay_helper_edges() -> None:
    payload = valid_api_payload()
    payload["portfolio_snapshot"]["base_currency"] = "SGD"
    payload["market_data_snapshot"]["prices"][0]["currency"] = "USD"
    payload["market_data_snapshot"]["fx_rates"] = []
    request = RebalanceRequest.model_validate(payload)
    context = AuthoritativeCurrencyOverlayContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-fx-policy",
        policy_id="currency-policy.v1",
        hedge_ratio_min=Decimal("0.00"),
        hedge_ratio_max=Decimal("1.00"),
        eligible_currencies=[],
        reason_codes=["CURRENCY_POLICY_READY"],
    )

    assert (
        construction_service._currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.BLOCKED
    )
    payload["market_data_snapshot"]["fx_rates"] = [
        {"pair": "USD/SGD", "rate": "1.35", "as_of": "2026-05-03"}
    ]
    request = RebalanceRequest.model_validate(payload)

    assert (
        construction_service._currency_overlay_status(request=request, context=None)
        == ConstructionMethodStatus.DEGRADED
    )
    assert (
        construction_service._currency_overlay_status(request=request, context=context)
        == ConstructionMethodStatus.PENDING_REVIEW
    )


def test_construction_service_uses_method_specific_run_correlation_ids() -> None:
    class FakeRunService:
        def __init__(self) -> None:
            self.correlation_ids: list[str] = []

        def record_run(self, *, result, request_hash, portfolio_id, idempotency_key) -> None:
            self.correlation_ids.append(result.correlation_id)

    payload = valid_api_payload()
    request = RebalanceRequest.model_validate(payload)
    run_service = FakeRunService()

    construction_service.generate_construction_alternative_set(
        request=request,
        idempotency_key="construction-correlation-test",
        correlation_id="corr-construct-test",
        repository=InMemoryConstructionRepository(),
        methods=[
            ConstructionMethod.DO_NOTHING_BASELINE,
            ConstructionMethod.HEURISTIC_EXPLAINABLE,
            ConstructionMethod.MIN_TURNOVER,
        ],
        run_service=run_service,
    )

    assert run_service.correlation_ids == [
        "corr-construct-test:heuristic_explainable",
        "corr-construct-test:min_turnover",
    ]
    assert len(set(run_service.correlation_ids)) == len(run_service.correlation_ids)


class _UnavailableRiskClient:
    def concentration_context(self, *, result, correlation_id):
        raise construction_service.LotusRiskAuthorityUnavailableError("risk down")

    def regime_scenario_context(self, *, result, portfolio_id, as_of_date, correlation_id):
        raise construction_service.LotusRiskAuthorityUnavailableError("regime down")


def test_enrichment_summary_marks_turnover_pending_review_when_budget_drops_intents() -> None:
    result = _trade_result(max_turnover_pct=Decimal("0.25"))

    summary = summarize_enrichment_posture(result=result, tax_required=False)

    assert summary.turnover_status == ConstructionMethodStatus.PENDING_REVIEW
    assert "TURNOVER_BUDGET_DROPPED_INTENTS" in summary.reason_codes


def test_enrichment_summary_does_not_bleed_optional_authority_reason_codes() -> None:
    result = _trade_result()

    summary = summarize_enrichment_posture(
        result=result,
        tax_required=False,
        risk_required=False,
        performance_required=False,
    )

    assert summary.risk_status == ConstructionMethodStatus.READY
    assert summary.performance_status == ConstructionMethodStatus.READY
    assert "RISK_ENRICHMENT_UNAVAILABLE" not in summary.reason_codes
    assert "PERFORMANCE_CONTEXT_UNAVAILABLE" not in summary.reason_codes


def test_enrichment_summary_preserves_authoritative_risk_and_performance_status() -> None:
    result = _trade_result()

    summary = summarize_enrichment_posture(
        result=result,
        tax_required=False,
        risk_context=AuthoritativeRiskContext(
            supportability_status=ConstructionMethodStatus.PENDING_REVIEW,
            source_system="lotus-risk",
            tracking_error=Decimal("0.042"),
            concentration_breaches=1,
            reason_codes=["RISK_TRACKING_ERROR_ATTENTION"],
        ),
        performance_context=AuthoritativePerformanceContext(
            supportability_status=ConstructionMethodStatus.READY,
            source_system="lotus-performance",
            benchmark_id="BM_GLOBAL_BAL",
            active_return=Decimal("-0.012"),
            underperformance_flag=True,
            reason_codes=["PERFORMANCE_UNDER_REVIEW"],
        ),
    )

    assert summary.risk_status == ConstructionMethodStatus.PENDING_REVIEW
    assert summary.performance_status == ConstructionMethodStatus.READY
    assert "RISK_TRACKING_ERROR_ATTENTION" in summary.reason_codes
    assert "PERFORMANCE_UNDER_REVIEW" in summary.reason_codes
    assert "RISK_ENRICHMENT_UNAVAILABLE" not in summary.reason_codes
    assert "PERFORMANCE_CONTEXT_UNAVAILABLE" not in summary.reason_codes
