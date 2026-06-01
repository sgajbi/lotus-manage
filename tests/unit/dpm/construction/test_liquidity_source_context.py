from decimal import Decimal

from src.api.services.construction_liquidity_source_context import (
    client_income_needs_schedule_context,
    liquidity_cashflow_projection_context,
    liquidity_reserve_requirement_context,
    planned_withdrawal_schedule_context,
    source_liquidity_context,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.construction.vocabulary import ConstructionMethodStatus
from tests.unit.dpm.construction.source_product_context_fixtures import (
    cashflow_projection_response,
    client_income_needs_schedule_response,
    liquidity_reserve_requirement_response,
    planned_withdrawal_schedule_response,
)


def test_client_income_needs_context_preserves_priority_currency_and_status() -> None:
    context = client_income_needs_schedule_context(client_income_needs_schedule_response())

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
    context = liquidity_reserve_requirement_context(liquidity_reserve_requirement_response())

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
    context = planned_withdrawal_schedule_context(planned_withdrawal_schedule_response())

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
    context = liquidity_cashflow_projection_context(cashflow_projection_response())

    assert context.source_system == "lotus-core"
    assert context.source_product_name == "PortfolioCashflowProjection"
    assert context.source_batch_fingerprint == "cashflow-lineage"
    assert context.total_net_cashflow.amount == Decimal("1250.50")
    assert context.total_net_cashflow.currency == "USD"
    assert context.include_projected is True
    assert context.data_quality_status == ConstructionMethodStatus.DEGRADED
    assert context.reason_codes == ["CORE_CASHFLOW_PROJECTION_READY"]


def test_client_income_needs_context_falls_back_to_content_hash_source_id() -> None:
    response = client_income_needs_schedule_response().model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )
    expected_hash = hash_canonical_payload(response.model_dump(mode="json", exclude_none=True))

    context = client_income_needs_schedule_context(response)

    assert context.source_id == expected_hash


def test_liquidity_reserve_context_falls_back_to_content_hash_source_id() -> None:
    response = liquidity_reserve_requirement_response().model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )
    expected_hash = hash_canonical_payload(response.model_dump(mode="json", exclude_none=True))

    context = liquidity_reserve_requirement_context(response)

    assert context.source_id == expected_hash


def test_planned_withdrawal_context_falls_back_to_content_hash_source_id() -> None:
    response = planned_withdrawal_schedule_response().model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )
    expected_hash = hash_canonical_payload(response.model_dump(mode="json", exclude_none=True))

    context = planned_withdrawal_schedule_context(response)

    assert context.source_id == expected_hash


def test_liquidity_cashflow_context_falls_back_to_content_hash_source_id() -> None:
    response = cashflow_projection_response().model_copy(
        update={
            "source_batch_fingerprint": None,
            "lineage": {},
        }
    )
    expected_hash = hash_canonical_payload(response.model_dump(mode="json", exclude_none=True))

    context = liquidity_cashflow_projection_context(response)

    assert context.source_batch_fingerprint == expected_hash


def test_source_liquidity_context_preserves_source_family_policy_and_children() -> None:
    context = source_liquidity_context(
        cashflow_projection=cashflow_projection_response(),
        income_needs=client_income_needs_schedule_response(),
        reserve_requirement=liquidity_reserve_requirement_response(),
        planned_withdrawals=planned_withdrawal_schedule_response(),
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
