from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definition_readiness import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    build_bulk_review_campaign_definition_preview_readiness,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition
from src.core.waves.campaign_discovery import (
    DpmBulkReviewCampaignDiscoveryItem,
    build_bulk_review_campaign_discovery_item,
)
from src.core.waves.campaign_operating_boundaries import (
    CAMPAIGN_APPROVAL_INBOX_OPERATING_BOUNDARIES,
)


CampaignApprovalInboxStatus = Literal[
    "APPROVAL_COMPLETE",
    "APPROVAL_REQUIRED",
    "APPROVAL_INCOMPLETE",
    "EXPIRY_ATTENTION",
    "ENTITLEMENT_ATTENTION",
    "CLOSED",
]


class DpmBulkReviewCampaignApprovalInboxItem(BaseModel):
    """Read-only approval attention row for one persisted campaign definition."""

    product_name: Literal["BulkReviewCampaignApprovalInboxItem"] = (
        "BulkReviewCampaignApprovalInboxItem"
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
    inbox_status: CampaignApprovalInboxStatus = Field(
        description="Bounded approval, expiry, or entitlement attention posture."
    )
    inbox_reason_codes: list[str] = Field(
        description="Bounded reason codes for approval-attention routing."
    )
    discovery: DpmBulkReviewCampaignDiscoveryItem = Field(
        description="Persisted definition identity, governance, expiry, and candidate posture."
    )
    preview_readiness: DpmBulkReviewCampaignDefinitionPreviewReadiness = Field(
        description="Fail-closed preview/create supportability for the requested date and actor."
    )
    approval_ref: str | None = Field(default=None, examples=["BRC-APPROVAL-2026-05"])
    approved_by: str | None = Field(default=None, examples=["cio_ops_committee"])
    approved_at: str | None = Field(default=None, examples=["2026-05-14T08:30:00+08:00"])
    expires_on: str | None = Field(default=None, examples=["2026-06-30"])
    access_purpose: str | None = Field(default=None, examples=["DPM_BULK_REVIEW_CAMPAIGN"])
    entitled_actor_count: int = Field(
        ge=0,
        description="Count of explicitly entitled actors on the persisted governance evidence.",
    )
    approval_source_ref_count: int = Field(
        ge=0,
        description="Count of governance source refs proving approval or control evidence.",
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: list(CAMPAIGN_APPROVAL_INBOX_OPERATING_BOUNDARIES),
        description="Unsupported downstream claims the approval inbox must not imply.",
    )
    content_hash: str = Field(description="Canonical hash over the approval inbox row.")


class DpmBulkReviewCampaignApprovalInboxPage(BaseModel):
    """Bounded approval attention page over persisted campaign definitions."""

    product_name: Literal["BulkReviewCampaignApprovalInbox"] = "BulkReviewCampaignApprovalInbox"
    product_version: Literal["v1"] = "v1"
    items: list[DpmBulkReviewCampaignApprovalInboxItem]
    limit: int
    offset: int
    count: int
    status_counts: dict[str, int] = Field(
        description="Inbox item counts by approval-attention posture for the returned page."
    )
    content_hash: str = Field(description="Canonical hash over the approval inbox page.")


def build_bulk_review_campaign_approval_inbox_item(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str | None,
    active_on: date | None,
) -> DpmBulkReviewCampaignApprovalInboxItem:
    """Compose campaign governance evidence into one read-only approval attention row."""

    discovery = build_bulk_review_campaign_discovery_item(
        definition=definition,
        active_on=active_on,
    )
    readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
    )
    status, reason_codes = _classify_approval_inbox_posture(
        definition=definition,
        discovery=discovery,
        readiness=readiness,
    )
    governance = definition.governance
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignApprovalInboxItem",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "display_name": definition.display_name,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "inbox_status": status,
        "inbox_reason_codes": reason_codes,
        "discovery": discovery.model_dump(mode="json"),
        "preview_readiness": readiness.model_dump(mode="json"),
        "approval_ref": governance.approval_ref if governance else None,
        "approved_by": governance.approved_by if governance else None,
        "approved_at": governance.approved_at if governance else None,
        "expires_on": governance.expires_on if governance else None,
        "access_purpose": governance.access_purpose if governance else None,
        "entitled_actor_count": len(governance.entitled_actor_ids) if governance else 0,
        "approval_source_ref_count": len(governance.source_refs) if governance else 0,
        "operating_boundaries": list(CAMPAIGN_APPROVAL_INBOX_OPERATING_BOUNDARIES),
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignApprovalInboxItem.model_validate(payload)


def build_bulk_review_campaign_approval_inbox_page(
    *,
    definitions: list[DpmBulkReviewCampaignDefinition],
    requested_as_of_date: str | None,
    actor_id: str | None,
    active_on: date | None,
    include_closed: bool,
    inbox_status: CampaignApprovalInboxStatus | None,
    limit: int,
    offset: int,
) -> DpmBulkReviewCampaignApprovalInboxPage:
    items = [
        build_bulk_review_campaign_approval_inbox_item(
            definition=definition,
            requested_as_of_date=requested_as_of_date or definition.as_of_date,
            actor_id=actor_id,
            active_on=active_on,
        )
        for definition in definitions
    ]
    if not include_closed:
        items = [item for item in items if item.inbox_status != "CLOSED"]
    if inbox_status is not None:
        items = [item for item in items if item.inbox_status == inbox_status]

    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.inbox_status] = status_counts.get(item.inbox_status, 0) + 1

    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignApprovalInbox",
        "product_version": "v1",
        "items": [item.model_dump(mode="json") for item in items],
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "status_counts": status_counts,
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignApprovalInboxPage.model_validate(payload)


def _classify_approval_inbox_posture(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    discovery: DpmBulkReviewCampaignDiscoveryItem,
    readiness: DpmBulkReviewCampaignDefinitionPreviewReadiness,
) -> tuple[CampaignApprovalInboxStatus, list[str]]:
    if definition.status in {"RETIRED", "SUPERSEDED"}:
        return "CLOSED", [f"CAMPAIGN_DEFINITION_{definition.status}"]
    if readiness.actor_entitlement_state in {"ACTOR_REQUIRED", "UNAUTHORIZED"}:
        return "ENTITLEMENT_ATTENTION", [
            reason
            for reason in readiness.reason_codes
            if reason
            in {
                "BULK_REVIEW_CAMPAIGN_ACTOR_REQUIRED_FOR_ENTITLEMENT",
                "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED",
            }
        ]
    if discovery.expiry_state in {"EXPIRED", "INVALID"} or readiness.expiry_state in {
        "EXPIRED",
        "INVALID",
    }:
        return "EXPIRY_ATTENTION", [
            reason
            for reason in readiness.reason_codes
            if reason
            in {
                "BULK_REVIEW_CAMPAIGN_EXPIRED",
                "BULK_REVIEW_CAMPAIGN_EXPIRY_DATE_INVALID",
            }
        ] or [f"CAMPAIGN_DEFINITION_EXPIRY_{discovery.expiry_state}"]
    if discovery.governance_status == "INCOMPLETE":
        return "APPROVAL_INCOMPLETE", ["BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_INCOMPLETE"]
    if discovery.governance_status == "NOT_SUPPLIED":
        return "APPROVAL_REQUIRED", ["BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_NOT_SUPPLIED"]
    return "APPROVAL_COMPLETE", ["BULK_REVIEW_CAMPAIGN_APPROVAL_EVIDENCE_COMPLETE"]


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
