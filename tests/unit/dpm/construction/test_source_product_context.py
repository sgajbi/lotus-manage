from datetime import date
from decimal import Decimal

from src.api.services.construction_client_profile_source_context import (
    client_restriction_profile_context,
    sustainability_preference_profile_context,
)
from src.api.services.construction_execution_source_context import (
    external_order_execution_acknowledgement_context,
)
from src.api.services.construction_liquidity_source_context import (
    client_income_needs_schedule_context,
    liquidity_cashflow_projection_context,
    liquidity_reserve_requirement_context,
    planned_withdrawal_schedule_context,
    source_liquidity_context,
)
from src.api.services.construction_source_product_context import (
    source_product_authority_context_updates,
)
from src.api.services.construction_transaction_cost_source_context import (
    transaction_cost_context_from_curve,
)
from src.api.services.construction_treasury_source_context import (
    external_treasury_currency_overlay_context,
)
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleEntry,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientIncomeNeedsScheduleSupportability,
    DpmCoreClientRestrictionEntry,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreClientRestrictionSupportability,
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmCoreExternalOrderExecutionAcknowledgementSupportability,
    DpmCoreExternalCurrencyExposureResponse,
    DpmCoreExternalCurrencyExposureSupportability,
    DpmCoreExternalEligibleHedgeInstrumentResponse,
    DpmCoreExternalEligibleHedgeInstrumentSupportability,
    DpmCoreExternalFXForwardCurveResponse,
    DpmCoreExternalFXForwardCurveSupportability,
    DpmCoreExternalHedgeExecutionReadinessResponse,
    DpmCoreExternalHedgeExecutionReadinessSupportability,
    DpmCoreExternalHedgePolicyResponse,
    DpmCoreExternalHedgePolicySupportability,
    DpmCoreExecutionContext,
    DpmCoreIntegrationWindow,
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
    DpmCoreTransactionCostCurvePageMetadata,
    DpmCoreTransactionCostCurvePoint,
    DpmCoreTransactionCostCurveResponse,
    DpmCoreTransactionCostCurveSupportability,
)


def _acknowledgement_response() -> DpmCoreExternalOrderExecutionAcknowledgementResponse:
    return DpmCoreExternalOrderExecutionAcknowledgementResponse(
        product_name="ExternalOrderExecutionAcknowledgement",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        supportability=DpmCoreExternalOrderExecutionAcknowledgementSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_OMS_SOURCE_NOT_INGESTED",
            acknowledgement_count=0,
            missing_data_families=["external_oms_acknowledgement"],
            blocked_capabilities=["execution", "fill", "settlement"],
        ),
        lineage={"source_batch_fingerprint": "core-ack-fingerprint"},
        acknowledgements=[],
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


def _currency_exposure_response() -> DpmCoreExternalCurrencyExposureResponse:
    return DpmCoreExternalCurrencyExposureResponse(
        product_name="ExternalCurrencyExposure",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR", "JPY"],
        exposures=[{"currency": "EUR", "net_exposure": "125000"}],
        supportability=DpmCoreExternalCurrencyExposureSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            exposure_count=1,
            missing_data_families=["external_currency_exposure"],
            blocked_capabilities=["fx", "treasury"],
        ),
        lineage={"source_batch_fingerprint": "core-currency-exposure"},
    )


def _hedge_policy_response() -> DpmCoreExternalHedgePolicyResponse:
    return DpmCoreExternalHedgePolicyResponse(
        product_name="ExternalHedgePolicy",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR"],
        policy_rules=[{"currency": "EUR", "hedge_ratio": "0.50"}],
        supportability=DpmCoreExternalHedgePolicySupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            policy_rule_count=1,
            missing_data_families=["external_hedge_policy"],
            blocked_capabilities=["hedge-policy", "treasury"],
        ),
        lineage={"source_batch_fingerprint": "core-hedge-policy"},
    )


def _eligible_hedge_instruments_response() -> DpmCoreExternalEligibleHedgeInstrumentResponse:
    return DpmCoreExternalEligibleHedgeInstrumentResponse(
        product_name="ExternalEligibleHedgeInstrument",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-1",
        mandate_id="mandate-1",
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR"],
        instrument_types=["FX_FORWARD"],
        eligible_instruments=[{"instrument_id": "FXFWD_EURUSD_1M", "currency": "EUR"}],
        supportability=DpmCoreExternalEligibleHedgeInstrumentSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            instrument_count=1,
            missing_data_families=["external_eligible_hedge_instruments"],
            blocked_capabilities=["eligible-instrument", "suitability"],
        ),
        lineage={"source_batch_fingerprint": "core-eligible-hedges"},
    )


