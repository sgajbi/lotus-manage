from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_construction_repository,
    get_mandate_repository,
    get_outcome_review_repository,
    get_pm_quality_score_run_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.main import app
from src.core.construction import build_alternative_set, build_do_nothing_baseline
from src.core.construction.models import ConstructionAlternativeSelection
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
from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityBookScopeEvidence,
)
from src.core.portfolio_memory import service as portfolio_memory_service
from src.core.portfolio_memory.service import build_portfolio_memory
from src.core.proof_packs import DpmProofPackEvidenceRef
from src.core.waves.models import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveHandoffRef,
    DpmWaveSourceRef,
    DpmWaveTrigger,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.pm_quality import InMemoryDpmPmQualityScoreRunRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository
from tests.unit.dpm.construction.test_alternative_engine import _ready_rebalance_result
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


def _pm_quality_score_run() -> DpmPmOperatingQualityScoreRun:
    book_ref = DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id="pm-book-snapshot-20260512",
        source_version="v1",
        content_hash="sha256:pm-book",
    )
    member_ref = DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
        source_id="pm-book:001",
        source_version="2026-05-12",
    )
    return DpmPmOperatingQualityScoreRun(
        score_run_id="pmq_score_run_001",
        pm_id="pm_001",
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        state="READY",
        score=Decimal("91.25"),
        indicator_results=[],
        book_scope_evidence=DpmPmQualityBookScopeEvidence(
            source_id="pm-book-snapshot-20260512",
            product_version="v1",
            supportability_state="READY",
            returned_portfolio_count=2,
            member_portfolio_ids=[PORTFOLIO_ID, "PB_SG_GLOBAL_INC_002"],
            filters_applied={"portfolio_types": ["DPM"], "include_inactive": False},
            reason_codes=["PM_BOOK_SCOPE_MATERIALIZED", "DPM_CORE_PM_BOOK_READY"],
            source_refs=[book_ref, member_ref],
        ),
        governance_evidence=None,
        reason_codes=["PM_QUALITY_SCORE_READY"],
        source_refs=[book_ref, member_ref],
        content_hash="sha256:pmq-score-run-001",
        generated_at=datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc),
        generated_by="ops",
        correlation_id="corr-pmq-memory",
    )


