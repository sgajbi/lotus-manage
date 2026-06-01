from datetime import date
from decimal import Decimal

from src.api.services.construction_liquidity_source_context import (
    client_income_needs_schedule_context,
    liquidity_cashflow_projection_context,
    liquidity_reserve_requirement_context,
    planned_withdrawal_schedule_context,
    source_liquidity_context,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleEntry,
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreClientIncomeNeedsScheduleSupportability,
    DpmCoreLiquidityReserveRequirementEntry,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCoreLiquidityReserveRequirementSupportability,
    DpmCorePlannedWithdrawalScheduleEntry,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePlannedWithdrawalScheduleSupportability,
    DpmCorePortfolioCashflowProjectionResponse,
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
