from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_assignment_plan import (
    DpmBulkReviewCampaignAssignmentPlanItem,
    build_bulk_review_campaign_assignment_plan_item,
)
from src.core.waves.campaign_assignment_tasks import (
    CampaignAssignmentTaskType,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionAssignmentTask,
)


CampaignWorkflowAutomationStatus = Literal[
    "AUTOMATION_CANDIDATE",
    "MANUAL_REVIEW_REQUIRED",
    "BLOCKED",
    "CLOSED",
]
CampaignWorkflowAutomationAction = Literal[
    "OPEN_ASSIGNMENT_TASK",
    "MONITOR_ACTIVE_TASK",
    "ESCALATE_ASSIGNMENT_TASK",
    "NO_AUTOMATION_BLOCKED",
    "NO_AUTOMATION_CLOSED",
]
CampaignWorkflowReadinessSupport = Literal["SUPPORTED"]
CampaignWorkflowMutationSupport = Literal["CONTROLLED_ENDPOINT_ONLY"]
ExternalWorkflowOrchestrationSupport = Literal["UNSUPPORTED"]
ExternalWorkflowOwnerPosture = Literal["DEFERRED_SOURCE_OWNER"]
ExternalWorkflowEventProjectionSupport = Literal[False]

_CLOSED_TASK_STATUSES = {"RESOLVED", "CANCELLED"}
_BLOCKED_TASK_STATUSES = {"BLOCKED"}
EXTERNAL_WORKFLOW_REQUIRED_SOURCE_PRODUCT = "ExternalWorkflowOrchestrationRecord:v1"
EXTERNAL_WORKFLOW_BLOCKED_CAPABILITIES = [
    "external_workflow_task_creation",
    "external_workflow_task_assignment",
    "external_workflow_state_synchronization",
    "external_workflow_escalation",
    "external_workflow_completion",
]
WORKFLOW_AUTOMATION_OPERATING_BOUNDARIES = [
    "READ_ONLY_WORKFLOW_AUTOMATION_PLAN",
    "NO_AUTOMATIC_TASK_MUTATION",
    "NO_EXTERNAL_WORKFLOW_ORCHESTRATION",
    "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY",
    "NO_SOURCE_FACT_RECALCULATION",
    "NO_APPROVAL_STATE_MUTATION",
    "NO_AUTOMATIC_MAKER_CHECKER_MUTATION",
    "NO_CLIENT_CONTACT",
    "NO_TRADE_APPROVAL",
    "NO_ORDER_GENERATION",
    "NO_OMS_EXECUTION_CLAIM",
]


def _workflow_capability_posture_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignWorkflowCapabilityPosture",
        "product_version": "v1",
        "manage_assignment_task_readiness": "SUPPORTED",
        "manage_assignment_task_mutation": "CONTROLLED_ENDPOINT_ONLY",
        "external_workflow_orchestration": "UNSUPPORTED",
        "external_workflow_events_projected": False,
        "external_workflow_owner_posture": "DEFERRED_SOURCE_OWNER",
        "required_source_product": EXTERNAL_WORKFLOW_REQUIRED_SOURCE_PRODUCT,
        "blocked_capabilities": list(EXTERNAL_WORKFLOW_BLOCKED_CAPABILITIES),
        "controlled_assignment_task_endpoint": (
            "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/"
            "{campaign_version}/assignment-tasks"
        ),
        "operating_boundaries": list(WORKFLOW_AUTOMATION_OPERATING_BOUNDARIES),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return payload


