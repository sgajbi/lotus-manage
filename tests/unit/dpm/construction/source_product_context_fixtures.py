from datetime import date
from decimal import Decimal

from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleEntry,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientIncomeNeedsScheduleSupportability,
    DpmCoreClientRestrictionEntry,
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreClientRestrictionSupportability,
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
    DpmCoreExternalOrderExecutionAcknowledgementResponse,
    DpmCoreExternalOrderExecutionAcknowledgementSupportability,
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


def external_order_acknowledgement_response() -> (
    DpmCoreExternalOrderExecutionAcknowledgementResponse
):
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


def transaction_cost_curve_response() -> DpmCoreTransactionCostCurveResponse:
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


def hedge_readiness_response() -> DpmCoreExternalHedgeExecutionReadinessResponse:
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


def currency_exposure_response() -> DpmCoreExternalCurrencyExposureResponse:
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


def hedge_policy_response() -> DpmCoreExternalHedgePolicyResponse:
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


def eligible_hedge_instruments_response() -> DpmCoreExternalEligibleHedgeInstrumentResponse:
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


def fx_forward_curve_response() -> DpmCoreExternalFXForwardCurveResponse:
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


def cashflow_projection_response() -> DpmCorePortfolioCashflowProjectionResponse:
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


def client_income_needs_schedule_response() -> DpmCoreClientIncomeNeedsScheduleResponse:
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


def liquidity_reserve_requirement_response() -> DpmCoreLiquidityReserveRequirementResponse:
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


def planned_withdrawal_schedule_response() -> DpmCorePlannedWithdrawalScheduleResponse:
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


def client_restriction_profile_response() -> DpmCoreClientRestrictionProfileResponse:
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


def sustainability_preference_profile_response() -> DpmCoreSustainabilityPreferenceProfileResponse:
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