def _construction_repository() -> InMemoryConstructionRepository:
    repository = InMemoryConstructionRepository()
    result = _ready_rebalance_result()
    alternative_set = build_alternative_set(
        alternative_set_id="cas_memory_001",
        portfolio_id=PORTFOLIO_ID,
        as_of="2026-05-03",
        alternatives=[build_do_nothing_baseline(result=result)],
    ).model_copy(
        update={
            "request_hash": "sha256:construction-memory",
            "generated_at": datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
            "source_supportability_state": "READY",
        }
    )
    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key="idem-construction-memory",
    )
    repository.save_selection(
        selection=ConstructionAlternativeSelection(
            selection_id="casel_memory_001",
            alternative_set_id="cas_memory_001",
            alternative_id="alt_do_nothing_baseline",
            actor_id="pm_001",
            reason_code="MINIMIZE_TURNOVER",
            comment="Keep portfolio stable for review.",
            correlation_id="corr-construction-memory",
            selected_at=datetime(2026, 5, 3, 10, 30, tzinfo=timezone.utc),
        )
    )
    return repository


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
    construction_repository = _construction_repository()
    pm_quality_repository = InMemoryDpmPmQualityScoreRunRepository()
    pm_quality_repository.save_score_run(score_run=_pm_quality_score_run())

    memory = build_portfolio_memory(
        portfolio_id=PORTFOLIO_ID,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=pm_quality_repository,
        generated_at=datetime(2026, 5, 7, 10, 0, tzinfo=timezone.utc),
    )

    assert memory.portfolio_id == PORTFOLIO_ID
    assert memory.event_count >= 6
    assert memory.content_hash.startswith("sha256:")
    assert memory.governance_policy == {
        "event_identity_scheme": (
            "source_system:source_type:source_id:content_hash_or_content_hash_unavailable"
        ),
        "retention_policy": "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y",
        "redaction_policy": "NO_RAW_PAYLOADS",
        "audit_policy": "AUDIT_READ_AND_EXPORT",
        "access_classification": "CLIENT_CONFIDENTIAL_INTERNAL",
        "source_authority_policy": (
            "portfolio memory projects source-owned facts; consumers must not reconstruct risk, "
            "performance, mandate-health, execution, tax, cash, FX, report, or AI truth"
        ),
    }
    assert memory.event_type_counts["PROOF_PACK_CREATED"] == 1
    assert memory.event_type_counts["MANDATE_HEALTH_SNAPSHOT"] == 1
    assert memory.event_type_counts["MANDATE_MONITORING_EXCEPTION"] == 1
    assert memory.event_type_counts["CONSTRUCTION_ALTERNATIVE_SET"] == 1
    assert memory.event_type_counts["CONSTRUCTION_ALTERNATIVE_SELECTED"] == 1
    assert memory.event_type_counts["WAVE_HANDOFF_READY"] == 1
    assert memory.event_type_counts["OUTCOME_REVIEW_CREATED"] == 1
    assert memory.event_type_counts["PM_QUALITY_SCORE_RUN"] == 1
    assert "lotus-manage" in memory.source_systems
    assert "lotus-core" in memory.source_systems
    assert "SOURCE_READY" in memory.reason_codes
    assert "ALLOCATION_DRIFT_REVIEW" in memory.reason_codes
    family_posture = {posture.family_key: posture for posture in memory.source_event_family_posture}
    assert family_posture["mandate_health"].support_status == "SUPPORTED"
    assert family_posture["report_lifecycle"].route == (
        "/reports/jobs/{job_id}/portfolio-memory-events"
    )
    assert family_posture["ai_workflow_pack"].source_system == "lotus-ai"
    assert family_posture["generated_document_archive"].source_system == "lotus-archive"
    assert family_posture["construction_alternatives"].support_status == "SUPPORTED"
    assert family_posture["construction_alternatives"].event_types == [
        "CONSTRUCTION_ALTERNATIVE_SET",
        "CONSTRUCTION_ALTERNATIVE_SELECTED",
    ]
    assert (
        "without copying raw request payloads"
        in family_posture["construction_alternatives"].summary
    )
    assert family_posture["external_oms_execution"].support_status == "DEFERRED_SOURCE_OWNER"
    assert family_posture["external_oms_execution"].event_types == []
    assert (
        family_posture["external_order_execution_acknowledgement"].support_status
        == "DEFERRED_SOURCE_OWNER"
    )
    assert family_posture["external_order_execution_acknowledgement"].source_system == "lotus-core"
    assert family_posture["external_order_execution_acknowledgement"].event_types == []
    assert (
        family_posture["external_order_execution_acknowledgement"].reason_code
        == "EXTERNAL_ORDER_ACKNOWLEDGEMENT_SOURCE_EVENTS_DEFERRED"
    )
    assert (
        "ExternalOrderExecutionAcknowledgement:v1"
        in family_posture["external_order_execution_acknowledgement"].summary
    )
    assert (
        "does not project acknowledgement, fill, settlement, or execution-status events"
        in family_posture["external_order_execution_acknowledgement"].summary
    )
    assert family_posture["pm_scoring"].source_system == "lotus-manage"
    assert family_posture["pm_scoring"].owner == "lotus-manage PM operating quality product"
    assert family_posture["pm_scoring"].support_status == "SUPPORTED"
    assert family_posture["pm_scoring"].event_types == ["PM_QUALITY_SCORE_RUN"]
    assert family_posture["pm_scoring"].route == (
        "/api/v1/rebalance/pm-operating-quality/score-runs"
    )
    assert family_posture["pm_scoring"].reason_code == (
        "PM_QUALITY_SCORE_RUN_SOURCE_EVENTS_SUPPORTED"
    )
    assert "bank-supplied policy" in family_posture["pm_scoring"].summary
    assert "does not copy raw score payloads" in family_posture["pm_scoring"].summary
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
    pm_quality_events = [
        event for event in memory.events if event.event_type == "PM_QUALITY_SCORE_RUN"
    ]
    assert pm_quality_events[0].source_id == "pmq_score_run_001"
    assert pm_quality_events[0].metadata["numeric_score_projected"] is False
    assert "score" not in pm_quality_events[0].metadata
    assert pm_quality_events[0].artifact_refs[0].content_hash == "sha256:pmq-score-run-001"
    construction_events = {
        event.event_type: event
        for event in memory.events
        if event.event_type in {"CONSTRUCTION_ALTERNATIVE_SET", "CONSTRUCTION_ALTERNATIVE_SELECTED"}
    }
    assert construction_events["CONSTRUCTION_ALTERNATIVE_SET"].content_hash == (
        "sha256:construction-memory"
    )
    assert construction_events["CONSTRUCTION_ALTERNATIVE_SET"].metadata["alternative_count"] == 1
    assert (
        construction_events["CONSTRUCTION_ALTERNATIVE_SET"].metadata[
            "raw_request_payload_projected"
        ]
        is False
    )
    assert (
        construction_events["CONSTRUCTION_ALTERNATIVE_SELECTED"].metadata["comment_projected"]
        is True
    )
    assert (
        construction_events["CONSTRUCTION_ALTERNATIVE_SELECTED"].metadata[
            "raw_selection_payload_projected"
        ]
        is False
    )
    assert memory.events == sorted(
        memory.events,
        key=lambda event: (event.event_time, event.event_id),
        reverse=True,
    )
    assert all(event.event_identity for event in memory.events)
    assert all(
        event.retention_policy == "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y"
        for event in memory.events
    )
    assert all(event.redaction_policy == "NO_RAW_PAYLOADS" for event in memory.events)
    assert all(event.audit_policy == "AUDIT_READ_AND_EXPORT" for event in memory.events)
    assert all(
        event.access_classification == "CLIENT_CONFIDENTIAL_INTERNAL" for event in memory.events
    )
    assert not any(
        event.metadata.get("external_execution_claimed") is True for event in memory.events
    )


