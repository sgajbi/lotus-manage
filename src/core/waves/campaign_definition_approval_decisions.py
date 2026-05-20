from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionApprovalDecision,
)
from src.core.waves.models import DpmWaveSourceRef

CampaignApprovalDecisionType = Literal["APPROVED", "REJECTED", "REQUIRES_REMEDIATION"]


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
    count: int = Field(description="Number of approval decisions returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


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
    if definition.status != "ACTIVE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_ACTIVE_REQUIRED")
    if not decision_ref.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_REQUIRED")
    if not decided_by.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_ACTOR_REQUIRED")
    if not decision_reason.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REASON_REQUIRED")
    if not correlation_id.strip():
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_CORRELATION_REQUIRED")

    decision = _build_decision(
        definition=definition,
        decision_type=decision_type,
        decision_ref=decision_ref.strip(),
        decided_by=decided_by.strip(),
        decision_reason=decision_reason.strip(),
        correlation_id=correlation_id.strip(),
        source_refs=source_refs or [],
    )
    existing_refs = {existing.decision_ref: existing for existing in definition.approval_decisions}
    existing = existing_refs.get(decision.decision_ref)
    if existing is not None:
        if existing.content_hash == decision.content_hash:
            return definition
        raise ValueError("BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_CONFLICT")

    return definition.model_copy(
        update={
            "approval_decisions": [*definition.approval_decisions, decision],
            "content_hash": "",
        }
    )


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
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
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