class DpmBulkReviewCampaignWorkflowCapabilityPosture(BaseModel):
    """Machine-readable capability posture for campaign workflow automation."""

    product_name: Literal["BulkReviewCampaignWorkflowCapabilityPosture"] = (
        "BulkReviewCampaignWorkflowCapabilityPosture"
    )
    product_version: Literal["v1"] = "v1"
    manage_assignment_task_readiness: CampaignWorkflowReadinessSupport = Field(
        default="SUPPORTED",
        description=(
            "Manage supports deterministic readiness classification for controlled assignment "
            "tasks from persisted campaign definitions."
        ),
        examples=["SUPPORTED"],
    )
    manage_assignment_task_mutation: CampaignWorkflowMutationSupport = Field(
        default="CONTROLLED_ENDPOINT_ONLY",
        description=(
            "Assignment task state may only be changed through the explicit controlled "
            "assignment-task endpoints, never by this read-only automation projection."
        ),
        examples=["CONTROLLED_ENDPOINT_ONLY"],
    )
    external_workflow_orchestration: ExternalWorkflowOrchestrationSupport = Field(
        default="UNSUPPORTED",
        description=(
            "External workflow-engine orchestration is outside this Manage projection and is not "
            "claimed by the workflow-automation endpoint."
        ),
        examples=["UNSUPPORTED"],
    )
    external_workflow_events_projected: ExternalWorkflowEventProjectionSupport = Field(
        default=False,
        description=(
            "The workflow-automation projection does not publish external workflow task, "
            "assignment, escalation, synchronization, or completion events."
        ),
        examples=[False],
    )
    external_workflow_owner_posture: ExternalWorkflowOwnerPosture = Field(
        default="DEFERRED_SOURCE_OWNER",
        description=(
            "Future external workflow orchestration requires an owning workflow source product "
            "or bank workflow authority before Manage can consume it."
        ),
        examples=["DEFERRED_SOURCE_OWNER"],
    )
    required_source_product: str = Field(
        default=EXTERNAL_WORKFLOW_REQUIRED_SOURCE_PRODUCT,
        description=(
            "Future source product required before Manage can consume external workflow "
            "orchestration truth."
        ),
        examples=[EXTERNAL_WORKFLOW_REQUIRED_SOURCE_PRODUCT],
    )
    blocked_capabilities: list[str] = Field(
        default_factory=lambda: list(EXTERNAL_WORKFLOW_BLOCKED_CAPABILITIES),
        description=(
            "External workflow capabilities blocked from this read-only Manage automation "
            "projection."
        ),
        examples=[["external_workflow_task_creation", "external_workflow_escalation"]],
    )
    controlled_assignment_task_endpoint: str = Field(
        default=(
            "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/"
            "{campaign_version}/assignment-tasks"
        ),
        description="Endpoint family for explicit controlled assignment-task state changes.",
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: list(WORKFLOW_AUTOMATION_OPERATING_BOUNDARIES),
        description="Unsupported claims this capability posture must not imply.",
    )
    content_hash: str = Field(
        default="",
        description="Canonical hash over the workflow capability posture payload.",
    )