def test_portfolio_memory_api_returns_queryable_source_backed_memory() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    construction_repository = _construction_repository()
    pm_quality_repository = InMemoryDpmPmQualityScoreRunRepository()
    pm_quality_repository.save_score_run(score_run=_pm_quality_score_run())
    app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    app.dependency_overrides[get_construction_repository] = lambda: construction_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_mandate_repository] = lambda: mandate_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: pm_quality_repository
    app.openapi_schema = None

    with TestClient(app) as client:
        response = client.get(f"/api/v1/rebalance/portfolio-memory/{PORTFOLIO_ID}?limit=20")
        openapi = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] == PORTFOLIO_ID
    assert payload["event_count"] >= 6
    assert payload["governance_policy"]["retention_policy"] == (
        "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y"
    )
    assert payload["event_type_counts"]["WAVE_EVENT"] == 1
    assert payload["event_type_counts"]["MANDATE_MONITORING_EXCEPTION"] == 1
    assert payload["event_type_counts"]["CONSTRUCTION_ALTERNATIVE_SET"] == 1
    assert payload["event_type_counts"]["CONSTRUCTION_ALTERNATIVE_SELECTED"] == 1
    assert payload["event_type_counts"]["PM_QUALITY_SCORE_RUN"] == 1
    family_posture = {
        posture["family_key"]: posture for posture in payload["source_event_family_posture"]
    }
    assert family_posture["proof_pack_decision_timeline"]["support_status"] == "SUPPORTED"
    assert family_posture["construction_alternatives"] == {
        "family_key": "construction_alternatives",
        "source_system": "lotus-manage",
        "owner": "lotus-manage construction alternatives product",
        "support_status": "SUPPORTED",
        "event_types": ["CONSTRUCTION_ALTERNATIVE_SET", "CONSTRUCTION_ALTERNATIVE_SELECTED"],
        "route": "/api/v1/rebalance/portfolio-memory/{portfolio_id}",
        "reason_code": "CONSTRUCTION_ALTERNATIVE_SOURCE_EVENTS_SUPPORTED",
        "summary": (
            "Construction alternative set generation and selected-alternative decisions are "
            "projected from persisted construction repository truth without copying raw "
            "request payloads or recalculating construction, risk, performance, tax, cash, "
            "FX, or execution methodology."
        ),
    }
    assert family_posture["external_oms_execution"] == {
        "family_key": "external_oms_execution",
        "source_system": "future-oms-owner",
        "owner": "future execution or OMS owner",
        "support_status": "DEFERRED_SOURCE_OWNER",
        "event_types": [],
        "route": None,
        "reason_code": "OMS_SOURCE_EVENTS_NOT_SUPPORTED",
        "summary": (
            "No external OMS execution, fill, or acknowledgement events are projected until a "
            "governed OMS owner publishes a no-raw-payload source-event family."
        ),
    }
    assert family_posture["external_order_execution_acknowledgement"] == {
        "family_key": "external_order_execution_acknowledgement",
        "source_system": "lotus-core",
        "owner": "lotus-core source-boundary posture; future execution or OMS owner",
        "support_status": "DEFERRED_SOURCE_OWNER",
        "event_types": [],
        "route": "/integration/portfolios/{portfolio_id}/external-order-execution-acknowledgement",
        "reason_code": "EXTERNAL_ORDER_ACKNOWLEDGEMENT_SOURCE_EVENTS_DEFERRED",
        "summary": (
            "Core ExternalOrderExecutionAcknowledgement:v1 is consumed only as fail-closed "
            "source-product posture for construction and outcome evidence; portfolio memory "
            "does not project acknowledgement, fill, settlement, or execution-status events "
            "until bank-owned OMS acknowledgement ingestion publishes a certified "
            "no-raw-payload source-event family."
        ),
    }
    assert family_posture["pm_scoring"]["support_status"] == "SUPPORTED"
    assert family_posture["pm_scoring"] == {
        "family_key": "pm_scoring",
        "source_system": "lotus-manage",
        "owner": "lotus-manage PM operating quality product",
        "support_status": "SUPPORTED",
        "event_types": ["PM_QUALITY_SCORE_RUN"],
        "route": "/api/v1/rebalance/pm-operating-quality/score-runs",
        "reason_code": "PM_QUALITY_SCORE_RUN_SOURCE_EVENTS_SUPPORTED",
        "summary": (
            "Persisted PM operating quality score runs are supported as a separate explicit "
            "Manage product with bank-supplied policy and source-backed evidence; portfolio "
            "memory projects only source-backed score-run lineage for portfolios included in "
            "Core PM-book membership evidence and does not copy raw score payloads or create "
            "portfolio-level rankings."
        ),
    }
    pm_quality_events = [
        event for event in payload["events"] if event["event_type"] == "PM_QUALITY_SCORE_RUN"
    ]
    assert pm_quality_events[0]["metadata"]["numeric_score_projected"] is False
    assert "score" not in pm_quality_events[0]["metadata"]
    assert all(event["event_identity"] for event in payload["events"])
    assert all(event["redaction_policy"] == "NO_RAW_PAYLOADS" for event in payload["events"])
    assert any(event["event_type"] == "OUTCOME_REVIEW_EVENT" for event in payload["events"])
    assert openapi.status_code == 200
    openapi_json = openapi.json()
    assert "/api/v1/rebalance/portfolio-memory/{portfolio_id}" in openapi_json["paths"]
    memory_schema = openapi_json["components"]["schemas"]["DpmPortfolioMemory"]
    assert "source_event_family_posture" in memory_schema["properties"]
    posture_schema = openapi_json["components"]["schemas"][
        "DpmPortfolioMemorySourceEventFamilyPosture"
    ]
    assert "hidden portfolio-memory truth" in posture_schema["properties"]["summary"]["description"]
    assert (
        "external order acknowledgement, and PM-quality projection boundaries"
        in memory_schema["properties"]["source_event_family_posture"]["description"]
    )


