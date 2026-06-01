from datetime import date
from decimal import Decimal

from src.api.services.construction_liquidity_source_context import (
    source_liquidity_context,
)
from src.api.services.construction_source_product_context import (
    source_product_authority_context_updates,
)
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleEntry,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientIncomeNeedsScheduleSupportability,
    DpmCoreClientRestrictionEntry,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreClientRestrictionSupportability,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgeExecutionReadinessSupportability,
    DpmCoreExecutionContext,
    DpmCoreLiquidityReserveRequirementEntry,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCoreLiquidityReserveRequirementSupportability,
    DpmCorePlannedWithdrawalScheduleEntry,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePlannedWithdrawalScheduleSupportability,
    DpmCorePortfolioCashflowProjectionResponse,
    DpmCoreSustainabilityPreferenceEntry,
    DpmCoreSustainabilityPreferenceProfileResponse,
    DpmCoreSustainabilityPreferenceSupportability,
)
from tests.unit.dpm.construction.source_product_context_fixtures import (
    external_order_acknowledgement_response,
    transaction_cost_curve_response,
)


def _hedge_readiness_response() -> DpmCoreExternalHedgeExecutionReadinessResponse:
    return DpmCoreExternalHedgeExecutionReadinessResponse(
        product_name="ExternalHedgeExecutionReadiness",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR", "GBP"],
        readiness_checks=[{"check": "source_ingestion", "status": "missing"}],
        supportability=DpmCoreExternalHedgeExecutionReadinessSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            missing_data_families=["external_treasury_hedge_readiness"],
            blocked_capabilities=["treasury", "oms", "execution"],
        ),
        lineage={"source_batch_fingerprint": "core-hedge-readiness"},
    )


def _cashflow_projection() -> DpmCorePortfolioCashflowProjectionResponse:
    return DpmCorePortfolioCashflowProjectionResponse(
        product_name="PortfolioCashflowProjection",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 6, 1),
        range_start_date=date(2026, 6, 1),
        range_end_date=date(2026, 6, 30),
        include_projected=True,
        portfolio_currency="USD",
        points=[],
        total_net_cashflow=Decimal("1250.50"),
        projection_days=30,
        data_quality_status="DEGRADED",
        source_batch_fingerprint=None,
        lineage={"source_batch_fingerprint": "cashflow-lineage"},
    )


def _income_needs_schedule() -> DpmCoreClientIncomeNeedsScheduleResponse:
    return DpmCoreClientIncomeNeedsScheduleResponse(
        product_name="ClientIncomeNeedsSchedule",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        schedules=[
            DpmCoreClientIncomeNeedsScheduleEntry(
                schedule_id="income-1",
                need_type="RETIREMENT_INCOME",
                need_status="ACTIVE",
                amount=Decimal("5000"),
                currency="SGD",
                frequency="MONTHLY",
                start_date=date(2026, 6, 1),
                priority=2,
            ),
            DpmCoreClientIncomeNeedsScheduleEntry(
                schedule_id="income-2",
                need_type="SCHOOL_FEES",
                need_status="ACTIVE",
                amount=Decimal("12000"),
                currency="USD",
                frequency="QUARTERLY",
                start_date=date(2026, 7, 1),
                priority=1,
            ),
        ],
        supportability=DpmCoreClientIncomeNeedsScheduleSupportability(
            state="INCOMPLETE",
            reason="CLIENT_INCOME_NEEDS_PARTIAL",
            schedule_count=2,
            missing_data_families=["income_needs_review"],
        ),
        lineage={"source_batch_fingerprint": "income-lineage"},
    )