class DpmBulkReviewCampaignWorkflowAutomationItem(BaseModel):
    """Read-only Manage-side automation readiness for one bulk-review campaign definition."""

    product_name: Literal["BulkReviewCampaignWorkflowAutomationItem"] = (
        "BulkReviewCampaignWorkflowAutomationItem"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    display_name: str = Field(examples=["Apple and Tesla holdings review"])
    requested_as_of_date: str = Field(examples=["2026-05-10"])
    actor_id: str | None = Field(
        default=None,
        description="Actor evaluated against optional entitlement evidence.",
    )
    automation_status: CampaignWorkflowAutomationStatus = Field(
        description="Manage-side workflow automation posture for this campaign definition."
    )
    automation_action: CampaignWorkflowAutomationAction = Field(
        description="Bounded Manage-side action the automation layer may propose but not execute."
    )
    proposed_task_type: CampaignAssignmentTaskType | None = Field(
        default=None,
        description=(
            "Task type that could be opened through the controlled assignment-task endpoint when "
            "the row is an automation candidate. This is proposal evidence only."
        ),
    )
    proposed_task_ref: str | None = Field(
        default=None,
        description="Deterministic proposed task reference for idempotent downstream task opening.",
        examples=["BRC-AUTO-20260510-7A3F91C2"],
    )
    active_task_refs: list[str] = Field(
        description="Existing non-closed assignment tasks that must be monitored before automation."
    )
    blocked_task_refs: list[str] = Field(
        description="Existing blocked or breached assignment tasks that require escalation."
    )
    automation_reason_codes: list[str] = Field(
        description="Reason codes explaining the automation readiness posture."
    )
    capability_posture: DpmBulkReviewCampaignWorkflowCapabilityPosture = Field(
        default_factory=lambda: DpmBulkReviewCampaignWorkflowCapabilityPosture.model_validate(
            _workflow_capability_posture_payload()
        ),
        description=(
            "Machine-readable support boundary for Manage-side assignment readiness versus "
            "unsupported external workflow orchestration."
        ),
    )
    assignment_plan: DpmBulkReviewCampaignAssignmentPlanItem = Field(
        description="Source assignment-plan row used to derive automation readiness."
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: list(WORKFLOW_AUTOMATION_OPERATING_BOUNDARIES),
        description="Unsupported downstream claims this automation projection must not imply.",
    )
    content_hash: str = Field(description="Canonical hash over the automation row.")


class DpmBulkReviewCampaignWorkflowAutomationPage(BaseModel):
    """Read-only Manage-side workflow automation readiness over persisted campaign definitions."""

    product_name: Literal["BulkReviewCampaignWorkflowAutomation"] = (
        "BulkReviewCampaignWorkflowAutomation"
    )
    product_version: Literal["v1"] = "v1"
    items: list[DpmBulkReviewCampaignWorkflowAutomationItem]
    limit: int
    offset: int
    count: int
    automation_status_counts: dict[str, int] = Field(
        description="Automation row counts by status for the returned page."
    )
    automation_action_counts: dict[str, int] = Field(
        description="Automation row counts by proposed action for the returned page."
    )
    capability_posture: DpmBulkReviewCampaignWorkflowCapabilityPosture = Field(
        default_factory=lambda: DpmBulkReviewCampaignWorkflowCapabilityPosture.model_validate(
            _workflow_capability_posture_payload()
        ),
        description=(
            "Page-level support boundary, present even when the returned automation page is empty."
        ),
    )
    content_hash: str = Field(description="Canonical hash over the automation page.")


def build_bulk_review_campaign_workflow_automation_item(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str | None,
    active_on: date | None,
) -> DpmBulkReviewCampaignWorkflowAutomationItem:
    """Classify bounded Manage-side automation readiness from assignment-plan and task state."""

    assignment_plan = build_bulk_review_campaign_assignment_plan_item(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
        active_on=active_on,
    )
    active_tasks = _active_tasks(definition.assignment_tasks)
    blocked_tasks = _blocked_tasks(active_tasks)
    status, action, proposed_task_type, reason_codes = _classify_automation(
        assignment_plan=assignment_plan,
        active_tasks=active_tasks,
        blocked_tasks=blocked_tasks,
    )
    proposed_task_ref = (
        _proposed_task_ref(definition=definition, assignment_plan=assignment_plan)
        if action == "OPEN_ASSIGNMENT_TASK"
        else None
    )
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignWorkflowAutomationItem",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "display_name": definition.display_name,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "automation_status": status,
        "automation_action": action,
        "proposed_task_type": proposed_task_type,
        "proposed_task_ref": proposed_task_ref,
        "active_task_refs": [task.task_ref for task in active_tasks],
        "blocked_task_refs": [task.task_ref for task in blocked_tasks],
        "automation_reason_codes": reason_codes,
        "capability_posture": _workflow_capability_posture().model_dump(mode="json"),
        "assignment_plan": assignment_plan.model_dump(mode="json"),
        "operating_boundaries": list(WORKFLOW_AUTOMATION_OPERATING_BOUNDARIES),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignWorkflowAutomationItem.model_validate(payload)


def build_bulk_review_campaign_workflow_automation_page(
    *,
    definitions: list[DpmBulkReviewCampaignDefinition],
    requested_as_of_date: str | None,
    actor_id: str | None,
    active_on: date | None,
    include_closed: bool,
    automation_status: CampaignWorkflowAutomationStatus | None,
    automation_action: CampaignWorkflowAutomationAction | None,
    limit: int,
    offset: int,
) -> DpmBulkReviewCampaignWorkflowAutomationPage:
    items = [
        build_bulk_review_campaign_workflow_automation_item(
            definition=definition,
            requested_as_of_date=requested_as_of_date or definition.as_of_date,
            actor_id=actor_id,
            active_on=active_on,
        )
        for definition in definitions
    ]
    if not include_closed:
        items = [item for item in items if item.automation_status != "CLOSED"]
    if automation_status is not None:
        items = [item for item in items if item.automation_status == automation_status]
    if automation_action is not None:
        items = [item for item in items if item.automation_action == automation_action]

    status_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.automation_status] = status_counts.get(item.automation_status, 0) + 1
        action_counts[item.automation_action] = action_counts.get(item.automation_action, 0) + 1

    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignWorkflowAutomation",
        "product_version": "v1",
        "items": [item.model_dump(mode="json") for item in items],
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "automation_status_counts": status_counts,
        "automation_action_counts": action_counts,
        "capability_posture": _workflow_capability_posture().model_dump(mode="json"),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignWorkflowAutomationPage.model_validate(payload)


