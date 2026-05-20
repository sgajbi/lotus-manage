from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionMakerCheckerControl,
)
from src.core.waves.models import DpmWaveSourceRef

CampaignMakerCheckerControlAction = Literal[
    "SUBMITTED_FOR_REVIEW",
    "REVIEWER_ASSIGNED",
    "REVIEW_COMPLETED",
    "CONTROL_EXCEPTION_RAISED",
    "CONTROL_EXCEPTION_RESOLVED",
]
CampaignMakerCheckerControlOutcome = Literal[
    "PENDING",
    "PASSED",
    "FAILED",
    "EXCEPTION_OPEN",
    "EXCEPTION_RESOLVED",
]


class DpmBulkReviewCampaignDefinitionMakerCheckerControlPage(BaseModel):
    product_name: Literal["BulkReviewCampaignDefinitionMakerCheckerControlPage"] = (
        "BulkReviewCampaignDefinitionMakerCheckerControlPage"
    )
    product_version: Literal["v1"] = "v1"
    campaign_id: str = Field(description="Campaign definition identifier.")
    campaign_version: str = Field(description="Campaign definition version.")
    maker_checker_controls: list[DpmBulkReviewCampaignDefinitionMakerCheckerControl] = Field(
        description="Bounded page of append-only maker-checker control evidence."
    )
    latest_control_action: CampaignMakerCheckerControlAction | None = Field(
        description="Most recent maker-checker control action in the returned definition."
    )
    current_control_outcome: CampaignMakerCheckerControlOutcome | None = Field(
        description="Most recent maker-checker control outcome in the returned definition."
    )
    current_reviewer_actor_id: str | None = Field(
        description="Most recent checker actor for the campaign control, when recorded."
    )
    count: int = Field(description="Number of maker-checker controls returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


def record_bulk_review_campaign_definition_maker_checker_control(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    control_action: CampaignMakerCheckerControlAction,
    control_ref: str,
    recorded_by: str,
    control_reason: str,
    correlation_id: str,
    control_outcome: CampaignMakerCheckerControlOutcome,
    submitter_actor_id: str | None = None,
    reviewer_actor_id: str | None = None,
    required_reviewer_role: str | None = None,
    source_refs: list[DpmWaveSourceRef] | None = None,
) -> DpmBulkReviewCampaignDefinition:
    if definition.status != "ACTIVE":
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_ACTIVE_REQUIRED")
    normalized_ref = control_ref.strip()
    normalized_recorded_by = recorded_by.strip()
    normalized_reason = control_reason.strip()
    normalized_correlation = correlation_id.strip()
    normalized_submitter = _normalize_optional_actor(submitter_actor_id)
    normalized_reviewer = _normalize_optional_actor(reviewer_actor_id)
    normalized_role = _normalize_optional_actor(required_reviewer_role)

    if not normalized_ref:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_REQUIRED")
    if not normalized_recorded_by:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_ACTOR_REQUIRED")
    if not normalized_reason:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REASON_REQUIRED")
    if not normalized_correlation:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_CORRELATION_REQUIRED")
    _validate_control_action(
        control_action=control_action,
        control_outcome=control_outcome,
        submitter_actor_id=normalized_submitter,
        reviewer_actor_id=normalized_reviewer,
        required_reviewer_role=normalized_role,
    )

    control = _build_control(
        definition=definition,
        control_action=control_action,
        control_ref=normalized_ref,
        recorded_by=normalized_recorded_by,
        submitter_actor_id=normalized_submitter,
        reviewer_actor_id=normalized_reviewer,
        required_reviewer_role=normalized_role,
        control_outcome=control_outcome,
        control_reason=normalized_reason,
        correlation_id=normalized_correlation,
        source_refs=source_refs or [],
    )
    existing_refs = {
        existing.control_ref: existing for existing in definition.maker_checker_controls
    }
    existing = existing_refs.get(control.control_ref)
    if existing is not None:
        if existing.content_hash == control.content_hash:
            return definition
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_CONFLICT")

    updated = definition.model_copy(
        update={
            "maker_checker_controls": [*definition.maker_checker_controls, control],
            "content_hash": "",
        }
    )
    return DpmBulkReviewCampaignDefinition.model_validate(updated.model_dump(mode="python"))


def build_bulk_review_campaign_definition_maker_checker_control_page(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    limit: int = 50,
    offset: int = 0,
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
    controls = sorted(
        definition.maker_checker_controls,
        key=lambda control: control.recorded_at,
        reverse=True,
    )
    page = controls[offset : offset + limit]
    latest = controls[0] if controls else None
    return DpmBulkReviewCampaignDefinitionMakerCheckerControlPage(
        campaign_id=definition.campaign_id,
        campaign_version=definition.campaign_version,
        maker_checker_controls=page,
        latest_control_action=latest.control_action if latest else None,
        current_control_outcome=latest.control_outcome if latest else None,
        current_reviewer_actor_id=latest.reviewer_actor_id if latest else None,
        count=len(page),
        limit=limit,
        offset=offset,
    )


def _validate_control_action(
    *,
    control_action: CampaignMakerCheckerControlAction,
    control_outcome: CampaignMakerCheckerControlOutcome,
    submitter_actor_id: str | None,
    reviewer_actor_id: str | None,
    required_reviewer_role: str | None,
) -> None:
    if control_action == "SUBMITTED_FOR_REVIEW":
        if not submitter_actor_id:
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMITTER_REQUIRED")
        if control_outcome != "PENDING":
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMISSION_OUTCOME_INVALID")
    elif control_action == "REVIEWER_ASSIGNED":
        if not reviewer_actor_id or not required_reviewer_role:
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEWER_REQUIRED")
        if control_outcome != "PENDING":
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ASSIGNMENT_OUTCOME_INVALID")
    elif control_action == "REVIEW_COMPLETED":
        if not submitter_actor_id or not reviewer_actor_id:
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTORS_REQUIRED")
        if submitter_actor_id == reviewer_actor_id:
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTOR_SEPARATION_REQUIRED")
        if control_outcome not in {"PASSED", "FAILED"}:
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEW_OUTCOME_INVALID")
    elif control_action == "CONTROL_EXCEPTION_RAISED":
        if control_outcome != "EXCEPTION_OPEN":
            raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_OUTCOME_INVALID")
    elif control_outcome != "EXCEPTION_RESOLVED":
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_RESOLUTION_INVALID")


def _build_control(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    control_action: CampaignMakerCheckerControlAction,
    control_ref: str,
    recorded_by: str,
    submitter_actor_id: str | None,
    reviewer_actor_id: str | None,
    required_reviewer_role: str | None,
    control_outcome: CampaignMakerCheckerControlOutcome,
    control_reason: str,
    correlation_id: str,
    source_refs: list[DpmWaveSourceRef],
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControl:
    recorded_at = datetime.now(timezone.utc)
    control_id_seed = "|".join(
        [
            definition.campaign_id,
            definition.campaign_version,
            control_ref,
            control_action,
        ]
    )
    control_id = (
        "brc_maker_checker_control_"
        + hashlib.sha256(control_id_seed.encode("utf-8")).hexdigest()[:16]
    )
    payload = {
        "campaign_id": definition.campaign_id,
        "campaign_version": definition.campaign_version,
        "control_id": control_id,
        "control_action": control_action,
        "control_ref": control_ref,
        "recorded_by": recorded_by,
        "submitter_actor_id": submitter_actor_id,
        "reviewer_actor_id": reviewer_actor_id,
        "required_reviewer_role": required_reviewer_role,
        "control_outcome": control_outcome,
        "control_reason": control_reason,
        "correlation_id": correlation_id,
        "source_refs": [ref.model_dump(mode="json") for ref in source_refs],
    }
    content_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return DpmBulkReviewCampaignDefinitionMakerCheckerControl(
        control_id=control_id,
        control_action=control_action,
        control_ref=control_ref,
        recorded_at=recorded_at,
        recorded_by=recorded_by,
        submitter_actor_id=submitter_actor_id,
        reviewer_actor_id=reviewer_actor_id,
        required_reviewer_role=required_reviewer_role,
        control_outcome=control_outcome,
        control_reason=control_reason,
        correlation_id=correlation_id,
        source_refs=source_refs,
        content_hash=content_hash,
    )


def _normalize_optional_actor(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