def _liquidity_reserve_requirement() -> DpmCoreLiquidityReserveRequirementResponse:
    return DpmCoreLiquidityReserveRequirementResponse(
        product_name="LiquidityReserveRequirement",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        requirements=[
            DpmCoreLiquidityReserveRequirementEntry(
                reserve_requirement_id="reserve-1",
                reserve_type="OPERATING_CASH",
                reserve_status="ACTIVE",
                required_amount=Decimal("7500"),
                currency="USD",
                horizon_days=30,
                priority=1,
                policy_source="BANK_POLICY",
                effective_from=date(2026, 6, 1),
                requirement_version=1,
            ),
            DpmCoreLiquidityReserveRequirementEntry(
                reserve_requirement_id="reserve-2",
                reserve_type="CLIENT_BUFFER",
                reserve_status="ACTIVE",
                required_amount=Decimal("10000"),
                currency="SGD",
                horizon_days=90,
                priority=2,
                policy_source="CLIENT_POLICY",
                effective_from=date(2026, 6, 1),
                requirement_version=1,
            ),
        ],
        supportability=DpmCoreLiquidityReserveRequirementSupportability(
            state="READY",
            reason="LIQUIDITY_RESERVE_READY",
            requirement_count=2,
        ),
        lineage={"source_batch_fingerprint": "reserve-lineage"},
    )


def _planned_withdrawal_schedule() -> DpmCorePlannedWithdrawalScheduleResponse:
    return DpmCorePlannedWithdrawalScheduleResponse(
        product_name="PlannedWithdrawalSchedule",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        horizon_days=120,
        withdrawals=[
            DpmCorePlannedWithdrawalScheduleEntry(
                withdrawal_schedule_id="withdrawal-1",
                withdrawal_type="TUITION",
                withdrawal_status="ACTIVE",
                amount=Decimal("12000"),
                currency="USD",
                scheduled_date=date(2026, 7, 15),
                recurrence_frequency="ONE_TIME",
            ),
            DpmCorePlannedWithdrawalScheduleEntry(
                withdrawal_schedule_id="withdrawal-2",
                withdrawal_type="LIFESTYLE",
                withdrawal_status="ACTIVE",
                amount=Decimal("5000"),
                currency="SGD",
                scheduled_date=date(2026, 8, 1),
                recurrence_frequency="MONTHLY",
            ),
        ],
        supportability=DpmCorePlannedWithdrawalScheduleSupportability(
            state="INCOMPLETE",
            reason="PLANNED_WITHDRAWALS_PARTIAL",
            withdrawal_count=2,
            missing_data_families=["external_planning_review"],
        ),
        lineage={"source_batch_fingerprint": "withdrawal-lineage"},
    )


def _client_restriction_profile() -> DpmCoreClientRestrictionProfileResponse:
    return DpmCoreClientRestrictionProfileResponse(
        product_name="ClientRestrictionProfile",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        restrictions=[
            DpmCoreClientRestrictionEntry(
                restriction_scope="INSTRUMENT",
                restriction_code="NO_SINGLE_STOCK_A",
                restriction_status="ACTIVE",
                restriction_source="CLIENT_MANDATE",
                applies_to_buy=True,
                applies_to_sell=False,
                instrument_ids=["EQ_A"],
                effective_from=date(2026, 1, 1),
                restriction_version=3,
                source_record_id="restriction-record-1",
            )
        ],
        supportability=DpmCoreClientRestrictionSupportability(
            state="READY",
            reason="CLIENT_RESTRICTIONS_READY",
            restriction_count=1,
            missing_data_families=[],
        ),
        lineage={"source_batch_fingerprint": "restriction-lineage"},
    )


