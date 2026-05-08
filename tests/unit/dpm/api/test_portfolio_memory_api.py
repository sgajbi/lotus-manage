from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.main import app
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateDimensionScore,
    DpmMandateHealthReason,
    DpmMandateHealthSnapshot,
    DpmMandatePreferences,
    DpmMandateReviewPolicy,
    DpmMonitoringException,
    DpmSourceProductLineage,
    MandateHealthDimension,
    MandateHealthState,
    MandateRecommendedAction,
    MonitoringSeverity,
)
from src.core.portfolio_memory.service import build_portfolio_memory
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveHandoffRef,
    DpmWaveSourceRef,
    DpmWaveTrigger,
)
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack
from tests.unit.infrastructure.test_outcome_review_repository import _review


PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def teardown_function() -> None:
    app.dependency_overrides.clear()
    app.openapi_schema = None


def _repositories() -> tuple[
    InMemoryDpmProofPackRepository,
    InMemoryDpmWaveRepository,
    InMemoryDpmOutcomeReviewRepository,
    InMemoryDpmMandateRepository,
]:
    proof_pack_repository = InMemoryDpmProofPackRepository()
    wave_repository = InMemoryDpmWaveRepository()
    outcome_repository = InMemoryDpmOutcomeReviewRepository()
    mandate_repository = InMemoryDpmMandateRepository()
    proof_pack = _proof_pack().model_copy(update={"portfolio_id": PORTFOLIO_ID})
    proof_pack_repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )
    wave_repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None)
    outcome_repository.save_outcome_review(review=_review(), retention_expires_at=None)
    mandate_repository.save_mandate_snapshot(_mandate_twin())
    mandate_repository.save_health_snapshot(_health_snapshot())
    mandate_repository.save_monitoring_exception(_monitoring_exception())
    return proof_pack_repository, wave_repository, outcome_repository, mandate_repository


def _mandate_twin() -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id=PORTFOLIO_ID,
        mandate_version="2026-05-03",
        as_of_date=datetime(2026, 5, 3, tzinfo=timezone.utc).date(),
        base_currency="USD",
        reference_currency="USD",
        risk_profile="BALANCED",
        investment_objective="GLOBAL_BALANCED_INCOME",
        time_horizon="MEDIUM_TERM",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        constraints=DpmMandateConstraintSet(cash_band_min_weight=Decimal("0.02")),
        preferences=DpmMandatePreferences(),
        review_policy=DpmMandateReviewPolicy(review_frequency="QUARTERLY"),
        source_lineage=[
            DpmSourceProductLineage(
                product_name="CoreMandateBinding",
                product_version="v1",
                source_system="lotus-core",
                source_record_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                data_quality_status="READY",
            )
        ],
    )


def _health_snapshot() -> DpmMandateHealthSnapshot:
    return DpmMandateHealthSnapshot(
        health_snapshot_id="dmh_memory_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id=PORTFOLIO_ID,
        as_of_date=datetime(2026, 5, 3, tzinfo=timezone.utc).date(),
        calculated_at=datetime(2026, 5, 3, 8, 45, tzinfo=timezone.utc),
        health_score=72,
        health_state=MandateHealthState.PENDING_REVIEW,
        dimension_scores=[
            DpmMandateDimensionScore(
                dimension=MandateHealthDimension.ALLOCATION_DRIFT,
                weight=18,
                score=72,
                state=MandateHealthState.PENDING_REVIEW,
                reason_code="ALLOCATION_DRIFT_REVIEW",
                measured_value=Decimal("0.08"),
                threshold_value=Decimal("0.05"),
                evidence_refs=["core:mandate-binding:MANDATE_PB_SG_GLOBAL_BAL_001"],
            )
        ],
        top_reasons=[
            DpmMandateHealthReason(
                dimension=MandateHealthDimension.ALLOCATION_DRIFT,
                reason_code="ALLOCATION_DRIFT_REVIEW",
                severity=MonitoringSeverity.WARNING,
                message="Allocation drift requires PM review.",
                recommended_action=MandateRecommendedAction.SIMULATE_REBALANCE,
            )
        ],
        recommended_action=MandateRecommendedAction.SIMULATE_REBALANCE,
        source_readiness_state="READY",
        evidence_refs=["core:mandate-binding:MANDATE_PB_SG_GLOBAL_BAL_001"],
    )


def _monitoring_exception() -> DpmMonitoringException:
    return DpmMonitoringException(
        exception_id="dme_memory_allocation",
        monitoring_run_id="dmr_memory_001",
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        portfolio_id=PORTFOLIO_ID,
        detected_at=datetime(2026, 5, 3, 8, 50, tzinfo=timezone.utc),
        as_of_date=datetime(2026, 5, 3, tzinfo=timezone.utc).date(),
        dimension=MandateHealthDimension.ALLOCATION_DRIFT,
        severity=MonitoringSeverity.WARNING,
        reason_code="ALLOCATION_DRIFT_REVIEW",
        state="ACTIVE",
        recommended_action=MandateRecommendedAction.SIMULATE_REBALANCE,
        measured_value=Decimal("0.08"),
        threshold_value=Decimal("0.05"),
        source_lineage=_mandate_twin().source_lineage,
    )


