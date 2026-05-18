from __future__ import annotations

from fastapi import HTTPException, status

from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
    DpmBulkReviewCampaignDefinitionRepository,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
)


_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL = {
    "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
    "message": "Bulk-review campaign definition was not found.",
}


def get_campaign_definition_or_404(
    *,
    repository: DpmBulkReviewCampaignDefinitionRepository,
    campaign_id: str,
    campaign_version: str,
) -> DpmBulkReviewCampaignDefinition:
    definition = repository.get_definition(
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL,
        )
    return definition


def campaign_definition_not_found_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=_CAMPAIGN_DEFINITION_NOT_FOUND_DETAIL,
    )


def campaign_definition_conflict_http_exception(
    exc: DpmBulkReviewCampaignDefinitionConflictError,
    *,
    message: str | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": str(exc), "message": message or str(exc)},
    )


def campaign_definition_value_http_exception(exc: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": str(exc), "message": str(exc)},
    )


def campaign_definition_lifecycle_http_exception(
    exc: DpmBulkReviewCampaignDefinitionLifecycleError,
) -> HTTPException:
    return HTTPException(
        status_code=_campaign_definition_lifecycle_status_code(exc.code),
        detail={"code": exc.code, "message": exc.message},
    )


def campaign_definition_launch_blocked_http_exception(
    exc: DpmBulkReviewCampaignDefinitionLaunchBlocked,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_BLOCKED",
            "message": "Bulk-review campaign definition is not ready for durable launch.",
            "reason_codes": exc.reason_codes,
            "readiness": exc.readiness.model_dump(mode="json"),
        },
    )


def invalid_campaign_discovery_date_http_exception(field_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "code": "BULK_REVIEW_CAMPAIGN_DISCOVERY_DATE_INVALID",
            "message": f"{field_name} must be an ISO date.",
        },
    )


def _campaign_definition_lifecycle_status_code(code: str) -> int:
    if code == "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND":
        return status.HTTP_404_NOT_FOUND
    if code == "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID":
        return status.HTTP_422_UNPROCESSABLE_CONTENT
    return status.HTTP_409_CONFLICT
