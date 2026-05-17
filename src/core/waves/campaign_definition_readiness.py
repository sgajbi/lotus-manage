from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definition_events import (
    build_bulk_review_campaign_definition_lifecycle_events,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


CampaignDefinitionReadinessState = Literal["READY", "BLOCKED"]
CampaignDefinitionGovernanceState = Literal["APPROVED", "INCOMPLETE", "NOT_SUPPLIED"]
CampaignDefinitionExpiryState = Literal["ACTIVE", "EXPIRED", "INVALID", "NOT_SUPPLIED"]
CampaignDefinitionActorEntitlementState = Literal[
    "AUTHORIZED", "UNAUTHORIZED", "ACTOR_REQUIRED", "NOT_SUPPLIED"
]


class DpmBulkReviewCampaignDefinitionPreviewReadiness(BaseModel):
    """Fail-closed preview/create readiness for one persisted campaign definition."""

    product_name: Literal["BulkReviewCampaignDefinitionPreviewReadiness"] = (
        "BulkReviewCampaignDefinitionPreviewReadiness"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    campaign_status: Literal["ACTIVE", "RETIRED", "SUPERSEDED"]
    definition_as_of_date: str = Field(examples=["2026-05-10"])
    requested_as_of_date: str = Field(examples=["2026-05-10"])
    actor_id: str | None = Field(
        default=None,
        description="Actor being checked against optional campaign entitlement evidence.",
    )
    preview_create_allowed: bool = Field(
        description="Whether this definition can be used for new BULK_REVIEW_CAMPAIGN preview/create."
    )
    supportability_state: CampaignDefinitionReadinessState = Field(
        description="READY only when all definition, candidate, governance, and lifecycle checks pass."
    )
    reason_codes: list[str] = Field(
        description="Fail-closed readiness reason codes; empty means preview/create is allowed."
    )
    candidate_count: int = Field(ge=0, description="Persisted source-backed candidate count.")
    eligible_candidate_count: int = Field(
        ge=0,
        description="Candidates matching the definition's eligible DPM portfolio types.",
    )
    excluded_candidate_count: int = Field(
        ge=0,
        description="Candidates excluded by source-owned portfolio type.",
    )
    eligible_portfolio_types: list[str] = Field(
        description="Upper-cased eligible portfolio types used for readiness evaluation."
    )
    governance_status: CampaignDefinitionGovernanceState = Field(
        description="Approval-evidence completeness posture."
    )
    expiry_state: CampaignDefinitionExpiryState = Field(
        description="Expiry posture evaluated against requested_as_of_date."
    )
    actor_entitlement_state: CampaignDefinitionActorEntitlementState = Field(
        description="Actor entitlement posture when entitlement evidence is supplied."
    )
    lifecycle_event_count: int = Field(
        ge=0,
        description="Projected lifecycle event count for create/retire/supersede audit posture.",
    )
    source_ref_count: int = Field(
        ge=0,
        description="Definition, governance, and candidate source-ref count preserved for audit.",
    )
    content_hash: str = Field(description="Canonical readiness hash.")


def build_bulk_review_campaign_definition_preview_readiness(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str | None = None,
) -> DpmBulkReviewCampaignDefinitionPreviewReadiness:
    reason_codes: list[str] = []
    requested_date = _parse_date(
        value=requested_as_of_date,
        reason_codes=reason_codes,
        invalid_code="BULK_REVIEW_CAMPAIGN_DEFINITION_REQUESTED_AS_OF_DATE_INVALID",
    )
    if definition.status == "RETIRED":
        reason_codes.append("BULK_REVIEW_CAMPAIGN_DEFINITION_RETIRED")
    if definition.status == "SUPERSEDED":
        reason_codes.append("BULK_REVIEW_CAMPAIGN_DEFINITION_SUPERSEDED")
    if definition.as_of_date != requested_as_of_date:
        reason_codes.append("BULK_REVIEW_CAMPAIGN_DEFINITION_AS_OF_DATE_MISMATCH")

    eligible_types = sorted(
        {portfolio_type.strip().upper() for portfolio_type in definition.eligible_portfolio_types}
    )
    if not eligible_types:
        reason_codes.append("BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED")
    eligible_type_set = set(eligible_types)
    eligible_candidate_count = 0
    source_ref_count = len(definition.source_refs)
    for candidate in definition.candidates:
        source_ref_count += len(candidate.source_refs)
        if candidate.portfolio_type.strip().upper() in eligible_type_set:
            eligible_candidate_count += 1
    if not definition.candidates:
        reason_codes.append("BULK_REVIEW_CAMPAIGN_CANDIDATE_PORTFOLIOS_REQUIRED")
    if definition.candidates and eligible_candidate_count == 0:
        reason_codes.append("BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY")

    governance_status, expiry_state, actor_entitlement_state, governance_source_ref_count = (
        _governance_readiness(
            definition=definition,
            requested_date=requested_date,
            actor_id=actor_id,
            reason_codes=reason_codes,
        )
    )
    source_ref_count += governance_source_ref_count
    lifecycle_event_count = build_bulk_review_campaign_definition_lifecycle_events(
        definition=definition
    ).count
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignDefinitionPreviewReadiness",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "campaign_status": definition.status,
        "definition_as_of_date": definition.as_of_date,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "preview_create_allowed": not reason_codes,
        "supportability_state": "READY" if not reason_codes else "BLOCKED",
        "reason_codes": sorted(set(reason_codes)),
        "candidate_count": len(definition.candidates),
        "eligible_candidate_count": eligible_candidate_count,
        "excluded_candidate_count": len(definition.candidates) - eligible_candidate_count,
        "eligible_portfolio_types": eligible_types,
        "governance_status": governance_status,
        "expiry_state": expiry_state,
        "actor_entitlement_state": actor_entitlement_state,
        "lifecycle_event_count": lifecycle_event_count,
        "source_ref_count": source_ref_count,
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignDefinitionPreviewReadiness.model_validate(payload)


def _governance_readiness(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_date: date | None,
    actor_id: str | None,
    reason_codes: list[str],
) -> tuple[
    CampaignDefinitionGovernanceState,
    CampaignDefinitionExpiryState,
    CampaignDefinitionActorEntitlementState,
    int,
]:
    governance = definition.governance
    if governance is None:
        return "NOT_SUPPLIED", "NOT_SUPPLIED", "NOT_SUPPLIED", 0

    source_ref_count = len(governance.source_refs)
    approval_fields = [governance.approval_ref, governance.approved_by, governance.approved_at]
    supplied_approval_fields = [value for value in approval_fields if value]
    governance_status: CampaignDefinitionGovernanceState = "NOT_SUPPLIED"
    if supplied_approval_fields:
        if len(supplied_approval_fields) == len(approval_fields):
            governance_status = "APPROVED"
        else:
            governance_status = "INCOMPLETE"
            reason_codes.append("BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_INCOMPLETE")

    expiry_state: CampaignDefinitionExpiryState = "NOT_SUPPLIED"
    if governance.expires_on:
        expires_on = _parse_date(
            value=governance.expires_on,
            reason_codes=reason_codes,
            invalid_code="BULK_REVIEW_CAMPAIGN_EXPIRY_DATE_INVALID",
        )
        if expires_on is None:
            expiry_state = "INVALID"
        elif requested_date is not None and expires_on < requested_date:
            expiry_state = "EXPIRED"
            reason_codes.append("BULK_REVIEW_CAMPAIGN_EXPIRED")
        else:
            expiry_state = "ACTIVE"

    entitled_actor_ids = {actor.strip() for actor in governance.entitled_actor_ids if actor.strip()}
    actor_entitlement_state: CampaignDefinitionActorEntitlementState = "NOT_SUPPLIED"
    if entitled_actor_ids:
        if not (actor_id or "").strip():
            actor_entitlement_state = "ACTOR_REQUIRED"
            reason_codes.append("BULK_REVIEW_CAMPAIGN_ACTOR_REQUIRED_FOR_ENTITLEMENT")
        elif actor_id in entitled_actor_ids:
            actor_entitlement_state = "AUTHORIZED"
        else:
            actor_entitlement_state = "UNAUTHORIZED"
            reason_codes.append("BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED")

    return governance_status, expiry_state, actor_entitlement_state, source_ref_count


def _parse_date(
    *,
    value: str,
    reason_codes: list[str],
    invalid_code: str,
) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        reason_codes.append(invalid_code)
        return None


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