def test_portfolio_memory_helper_edges_preserve_source_safe_states() -> None:
    wave = _wave()
    outcome_ref = DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type="DpmPostTradeOutcomeReview",
        source_id="dor_memory_helper",
        source_version="v1",
        content_hash="sha256:outcome-ref",
    )
    proof_pack_ref = DpmProofPackEvidenceRef(
        ref_type="AI_EVIDENCE_INPUT",
        ref_id="ai-evidence:memory-helper",
        source_system="lotus-manage",
        content_hash="sha256:ai-evidence",
    )
    assert (
        portfolio_memory_service._from_proof_pack_evidence_ref(proof_pack_ref).source_id
        == proof_pack_ref.ref_id
    )
    assert (
        portfolio_memory_service._from_source_product_lineage(
            _mandate_twin().source_lineage[0]
        ).source_type
        == "CoreMandateBinding"
    )
    assert (
        portfolio_memory_service._from_wave_source_ref(wave.items[0].source_refs[0]).source_version
        == "v1"
    )
    assert (
        portfolio_memory_service._from_outcome_source_ref(outcome_ref).source_id
        == outcome_ref.source_id
    )
    assert portfolio_memory_service._memory_state([]) == "EMPTY"
    assert portfolio_memory_service._state("FAILED") == "BLOCKED"
    assert portfolio_memory_service._state("PARTIAL") == "DEGRADED"
    assert portfolio_memory_service._state("CREATED") == "PENDING_REVIEW"
    assert (
        portfolio_memory_service._score_run_includes_portfolio(
            score_run=_pm_quality_score_run().model_copy(update={"book_scope_evidence": None}),
            portfolio_id=PORTFOLIO_ID,
        )
        is False
    )
    assert (
        portfolio_memory_service._score_run_includes_portfolio(
            score_run=_pm_quality_score_run().model_copy(
                update={
                    "book_scope_evidence": _pm_quality_score_run().book_scope_evidence.model_copy(
                        update={
                            "member_portfolio_ids": [],
                            "source_refs": [
                                DpmOutcomeSourceRef(
                                    source_system="lotus-core",
                                    source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
                                    source_id=f"pm-book:{PORTFOLIO_ID}",
                                )
                            ],
                        }
                    )
                }
            ),
            portfolio_id=PORTFOLIO_ID,
        )
        is True
    )
    assert (
        portfolio_memory_service._monitoring_exception_state(
            _monitoring_exception().model_copy(update={"state": "RESOLVED"})
        )
        == "READY"
    )
    assert (
        portfolio_memory_service._monitoring_exception_state(
            _monitoring_exception().model_copy(update={"severity": MonitoringSeverity.CRITICAL})
        )
        == "BLOCKED"
    )
    assert portfolio_memory_service._monitoring_exception_state(_monitoring_exception()) == (
        "DEGRADED"
    )
    assert (
        portfolio_memory_service._monitoring_exception_state(
            _monitoring_exception().model_copy(update={"severity": MonitoringSeverity.INFO})
        )
        == "PENDING_REVIEW"
    )
