from datetime import date
from decimal import Decimal

from src.api.services.mandate_monitoring_support import aggregate_monitoring_results
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    DpmMandateReviewPolicy,
)


def _twin(
    *,
    mandate_id: str,
) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_version="3",
        as_of_date=date(2026, 5, 3),
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        constraints=DpmMandateConstraintSet(
            cash_band_min_weight=Decimal("0.02"),
            cash_band_max_weight=Decimal("0.10"),
            turnover_budget=Decimal("0.15"),
        ),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )


def test_aggregate_monitoring_results_updates_distribution_and_calls_callbacks() -> None:
    mandate_ids = ["MANDATE_PB_SG_GLOBAL_BAL_001", "MANDATE_PB_SG_GLOBAL_BAL_002"]
    twins = {mandate_id: _twin(mandate_id=mandate_id) for mandate_id in mandate_ids}
    resolved = []
    persisted = []

    def resolve_twin(mandate_id: str) -> DpmMandateDigitalTwin:
        resolved.append(mandate_id)
        return twins[mandate_id]

    def persist_snapshot(
        twin: DpmMandateDigitalTwin,
        snapshot: DpmMandateHealthSnapshot,
        exceptions: list[DpmMonitoringException],
    ) -> None:
        persisted.append((twin.mandate_id, snapshot.health_state.value, len(exceptions)))

    accumulator = aggregate_monitoring_results(
        mandate_ids=mandate_ids,
        as_of_date=date(2026, 5, 3),
        monitoring_run_id="dmr_test",
        resolve_twin=resolve_twin,
        persist_result=persist_snapshot,
        tenant_id="tenant-test",
    )

    assert resolved == mandate_ids
    assert len(persisted) == len(mandate_ids)
    assert all(persisted_entry[0] in mandate_ids for persisted_entry in persisted)
    assert sum(entry[2] for entry in persisted) == accumulator.exception_count
    assert sum(health_count for health_count in accumulator.health_distribution.values()) == len(
        mandate_ids
    )
