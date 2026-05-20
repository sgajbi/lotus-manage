from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.core.waves.models import DpmWaveSourceRef


class DpmBulkReviewCampaignDefinitionGovernance(BaseModel):
    """Governance evidence attached to an immutable bulk-review campaign definition."""

    approval_ref: str | None = Field(default=None, examples=["BRC-APPROVAL-2026-05"])
    approved_by: str | None = Field(default=None, examples=["cio_ops_committee"])
    approved_at: str | None = Field(default=None, examples=["2026-05-14T08:30:00+08:00"])
    expires_on: str | None = Field(default=None, examples=["2026-06-30"])
    entitled_actor_ids: list[str] = Field(default_factory=list)
    access_purpose: str = Field(default="DPM_BULK_REVIEW_CAMPAIGN")
    source_refs: list[DpmWaveSourceRef] = Field(default_factory=list)


class DpmBulkReviewCampaignDefinitionCandidate(BaseModel):
    """Source-backed candidate portfolio captured by a campaign definition."""

    portfolio_id: str = Field(examples=["PB_SG_GLOBAL_BAL_001"])
    mandate_id: str | None = Field(default=None, examples=["MANDATE_PB_SG_GLOBAL_BAL_001"])
    portfolio_manager_id: str | None = Field(default=None, examples=["PM_SG_DPM_001"])
    portfolio_type: str = Field(examples=["DISCRETIONARY"])
    source_refs: list[DpmWaveSourceRef] = Field(
        description="Source refs proving why this portfolio belongs to the campaign candidate set."
    )

    @model_validator(mode="after")
    def validate_candidate(self) -> "DpmBulkReviewCampaignDefinitionCandidate":
        if not self.portfolio_type.strip():
            raise ValueError("BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED")
        if not self.source_refs:
            raise ValueError("BULK_REVIEW_CAMPAIGN_SOURCE_REFS_REQUIRED")
        return self


class DpmBulkReviewCampaignDefinitionLaunchRecord(BaseModel):
    """Durable launch audit record for a persisted bulk-review campaign definition."""

    wave_id: str = Field(
        description="Durable rebalance wave created from this campaign definition.",
        examples=["dwv_campaign_001"],
    )
    launched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when Manage recorded the launch.",
    )
    launched_by: str = Field(
        description="Actor who launched the campaign definition wave.",
        examples=["pm_001"],
    )
    requested_as_of_date: str = Field(
        description="Requested as-of date used for the launched wave.",
        examples=["2026-05-10"],
    )
    correlation_id: str = Field(
        description="Correlation id carried into the durable wave launch.",
        examples=["corr-campaign-definition-launch-001"],
    )
    idempotency_key: str = Field(
        description="Deterministic launch idempotency key used for durable wave replay.",
        examples=["campaign-launch:campaign-holdings-apple-tesla-20260510:2026.05:..."],
    )


