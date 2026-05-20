from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_campaign_definition_repository,
    get_construction_repository,
    get_mandate_repository,
    get_outcome_review_repository,
    get_pm_quality_review_action_repository,
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
    DpmPmQualityReviewAction,
)
from src.core.pm_quality.review_actions import build_pm_quality_review_action
from src.core.portfolio_memory import service as portfolio_memory_service
from src.core.portfolio_memory.service import build_portfolio_memory, search_portfolio_memory
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
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentAction,
    DpmBulkReviewCampaignDefinitionAssignmentTask,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
    DpmBulkReviewCampaignDefinitionMakerCheckerControl,
)
from src.core.waves.campaign_definition_approval_decisions import (
    record_bulk_review_campaign_definition_approval_decision,
)
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityScoreRunRepository,
)
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.waves import (
    InMemoryDpmBulkReviewCampaignDefinitionRepository,
    InMemoryDpmWaveRepository,
)
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


def _pm_quality_review_action() -> DpmPmQualityReviewAction:
    score_run = _pm_quality_score_run()
    return build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="REQUEST_EVIDENCE_REMEDIATION",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Request source evidence remediation before supervisory closure.",
        actor_id="cio_ops_committee",
        source_refs=[
            DpmOutcomeSourceRef(
                source_system="lotus-manage",
                source_type="CIO_REVIEW_TICKET",
                source_id="cio-review-ticket-001",
                source_version="2026-05",
                content_hash="sha256:cio-review-ticket-001",
            )
        ],
        remediation_due_date="2026-05-20",
        correlation_id="corr-pmq-review-action-memory",
        generated_at=datetime(2026, 5, 12, 11, 0, tzinfo=timezone.utc),
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