def _classify_automation(
    *,
    assignment_plan: DpmBulkReviewCampaignAssignmentPlanItem,
    active_tasks: list[DpmBulkReviewCampaignDefinitionAssignmentTask],
    blocked_tasks: list[DpmBulkReviewCampaignDefinitionAssignmentTask],
) -> tuple[
    CampaignWorkflowAutomationStatus,
    CampaignWorkflowAutomationAction,
    CampaignAssignmentTaskType | None,
    list[str],
]:
    if assignment_plan.workflow_board.board_status == "CLOSED":
        return "CLOSED", "NO_AUTOMATION_CLOSED", None, ["CAMPAIGN_DEFINITION_CLOSED"]
    if blocked_tasks:
        return (
            "BLOCKED",
            "ESCALATE_ASSIGNMENT_TASK",
            None,
            ["ACTIVE_ASSIGNMENT_TASK_BLOCKED_OR_BREACHED"],
        )
    if active_tasks:
        return "MANUAL_REVIEW_REQUIRED", "MONITOR_ACTIVE_TASK", None, ["ACTIVE_TASK_EXISTS"]
    return (
        "AUTOMATION_CANDIDATE",
        "OPEN_ASSIGNMENT_TASK",
        _task_type_for_next_action(assignment_plan.next_action),
        [*assignment_plan.escalation_reason_codes, "NO_ACTIVE_ASSIGNMENT_TASK"],
    )


def _task_type_for_next_action(next_action: str) -> CampaignAssignmentTaskType:
    mapping: dict[str, CampaignAssignmentTaskType] = {
        "LAUNCH_CAMPAIGN": "ASSIGNMENT",
        "RECORD_APPROVAL_DECISION": "APPROVAL_REMEDIATION",
        "REMEDIATE_APPROVAL_EVIDENCE": "APPROVAL_REMEDIATION",
        "REFRESH_EXPIRY_OR_AS_OF_DATE": "EXPIRY_REVIEW",
        "REVIEW_ACTOR_ENTITLEMENT": "ENTITLEMENT_REVIEW",
        "REVIEW_CAMPAIGN_ATTENTION": "ESCALATION",
    }
    return mapping.get(next_action, "ESCALATION")


def _active_tasks(
    tasks: list[DpmBulkReviewCampaignDefinitionAssignmentTask],
) -> list[DpmBulkReviewCampaignDefinitionAssignmentTask]:
    return sorted(
        [task for task in tasks if task.status not in _CLOSED_TASK_STATUSES],
        key=lambda task: task.opened_at,
    )


def _blocked_tasks(
    tasks: list[DpmBulkReviewCampaignDefinitionAssignmentTask],
) -> list[DpmBulkReviewCampaignDefinitionAssignmentTask]:
    return [
        task
        for task in tasks
        if task.status in _BLOCKED_TASK_STATUSES or task.sla_posture == "BREACHED_OR_BLOCKED"
    ]


def _proposed_task_ref(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    assignment_plan: DpmBulkReviewCampaignAssignmentPlanItem,
) -> str:
    seed = "|".join(
        [
            definition.campaign_id,
            definition.campaign_version,
            assignment_plan.next_action,
            assignment_plan.escalation_tier,
        ]
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8].upper()
    return f"BRC-AUTO-{definition.campaign_version.replace('.', '')}-{digest}"


def _workflow_capability_posture() -> DpmBulkReviewCampaignWorkflowCapabilityPosture:
    return DpmBulkReviewCampaignWorkflowCapabilityPosture.model_validate(
        _workflow_capability_posture_payload()
    )


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
