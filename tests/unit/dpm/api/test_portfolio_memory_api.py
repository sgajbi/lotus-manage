from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.main import app
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
]:
    proof_pack_repository = InMemoryDpmProofPackRepository()
    wave_repository = InMemoryDpmWaveRepository()
    outcome_repository = InMemoryDpmOutcomeReviewRepository()
    proof_pack = _proof_pack().model_copy(update={"portfolio_id": PORTFOLIO_ID})
    proof_pack_repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
    )
    wave_repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None)
    outcome_repository.save_outcome_review(review=_review(), retention_expires_at=None)
    return proof_pack_repository, wave_repository, outcome_repository


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
    proof_pack_repository, wave_repository, outcome_repository = _repositories()

    memory = build_portfolio_memory(
        portfolio_id=PORTFOLIO_ID,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        generated_at=datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc),
    )

    assert memory.portfolio_id == PORTFOLIO_ID
    assert memory.event_count >= 6
    assert memory.content_hash.startswith("sha256:")
    assert memory.event_type_counts["PROOF_PACK_CREATED"] == 1
    assert memory.event_type_counts["WAVE_HANDOFF_READY"] == 1
    assert memory.event_type_counts["OUTCOME_REVIEW_CREATED"] == 1
    assert "lotus-manage" in memory.source_systems
    assert "lotus-core" in memory.source_systems
    assert "SOURCE_READY" in memory.reason_codes
    assert memory.events == sorted(
        memory.events,
        key=lambda event: (event.event_time, event.event_id),
        reverse=True,
    )
    assert not any(
        event.metadata.get("external_execution_claimed") is True for event in memory.events
    )


def test_portfolio_memory_api_returns_queryable_source_backed_memory() -> None:
    proof_pack_repository, wave_repository, outcome_repository = _repositories()
    app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.openapi_schema = None

    with TestClient(app) as client:
        response = client.get(f"/api/v1/rebalance/portfolio-memory/{PORTFOLIO_ID}?limit=20")
        openapi = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == PORTFOLIO_ID
    assert payload["event_count"] >= 6
    assert payload["event_type_counts"]["WAVE_EVENT"] == 1
    assert any(event["event_type"] == "OUTCOME_REVIEW_EVENT" for event in payload["events"])
    assert openapi.status_code == 200
    assert "/api/v1/rebalance/portfolio-memory/{portfolio_id}" in openapi.json()["paths"]
