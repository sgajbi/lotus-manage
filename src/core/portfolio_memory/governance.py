"""Governance and source-boundary posture for portfolio memory."""

from src.core.common.boundary_promotion import (
    CLIENT_COMMUNICATION_PROMOTION_REQUIREMENTS,
    EXTERNAL_EXECUTION_PROMOTION_REQUIREMENTS,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.portfolio_memory.models import (
    DpmPortfolioMemoryClientCommunicationBoundaryEvidence,
    DpmPortfolioMemoryExternalExecutionBoundaryEvidence,
    DpmPortfolioMemorySourceEventFamilyPosture,
    PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
    PORTFOLIO_MEMORY_AUDIT_POLICY,
    PORTFOLIO_MEMORY_EVENT_IDENTITY_SCHEME,
    PORTFOLIO_MEMORY_REDACTION_POLICY,
    PORTFOLIO_MEMORY_RETENTION_POLICY,
    PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
)


def portfolio_memory_governance_policy() -> dict[str, str]:
    return {
        "event_identity_scheme": PORTFOLIO_MEMORY_EVENT_IDENTITY_SCHEME,
        "retention_policy": PORTFOLIO_MEMORY_RETENTION_POLICY,
        "redaction_policy": PORTFOLIO_MEMORY_REDACTION_POLICY,
        "audit_policy": PORTFOLIO_MEMORY_AUDIT_POLICY,
        "access_classification": PORTFOLIO_MEMORY_ACCESS_CLASSIFICATION,
        "source_authority_policy": PORTFOLIO_MEMORY_SOURCE_AUTHORITY_POLICY,
    }


def external_execution_boundary_evidence() -> DpmPortfolioMemoryExternalExecutionBoundaryEvidence:
    payload = {
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
        "promotion_requirements": list(EXTERNAL_EXECUTION_PROMOTION_REQUIREMENTS),
        "summary": (
            "Portfolio memory preserves source-backed Manage, report, AI, archive, and PM-quality "
            "lineage only; external execution, OMS acknowledgement, fill, settlement, and "
            "execution-status events remain blocked until a certified bank-owned OMS source-event "
            "family is published."
        ),
    }
    payload["content_hash"] = hash_canonical_payload(payload)
    return DpmPortfolioMemoryExternalExecutionBoundaryEvidence.model_validate(payload)


def client_communication_boundary_evidence() -> (
    DpmPortfolioMemoryClientCommunicationBoundaryEvidence
):
    payload = {
        "boundary_id": "DPM_PORTFOLIO_MEMORY_CLIENT_COMMUNICATION_BOUNDARY",
        "supportability_state": "BLOCKED",
        "source_system": "lotus-manage",
        "source_product_name": "DpmPortfolioMemory",
        "source_product_version": "v1",
        "client_communication_events_projected": False,
        "client_delivery_events_projected": False,
        "client_approval_events_projected": False,
        "reason_code": "PORTFOLIO_MEMORY_CLIENT_COMMUNICATION_EVENTS_NOT_SUPPORTED",
        "blocked_capabilities": [
            "client_contact",
            "client_message_generation",
            "client_delivery",
            "delivery_confirmation",
            "client_approval",
            "communication_audit",
        ],
        "required_owner": "future client-communication owner",
        "required_source_product": "ClientCommunicationRecord:v1",
        "promotion_requirements": list(CLIENT_COMMUNICATION_PROMOTION_REQUIREMENTS),
        "summary": (
            "Portfolio memory preserves internal Manage, report, AI, archive, and PM-quality "
            "lineage only; client contact, client message generation, client delivery "
            "confirmation, client approval, and communication audit events remain blocked until "
            "a certified client-communication owner publishes governed source events."
        ),
    }
    payload["content_hash"] = hash_canonical_payload(payload)
    return DpmPortfolioMemoryClientCommunicationBoundaryEvidence.model_validate(payload)


def source_event_family_posture() -> list[DpmPortfolioMemorySourceEventFamilyPosture]:
    return [
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="mandate_health",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["MANDATE_HEALTH_SNAPSHOT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="MANDATE_HEALTH_SOURCE_EVENTS_SUPPORTED",
            summary="Mandate health snapshots are projected from persisted mandate repository truth.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="mandate_monitoring_exception",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["MANDATE_MONITORING_EXCEPTION"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="MANDATE_MONITORING_SOURCE_EVENTS_SUPPORTED",
            summary="Mandate monitoring exceptions are projected from persisted exception truth.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="proof_pack_decision_timeline",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["PROOF_PACK_CREATED", "PROOF_PACK_TIMELINE_EVENT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="PROOF_PACK_SOURCE_EVENTS_SUPPORTED",
            summary="Proof-pack creation and proof-pack-local decision timeline events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="construction_alternatives",
            source_system="lotus-manage",
            owner="lotus-manage construction alternatives product",
            support_status="SUPPORTED",
            event_types=["CONSTRUCTION_ALTERNATIVE_SET", "CONSTRUCTION_ALTERNATIVE_SELECTED"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="CONSTRUCTION_ALTERNATIVE_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Construction alternative set generation and selected-alternative decisions are "
                "projected from persisted construction repository truth without copying raw "
                "request payloads or recalculating construction, risk, performance, tax, cash, "
                "FX, or execution methodology."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="rebalance_wave",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["WAVE_CREATED", "WAVE_EVENT", "WAVE_HANDOFF_READY"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="REBALANCE_WAVE_SOURCE_EVENTS_SUPPORTED",
            summary="Rebalance wave lifecycle and internal handoff events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="bulk_review_campaign_workflow",
            source_system="lotus-manage",
            owner="lotus-manage campaign definition product",
            support_status="SUPPORTED",
            event_types=[
                "BULK_REVIEW_CAMPAIGN_DEFINITION",
                "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION",
                "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION",
                "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK",
                "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION",
                "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL",
            ],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="BULK_REVIEW_CAMPAIGN_WORKFLOW_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Bulk-review campaign definitions and Manage-side approval, assignment, task, "
                "task-transition, and maker-checker evidence are projected from persisted "
                "campaign truth without discovering the global portfolio universe, "
                "recalculating membership, or orchestrating external workflow, client-contact, "
                "order, or OMS actions."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="post_trade_outcome_review",
            source_system="lotus-manage",
            owner="lotus-manage",
            support_status="SUPPORTED",
            event_types=["OUTCOME_REVIEW_CREATED", "OUTCOME_REVIEW_EVENT"],
            route="/api/v1/rebalance/portfolio-memory/{portfolio_id}",
            reason_code="OUTCOME_REVIEW_SOURCE_EVENTS_SUPPORTED",
            summary="Post-trade outcome-review creation and review events are projected.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="report_lifecycle",
            source_system="lotus-report",
            owner="lotus-report",
            support_status="SUPPORTED",
            event_types=[
                "REPORT_JOB_CREATED",
                "REPORT_SNAPSHOT_CAPTURED",
                "REPORT_RENDERED",
                "REPORT_ARCHIVED",
            ],
            route="/reports/jobs/{job_id}/portfolio-memory-events",
            reason_code="REPORT_SOURCE_EVENTS_SUPPORTED",
            summary="Report lifecycle, snapshot, render, and archive lineage are source-owned by report.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="ai_workflow_pack",
            source_system="lotus-ai",
            owner="lotus-ai",
            support_status="SUPPORTED",
            event_types=[
                "AI_WORKFLOW_PACK_RUN",
                "AI_WORKFLOW_PACK_REVIEW",
                "AI_WORKFLOW_PACK_LINEAGE",
            ],
            route="/platform/workflow-packs/source-events",
            reason_code="AI_WORKFLOW_PACK_SOURCE_EVENTS_SUPPORTED",
            summary="AI workflow-pack run, review, and lineage posture are source-owned by AI.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="generated_document_archive",
            source_system="lotus-archive",
            owner="lotus-archive",
            support_status="SUPPORTED",
            event_types=[
                "GENERATED_DOCUMENT_ARCHIVED",
                "GENERATED_DOCUMENT_SUPERSEDED",
                "GENERATED_DOCUMENT_CORRECTED",
                "CLIENT_DELIVERY_REISSUED",
            ],
            route="/documents/{document_id}/source-events",
            reason_code="GENERATED_DOCUMENT_SOURCE_EVENTS_SUPPORTED",
            summary="Generated-document archive and client-delivery lineage are source-owned by archive.",
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="client_communication",
            source_system="future-client-communication-owner",
            owner="future client-communication owner",
            support_status="DEFERRED_SOURCE_OWNER",
            event_types=[],
            route=None,
            reason_code="CLIENT_COMMUNICATION_SOURCE_EVENTS_NOT_SUPPORTED",
            summary=(
                "No client contact, message generation, delivery confirmation, client approval, "
                "or communication-audit events are projected until a governed "
                "client-communication owner publishes a no-raw-payload source-event family."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="external_oms_execution",
            source_system="future-oms-owner",
            owner="future execution or OMS owner",
            support_status="DEFERRED_SOURCE_OWNER",
            event_types=[],
            route=None,
            reason_code="OMS_SOURCE_EVENTS_NOT_SUPPORTED",
            summary=(
                "No external OMS execution, fill, or acknowledgement events are projected until a "
                "governed OMS owner publishes a no-raw-payload source-event family."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="external_order_execution_acknowledgement",
            source_system="lotus-core",
            owner="lotus-core source-boundary posture; future execution or OMS owner",
            support_status="DEFERRED_SOURCE_OWNER",
            event_types=[],
            route="/integration/portfolios/{portfolio_id}/external-order-execution-acknowledgement",
            reason_code="EXTERNAL_ORDER_ACKNOWLEDGEMENT_SOURCE_EVENTS_DEFERRED",
            summary=(
                "Core ExternalOrderExecutionAcknowledgement:v1 is consumed only as fail-closed "
                "source-product posture for construction and outcome evidence; portfolio memory "
                "does not project acknowledgement, fill, settlement, or execution-status events "
                "until bank-owned OMS acknowledgement ingestion publishes a certified "
                "no-raw-payload source-event family."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="pm_scoring",
            source_system="lotus-manage",
            owner="lotus-manage PM operating quality product",
            support_status="SUPPORTED",
            event_types=["PM_QUALITY_SCORE_RUN"],
            route="/api/v1/rebalance/pm-operating-quality/score-runs",
            reason_code="PM_QUALITY_SCORE_RUN_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Persisted PM operating quality score runs are supported as a separate explicit "
                "Manage product with bank-supplied policy and source-backed evidence; portfolio "
                "memory projects only source-backed score-run lineage for portfolios included in "
                "Core PM-book membership evidence and does not copy raw score payloads or create "
                "portfolio-level rankings."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="pm_quality_review_action",
            source_system="lotus-manage",
            owner="lotus-manage PM operating quality product",
            support_status="SUPPORTED",
            event_types=["PM_QUALITY_REVIEW_ACTION"],
            route="/api/v1/rebalance/pm-operating-quality/review-actions",
            reason_code="PM_QUALITY_REVIEW_ACTION_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Persisted PM operating quality review actions are projected as bounded "
                "supervisory evidence for portfolios included in the reviewed score-run's "
                "Core PM-book membership evidence. Portfolio memory preserves target identity, "
                "state, source refs, content hashes, and action posture without copying raw "
                "review rationale, recalculating scores, recomputing fairness, ranking PMs, "
                "or creating HR, conduct, client-contact, trade, order, or OMS claims."
            ),
        ),
        DpmPortfolioMemorySourceEventFamilyPosture(
            family_key="pm_quality_summary_invocation",
            source_system="lotus-manage",
            owner="lotus-manage PM operating quality product",
            support_status="SUPPORTED",
            event_types=["PM_QUALITY_SUMMARY_INVOCATION"],
            route="/api/v1/rebalance/pm-operating-quality/summary-invocations",
            reason_code="PM_QUALITY_SUMMARY_INVOCATION_SOURCE_EVENTS_SUPPORTED",
            summary=(
                "Persisted PM operating quality summary invocations are projected as bounded "
                "workflow invocation lineage for portfolios included in the summarized score-run's "
                "Core PM-book membership evidence. Portfolio memory preserves score-run, "
                "review-action, workflow-run, artifact refs, hashes, and summary-text boundary "
                "posture without storing generated summary text, reconstructing prompts or model "
                "responses, recalculating scores, recomputing fairness, ranking PMs, contacting "
                "clients, approving trades, routing orders, or claiming OMS execution."
            ),
        ),
    ]