def _campaign_definition() -> DpmBulkReviewCampaignDefinition:
    source_ref = DpmWaveSourceRef(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id="pm-book-snapshot-20260513",
        source_version="v1",
        supportability_state="READY",
        content_hash="sha256:pm-book-campaign",
    )
    definition = DpmBulkReviewCampaignDefinition(
        campaign_id="campaign-memory-review-20260513",
        campaign_version="2026.05",
        display_name="Memory-backed campaign review",
        as_of_date="2026-05-13",
        rationale="Review discretionary portfolios affected by a source-backed campaign.",
        eligible_portfolio_types=["DISCRETIONARY"],
        candidates=[
            DpmBulkReviewCampaignDefinitionCandidate(
                portfolio_id=PORTFOLIO_ID,
                mandate_id="MANDATE_PB_SG_GLOBAL_BAL_001",
                portfolio_manager_id="pm_001",
                portfolio_type="DISCRETIONARY",
                source_refs=[source_ref],
            )
        ],
        governance=DpmBulkReviewCampaignDefinitionGovernance(
            approval_ref="BRC-APPROVAL-2026-05",
            approved_by="cio_ops_committee",
            approved_at="2026-05-13T08:30:00+00:00",
            expires_on="2026-06-30",
            entitled_actor_ids=["pm_001"],
            access_purpose="SUPERVISORY_BULK_REVIEW",
            source_refs=[
                DpmWaveSourceRef(
                    source_system="lotus-manage",
                    source_type="BULK_REVIEW_CAMPAIGN_APPROVAL_RECORD",
                    source_id="BRC-APPROVAL-2026-05",
                    source_version="2026.05",
                    supportability_state="READY",
                    content_hash="sha256:campaign-approval",
                )
            ],
        ),
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="BULK_REVIEW_CAMPAIGN_DEFINITION_RECORD",
                source_id="campaign-memory-review-20260513",
                source_version="2026.05",
                supportability_state="READY",
                content_hash="sha256:campaign-definition-record",
            )
        ],
        created_at=datetime(2026, 5, 13, 8, 0, tzinfo=timezone.utc),
        created_by="ops",
        correlation_id="corr-campaign-memory-definition",
    )
    definition = record_bulk_review_campaign_definition_approval_decision(
        definition=definition,
        decision_type="APPROVED",
        decision_ref="BRC-DECISION-2026-05",
        decided_by="cio_ops_committee",
        decision_reason="Campaign candidate evidence is source-backed.",
        correlation_id="corr-campaign-memory-approval",
        source_refs=[
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_RECORD",
                source_id="BRC-DECISION-2026-05",
                source_version="2026.05",
                supportability_state="READY",
                content_hash="sha256:campaign-approval-decision",
            )
        ],
    )
    transition = DpmBulkReviewCampaignDefinitionAssignmentTaskTransition(
        transition_id="brc_assignment_task_transition_memory_001",
        transition_type="OPENED",
        transition_ref="BRC-TASK-2026-05-001:opened",
        transitioned_at=datetime(2026, 5, 13, 9, 20, tzinfo=timezone.utc),
        transitioned_by="ops",
        from_status=None,
        to_status="OPEN",
        transition_reason="Open PM review task.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-memory-task-opened",
        content_hash="sha256:campaign-task-transition",
    )
    return DpmBulkReviewCampaignDefinition.model_validate(
        definition.model_copy(
            update={
                "assignment_actions": [
                    DpmBulkReviewCampaignDefinitionAssignmentAction(
                        action_id="brc_assignment_action_memory_001",
                        action_type="ASSIGNED",
                        action_ref="BRC-ASSIGN-2026-05-001",
                        recorded_at=datetime(2026, 5, 13, 9, 0, tzinfo=timezone.utc),
                        recorded_by="ops",
                        action_reason="Assign source-backed candidate to PM review.",
                        assigned_actor_ids=["pm_001"],
                        escalation_tier="PM",
                        sla_posture="ON_TRACK",
                        correlation_id="corr-campaign-memory-assignment",
                        content_hash="sha256:campaign-assignment-action",
                    )
                ],
                "assignment_tasks": [
                    DpmBulkReviewCampaignDefinitionAssignmentTask(
                        task_id="brc_assignment_task_memory_001",
                        task_ref="BRC-TASK-2026-05-001",
                        task_type="ASSIGNMENT",
                        status="OPEN",
                        opened_at=datetime(2026, 5, 13, 9, 15, tzinfo=timezone.utc),
                        opened_by="ops",
                        task_reason="PM must review campaign candidate.",
                        assigned_actor_ids=["pm_001"],
                        escalation_tier="PM",
                        sla_posture="ON_TRACK",
                        correlation_id="corr-campaign-memory-task",
                        transitions=[transition],
                        content_hash="sha256:campaign-assignment-task",
                    )
                ],
                "maker_checker_controls": [
                    DpmBulkReviewCampaignDefinitionMakerCheckerControl(
                        control_id="brc_maker_checker_memory_001",
                        control_action="REVIEW_COMPLETED",
                        control_ref="BRC-MC-2026-05-001",
                        recorded_at=datetime(2026, 5, 13, 9, 30, tzinfo=timezone.utc),
                        recorded_by="ops",
                        submitter_actor_id="pm_001",
                        reviewer_actor_id="cio_ops_committee",
                        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
                        control_outcome="PASSED",
                        control_reason="Maker and checker actors are distinct.",
                        correlation_id="corr-campaign-memory-maker-checker",
                        content_hash="sha256:campaign-maker-checker",
                    )
                ],
                "content_hash": "",
            }
        ).model_dump(mode="python")
    )