class DpmBulkReviewCampaignDefinitionApprovalDecision(BaseModel):
    """Append-only approval decision evidence for a bulk-review campaign definition."""

    decision_id: str = Field(
        description="Stable content-addressed approval-decision identity.",
        examples=["brc_approval_decision_9f4e1a2b3c4d5e6f"],
    )
    decision_type: Literal["APPROVED", "REJECTED", "REQUIRES_REMEDIATION"] = Field(
        description="Bounded campaign approval decision."
    )
    decision_ref: str = Field(
        description="Bank workflow, committee, or ticket reference for the decision.",
        examples=["BRC-APPROVAL-2026-05-001"],
    )
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when Manage recorded the approval decision.",
    )
    decided_by: str = Field(
        description="Actor who recorded the approval decision.",
        examples=["cio_ops_committee"],
    )
    decision_reason: str = Field(description="Human-authored approval decision rationale.")
    correlation_id: str = Field(examples=["corr-campaign-approval-decision-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs for committee minutes, ticket evidence, or control records.",
    )
    forbidden_actions: list[str] = Field(
        default_factory=lambda: [
            "maker_checker_workflow",
            "trade_approval",
            "order_generation",
            "order_routing",
            "oms_execution",
            "client_contact",
        ],
        description="Actions outside this approval-decision evidence contract.",
    )
    content_hash: str = Field(description="Deterministic hash of the approval decision record.")


class DpmBulkReviewCampaignDefinitionAssignmentAction(BaseModel):
    """Append-only assignment or escalation action for a bulk-review campaign definition."""

    action_id: str = Field(
        description="Stable content-addressed assignment-action identity.",
        examples=["brc_assignment_action_9f4e1a2b3c4d5e6f"],
    )
    action_type: Literal[
        "ASSIGNED",
        "REASSIGNED",
        "ESCALATED",
        "DEESCALATED",
        "RESOLVED",
    ] = Field(description="Bounded campaign assignment or escalation action.")
    action_ref: str = Field(
        description="Bank workflow, ticket, or queue reference for the assignment action.",
        examples=["BRC-ASSIGN-2026-05-001"],
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when Manage recorded the assignment action.",
    )
    recorded_by: str = Field(
        description="Actor who recorded the assignment action.",
        examples=["ops"],
    )
    action_reason: str = Field(description="Human-authored assignment or escalation rationale.")
    assigned_actor_ids: list[str] = Field(
        default_factory=list,
        description="Actors assigned or routed by this action. Empty only for resolved actions.",
    )
    escalation_tier: Literal["NONE", "PM", "OPS", "GOVERNANCE"] = Field(
        description="Bounded escalation tier after this action."
    )
    sla_posture: Literal["ON_TRACK", "ATTENTION", "BREACHED_OR_BLOCKED"] = Field(
        description="Bounded operational SLA posture after this action."
    )
    correlation_id: str = Field(examples=["corr-campaign-assignment-action-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs for ticket, queue, committee, or control evidence.",
    )
    forbidden_actions: list[str] = Field(
        default_factory=lambda: [
            "maker_checker_workflow",
            "approval_state_mutation",
            "trade_approval",
            "order_generation",
            "order_routing",
            "oms_execution",
            "client_contact",
        ],
        description="Actions outside this assignment-action evidence contract.",
    )
    content_hash: str = Field(description="Deterministic hash of the assignment-action record.")


class DpmBulkReviewCampaignDefinitionMakerCheckerControl(BaseModel):
    """Append-only maker-checker control evidence for a bulk-review campaign definition."""

    control_id: str = Field(
        description="Stable content-addressed maker-checker control identity.",
        examples=["brc_maker_checker_control_9f4e1a2b3c4d5e6f"],
    )
    control_action: Literal[
        "SUBMITTED_FOR_REVIEW",
        "REVIEWER_ASSIGNED",
        "REVIEW_COMPLETED",
        "CONTROL_EXCEPTION_RAISED",
        "CONTROL_EXCEPTION_RESOLVED",
    ] = Field(description="Bounded maker-checker control action.")
    control_ref: str = Field(
        description="Bank workflow, control, or ticket reference for the maker-checker action.",
        examples=["BRC-MC-2026-05-001"],
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when Manage recorded the maker-checker control action.",
    )
    recorded_by: str = Field(
        description="Actor who recorded the maker-checker control action.",
        examples=["ops"],
    )
    submitter_actor_id: str | None = Field(
        default=None,
        description="Maker actor for the campaign approval control, when applicable.",
        examples=["pm_001"],
    )
    reviewer_actor_id: str | None = Field(
        default=None,
        description="Checker actor for the campaign approval control, when applicable.",
        examples=["cio_ops_committee"],
    )
    required_reviewer_role: str | None = Field(
        default=None,
        description="Required checker role or committee role for this control action.",
        examples=["CIO_OPERATIONS_REVIEWER"],
    )
    control_outcome: Literal[
        "PENDING",
        "PASSED",
        "FAILED",
        "EXCEPTION_OPEN",
        "EXCEPTION_RESOLVED",
    ] = Field(description="Bounded control outcome after this action.")
    control_reason: str = Field(description="Human-authored maker-checker control rationale.")
    correlation_id: str = Field(examples=["corr-campaign-maker-checker-control-001"])
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Source refs for workflow tickets, review minutes, or control evidence.",
    )
    forbidden_actions: list[str] = Field(
        default_factory=lambda: [
            "trade_approval",
            "order_generation",
            "order_routing",
            "oms_execution",
            "client_contact",
            "external_workflow_orchestration",
        ],
        description="Actions outside this maker-checker control evidence contract.",
    )
    content_hash: str = Field(description="Deterministic hash of the maker-checker record.")


class DpmBulkReviewCampaignDefinition(BaseModel):
    """Manage-owned bulk-review campaign definition over source-backed candidates."""

    product_name: Literal["BulkReviewCampaignDefinition"] = "BulkReviewCampaignDefinition"
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    display_name: str = Field(examples=["Apple and Tesla holdings review"])
    status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"] = "ACTIVE"
    as_of_date: str = Field(examples=["2026-05-10"])
    rationale: str = Field(description="Business rationale for the persisted campaign definition.")
    eligible_portfolio_types: list[str] = Field(default_factory=lambda: ["DISCRETIONARY"])
    candidates: list[DpmBulkReviewCampaignDefinitionCandidate] = Field(
        description="Source-backed candidate portfolios; Manage does not discover the global book."
    )
    governance: DpmBulkReviewCampaignDefinitionGovernance | None = None
    source_refs: list[DpmWaveSourceRef] = Field(
        default_factory=list,
        description="Definition-level source refs for campaign planning, source files, or controls.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(examples=["ops"])
    correlation_id: str = Field(examples=["corr-campaign-definition-001"])
    retired_at: datetime | None = Field(default=None)
    retired_by: str | None = Field(default=None, examples=["ops"])
    retirement_reason: str | None = Field(default=None)
    retirement_correlation_id: str | None = Field(default=None)
    superseded_at: datetime | None = Field(
        default=None,
        description="Timestamp when this definition was replaced by a newer active version.",
    )
    superseded_by: str | None = Field(
        default=None,
        description="Actor who superseded this definition.",
        examples=["ops"],
    )
    supersession_reason: str | None = Field(
        default=None,
        description="Business reason for replacing this definition.",
    )
    supersession_correlation_id: str | None = Field(
        default=None,
        description="Correlation id for the supersession lifecycle action.",
    )
    superseded_by_campaign_id: str | None = Field(
        default=None,
        description="Replacement campaign id. For this lifecycle it must match campaign_id.",
    )
    superseded_by_campaign_version: str | None = Field(
        default=None,
        description="Replacement active campaign version.",
    )
    superseded_by_content_hash: str | None = Field(
        default=None,
        description="Content hash of the replacement active campaign definition.",
    )
    launch_history: list[DpmBulkReviewCampaignDefinitionLaunchRecord] = Field(
        default_factory=list,
        description=(
            "Append-only durable launch audit records. These records prove Manage-created waves "
            "from this definition without implying maker-checker, trade approval, or OMS execution."
        ),
    )
    approval_decisions: list[DpmBulkReviewCampaignDefinitionApprovalDecision] = Field(
        default_factory=list,
        description=(
            "Append-only campaign approval-decision evidence. These records mutate campaign "
            "approval posture only and do not approve trades, generate orders, route orders, "
            "or claim OMS execution."
        ),
    )
    assignment_actions: list[DpmBulkReviewCampaignDefinitionAssignmentAction] = Field(
        default_factory=list,
        description=(
            "Append-only campaign assignment and escalation actions. These records mutate "
            "assignment posture only and do not create maker-checker workflow, approval state "
            "changes, trade approval, order routing, client contact, or OMS execution."
        ),
    )
    maker_checker_controls: list[DpmBulkReviewCampaignDefinitionMakerCheckerControl] = Field(
        default_factory=list,
        description=(
            "Append-only maker-checker control evidence for campaign approval operations. These "
            "records enforce Manage-side actor-separation evidence without approving trades, "
            "generating orders, routing orders, contacting clients, orchestrating an external "
            "workflow engine, or claiming OMS execution."
        ),
    )
    content_hash: str = Field(default="")

    @model_validator(mode="after")
    def validate_definition(self) -> "DpmBulkReviewCampaignDefinition":
        if self.status == "ACTIVE":
            lifecycle_fields = [
                self.retired_at,
                self.retired_by,
                self.retirement_reason,
                self.retirement_correlation_id,
                self.superseded_at,
                self.superseded_by,
                self.supersession_reason,
                self.supersession_correlation_id,
                self.superseded_by_campaign_id,
                self.superseded_by_campaign_version,
                self.superseded_by_content_hash,
            ]
            if any(value is not None for value in lifecycle_fields):
                raise ValueError("BULK_REVIEW_CAMPAIGN_ACTIVE_LIFECYCLE_FIELDS_FORBIDDEN")
        elif self.status == "RETIRED":
            if self.retired_at is None:
                raise ValueError("BULK_REVIEW_CAMPAIGN_RETIREMENT_TIMESTAMP_REQUIRED")
            if not (self.retired_by or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_RETIREMENT_ACTOR_REQUIRED")
            if not (self.retirement_reason or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_RETIREMENT_REASON_REQUIRED")
            if not (self.retirement_correlation_id or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_RETIREMENT_CORRELATION_REQUIRED")
            supersession_fields = [
                self.superseded_at,
                self.superseded_by,
                self.supersession_reason,
                self.supersession_correlation_id,
                self.superseded_by_campaign_id,
                self.superseded_by_campaign_version,
                self.superseded_by_content_hash,
            ]
            if any(value is not None for value in supersession_fields):
                raise ValueError("BULK_REVIEW_CAMPAIGN_RETIRED_SUPERSESSION_FIELDS_FORBIDDEN")
        else:
            if self.superseded_at is None:
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSESSION_TIMESTAMP_REQUIRED")
            if not (self.superseded_by or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSESSION_ACTOR_REQUIRED")
            if not (self.supersession_reason or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSESSION_REASON_REQUIRED")
            if not (self.supersession_correlation_id or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSESSION_CORRELATION_REQUIRED")
            if not (self.superseded_by_campaign_id or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSESSION_CAMPAIGN_ID_REQUIRED")
            if not (self.superseded_by_campaign_version or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSESSION_CAMPAIGN_VERSION_REQUIRED")
            if not (self.superseded_by_content_hash or "").strip():
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSESSION_CONTENT_HASH_REQUIRED")
            retirement_fields = [
                self.retired_at,
                self.retired_by,
                self.retirement_reason,
                self.retirement_correlation_id,
            ]
            if any(value is not None for value in retirement_fields):
                raise ValueError("BULK_REVIEW_CAMPAIGN_SUPERSEDED_RETIREMENT_FIELDS_FORBIDDEN")
        if not [value for value in self.eligible_portfolio_types if value.strip()]:
            raise ValueError("BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED")
        if not self.candidates:
            raise ValueError("BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED")
        expected_hash = bulk_review_campaign_definition_hash(self, include_hash=False)
        if self.content_hash and self.content_hash != expected_hash:
            raise ValueError("BULK_REVIEW_CAMPAIGN_DEFINITION_HASH_MISMATCH")
        self.content_hash = expected_hash
        return self


def bulk_review_campaign_definition_hash(
    definition: DpmBulkReviewCampaignDefinition,
    *,
    include_hash: bool = False,
) -> str:
    payload = definition.model_dump(mode="json")
    if not include_hash:
        payload["content_hash"] = ""
    payload["created_at"] = ""
    if not payload.get("approval_decisions"):
        payload.pop("approval_decisions", None)
    if not payload.get("assignment_actions"):
        payload.pop("assignment_actions", None)
    if not payload.get("maker_checker_controls"):
        payload.pop("maker_checker_controls", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