def _sustainability_preference_profile() -> DpmCoreSustainabilityPreferenceProfileResponse:
    return DpmCoreSustainabilityPreferenceProfileResponse(
        product_name="SustainabilityPreferenceProfile",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        preferences=[
            DpmCoreSustainabilityPreferenceEntry(
                preference_framework="SFDR",
                preference_code="MIN_ARTICLE_8",
                preference_status="ACTIVE",
                preference_source="CLIENT_MANDATE",
                minimum_allocation=Decimal("0.40"),
                applies_to_asset_classes=["EQUITY"],
                exclusion_codes=["THERMAL_COAL"],
                positive_tilt_codes=["LOW_CARBON"],
                effective_from=date(2026, 1, 1),
                preference_version=2,
                source_record_id="preference-record-1",
            )
        ],
        supportability=DpmCoreSustainabilityPreferenceSupportability(
            state="INCOMPLETE",
            reason="SUSTAINABILITY_PREFERENCES_PARTIAL",
            preference_count=1,
            missing_data_families=["classification_review"],
        ),
        lineage={"source_batch_fingerprint": "sustainability-lineage"},
    )


def _source_execution_context(**overrides: object) -> DpmCoreExecutionContext:
    source_products = {
        "transaction_cost_curve": None,
        "portfolio_cashflow_projection": None,
        "client_income_needs_schedule": None,
        "liquidity_reserve_requirement": None,
        "planned_withdrawal_schedule": None,
        "external_hedge_execution_readiness": None,
        "external_currency_exposure": None,
        "external_hedge_policy": None,
        "external_eligible_hedge_instruments": None,
        "external_fx_forward_curve": None,
        "external_order_execution_acknowledgement": None,
        "client_restriction_profile": None,
        "sustainability_preference_profile": None,
    }
    source_products.update(overrides)
    return DpmCoreExecutionContext.model_construct(**source_products)


def test_source_product_authority_context_updates_lifts_all_source_families() -> None:
    updates = source_product_authority_context_updates(
        source_context=_source_execution_context(
            transaction_cost_curve=transaction_cost_curve_response(),
            portfolio_cashflow_projection=_cashflow_projection(),
            client_income_needs_schedule=_income_needs_schedule(),
            liquidity_reserve_requirement=_liquidity_reserve_requirement(),
            planned_withdrawal_schedule=_planned_withdrawal_schedule(),
            external_hedge_execution_readiness=_hedge_readiness_response(),
            external_order_execution_acknowledgement=external_order_acknowledgement_response(),
            client_restriction_profile=_client_restriction_profile(),
            sustainability_preference_profile=_sustainability_preference_profile(),
        ),
        authority_context=ConstructionAuthorityContext(),
    )

    assert sorted(updates) == [
        "client_restriction_context",
        "currency_overlay_context",
        "execution_acknowledgement_context",
        "liquidity_context",
        "sustainability_preference_context",
        "transaction_cost_context",
    ]
    assert updates["transaction_cost_context"].source_id == "curve-lineage"
    assert updates["liquidity_context"].planned_withdrawal_schedule is not None
    assert updates["currency_overlay_context"].source_id == "core-hedge-readiness"
    assert updates["execution_acknowledgement_context"].source_id == "core-ack-fingerprint"
    assert updates["client_restriction_context"].source_id == "restriction-lineage"
    assert updates["sustainability_preference_context"].source_id == "sustainability-lineage"


def test_source_product_authority_context_updates_preserves_existing_contexts() -> None:
    existing_liquidity_context = source_liquidity_context(
        cashflow_projection=_cashflow_projection(),
        income_needs=None,
        reserve_requirement=None,
        planned_withdrawals=None,
    )
    assert existing_liquidity_context is not None
    updates = source_product_authority_context_updates(
        source_context=_source_execution_context(
            transaction_cost_curve=transaction_cost_curve_response(),
            portfolio_cashflow_projection=_cashflow_projection(),
            external_order_execution_acknowledgement=external_order_acknowledgement_response(),
        ),
        authority_context=ConstructionAuthorityContext(
            transaction_cost_context=transaction_cost_context_from_curve(
                transaction_cost_curve_response()
            ),
            liquidity_context=existing_liquidity_context,
        ),
    )

    assert "transaction_cost_context" not in updates
    assert "liquidity_context" not in updates
    assert sorted(updates) == ["execution_acknowledgement_context"]