def test_portfolio_memory_composes_proof_pack_wave_handoff_and_outcome_events() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    construction_repository = _construction_repository()
    pm_quality_repository = InMemoryDpmPmQualityScoreRunRepository()
    pm_quality_repository.save_score_run(score_run=_pm_quality_score_run())
    pm_quality_review_repository = InMemoryDpmPmQualityReviewActionRepository()
    pm_quality_review_repository.save_review_action(action=_pm_quality_review_action())
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    campaign_repository.save_definition(definition=_campaign_definition())

    memory = build_portfolio_memory(
        portfolio_id=PORTFOLIO_ID,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        construction_repository=construction_repository,
        pm_quality_score_run_repository=pm_quality_repository,
        pm_quality_review_action_repository=pm_quality_review_repository,
        campaign_definition_repository=campaign_repository,
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
    assert memory.event_type_counts["BULK_REVIEW_CAMPAIGN_DEFINITION"] == 1
    assert memory.event_type_counts["BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION"] == 1
    assert memory.event_type_counts["BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION"] == 1
    assert memory.event_type_counts["BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK"] == 1
    assert memory.event_type_counts["BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL"] == 1
    assert memory.event_type_counts["OUTCOME_REVIEW_CREATED"] == 1
    assert memory.event_type_counts["PM_QUALITY_SCORE_RUN"] == 1
    assert memory.event_type_counts["PM_QUALITY_REVIEW_ACTION"] == 1
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
    assert family_posture["bulk_review_campaign_workflow"].support_status == "SUPPORTED"
    assert family_posture["bulk_review_campaign_workflow"].event_types == [
        "BULK_REVIEW_CAMPAIGN_DEFINITION",
        "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
        "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
    ]
    assert "without discovering the global portfolio universe" in (
        family_posture["bulk_review_campaign_workflow"].summary
    )
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
    assert family_posture["pm_quality_review_action"].source_system == "lotus-manage"
    assert family_posture["pm_quality_review_action"].support_status == "SUPPORTED"
    assert family_posture["pm_quality_review_action"].event_types == ["PM_QUALITY_REVIEW_ACTION"]
    assert family_posture["pm_quality_review_action"].route == (
        "/api/v1/rebalance/pm-operating-quality/review-actions"
    )
    assert family_posture["pm_quality_review_action"].reason_code == (
        "PM_QUALITY_REVIEW_ACTION_SOURCE_EVENTS_SUPPORTED"
    )
    assert "without copying raw review rationale" in (
        family_posture["pm_quality_review_action"].summary
    )
    assert memory.external_execution_boundary.boundary_id == (
        "DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY"
    )
    assert memory.external_execution_boundary.supportability_state == "BLOCKED"
    assert memory.external_execution_boundary.external_execution_events_projected is False
    assert memory.external_execution_boundary.external_acknowledgement_events_projected is False
    assert memory.external_execution_boundary.required_owner == "future execution/OMS owner"
    assert memory.external_execution_boundary.required_source_product == (
        "ExternalOrderExecutionAcknowledgement:v1"
    )
    assert "oms_acknowledgement" in memory.external_execution_boundary.blocked_capabilities
    assert "execution_status_projection" in memory.external_execution_boundary.blocked_capabilities
    assert memory.external_execution_boundary.content_hash.startswith("sha256:")
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
    pm_quality_review_events = [
        event for event in memory.events if event.event_type == "PM_QUALITY_REVIEW_ACTION"
    ]
    assert pm_quality_review_events[0].source_id == _pm_quality_review_action().review_action_id
    assert pm_quality_review_events[0].supportability_state == "PENDING_REVIEW"
    assert pm_quality_review_events[0].metadata["action_state"] == "REVIEW_REQUIRED"
    assert pm_quality_review_events[0].metadata["review_reason_projected"] is False
    assert pm_quality_review_events[0].metadata["numeric_score_projected"] is False
    assert pm_quality_review_events[0].metadata["fairness_recomputed"] is False
    assert pm_quality_review_events[0].metadata["pm_ranking_created"] is False
    assert pm_quality_review_events[0].metadata["client_contact_claimed"] is False
    assert pm_quality_review_events[0].metadata["external_execution_claimed"] is False
    assert "review_reason" not in pm_quality_review_events[0].metadata
    assert "score" not in pm_quality_review_events[0].metadata
    assert (
        "NO_SCORE_RECALCULATION" in (pm_quality_review_events[0].metadata["operating_boundaries"])
    )
    construction_events = {
        event.event_type: event
        for event in memory.events
        if event.event_type in {"CONSTRUCTION_ALTERNATIVE_SET", "CONSTRUCTION_ALTERNATIVE_SELECTED"}
    }
    campaign_events = {
        event.event_type: event
        for event in memory.events
        if event.event_type.startswith("BULK_REVIEW_CAMPAIGN_")
    }
    assert (
        campaign_events["BULK_REVIEW_CAMPAIGN_DEFINITION"].metadata[
            "global_portfolio_universe_discovered"
        ]
        is False
    )
    assert (
        campaign_events["BULK_REVIEW_CAMPAIGN_DEFINITION"].metadata[
            "raw_campaign_payload_projected"
        ]
        is False
    )
    assert campaign_events["BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK"].supportability_state == (
        "PENDING_REVIEW"
    )
    assert (
        campaign_events["BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION"].metadata[
            "external_workflow_orchestration_claimed"
        ]
        is False
    )
    assert (
        campaign_events["BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL"].metadata[
            "external_execution_claimed"
        ]
        is False
    )
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
    pm_quality_review_repository = InMemoryDpmPmQualityReviewActionRepository()
    pm_quality_review_repository.save_review_action(action=_pm_quality_review_action())
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    campaign_repository.save_definition(definition=_campaign_definition())
    app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    app.dependency_overrides[get_construction_repository] = lambda: construction_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_mandate_repository] = lambda: mandate_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: pm_quality_repository
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: (
        pm_quality_review_repository
    )
    app.dependency_overrides[get_campaign_definition_repository] = lambda: campaign_repository
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
    assert payload["event_type_counts"]["PM_QUALITY_REVIEW_ACTION"] == 1
    assert payload["event_type_counts"]["BULK_REVIEW_CAMPAIGN_DEFINITION"] == 1
    assert payload["event_type_counts"]["BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL"] == 1
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
    assert family_posture["pm_quality_review_action"] == {
        "family_key": "pm_quality_review_action",
        "source_system": "lotus-manage",
        "owner": "lotus-manage PM operating quality product",
        "support_status": "SUPPORTED",
        "event_types": ["PM_QUALITY_REVIEW_ACTION"],
        "route": "/api/v1/rebalance/pm-operating-quality/review-actions",
        "reason_code": "PM_QUALITY_REVIEW_ACTION_SOURCE_EVENTS_SUPPORTED",
        "summary": (
            "Persisted PM operating quality review actions are projected as bounded "
            "supervisory evidence for portfolios included in the reviewed score-run's "
            "Core PM-book membership evidence. Portfolio memory preserves target identity, "
            "state, source refs, content hashes, and action posture without copying raw "
            "review rationale, recalculating scores, recomputing fairness, ranking PMs, "
            "or creating HR, conduct, client-contact, trade, order, or OMS claims."
        ),
    }
    assert family_posture["bulk_review_campaign_workflow"]["support_status"] == "SUPPORTED"
    assert family_posture["bulk_review_campaign_workflow"]["reason_code"] == (
        "BULK_REVIEW_CAMPAIGN_WORKFLOW_SOURCE_EVENTS_SUPPORTED"
    )
    assert payload["external_execution_boundary"] == {
        "boundary_id": "DPM_PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_BOUNDARY",
        "supportability_state": "BLOCKED",
        "source_system": "lotus-manage",
        "source_product_name": "DpmPortfolioMemory",
        "source_product_version": "v1",
        "external_execution_events_projected": False,
        "external_acknowledgement_events_projected": False,
        "reason_code": "PORTFOLIO_MEMORY_EXTERNAL_EXECUTION_EVENTS_NOT_SUPPORTED",
        "blocked_capabilities": [
            "order_generation",
            "venue_routing",
            "best_execution",
            "oms_acknowledgement",
            "fills",
            "settlement",
            "execution_status_projection",
        ],
        "required_owner": "future execution/OMS owner",
        "required_source_product": "ExternalOrderExecutionAcknowledgement:v1",
        "summary": (
            "Portfolio memory preserves source-backed Manage, report, AI, archive, and PM-quality "
            "lineage only; external execution, OMS acknowledgement, fill, settlement, and "
            "execution-status events remain blocked until a certified bank-owned OMS source-event "
            "family is published."
        ),
        "content_hash": payload["external_execution_boundary"]["content_hash"],
    }
    assert payload["external_execution_boundary"]["content_hash"].startswith("sha256:")
    pm_quality_events = [
        event for event in payload["events"] if event["event_type"] == "PM_QUALITY_SCORE_RUN"
    ]
    campaign_definition_events = [
        event
        for event in payload["events"]
        if event["event_type"] == "BULK_REVIEW_CAMPAIGN_DEFINITION"
    ]
    assert campaign_definition_events[0]["metadata"]["membership_recalculated"] is False
    assert campaign_definition_events[0]["metadata"]["external_execution_claimed"] is False
    assert pm_quality_events[0]["metadata"]["numeric_score_projected"] is False
    assert "score" not in pm_quality_events[0]["metadata"]
    pm_quality_review_events = [
        event for event in payload["events"] if event["event_type"] == "PM_QUALITY_REVIEW_ACTION"
    ]
    assert pm_quality_review_events[0]["metadata"]["review_reason_projected"] is False
    assert pm_quality_review_events[0]["metadata"]["numeric_score_projected"] is False
    assert pm_quality_review_events[0]["metadata"]["score_recalculated"] is False
    assert pm_quality_review_events[0]["metadata"]["fairness_recomputed"] is False
    assert pm_quality_review_events[0]["metadata"]["pm_ranking_created"] is False
    assert pm_quality_review_events[0]["metadata"]["client_contact_claimed"] is False
    assert pm_quality_review_events[0]["metadata"]["external_execution_claimed"] is False
    assert "review_reason" not in pm_quality_review_events[0]["metadata"]
    assert "score" not in pm_quality_review_events[0]["metadata"]
    assert all(event["event_identity"] for event in payload["events"])
    assert all(event["redaction_policy"] == "NO_RAW_PAYLOADS" for event in payload["events"])
    assert any(event["event_type"] == "OUTCOME_REVIEW_EVENT" for event in payload["events"])
    assert openapi.status_code == 200
    openapi_json = openapi.json()
    assert "/api/v1/rebalance/portfolio-memory/{portfolio_id}" in openapi_json["paths"]
    memory_schema = openapi_json["components"]["schemas"]["DpmPortfolioMemory"]
    assert "source_event_family_posture" in memory_schema["properties"]
    assert "external_execution_boundary" in memory_schema["properties"]
    boundary_schema = openapi_json["components"]["schemas"][
        "DpmPortfolioMemoryExternalExecutionBoundaryEvidence"
    ]
    assert (
        "External execution capabilities blocked from portfolio-memory projection."
        in boundary_schema["properties"]["blocked_capabilities"]["description"]
    )
    posture_schema = openapi_json["components"]["schemas"][
        "DpmPortfolioMemorySourceEventFamilyPosture"
    ]
    assert "hidden portfolio-memory truth" in posture_schema["properties"]["summary"]["description"]
    assert (
        "external order acknowledgement, and PM-quality projection boundaries"
        in memory_schema["properties"]["source_event_family_posture"]["description"]
    )


