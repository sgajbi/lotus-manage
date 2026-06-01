from decimal import Decimal

from src.api.services.construction_source_product_status import source_status_to_method_status
from src.api.services.construction_source_identity import (
    response_source_id,
    source_product_identity,
    source_hash,
    source_payload,
)
from src.core.construction.models import (
    AuthoritativeClientIncomeNeedsSchedule,
    AuthoritativeLiquidityCashflowProjection,
    AuthoritativeLiquidityContext,
    AuthoritativeLiquidityReserveRequirement,
    AuthoritativePlannedWithdrawalSchedule,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.dpm_source_context import (
    DpmCoreClientIncomeNeedsScheduleResponse,
    DpmCoreLiquidityReserveRequirementResponse,
    DpmCorePlannedWithdrawalScheduleResponse,
    DpmCorePortfolioCashflowProjectionResponse,
)
from src.core.models import Money

_MANAGE_LIQUIDITY_SOURCE_SYSTEM = "lotus-manage-settlement-engine"
_MANAGE_LIQUIDITY_POLICY_ID = "manage-liquidity-policy.v1"
_MANAGE_MINIMUM_CASH_WEIGHT = Decimal("0.02")
_MANAGE_ALLOWED_LIQUIDITY_TIERS = ["L1", "L2", "L3"]
_MANAGE_LIQUIDITY_POLICY_REASON = "LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES"
_CORE_LIQUIDITY_SOURCE_REASON = "CORE_LIQUIDITY_SOURCE_CONTEXT_PRESENT"


def _liquidity_reason_codes(
    *,
    has_income_needs: bool,
    has_reserve_requirement: bool,
    has_planned_withdrawals: bool,
) -> list[str]:
    reason_codes = [
        _MANAGE_LIQUIDITY_POLICY_REASON,
        _CORE_LIQUIDITY_SOURCE_REASON,
    ]
    if has_income_needs:
        reason_codes.append("CLIENT_INCOME_NEEDS_SOURCE_PRESENT")
    if has_reserve_requirement:
        reason_codes.append("LIQUIDITY_RESERVE_SOURCE_PRESENT")
    if has_planned_withdrawals:
        reason_codes.append("PLANNED_WITHDRAWAL_SOURCE_PRESENT")
    return reason_codes


def client_income_needs_schedule_context(
    income_needs: DpmCoreClientIncomeNeedsScheduleResponse,
) -> AuthoritativeClientIncomeNeedsSchedule:
    identity = source_product_identity(income_needs)
    return AuthoritativeClientIncomeNeedsSchedule(
        source_product_name=identity.source_product_name,
        source_product_version=identity.source_product_version,
        source_system=identity.source_system,
        source_id=identity.source_id,
        content_hash=identity.content_hash,
        schedule_count=income_needs.supportability.schedule_count,
        currencies=sorted({entry.currency for entry in income_needs.schedules}),
        highest_priority=(
            min(entry.priority for entry in income_needs.schedules)
            if income_needs.schedules
            else None
        ),
        supportability_status=source_status_to_method_status(income_needs.supportability.state),
        reason_codes=[income_needs.supportability.reason, "CORE_INCOME_NEEDS_PRESENT"],
    )


def liquidity_cashflow_projection_context(
    cashflow_projection: DpmCorePortfolioCashflowProjectionResponse,
) -> AuthoritativeLiquidityCashflowProjection:
    payload = source_payload(cashflow_projection)
    source_hash_value = source_hash(payload)
    status = (
        cashflow_projection.data_quality_status
        if cashflow_projection.data_quality_status in {"READY", "DEGRADED", "INCOMPLETE"}
        else "READY"
    )
    return AuthoritativeLiquidityCashflowProjection(
        source_product_name=cashflow_projection.product_name,
        source_product_version=cashflow_projection.product_version,
        source_system="lotus-core",
        total_net_cashflow=Money(
            amount=cashflow_projection.total_net_cashflow,
            currency=cashflow_projection.portfolio_currency,
        ),
        projection_start=cashflow_projection.range_start_date,
        projection_end=cashflow_projection.range_end_date,
        include_projected=cashflow_projection.include_projected,
        latest_evidence_timestamp=cashflow_projection.latest_evidence_timestamp,
        source_batch_fingerprint=response_source_id(cashflow_projection, source_hash_value),
        data_quality_status=source_status_to_method_status(status),
        reason_codes=["CORE_CASHFLOW_PROJECTION_READY"],
    )


def liquidity_reserve_requirement_context(
    reserve_requirement: DpmCoreLiquidityReserveRequirementResponse,
) -> AuthoritativeLiquidityReserveRequirement:
    identity = source_product_identity(reserve_requirement)
    return AuthoritativeLiquidityReserveRequirement(
        source_product_name=identity.source_product_name,
        source_product_version=identity.source_product_version,
        source_system=identity.source_system,
        source_id=identity.source_id,
        content_hash=identity.content_hash,
        requirement_count=reserve_requirement.supportability.requirement_count,
        currencies=sorted({entry.currency for entry in reserve_requirement.requirements}),
        maximum_horizon_days=(
            max(entry.horizon_days for entry in reserve_requirement.requirements)
            if reserve_requirement.requirements
            else None
        ),
        supportability_status=source_status_to_method_status(
            reserve_requirement.supportability.state
        ),
        reason_codes=[
            reserve_requirement.supportability.reason,
            "CORE_LIQUIDITY_RESERVE_PRESENT",
        ],
    )


def planned_withdrawal_schedule_context(
    planned_withdrawals: DpmCorePlannedWithdrawalScheduleResponse,
) -> AuthoritativePlannedWithdrawalSchedule:
    identity = source_product_identity(planned_withdrawals)
    return AuthoritativePlannedWithdrawalSchedule(
        source_product_name=identity.source_product_name,
        source_product_version=identity.source_product_version,
        source_system=identity.source_system,
        source_id=identity.source_id,
        content_hash=identity.content_hash,
        withdrawal_count=planned_withdrawals.supportability.withdrawal_count,
        currencies=sorted({entry.currency for entry in planned_withdrawals.withdrawals}),
        horizon_days=planned_withdrawals.horizon_days,
        supportability_status=source_status_to_method_status(
            planned_withdrawals.supportability.state
        ),
        reason_codes=[
            planned_withdrawals.supportability.reason,
            "CORE_PLANNED_WITHDRAWALS_PRESENT",
        ],
    )


def source_liquidity_context(
    *,
    cashflow_projection: DpmCorePortfolioCashflowProjectionResponse | None,
    income_needs: DpmCoreClientIncomeNeedsScheduleResponse | None,
    reserve_requirement: DpmCoreLiquidityReserveRequirementResponse | None,
    planned_withdrawals: DpmCorePlannedWithdrawalScheduleResponse | None,
) -> AuthoritativeLiquidityContext | None:
    if (
        cashflow_projection is None
        and income_needs is None
        and reserve_requirement is None
        and planned_withdrawals is None
    ):
        return None

    cashflow_context = (
        liquidity_cashflow_projection_context(cashflow_projection)
        if cashflow_projection is not None
        else None
    )
    income_context = (
        client_income_needs_schedule_context(income_needs) if income_needs is not None else None
    )
    reserve_context = (
        liquidity_reserve_requirement_context(reserve_requirement)
        if reserve_requirement is not None
        else None
    )
    withdrawal_context = (
        planned_withdrawal_schedule_context(planned_withdrawals)
        if planned_withdrawals is not None
        else None
    )

    return AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system=_MANAGE_LIQUIDITY_SOURCE_SYSTEM,
        policy_id=_MANAGE_LIQUIDITY_POLICY_ID,
        minimum_cash_weight=_MANAGE_MINIMUM_CASH_WEIGHT,
        allowed_liquidity_tiers=_MANAGE_ALLOWED_LIQUIDITY_TIERS,
        cashflow_projection=cashflow_context,
        client_income_needs_schedule=income_context,
        liquidity_reserve_requirement=reserve_context,
        planned_withdrawal_schedule=withdrawal_context,
        reason_codes=_liquidity_reason_codes(
            has_income_needs=income_context is not None,
            has_reserve_requirement=reserve_context is not None,
            has_planned_withdrawals=withdrawal_context is not None,
        ),
    )


__all__ = [
    "client_income_needs_schedule_context",
    "liquidity_cashflow_projection_context",
    "liquidity_reserve_requirement_context",
    "planned_withdrawal_schedule_context",
    "source_liquidity_context",
]
