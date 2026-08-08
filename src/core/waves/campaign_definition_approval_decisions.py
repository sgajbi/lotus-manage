from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecision,
)
from src.core.waves.models import DpmWaveSourceRef, dpm_wave_source_ref_hash_payload
from src.core.waves.campaign_page_validation import validate_page_count

CampaignApprovalDecisionType = Literal["APPROVED", "REJECTED", "REQUIRES_REMEDIATION"]


@dataclass(frozen=True)
class _ApprovalDecisionInput:
    decision_ref: str
    decided_by: str
    decision_reason: str
    correlation_id: str
    source_refs: list[DpmWaveSourceRef]


class DpmBulkReviewCampaignDefinitionApprovalDecisionPage(BaseModel):
    product_name: Literal["BulkReviewCampaignDefinitionApprovalDecisionPage"] = (
        "BulkReviewCampaignDefinitionApprovalDecisionPage"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(description="Campaign definition identifier.")
    campaign_version: str = Field(description="Campaign definition version.")
    approval_decisions: list[DpmBulkReviewCampaignDefinitionApprovalDecision] = Field(
        description="Bounded page of append-only approval-decision evidence."
    )
    latest_decision_type: CampaignApprovalDecisionType | None = Field(
        description="Most recent approval decision type in the returned definition."
    )
    count: int = Field(ge=0, description="Number of approval decisions returned.")
    limit: int = Field(ge=1, description="Requested page size.")
    offset: int = Field(ge=0, description="Requested page offset.")

    @model_validator(mode="after")
    def validate_page_metadata(self) -> DpmBulkReviewCampaignDefinitionApprovalDecisionPage:
        validate_page_count(count=self.count, item_count=len(self.approval_decisions))
        return self


def record_bulk_review_campaign_definition_approval_decision(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    decision_type: CampaignApprovalDecisionType,
    decision_ref: str,
    decided_by: str,
    decision_reason: str,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef] | None = None,
) -> DpmBulkReviewCampaignDefinition:
    _validate_active_campaign_definition(definition)
    decision_input = _approval_decision_input(
        decision_ref=decision_ref,
        decided_by=decided_by,
        decision_reason=decision_reason,
        correlation_id=correlation_id,
        source_refs=source_refs,
    )

    decision = _build_decision(
        definition=definition,
        decision_type=decision_type,
        decision_ref=decision_input.decision_ref,
        decided_by=decision_input.decided_by,
        decision_reason=decision_input.decision_reason,
        correlation_id=decision_input.correlation_id,
        source_refs=decision_input.source_refs,
    )
    existing = _existing_approval_decision(definition=definition, decision=decision)
    if existing is not None:
        if existing.content_hash == decision.content_hash:
            return definition
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_CONFLICT")

    return _append_approval_decision(definition=definition, decision=decision)


def _validate_active_campaign_definition(definition: DpmBulkReviewCampaignDefinition) -> None:
    if definition.status != "ACTIVE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_ACTIVE_REQUIRED")


def _approval_decision_input(
    *,
    decision_ref: str,
    decided_by: str,
    decision_reason: str,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef] | None,
) -> _ApprovalDecisionInput:
    return _ApprovalDecisionInput(
        decision_ref=_required_approval_decision_text(
            decision_ref,
            "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_REQUIRED",
        ),
        decided_by=_required_approval_decision_text(
            decided_by,
            "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_ACTOR_REQUIRED",
        ),
        decision_reason=_required_approval_decision_text(
            decision_reason,
            "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REASON_REQUIRED",
        ),
        correlation_id=_required_approval_decision_text(
            correlation_id,
            "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_CORRELATION_REQUIRED",
        ),
        source_refs=source_refs or [],
    )


def _required_approval_decision_text(value: str, error_code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(error_code)
    return normalized


def _existing_approval_decision(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    decision: DpmBulkReviewCampaignDefinitionApprovalDecision,
) -> DpmBulkReviewCampaignDefinitionApprovalDecision | None:
    existing_refs = {existing.decision_ref: existing for existing in definition.approval_decisions}
    return existing_refs.get(decision.decision_ref)


def _append_approval_decision(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    decision: DpmBulkReviewCampaignDefinitionApprovalDecision,
) -> DpmBulkReviewCampaignDefinition:
    updated = definition.model_copy(
        update={
            "approval_decisions": [*definition.approval_decisions, decision],
            "content_hash": "",
        }
    )
    return DpmBulkReviewCampaignDefinition.model_validate(updated.model_dump(mode="python"))


def build_bulk_review_campaign_definition_approval_decision_page(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    limit: int = 50,
    offset: int = 0,
) -> DpmBulkReviewCampaignDefinitionApprovalDecisionPage:
    decisions = sorted(
        definition.approval_decisions,
        key=lambda decision: decision.decided_at,
        reverse=True,
    )
    page = decisions[offset : offset + limit]
    latest = decisions[0].decision_type if decisions else None
    return DpmBulkReviewCampaignDefinitionApprovalDecisionPage(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        approval_decisions=page,
        latest_decision_type=latest,
        count=len(page),
        limit=limit,
        offset=offset,
    )


def _build_decision(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    decision_type: CampaignApprovalDecisionType,
    decision_ref: str,
    decided_by: str,
    decision_reason: str,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef],
) -> DpmBulkReviewCampaignDefinitionApprovalDecision:
    decided_at = datetime.now(timezone.utc)
    decision_id_seed = "|".join(
        [
            definition.campaign_id,
            definition.campaign_version,
            decision_ref,
            decision_type,
        ]
    )
    decision_id = (
        "brc_approval_decision_" + hashlib.sha256(decision_id_seed.encode("utf-8")).hexdigest()[:16]
    )
    payload = {
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "decision_id": decision_id,
        "decision_type": decision_type,
        "decision_ref": decision_ref,
        "decided_by": decided_by,
        "decision_reason": decision_reason,
        "correlation_id": correlation_id,
        "source_refs": [dpm_wave_source_ref_hash_payload(ref) for ref in source_refs],
    }
    content_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return DpmBulkReviewCampaignDefinitionApprovalDecision(
        decision_id=decision_id,
        decision_type=decision_type,
        decision_ref=decision_ref,
        decided_at=decided_at,
        decided_by=decided_by,
        decision_reason=decision_reason,
        correlation_id=correlation_id,
        source_refs=source_refs,
        content_hash=content_hash,
    )