def test_portfolio_memory_search_indexes_manage_local_evidence_without_global_discovery() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()
    construction_repository = _construction_repository()
    pm_quality_repository = InMemoryDpmPmQualityScoreRunRepository()
    pm_quality_repository.save_score_run(score_run=_pm_quality_score_run())
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    campaign_repository.save_definition(definition=_campaign_definition())
    app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    app.dependency_overrides[get_construction_repository] = lambda: construction_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_mandate_repository] = lambda: mandate_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: pm_quality_repository
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: (
        InMemoryDpmPmQualityReviewActionRepository()
    )
    app.dependency_overrides[get_campaign_definition_repository] = lambda: campaign_repository
    app.openapi_schema = None

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/rebalance/portfolio-memory/search",
            params={
                "event_type": "WAVE_HANDOFF_READY",
                "source_system": "lotus-manage",
                "limit": 10,
            },
        )
        openapi = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["returned_count"] == 1
    assert payload["total_count"] == 1
    assert payload["scanned_portfolio_count"] == 1
    assert payload["items"][0]["portfolio_id"] == PORTFOLIO_ID
    assert payload["items"][0]["event_count"] >= 6
    assert payload["items"][0]["event_type_counts"]["WAVE_HANDOFF_READY"] == 1
    assert payload["items"][0]["event_type_counts"]["BULK_REVIEW_CAMPAIGN_DEFINITION"] == 1
    assert payload["items"][0]["latest_event_time"] is not None
    assert payload["items"][0]["content_hash"].startswith("sha256:")
    assert "does not discover the global portfolio universe" in payload["support_boundary"]
    assert "project OMS" in payload["support_boundary"]
    assert openapi.status_code == 200
    openapi_json = openapi.json()
    assert "/api/v1/rebalance/portfolio-memory/search" in openapi_json["paths"]
    search_schema = openapi_json["components"]["schemas"]["DpmPortfolioMemorySearchPage"]
    assert (
        "global portfolio-universe discovery product"
        in (search_schema["properties"]["items"]["description"])
    )


