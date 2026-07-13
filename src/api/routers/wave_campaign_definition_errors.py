from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status

from src.api.routers.wave_campaign_problem_details import campaign_problem_details_exception
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
)


_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL = {
    "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
    "message": "Bulk-review campaign definition was not found.",
}


def campaign_definition_not_found_http_exception() -> HTTPException:
    return campaign_problem_details_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        reason_code=_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL["code"],
        detail=_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL["message"],
    )


def campaign_definition_conflict_http_exception(
    exc: DpmBulkReviewCampaignDefinitionConflictError,
    *,
    message: str | None = None,
) -> HTTPException:
    return campaign_problem_details_exception(
        status_code=status.HTTP_409_CONFLICT,
        reason_code=str(exc),
        detail=message or str(exc),
    )


def campaign_definition_value_http_exception(exc: ValueError) -> HTTPException:
    return campaign_problem_details_exception(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        reason_code=str(exc),
        detail=str(exc),
    )


def campaign_definition_trusted_tenant_http_exception() -> HTTPException:
    return campaign_problem_details_exception(
        status_code=status.HTTP_400_BAD_REQUEST,
        reason_code="BULK_REVIEW_CAMPAIGN_TRUSTED_TENANT_REQUIRED",
        detail="X-Tenant-Id is required for bulk-review campaign definition operations.",
    )


_CAMPAIGN_EVIDENCE_CONFLICT_CODES = frozenset(
    {
        "BULK_REVIEW_CAMPAIGN_APPROVAL_DECISION_REF_CONFLICT",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_CONFLICT",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT",
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_CONFLICT",
        "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_CONFLICT",
    }
)

_CAMPAIGN_EVIDENCE_NOT_FOUND_CODES = frozenset(
    {
        "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND",
    }
)


def campaign_definition_evidence_value_http_exception(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code in _CAMPAIGN_EVIDENCE_CONFLICT_CODES:
        return campaign_problem_details_exception(
            status_code=status.HTTP_409_CONFLICT,
            reason_code=code,
            detail=code,
        )
    if code in _CAMPAIGN_EVIDENCE_NOT_FOUND_CODES:
        return campaign_problem_details_exception(
            status_code=status.HTTP_404_NOT_FOUND,
            reason_code=code,
            detail=code,
        )
    return campaign_definition_value_http_exception(exc)


def campaign_definition_lifecycle_http_exception(
    exc: DpmBulkReviewCampaignDefinitionLifecycleError,
) -> HTTPException:
    return campaign_problem_details_exception(
        status_code=_campaign_definition_lifecycle_status_code(exc.code),
        reason_code=exc.code,
        detail=exc.message,
    )


def campaign_definition_launch_blocked_http_exception(
    exc: DpmBulkReviewCampaignDefinitionLaunchBlocked,
) -> HTTPException:
    return campaign_problem_details_exception(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        reason_code="BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_BLOCKED",
        detail="Bulk-review campaign definition is not ready for durable launch.",
        extensions={
            "reason_codes": exc.reason_codes,
            "readiness": exc.readiness.model_dump(mode="json"),
        },
    )


def invalid_campaign_discovery_date_http_exception(field_name: str) -> HTTPException:
    return campaign_problem_details_exception(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        reason_code="BULK_REVIEW_CAMPAIGN_DISCOVERY_DATE_INVALID",
        detail=f"{field_name} must be an ISO date.",
    )


def parse_optional_campaign_discovery_date(
    *,
    value: str | None,
    field_name: str,
) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise invalid_campaign_discovery_date_http_exception(field_name) from exc


def _campaign_definition_lifecycle_status_code(code: str) -> int:
    if code == "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND":
        return status.HTTP_404_NOT_FOUND
    if code == "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID":
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    return status.HTTP_409_CONFLICT
