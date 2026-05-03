from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMandateHealthInput,
    DpmMandateReviewPolicy,
    MandateHealthDimension,
    MandateHealthState,
    calculate_mandate_health,
    monitoring_exceptions_from_health,
)
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json


def _twin(*, version: str = "1", as_of: date = date(2026, 5, 3)) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        mandate_version=version,
        as_of_date=as_of,
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


def _health_snapshot(twin: DpmMandateDigitalTwin) -> DpmMandateHealthSnapshot:
    return calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={
                "EQ_US_AAPL": Decimal("0.60"),
                "FI_US_TREASURY_10Y": Decimal("0.40"),
            },
            target_weights={
                "EQ_US_AAPL": Decimal("0.60"),
                "FI_US_TREASURY_10Y": Decimal("0.40"),
            },
            cash_weight=Decimal("0.05"),
        )
    )


def test_repository_persists_mandate_versions_idempotently_and_lists_latest() -> None:
    repository = InMemoryDpmMandateRepository()
    old_twin = _twin(version="1", as_of=date(2026, 5, 1))
    latest_twin = _twin(version="2", as_of=date(2026, 5, 3))

    repository.save_mandate_snapshot(old_twin)
    repository.save_mandate_snapshot(latest_twin)
    repository.save_mandate_snapshot(latest_twin.model_copy(update={"risk_profile": "GROWTH"}))

    by_portfolio = repository.get_latest_mandate_by_portfolio(portfolio_id="PB_SG_GLOBAL_BAL_001")
    by_mandate = repository.get_latest_mandate(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")
    versions = repository.list_mandate_versions(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")

    assert by_portfolio is not None
    assert by_portfolio.mandate_version == "2"
    assert by_portfolio.risk_profile == "GROWTH"
    assert by_mandate is not None
    assert by_mandate.mandate_version == "2"
    assert [version.mandate_version for version in versions] == ["2", "1"]


def test_repository_returns_defensive_copies() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin())

    stored = repository.get_latest_mandate(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")
    assert stored is not None
    stored.risk_profile = "MUTATED"

    reloaded = repository.get_latest_mandate(mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001")
    assert reloaded is not None
    assert reloaded.risk_profile == "BALANCED"


def test_repository_persists_latest_health_snapshot() -> None:
    repository = InMemoryDpmMandateRepository()
    twin = _twin()
    first = _health_snapshot(twin)
    second = first.model_copy(
        update={
            "health_snapshot_id": "mh_second",
            "calculated_at": first.calculated_at + timedelta(minutes=1),
            "health_score": 91,
        }
    )

    repository.save_health_snapshot(first)
    repository.save_health_snapshot(second)

    latest = repository.get_latest_health_snapshot(mandate_id=twin.mandate_id)
    assert latest is not None
    assert latest.health_snapshot_id == "mh_second"
    assert latest.health_score == 91


def test_repository_filters_pages_and_resolves_monitoring_exceptions() -> None:
    repository = InMemoryDpmMandateRepository()
    twin = _twin()
    snapshot = calculate_mandate_health(
        DpmMandateHealthInput(
            twin=twin,
            current_weights={"EQ_US_AAPL": Decimal("0.60")},
            target_weights={"EQ_US_AAPL": Decimal("0.60")},
            cash_weight=Decimal("0.05"),
            restricted_held_instruments=["EQ_RESTRICTED"],
        )
    )
    exceptions = monitoring_exceptions_from_health(snapshot, source_lineage=twin.source_lineage)
    assert exceptions
    repository.save_monitoring_exception(exceptions[0])

    rows, cursor = repository.list_monitoring_exceptions(
        mandate_id=twin.mandate_id,
        portfolio_id=None,
        state="ACTIVE",
        limit=1,
        cursor=None,
    )
    assert cursor is None
    assert rows[0].dimension == MandateHealthDimension.ELIGIBILITY_RESTRICTIONS

    resolved = repository.resolve_monitoring_exception(
        exception_id=rows[0].exception_id,
        resolved_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        resolution_reason="PM_CONFIRMED_EXIT_REQUIRED",
    )
    assert resolved is not None
    assert resolved.state == "RESOLVED"
    assert resolved.resolution_reason == "PM_CONFIRMED_EXIT_REQUIRED"

    active_rows, _ = repository.list_monitoring_exceptions(
        mandate_id=twin.mandate_id,
        portfolio_id=None,
        state="ACTIVE",
        limit=10,
        cursor=None,
    )
    assert active_rows == []


def test_repository_retention_keeps_active_exceptions_but_purges_old_resolved_records() -> None:
    repository = InMemoryDpmMandateRepository()
    old_twin = _twin(as_of=date(2024, 1, 1))
    repository.save_mandate_snapshot(old_twin)
    old_health = _health_snapshot(old_twin).model_copy(
        update={"calculated_at": datetime(2024, 1, 1, tzinfo=timezone.utc)}
    )
    repository.save_health_snapshot(old_health)
    old_exception = monitoring_exceptions_from_health(
        calculate_mandate_health(
            DpmMandateHealthInput(
                twin=old_twin,
                cash_weight=Decimal("0.50"),
                current_weights={"EQ_US_AAPL": Decimal("0.60")},
                target_weights={"EQ_US_AAPL": Decimal("0.60")},
            )
        ),
        source_lineage=[],
    )[0].model_copy(update={"detected_at": datetime(2024, 1, 1, tzinfo=timezone.utc)})
    repository.save_monitoring_exception(old_exception)
    repository.resolve_monitoring_exception(
        exception_id=old_exception.exception_id,
        resolved_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        resolution_reason="OLD_EXCEPTION_RESOLVED",
    )

    purged = repository.purge_mandate_records_before(
        cutoff=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )

    assert purged == 3
    assert repository.get_latest_mandate(mandate_id=old_twin.mandate_id) is None
    assert repository.get_latest_health_snapshot(mandate_id=old_twin.mandate_id) is None
    rows, _ = repository.list_monitoring_exceptions(
        mandate_id=old_twin.mandate_id,
        portfolio_id=None,
        state=None,
        limit=10,
        cursor=None,
    )
    assert rows == []


def test_repository_serialization_round_trip_preserves_domain_types() -> None:
    snapshot = _health_snapshot(_twin())

    payload = dump_model_json(snapshot)
    reloaded = load_model_json(type(snapshot), payload)

    assert reloaded.health_state == MandateHealthState.READY
    assert reloaded.dimension_scores[0].dimension in set(MandateHealthDimension)
