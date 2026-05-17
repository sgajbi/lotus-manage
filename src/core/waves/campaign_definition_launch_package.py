from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definition_readiness import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
    build_bulk_review_campaign_definition_preview_readiness,
)
from src.core.waves.campaign_definitions import DpmBulkReviewCampaignDefinition


CampaignDefinitionLaunchState = Literal["READY", "BLOCKED"]


class DpmBulkReviewCampaignDefinitionWaveRequestDraft(BaseModel):
    """Bounded wave request draft for one persisted campaign definition."""

    trigger_type: Literal["BULK_REVIEW_CAMPAIGN"] = "BULK_REVIEW_CAMPAIGN"
    trigger_id: str = Field(description="Campaign id used as the wave trigger id.")
    rationale: str = Field(description="Definition rationale copied into the wave request.")
    as_of_date: str = Field(description="Requested wave as-of date.")
    actor_id: str = Field(description="Actor to use for preview/create.")
    campaign_definition_id: str = Field(description="Persisted campaign definition id.")
    campaign_definition_version: str = Field(description="Persisted campaign definition version.")
    portfolio_types: list[str] = Field(
        description="Eligible portfolio types copied from the definition for operator visibility."
    )
    portfolios: list[object] = Field(
        default_factory=list,
        description="Always empty; persisted campaign definitions supply the candidate set.",
    )


class DpmBulkReviewCampaignDefinitionLaunchPackage(BaseModel):
    """Operator package for launching a campaign definition into preview/create."""

    product_name: Literal["BulkReviewCampaignDefinitionLaunchPackage"] = (
        "BulkReviewCampaignDefinitionLaunchPackage"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(examples=["campaign-holdings-apple-tesla-20260510"])
    campaign_version: str = Field(examples=["2026.05"])
    requested_as_of_date: str = Field(examples=["2026-05-10"])
    actor_id: str = Field(examples=["pm_001"])
    correlation_id: str = Field(examples=["corr-campaign-launch-001"])
    launch_state: CampaignDefinitionLaunchState = Field(
        description="READY only when preview/create readiness allows launch."
    )
    reason_codes: list[str] = Field(description="Readiness reason codes blocking launch.")
    readiness: DpmBulkReviewCampaignDefinitionPreviewReadiness
    preview_request: DpmBulkReviewCampaignDefinitionWaveRequestDraft
    create_request: DpmBulkReviewCampaignDefinitionWaveRequestDraft
    create_headers: dict[str, str] = Field(
        description="Headers required for durable create, including idempotency and correlation ids."
    )
    operating_boundaries: list[str] = Field(
        description="Explicit non-claim boundaries that downstream consumers must preserve."
    )
    content_hash: str = Field(description="Canonical launch-package hash.")


def build_bulk_review_campaign_definition_launch_package(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str,
    correlation_id: str | None = None,
) -> DpmBulkReviewCampaignDefinitionLaunchPackage:
    actor_id = actor_id.strip()
    correlation_id = (
        correlation_id.strip()
        if correlation_id and correlation_id.strip()
        else f"corr-campaign-launch-{definition.campaign_id}-{definition.campaign_version}"
    )
    readiness = build_bulk_review_campaign_definition_preview_readiness(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
    )
    request_draft = DpmBulkReviewCampaignDefinitionWaveRequestDraft(
        trigger_id=definition.campaign_id,
        rationale=definition.rationale,
        as_of_date=requested_as_of_date,
        actor_id=actor_id,
        campaign_definition_id=definition.campaign_id,
        campaign_definition_version=definition.campaign_version,
        portfolio_types=definition.eligible_portfolio_types,
    )
    idempotency_key = _idempotency_key(
        definition=definition,
        requested_as_of_date=requested_as_of_date,
        actor_id=actor_id,
    )
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignDefinitionLaunchPackage",
        "product_version": "v1",
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "correlation_id": correlation_id,
        "launch_state": "READY" if readiness.preview_create_allowed else "BLOCKED",
        "reason_codes": readiness.reason_codes,
        "readiness": readiness.model_dump(mode="json"),
        "preview_request": request_draft.model_dump(mode="json"),
        "create_request": request_draft.model_dump(mode="json"),
        "create_headers": {
            "Idempotency-Key": idempotency_key,
            "X-Correlation-Id": correlation_id,
        },
        "operating_boundaries": [
            "NO_GLOBAL_PORTFOLIO_UNIVERSE_DISCOVERY",
            "NO_MEMBERSHIP_RECALCULATION",
            "NO_MAKER_CHECKER_WORKFLOW",
            "NO_TRADE_APPROVAL",
            "NO_OMS_EXECUTION_CLAIM",
        ],
        "content_hash": "",
    }
    payload["content_hash"] = _hash_payload(payload)
    return DpmBulkReviewCampaignDefinitionLaunchPackage.model_validate(payload)


def _idempotency_key(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    requested_as_of_date: str,
    actor_id: str,
) -> str:
    payload: dict[str, object] = {
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "requested_as_of_date": requested_as_of_date,
        "actor_id": actor_id,
        "definition_hash": _launch_basis_hash(definition),
    }
    digest = _hash_payload(payload).removeprefix("sha256:")[:24]
    return f"campaign-launch:{definition.campaign_id}:{definition.campaign_version}:{digest}"


def _launch_basis_hash(definition: DpmBulkReviewCampaignDefinition) -> str:
    payload = definition.model_dump(mode="json")
    payload["content_hash"] = ""
    payload["created_at"] = ""
    payload["launch_history"] = []
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_payload(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
