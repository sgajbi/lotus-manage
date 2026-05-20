from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves import (
    CampaignApprovalDecisionType,
    CampaignAssignmentActionType,
    CampaignAssignmentEscalationTier,
    CampaignAssignmentSlaPosture,
    CampaignAssignmentTaskTransitionType,
    CampaignAssignmentTaskType,
    CampaignMakerCheckerControlAction,
    CampaignMakerCheckerControlOutcome,
    DpmBulkReviewCampaignDefinition,
    DpmWaveSourceRef,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmBulkReviewCampaignDefinitionGovernance,
)


class DpmBulkReviewCampaignGovernanceInput(BaseModel):
    approval_ref: str | None = Field(
        default=None,
        description=(
            "Optional bank approval reference for this bulk-review campaign. When any approval "
            "field is supplied, all approval fields are required."
        ),
        examples=["BRC-APPROVAL-2026-05"],
    )
    approved_by: str | None = Field(
        default=None,
        description="Optional approving actor or committee identifier.",
        examples=["cio_ops_committee"],
    )
    approved_at: str | None = Field(
        default=None,
        description="Optional approval timestamp or business date from the bank control record.",
        examples=["2026-05-14T08:30:00+08:00"],
    )
    expires_on: str | None = Field(
        default=None,
        description=(
            "Optional campaign expiry date. Expired campaigns fail closed for preview/create."
        ),
        examples=["2026-06-30"],
    )
    entitled_actor_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Optional actor allow-list for this campaign. When supplied, actor_id must be listed."
        ),
        examples=[["pm_001", "ops"]],
    )
    access_purpose: str = Field(
        default="DPM_BULK_REVIEW_CAMPAIGN",
        description="Bank access purpose preserved in campaign membership diagnostics.",
        examples=["DPM_BULK_REVIEW_CAMPAIGN"],
    )
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Optional source refs for approval, entitlement, or campaign-control evidence.",
    )


class DpmBulkReviewCampaignDefinitionRequest(BaseModel):
    display_name: str = Field(examples=["Apple and Tesla holdings review"])
    status: Literal["ACTIVE"] = Field(default="ACTIVE")
    as_of_date: str = Field(examples=["2026-05-10"])
    rationale: str = Field(description="Business rationale for the persisted campaign definition.")
    eligible_portfolio_types: list[str] = Field(default_factory=lambda: ["DISCRETIONARY"])
    candidates: list[DpmBulkReviewCampaignDefinitionCandidate] = Field(
        description=(
            "Source-backed candidates captured by the campaign definition. Manage persists this "
            "bounded set but does not discover a global portfolio universe."
        )
    )
    governance: DpmBulkReviewCampaignDefinitionGovernance | None = Field(default=None)
    source_refs: list[DpmWaveSourceRef] = Field(default_factory=list)
    created_by: str = Field(examples=["ops"])
    correlation_id: str = Field(examples=["corr-campaign-definition-001"])


class DpmBulkReviewCampaignDefinitionRetirementRequest(BaseModel):
    retired_by: str = Field(
        description="Actor retiring the campaign definition for future preview/create use.",
        examples=["ops"],
    )
    retirement_reason: str = Field(
        description="Business reason for retiring the persisted campaign definition.",
        examples=["Campaign review completed and no longer available for new waves."],
    )
    correlation_id: str = Field(examples=["corr-campaign-definition-retire-001"])


class DpmBulkReviewCampaignDefinitionSupersessionRequest(BaseModel):
    superseded_by_campaign_version: str = Field(
        description=(
            "Replacement version for the same campaign id. The replacement definition must already "
            "exist and be ACTIVE."
        ),
        examples=["2026.06"],
    )
    superseded_by: str = Field(
        description="Actor superseding the campaign definition for future preview/create use.",
        examples=["ops"],
    )
    supersession_reason: str = Field(
        description="Business reason for replacing the persisted campaign definition.",
        examples=["Updated source-backed candidate set after campaign refresh."],
    )
    correlation_id: str = Field(examples=["corr-campaign-definition-supersede-001"])


class DpmBulkReviewCampaignDefinitionLaunchRequest(BaseModel):
    requested_as_of_date: str = Field(
        description="ISO date used for the durable campaign wave.",
        examples=["2026-05-10"],
    )
    actor_id: str = Field(
        description="Human or service actor launching the persisted campaign definition.",
        examples=["pm_001"],
    )
    correlation_id: str | None = Field(
        default=None,
        description=(
            "Optional correlation id for the durable wave. When omitted, Manage derives the same "
            "deterministic correlation id used by the launch package."
        ),
    )