def _fx_forward_curve_response() -> DpmCoreExternalFXForwardCurveResponse:
    return DpmCoreExternalFXForwardCurveResponse(
        product_name="ExternalFXForwardCurve",
        product_version="v1",
        portfolio_id=None,
        client_id=None,
        mandate_id=None,
        as_of_date=date(2026, 6, 1),
        reporting_currency="USD",
        exposure_currencies=["EUR/USD"],
        curve_points=[{"tenor": "1M", "forward_points": "12.5"}],
        supportability=DpmCoreExternalFXForwardCurveSupportability(
            state="UNAVAILABLE",
            reason="EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
            curve_point_count=1,
            missing_data_families=["external_fx_forward_curve"],
            blocked_capabilities=["forward-pricing", "treasury"],
        ),
        lineage={"source_batch_fingerprint": "core-fx-forward-curve"},
    )


def _transaction_cost_curve() -> DpmCoreTransactionCostCurveResponse:
    return DpmCoreTransactionCostCurveResponse(
        product_name="TransactionCostCurve",
        product_version="v1",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=date(2026, 6, 1),
        window=DpmCoreIntegrationWindow(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 6, 1),
        ),
        curve_points=[
            DpmCoreTransactionCostCurvePoint(
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                security_id="EQ_A",
                transaction_type="BUY",
                currency="USD",
                observation_count=3,
                total_notional=Decimal("1000"),
                total_cost=Decimal("2"),
                average_cost_bps=Decimal("20"),
                min_cost_bps=Decimal("15"),
                max_cost_bps=Decimal("25"),
                first_observed_date=date(2026, 5, 1),
                last_observed_date=date(2026, 6, 1),
                sample_transaction_ids=["tx1", "tx2", "tx3", "tx4", "tx5", "tx6"],
            )
        ],
        page=DpmCoreTransactionCostCurvePageMetadata(
            page_size=50,
            sort_key="security_id",
            returned_component_count=1,
            request_scope_fingerprint="curve-page-fingerprint",
        ),
        supportability=DpmCoreTransactionCostCurveSupportability(
            state="DEGRADED",
            reason="TRANSACTION_COST_CURVE_PARTIAL",
            requested_security_count=2,
            returned_curve_point_count=1,
            missing_security_ids=["EQ_B"],
        ),
        lineage={"source_batch_fingerprint": "curve-lineage"},
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


def test_client_income_needs_context_preserves_priority_currency_and_status() -> None:
    context = client_income_needs_schedule_context(_income_needs_schedule())

    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ClientIncomeNeedsSchedule"
    assert context.source_id == "income-lineage"
    assert context.schedule_count == 2
    assert context.currencies == ["SGD", "USD"]
    assert context.highest_priority == 1
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.reason_codes == [
        "CLIENT_INCOME_NEEDS_PARTIAL",
        "CORE_INCOME_NEEDS_PRESENT",
    ]


def test_liquidity_reserve_requirement_context_preserves_horizon_currency_and_status() -> None:
    context = liquidity_reserve_requirement_context(_liquidity_reserve_requirement())

    assert context.source_system == "lotus-core"
    assert context.source_product_name == "LiquidityReserveRequirement"
    assert context.source_id == "reserve-lineage"
    assert context.requirement_count == 2
    assert context.currencies == ["SGD", "USD"]
    assert context.maximum_horizon_days == 90
    assert context.supportability_status == ConstructionMethodStatus.READY
    assert context.reason_codes == [
        "LIQUIDITY_RESERVE_READY",
        "CORE_LIQUIDITY_RESERVE_PRESENT",
    ]


def test_planned_withdrawal_context_preserves_horizon_currency_and_status() -> None:
    context = planned_withdrawal_schedule_context(_planned_withdrawal_schedule())

    assert context.source_system == "lotus-core"
    assert context.source_product_name == "PlannedWithdrawalSchedule"
    assert context.source_id == "withdrawal-lineage"
    assert context.withdrawal_count == 2
    assert context.currencies == ["SGD", "USD"]
    assert context.horizon_days == 120
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.reason_codes == [
        "PLANNED_WITHDRAWALS_PARTIAL",
        "CORE_PLANNED_WITHDRAWALS_PRESENT",
    ]


def test_liquidity_cashflow_projection_context_preserves_source_lineage_and_status() -> None:
    context = liquidity_cashflow_projection_context(_cashflow_projection())

    assert context.source_system == "lotus-core"
    assert context.source_product_name == "PortfolioCashflowProjection"
    assert context.source_batch_fingerprint == "cashflow-lineage"
    assert context.total_net_cashflow.amount == Decimal("1250.50")
    assert context.total_net_cashflow.currency == "USD"
    assert context.include_projected is True
    assert context.data_quality_status == ConstructionMethodStatus.DEGRADED
    assert context.reason_codes == ["CORE_CASHFLOW_PROJECTION_READY"]


