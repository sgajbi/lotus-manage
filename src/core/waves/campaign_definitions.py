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


class DpmBulkReviewCampaignDefinition(BaseModel):
    """Immutable Manage-owned bulk-review campaign definition over source-backed candidates."""

    product_name: Literal["BulkReviewCampaignDefinition"] = "BulkReviewCampaignDefinition"
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    display_name: str = Field(examples=["Apple and Tesla holdings review"])
    status: Literal["ACTIVE", "RETIRED"] = "ACTIVE"
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
    content_hash: str = Field(default="")

    @model_validator(mode="after")
    def validate_definition(self) -> "DpmBulkReviewCampaignDefinition":
        if self.status != "ACTIVE":
            raise ValueError("BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_ACTIVE")
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
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