class DpmBulkReviewCampaignDefinitionApprovalDecisionRequest(BaseModel):
    decision_type: CampaignApprovalDecisionType = Field(
        description="Bounded campaign approval decision.",
        examples=["APPROVED"],
    )
    decision_ref: str = Field(
        min_length=1,
        description="Bank workflow, committee, or ticket reference for this decision.",
        examples=["BRC-APPROVAL-2026-05-001"],
    )
    decided_by: str = Field(
        min_length=1,
        description="Actor recording the campaign approval decision.",
        examples=["cio_ops_committee"],
    )
    decision_reason: str = Field(
        min_length=1,
        description="Human-authored campaign approval decision rationale.",
        examples=["Campaign definition approved for bounded DPM review launch."],
    )
    correlation_id: str = Field(examples=["corr-campaign-approval-decision-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Optional decision evidence refs such as committee minutes or ticket ids.",
    )


class DpmBulkReviewCampaignDefinitionAssignmentActionRequest(BaseModel):
    action_type: CampaignAssignmentActionType = Field(
        description="Bounded campaign assignment or escalation action.",
        examples=["ASSIGNED"],
    )
    action_ref: str = Field(
        min_length=1,
        description="Bank workflow, ticket, or queue reference for this assignment action.",
        examples=["BRC-ASSIGN-2026-05-001"],
    )
    recorded_by: str = Field(
        min_length=1,
        description="Actor recording the campaign assignment action.",
        examples=["ops"],
    )
    action_reason: str = Field(
        min_length=1,
        description="Human-authored assignment or escalation rationale.",
        examples=["Campaign routed to assigned PM with governance attention."],
    )
    assigned_actor_ids: list[str] = Field(
        default_factory=list,
        description="Actors assigned by this action. Required unless action_type is RESOLVED.",
        examples=[["pm_001"]],
    )
    escalation_tier: CampaignAssignmentEscalationTier = Field(
        description="Bounded escalation tier after this action.",
        examples=["PM"],
    )
    sla_posture: CampaignAssignmentSlaPosture = Field(
        description="Bounded operational SLA posture after this action.",
        examples=["ON_TRACK"],
    )
    correlation_id: str = Field(examples=["corr-campaign-assignment-action-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Optional assignment evidence refs such as queue or ticket ids.",
    )


class DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest(BaseModel):
    task_ref: str = Field(
        min_length=1,
        description="Bank workflow, ticket, or queue reference for this assignment task.",
        examples=["BRC-TASK-2026-05-001"],
    )
    task_type: CampaignAssignmentTaskType = Field(
        description="Bounded assignment task type.",
        examples=["ASSIGNMENT"],
    )
    opened_by: str = Field(
        min_length=1,
        description="Actor opening the assignment task.",
        examples=["ops"],
    )
    task_reason: str = Field(
        min_length=1,
        description="Human-authored task rationale.",
        examples=["Campaign requires assigned PM acknowledgement before launch."],
    )
    assigned_actor_ids: list[str] = Field(
        description="Current task assignees.",
        examples=[["pm_001"]],
    )
    escalation_tier: CampaignAssignmentEscalationTier = Field(
        description="Current task escalation tier.",
        examples=["PM"],
    )
    sla_posture: CampaignAssignmentSlaPosture = Field(
        description="Current task SLA posture.",
        examples=["ON_TRACK"],
    )
    due_at: datetime | None = Field(
        default=None,
        description="Optional task due timestamp.",
        examples=["2026-05-11T08:00:00Z"],
    )
    correlation_id: str = Field(examples=["corr-campaign-assignment-task-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Optional task evidence refs such as queue or ticket ids.",
    )


class DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest(BaseModel):
    transition_type: CampaignAssignmentTaskTransitionType = Field(
        description="Bounded task transition.",
        examples=["ACKNOWLEDGED"],
    )
    transition_ref: str = Field(
        min_length=1,
        description="Bank workflow, ticket, or queue reference for this transition.",
        examples=["BRC-TASK-2026-05-001:ack"],
    )
    transitioned_by: str = Field(
        min_length=1,
        description="Actor recording the task transition.",
        examples=["pm_001"],
    )
    transition_reason: str = Field(
        min_length=1,
        description="Human-authored transition rationale.",
        examples=["Assigned PM acknowledged the campaign review task."],
    )
    assigned_actor_ids: list[str] | None = Field(
        default=None,
        description="Optional replacement assignees for reassignment or escalation transitions.",
        examples=[["pm_001", "ops_lead"]],
    )
    escalation_tier: CampaignAssignmentEscalationTier | None = Field(
        default=None,
        description="Optional replacement escalation tier after this transition.",
        examples=["OPS"],
    )
    sla_posture: CampaignAssignmentSlaPosture | None = Field(
        default=None,
        description="Optional replacement SLA posture after this transition.",
        examples=["ATTENTION"],
    )
    due_at: datetime | None = Field(
        default=None,
        description="Optional replacement due timestamp.",
        examples=["2026-05-12T08:00:00Z"],
    )
    correlation_id: str = Field(examples=["corr-campaign-assignment-task-transition-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Optional transition evidence refs such as queue or ticket ids.",
    )


class DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest(BaseModel):
    control_action: CampaignMakerCheckerControlAction = Field(
        description="Bounded campaign maker-checker control action.",
        examples=["REVIEW_COMPLETED"],
    )
    control_ref: str = Field(
        min_length=1,
        description="Bank workflow, control, or ticket reference for this control action.",
        examples=["BRC-MC-2026-05-001"],
    )
    recorded_by: str = Field(
        min_length=1,
        description="Actor recording the campaign maker-checker control action.",
        examples=["ops"],
    )
    submitter_actor_id: str | None = Field(
        default=None,
        description="Maker actor for the control. Required for submissions and completed reviews.",
        examples=["pm_001"],
    )
    reviewer_actor_id: str | None = Field(
        default=None,
        description="Checker actor for the control. Required for assignments and completed reviews.",
        examples=["cio_ops_committee"],
    )
    required_reviewer_role: str | None = Field(
        default=None,
        description="Required checker role or committee role for this control action.",
        examples=["CIO_OPERATIONS_REVIEWER"],
    )
    control_outcome: CampaignMakerCheckerControlOutcome = Field(
        description="Bounded control outcome after this action.",
        examples=["PASSED"],
    )
    control_reason: str = Field(
        min_length=1,
        description="Human-authored campaign maker-checker control rationale.",
        examples=["Independent reviewer approved the campaign definition control evidence."],
    )
    correlation_id: str = Field(examples=["corr-campaign-maker-checker-control-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Optional control evidence refs such as workflow tickets or review minutes.",
    )


class DpmBulkReviewCampaignDefinitionPage(BaseModel):
    items: list[DpmBulkReviewCampaignDefinition]
    limit: int
    offset: int
    count: int