def test_source_liquidity_context_preserves_source_family_policy_and_children() -> None:
    context = source_liquidity_context(
        cashflow_projection=_cashflow_projection(),
        income_needs=_income_needs_schedule(),
        reserve_requirement=_liquidity_reserve_requirement(),
        planned_withdrawals=_planned_withdrawal_schedule(),
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.READY
    assert context.source_system == "lotus-manage-settlement-engine"
    assert context.policy_id == "manage-liquidity-policy.v1"
    assert context.minimum_cash_weight == Decimal("0.02")
    assert context.allowed_liquidity_tiers == ["L1", "L2", "L3"]
    assert context.cashflow_projection is not None
    assert context.cashflow_projection.source_batch_fingerprint == "cashflow-lineage"
    assert context.client_income_needs_schedule is not None
    assert context.client_income_needs_schedule.source_id == "income-lineage"
    assert context.liquidity_reserve_requirement is not None
    assert context.liquidity_reserve_requirement.source_id == "reserve-lineage"
    assert context.planned_withdrawal_schedule is not None
    assert context.planned_withdrawal_schedule.source_id == "withdrawal-lineage"
    assert context.reason_codes == [
        "LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES",
        "CORE_LIQUIDITY_SOURCE_CONTEXT_PRESENT",
        "CLIENT_INCOME_NEEDS_SOURCE_PRESENT",
        "LIQUIDITY_RESERVE_SOURCE_PRESENT",
        "PLANNED_WITHDRAWAL_SOURCE_PRESENT",
    ]


def test_source_liquidity_context_absent_without_source_family() -> None:
    assert (
        source_liquidity_context(
            cashflow_projection=None,
            income_needs=None,
            reserve_requirement=None,
            planned_withdrawals=None,
        )
        is None
    )


def test_source_product_authority_context_updates_lifts_all_source_families() -> None:
    updates = source_product_authority_context_updates(
        source_context=_source_execution_context(
            transaction_cost_curve=_transaction_cost_curve(),
            portfolio_cashflow_projection=_cashflow_projection(),
            client_income_needs_schedule=_income_needs_schedule(),
            liquidity_reserve_requirement=_liquidity_reserve_requirement(),
            planned_withdrawal_schedule=_planned_withdrawal_schedule(),
            external_hedge_execution_readiness=_hedge_readiness_response(),
            external_order_execution_acknowledgement=_acknowledgement_response(),
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
            transaction_cost_curve=_transaction_cost_curve(),
            portfolio_cashflow_projection=_cashflow_projection(),
            external_order_execution_acknowledgement=_acknowledgement_response(),
        ),
        authority_context=ConstructionAuthorityContext(
            transaction_cost_context=transaction_cost_context_from_curve(_transaction_cost_curve()),
            liquidity_context=existing_liquidity_context,
        ),
    )

    assert "transaction_cost_context" not in updates
    assert "liquidity_context" not in updates
    assert sorted(updates) == ["execution_acknowledgement_context"]


def test_client_restriction_profile_context_preserves_rules_and_lineage() -> None:
    context = client_restriction_profile_context(_client_restriction_profile())

    assert context.supportability_status == ConstructionMethodStatus.READY
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ClientRestrictionProfile"
    assert context.source_id == "restriction-lineage"
    assert context.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert context.client_id == "client-1"
    assert context.restriction_count == 1
    assert context.reason_codes == ["CLIENT_RESTRICTIONS_READY"]
    assert len(context.restrictions) == 1
    assert context.restrictions[0].restriction_code == "NO_SINGLE_STOCK_A"
    assert context.restrictions[0].instrument_ids == ["EQ_A"]
    assert context.restrictions[0].source_record_id == "restriction-record-1"


def test_sustainability_preference_context_preserves_preferences_and_status() -> None:
    context = sustainability_preference_profile_context(_sustainability_preference_profile())

    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "SustainabilityPreferenceProfile"
    assert context.source_id == "sustainability-lineage"
    assert context.preference_count == 1
    assert context.missing_data_families == ["classification_review"]
    assert context.reason_codes == ["SUSTAINABILITY_PREFERENCES_PARTIAL"]
    assert len(context.preferences) == 1
    assert context.preferences[0].preference_code == "MIN_ARTICLE_8"
    assert context.preferences[0].minimum_allocation == Decimal("0.40")
    assert context.preferences[0].positive_tilt_codes == ["LOW_CARBON"]


def test_transaction_cost_context_preserves_core_curve_lineage_and_bounds_samples() -> None:
    context = transaction_cost_context_from_curve(_transaction_cost_curve())

    assert context.supportability_status == ConstructionMethodStatus.DEGRADED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "TransactionCostCurve"
    assert context.source_id == "curve-lineage"
    assert context.returned_curve_point_count == 1
    assert context.missing_security_ids == ["EQ_B"]
    assert context.reason_codes == ["TRANSACTION_COST_CURVE_PARTIAL"]
    assert len(context.curve_points) == 1
    assert context.curve_points[0].sample_transaction_ids == [
        "tx1",
        "tx2",
        "tx3",
        "tx4",
        "tx5",
    ]


def test_external_treasury_currency_overlay_context_preserves_fail_closed_readiness() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=_hedge_readiness_response(),
        currency_exposure=None,
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ExternalHedgeExecutionReadiness"
    assert context.source_id == "core-hedge-readiness"
    assert context.eligible_currencies == ["EUR", "GBP"]
    assert context.hedge_ratio_min == 0
    assert context.hedge_ratio_max == 0
    assert context.missing_data_families == ["external_treasury_hedge_readiness"]
    assert context.blocked_capabilities == ["execution", "oms", "treasury"]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_preserves_exposure_fallback() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=None,
        currency_exposure=_currency_exposure_response(),
        hedge_policy=None,
        eligible_hedge_instruments=None,
        fx_forward_curve=None,
    )

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_product_name is None
    assert context.source_id
    assert context.eligible_currencies == ["EUR", "JPY"]
    assert context.external_currency_exposure_source_id == "core-currency-exposure"
    assert context.external_currency_exposure_count == 1
    assert context.external_currency_exposure_rows == [
        {"currency": "EUR", "net_exposure": "125000"}
    ]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_combines_source_family_evidence() -> None:
    context = external_treasury_currency_overlay_context(
        hedge_readiness=_hedge_readiness_response(),
        currency_exposure=_currency_exposure_response(),
        hedge_policy=_hedge_policy_response(),
        eligible_hedge_instruments=_eligible_hedge_instruments_response(),
        fx_forward_curve=_fx_forward_curve_response(),
    )

    assert context is not None
    assert context.source_id == "core-hedge-readiness"
    assert context.external_currency_exposure_source_id == "core-currency-exposure"
    assert context.external_hedge_policy_source_id == "core-hedge-policy"
    assert context.external_eligible_hedge_instrument_source_id == "core-eligible-hedges"
    assert context.external_fx_forward_curve_source_id == "core-fx-forward-curve"
    assert context.missing_data_families == [
        "external_currency_exposure",
        "external_eligible_hedge_instruments",
        "external_fx_forward_curve",
        "external_hedge_policy",
        "external_treasury_hedge_readiness",
    ]
    assert context.blocked_capabilities == [
        "eligible-instrument",
        "execution",
        "forward-pricing",
        "fx",
        "hedge-policy",
        "oms",
        "suitability",
        "treasury",
    ]
    assert context.reason_codes == [
        "EXTERNAL_TREASURY_SOURCE_NOT_INGESTED",
        "EXTERNAL_HEDGE_EXECUTION_READINESS_FAIL_CLOSED",
        "EXTERNAL_CURRENCY_EXPOSURE_FAIL_CLOSED",
        "EXTERNAL_HEDGE_POLICY_FAIL_CLOSED",
        "EXTERNAL_ELIGIBLE_HEDGE_INSTRUMENTS_FAIL_CLOSED",
        "EXTERNAL_FX_FORWARD_CURVE_FAIL_CLOSED",
    ]


def test_external_treasury_currency_overlay_context_absent_without_source_response() -> None:
    assert (
        external_treasury_currency_overlay_context(
            hedge_readiness=None,
            currency_exposure=None,
            hedge_policy=None,
            eligible_hedge_instruments=None,
            fx_forward_curve=None,
        )
        is None
    )


def test_external_order_acknowledgement_context_is_fail_closed_source_evidence() -> None:
    context = external_order_execution_acknowledgement_context(_acknowledgement_response())

    assert context is not None
    assert context.supportability_status == ConstructionMethodStatus.BLOCKED
    assert context.source_system == "lotus-core"
    assert context.source_product_name == "ExternalOrderExecutionAcknowledgement"
    assert context.source_id == "core-ack-fingerprint"
    assert context.acknowledgement_count == 0
    assert context.blocked_capabilities == ["execution", "fill", "settlement"]
    assert context.reason_codes == [
        "EXTERNAL_OMS_SOURCE_NOT_INGESTED",
        "EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
    ]


def test_external_order_acknowledgement_context_absent_without_source_response() -> None:
    assert external_order_execution_acknowledgement_context(None) is None