def _wave() -> DpmRebalanceWave:
    item = DpmRebalanceWaveItem(
        wave_item_id="dwi_memory_001",
        portfolio_id=PORTFOLIO_ID,
        mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
        state="HANDOFF_READY",
        proof_pack_id="dpp_001",
        reason_codes=["WAVE_ITEM_HANDOFF_READY"],
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-core",
                source_type="PortfolioManagerBookMembership",
                source_id="pm-book-snapshot-20260503",
                source_version="v1",
                supportability_state="READY",
                content_hash="sha256:pm-book",
            )
        ],
    )
    return DpmRebalanceWave(
        wave_id="dwv_001",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="PM_BOOK_REVIEW",
            trigger_id="pm-book-review-20260503",
            rationale="Review source-owned PM book cohort.",
        ),
        as_of_date="2026-05-03",
        created_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
        created_by="pm_001",
        correlation_id="corr-wave-memory",
        items=[item],
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"HANDOFF_READY": 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        events=[
            DpmRebalanceWaveEvent(
                event_id="dwe_memory_handoff",
                wave_id="dwv_001",
                from_state="STAGED",
                to_state="HANDOFF_READY",
                event_type="STATE_TRANSITION",
                actor_id="ops_001",
                reason_code="WAVE_HANDOFF_READY",
                correlation_id="corr-wave-handoff",
                created_at=datetime(2026, 5, 4, 9, 0, tzinfo=timezone.utc),
            )
        ],
        handoff_refs=[
            DpmWaveHandoffRef(
                handoff_ref_id="dwh_001",
                wave_id="dwv_001",
                item_ids=["dwi_memory_001"],
                actor_id="ops_001",
                reason_code="READY_FOR_OPERATIONS_REVIEW",
                correlation_id="corr-handoff-memory",
                external_execution_claimed=False,
                content_hash="sha256:handoff-memory",
                created_at=datetime(2026, 5, 4, 9, 15, tzinfo=timezone.utc),
            )
        ],
    )


def test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()

    memory = build_portfolio_memory(
        portfolio_id=PORTFOLIO_ID,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        generated_at=datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc),
    )

    assert memory.portfolio_id == PORTFOLIO_ID
    assert memory.event_count >= 6
    assert memory.content_hash.startswith("sha256:")
    assert memory.event_type_counts["PROOF_PACK_CREATED"] == 1
    assert memory.event_type_counts["MANDATE_HEALTH_SNAPSHOT"] == 1
    assert memory.event_type_counts["MANDATE_MONITORING_EXCEPTION"] == 1
    assert memory.event_type_counts["WAVE_HANDOFF_READY"] == 1
    assert memory.event_type_counts["OUTCOME_REVIEW_CREATED"] == 1
    assert "lotus-manage" in memory.source_systems
    assert "lotus-core" in memory.source_systems
    assert "SOURCE_READY" in memory.reason_codes
    assert "ALLOCATION_DRIFT_REVIEW" in memory.reason_codes
    mandate_events = {
        event.event_type: event
        for event in memory.events
        if event.event_type in {"MANDATE_HEALTH_SNAPSHOT", "MANDATE_MONITORING_EXCEPTION"}
    }
    assert mandate_events["MANDATE_HEALTH_SNAPSHOT"].content_hash.startswith("sha256:")
    assert mandate_events["MANDATE_MONITORING_EXCEPTION"].supportability_state == "DEGRADED"
    assert (
        mandate_events["MANDATE_MONITORING_EXCEPTION"].metadata["monitoring_run_id"]
        == "dmr_memory_001"
    )
    assert memory.events == sorted(
        memory.events,
        key=lambda event: (event.event_time, event.event_id),
        reverse=True,
    )
    assert not any(
        event.metadata.get("external_execution_claimed") is True for event in memory.events
    )


def test_portfolio_memory_api_returns_queryable_source_backed_memory() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_mandate_repository] = lambda: mandate_repository
    app.openapi_schema = None

    with TestClient(app) as client:
        response = client.get(f"/api/v1/rebalance/portfolio-memory/{PORTFOLIO_ID}?limit=20")
        openapi = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == PORTFOLIO_ID
    assert payload["event_count"] >= 6
    assert payload["event_type_counts"]["WAVE_EVENT"] == 1
    assert payload["event_type_counts"]["MANDATE_MONITORING_EXCEPTION"] == 1
    assert any(event["event_type"] == "OUTCOME_REVIEW_EVENT" for event in payload["events"])
    assert openapi.status_code == 200
    assert "/api/v1/rebalance/portfolio-memory/{portfolio_id}" in openapi.json()["paths"]
