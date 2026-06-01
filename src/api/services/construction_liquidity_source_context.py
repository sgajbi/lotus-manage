from decimal import Decimal

from src.core.common.canonical import hash_canonical_payload
from src.api.services.construction_source_product_status import source_status_to_method_status
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


def client_income_needs_schedule_context(
    income_needs: DpmCoreClientIncomeNeedsScheduleResponse,
) -> AuthoritativeClientIncomeNeedsSchedule:
    payload = income_needs.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeClientIncomeNeedsSchedule(
        source_product_name=income_needs.product_name,
        source_product_version=income_needs.product_version,
        source_system="lotus-core",
        source_id=income_needs.source_batch_fingerprint
        or income_needs.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
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
    payload = cashflow_projection.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
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
        source_batch_fingerprint=cashflow_projection.source_batch_fingerprint
        or cashflow_projection.lineage.get("source_batch_fingerprint")
        or source_hash,
        data_quality_status=source_status_to_method_status(status),
        reason_codes=["CORE_CASHFLOW_PROJECTION_READY"],
    )


def liquidity_reserve_requirement_context(
    reserve_requirement: DpmCoreLiquidityReserveRequirementResponse,
) -> AuthoritativeLiquidityReserveRequirement:
    payload = reserve_requirement.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativeLiquidityReserveRequirement(
        source_product_name=reserve_requirement.product_name,
        source_product_version=reserve_requirement.product_version,
        source_system="lotus-core",
        source_id=reserve_requirement.source_batch_fingerprint
        or reserve_requirement.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
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
    payload = planned_withdrawals.model_dump(mode="json", exclude_none=True)
    source_hash = hash_canonical_payload(payload)
    return AuthoritativePlannedWithdrawalSchedule(
        source_product_name=planned_withdrawals.product_name,
        source_product_version=planned_withdrawals.product_version,
        source_system="lotus-core",
        source_id=planned_withdrawals.source_batch_fingerprint
        or planned_withdrawals.lineage.get("source_batch_fingerprint")
        or source_hash,
        content_hash=source_hash,
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

    source_reason_codes = [
        "LIQUIDITY_POLICY_DERIVED_FROM_MANAGE_SETTLEMENT_RULES",
        "CORE_LIQUIDITY_SOURCE_CONTEXT_PRESENT",
    ]
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
    if income_context is not None:
        source_reason_codes.append("CLIENT_INCOME_NEEDS_SOURCE_PRESENT")
    if reserve_context is not None:
        source_reason_codes.append("LIQUIDITY_RESERVE_SOURCE_PRESENT")
    if withdrawal_context is not None:
        source_reason_codes.append("PLANNED_WITHDRAWAL_SOURCE_PRESENT")

    return AuthoritativeLiquidityContext(
        supportability_status=ConstructionMethodStatus.READY,
        source_system="lotus-manage-settlement-engine",
        policy_id="manage-liquidity-policy.v1",
        minimum_cash_weight=Decimal("0.02"),
        allowed_liquidity_tiers=["L1", "L2", "L3"],
        cashflow_projection=cashflow_context,
        client_income_needs_schedule=income_context,
        liquidity_reserve_requirement=reserve_context,
        planned_withdrawal_schedule=withdrawal_context,
        reason_codes=source_reason_codes,
    )


__all__ = [
    "client_income_needs_schedule_context",
    "liquidity_cashflow_projection_context",
    "liquidity_reserve_requirement_context",
    "planned_withdrawal_schedule_context",
    "source_liquidity_context",
    "source_status_to_method_status",
]
