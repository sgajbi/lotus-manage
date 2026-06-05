from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Callable, Literal, NamedTuple

from pydantic import BaseModel, Field, model_validator

from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionMakerCheckerControl,
)
from src.core.waves.models import DpmWaveSourceRef
from src.core.waves.campaign_page_validation import validate_page_count

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


class CampaignControlValidationContext(NamedTuple):
    control_outcome: CampaignMakerCheckerControlOutcome
    submitter_actor_id: str | None
    reviewer_actor_id: str | None
    required_reviewer_role: str | None


class CampaignControlNormalizedInput(NamedTuple):
    control_ref: str
    recorded_by: str
    control_reason: str
    correlation_id: str
    submitter_actor_id: str | None
    reviewer_actor_id: str | None
    required_reviewer_role: str | None


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
    count: int = Field(ge=0, description="Number of maker-checker controls returned.")
    limit: int = Field(ge=1, description="Requested page size.")
    offset: int = Field(ge=0, description="Requested page offset.")

    @model_validator(mode="after")
    def validate_page_metadata(self) -> DpmBulkReviewCampaignDefinitionMakerCheckerControlPage:
        validate_page_count(count=self.count, item_count=len(self.maker_checker_controls))
        return self


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
    normalized = _normalize_control_request(
        control_ref=control_ref,
        recorded_by=recorded_by,
        control_reason=control_reason,
        correlation_id=correlation_id,
        submitter_actor_id=submitter_actor_id,
        reviewer_actor_id=reviewer_actor_id,
        required_reviewer_role=required_reviewer_role,
    )
    _validate_required_control_fields(normalized)
    _validate_control_action(
        control_action=control_action,
        control_outcome=control_outcome,
        submitter_actor_id=normalized.submitter_actor_id,
        reviewer_actor_id=normalized.reviewer_actor_id,
        required_reviewer_role=normalized.required_reviewer_role,
    )

    control = _build_control(
        definition=definition,
        control_action=control_action,
        control_ref=normalized.control_ref,
        recorded_by=normalized.recorded_by,
        submitter_actor_id=normalized.submitter_actor_id,
        reviewer_actor_id=normalized.reviewer_actor_id,
        required_reviewer_role=normalized.required_reviewer_role,
        control_outcome=control_outcome,
        control_reason=normalized.control_reason,
        correlation_id=normalized.correlation_id,
        source_refs=source_refs or [],
    )
    existing = _existing_control_by_ref(definition=definition, control_ref=control.control_ref)
    if existing is not None:
        if existing.content_hash == control.content_hash:
            return definition
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_CONFLICT")

    return _definition_with_appended_control(definition=definition, control=control)


def _normalize_control_request(
    *,
    control_ref: str,
    recorded_by: str,
    control_reason: str,
    correlation_id: str,
    submitter_actor_id: str | None,
    reviewer_actor_id: str | None,
    required_reviewer_role: str | None,
) -> CampaignControlNormalizedInput:
    return CampaignControlNormalizedInput(
        control_ref=control_ref.strip(),
        recorded_by=recorded_by.strip(),
        control_reason=control_reason.strip(),
        correlation_id=correlation_id.strip(),
        submitter_actor_id=_normalize_optional_actor(submitter_actor_id),
        reviewer_actor_id=_normalize_optional_actor(reviewer_actor_id),
        required_reviewer_role=_normalize_optional_actor(required_reviewer_role),
    )


def _validate_required_control_fields(normalized: CampaignControlNormalizedInput) -> None:
    if not normalized.control_ref:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_REQUIRED")
    if not normalized.recorded_by:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_ACTOR_REQUIRED")
    if not normalized.control_reason:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REASON_REQUIRED")
    if not normalized.correlation_id:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_CORRELATION_REQUIRED")


def _existing_control_by_ref(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    control_ref: str,
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControl | None:
    return {existing.control_ref: existing for existing in definition.maker_checker_controls}.get(
        control_ref
    )


def _definition_with_appended_control(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    control: DpmBulkReviewCampaignDefinitionMakerCheckerControl,
) -> DpmBulkReviewCampaignDefinition:
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
    context = CampaignControlValidationContext(
        control_outcome=control_outcome,
        submitter_actor_id=submitter_actor_id,
        reviewer_actor_id=reviewer_actor_id,
        required_reviewer_role=required_reviewer_role,
    )
    validator = _CONTROL_ACTION_VALIDATORS.get(control_action, _validate_exception_resolved_control)
    validator(context)


def _validate_submission_control(context: CampaignControlValidationContext) -> None:
    if not context.submitter_actor_id:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMITTER_REQUIRED")
    if context.control_outcome != "PENDING":
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMISSION_OUTCOME_INVALID")


def _validate_reviewer_assignment_control(context: CampaignControlValidationContext) -> None:
    if not context.reviewer_actor_id or not context.required_reviewer_role:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEWER_REQUIRED")
    if context.control_outcome != "PENDING":
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ASSIGNMENT_OUTCOME_INVALID")


def _validate_review_completed_control(context: CampaignControlValidationContext) -> None:
    if not context.submitter_actor_id or not context.reviewer_actor_id:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTORS_REQUIRED")
    if context.submitter_actor_id == context.reviewer_actor_id:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTOR_SEPARATION_REQUIRED")
    if context.control_outcome not in {"PASSED", "FAILED"}:
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEW_OUTCOME_INVALID")


def _validate_exception_raised_control(context: CampaignControlValidationContext) -> None:
    if context.control_outcome != "EXCEPTION_OPEN":
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_OUTCOME_INVALID")


def _validate_exception_resolved_control(context: CampaignControlValidationContext) -> None:
    if context.control_outcome != "EXCEPTION_RESOLVED":
        raise ValueError("BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_RESOLUTION_INVALID")


_CONTROL_ACTION_VALIDATORS: dict[
    CampaignMakerCheckerControlAction,
    Callable[[CampaignControlValidationContext], None],
] = {
    "SUBMITTED_FOR_REVIEW": _validate_submission_control,
    "REVIEWER_ASSIGNED": _validate_reviewer_assignment_control,
    "REVIEW_COMPLETED": _validate_review_completed_control,
    "CONTROL_EXCEPTION_RAISED": _validate_exception_raised_control,
    "CONTROL_EXCEPTION_RESOLVED": _validate_exception_resolved_control,
}


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