def test_portfolio_memory_search_can_include_explicit_portfolio_for_manage_only_events() -> None:
    proof_pack_repository = InMemoryDpmProofPackRepository()
    wave_repository = InMemoryDpmWaveRepository()
    outcome_repository = InMemoryDpmOutcomeReviewRepository()
    mandate_repository = InMemoryDpmMandateRepository()
    construction_repository = _construction_repository()
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    app.dependency_overrides[get_proof_pack_repository] = lambda: proof_pack_repository
    app.dependency_overrides[get_construction_repository] = lambda: construction_repository
    app.dependency_overrides[get_wave_repository] = lambda: wave_repository
    app.dependency_overrides[get_outcome_review_repository] = lambda: outcome_repository
    app.dependency_overrides[get_mandate_repository] = lambda: mandate_repository
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: (
        InMemoryDpmPmQualityScoreRunRepository()
    )
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: (
        InMemoryDpmPmQualityReviewActionRepository()
    )
    app.dependency_overrides[get_campaign_definition_repository] = lambda: campaign_repository

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/rebalance/portfolio-memory/search",
            params={
                "portfolio_ids": PORTFOLIO_ID,
                "event_type": "CONSTRUCTION_ALTERNATIVE_SELECTED",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["returned_count"] == 1
    assert payload["scanned_portfolio_count"] == 1
    assert payload["items"][0]["event_type_counts"] == {
        "CONSTRUCTION_ALTERNATIVE_SET": 1,
        "CONSTRUCTION_ALTERNATIVE_SELECTED": 1,
    }
    assert "lotus-manage" in payload["items"][0]["source_systems"]


def test_portfolio_memory_search_indexes_campaign_definition_candidates_without_global_discovery() -> (
    None
):
    campaign_repository = InMemoryDpmBulkReviewCampaignDefinitionRepository()
    campaign_repository.save_definition(definition=_campaign_definition())
    app.dependency_overrides[get_proof_pack_repository] = lambda: InMemoryDpmProofPackRepository()
    app.dependency_overrides[get_construction_repository] = lambda: InMemoryConstructionRepository()
    app.dependency_overrides[get_wave_repository] = lambda: InMemoryDpmWaveRepository()
    app.dependency_overrides[get_outcome_review_repository] = lambda: (
        InMemoryDpmOutcomeReviewRepository()
    )
    app.dependency_overrides[get_mandate_repository] = lambda: InMemoryDpmMandateRepository()
    app.dependency_overrides[get_pm_quality_score_run_repository] = lambda: (
        InMemoryDpmPmQualityScoreRunRepository()
    )
    app.dependency_overrides[get_pm_quality_review_action_repository] = lambda: (
        InMemoryDpmPmQualityReviewActionRepository()
    )
    app.dependency_overrides[get_campaign_definition_repository] = lambda: campaign_repository

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/rebalance/portfolio-memory/search",
            params={"event_type": "BULK_REVIEW_CAMPAIGN_DEFINITION"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["returned_count"] == 1
    assert payload["scanned_portfolio_count"] == 1
    assert payload["items"][0]["portfolio_id"] == PORTFOLIO_ID
    assert payload["items"][0]["event_type_counts"] == {
        "BULK_REVIEW_CAMPAIGN_DEFINITION": 1,
        "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION": 1,
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION": 1,
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK": 1,
        "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL": 1,
    }
    assert "does not discover the global portfolio universe" in payload["support_boundary"]


def test_portfolio_memory_search_filters_empty_type_state_and_source_candidates() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()

    empty_filtered = search_portfolio_memory(
        proof_pack_repository=InMemoryDpmProofPackRepository(),
        wave_repository=InMemoryDpmWaveRepository(),
        outcome_review_repository=InMemoryDpmOutcomeReviewRepository(),
        mandate_repository=InMemoryDpmMandateRepository(),
        portfolio_ids=["EMPTY_PORTFOLIO"],
    )
    event_type_filtered = search_portfolio_memory(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        portfolio_ids=[PORTFOLIO_ID],
        event_type="NOT_A_MEMORY_EVENT",
    )
    state_filtered = search_portfolio_memory(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        portfolio_ids=[PORTFOLIO_ID],
        supportability_state="BLOCKED",
    )
    source_filtered = search_portfolio_memory(
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_repository,
        mandate_repository=mandate_repository,
        portfolio_ids=[PORTFOLIO_ID],
        source_system="not-a-source-system",
    )

    assert empty_filtered.returned_count == 0
    assert event_type_filtered.returned_count == 0
    assert state_filtered.returned_count == 0
    assert source_filtered.returned_count == 0


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
    assert (
        portfolio_memory_service._pm_quality_review_action_state(
            _pm_quality_review_action().model_copy(update={"action_state": "ESCALATED"})
        )
        == "DEGRADED"
    )
    assert (
        portfolio_memory_service._pm_quality_review_action_state(
            _pm_quality_review_action().model_copy(update={"action_state": "CLOSED"})
        )
        == "READY"
    )
    assert portfolio_memory_service._assignment_sla_state("BREACHED_OR_BLOCKED") == "DEGRADED"
    assert portfolio_memory_service._assignment_task_state("CANCELLED", "ON_TRACK") == "BLOCKED"
    assert portfolio_memory_service._assignment_task_state("BLOCKED", "ON_TRACK") == "DEGRADED"
    assert portfolio_memory_service._assignment_task_state("OPEN", "ON_TRACK") == "PENDING_REVIEW"
    assert portfolio_memory_service._assignment_task_state("DONE", "ON_TRACK") == "READY"
    assert portfolio_memory_service._maker_checker_state("FAILED") == "BLOCKED"
    assert portfolio_memory_service._maker_checker_state("EXCEPTION_OPEN") == "DEGRADED"
    assert portfolio_memory_service._maker_checker_state("PENDING") == "PENDING_REVIEW"
