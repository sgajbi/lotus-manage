from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status

from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionPage,
    DpmBulkReviewCampaignDefinitionRequest,
    DpmBulkReviewCampaignDefinitionRetirementRequest,
    DpmBulkReviewCampaignDefinitionSupersessionRequest,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
    DpmBulkReviewCampaignDefinitionRepository,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
    retire_bulk_review_campaign_definition,
    supersede_bulk_review_campaign_definition,
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


def get_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    return get_campaign_definition_or_404(
        repository=repository,
        campaign_id=campaign_id,
        campaign_version=campaign_version,
    )


def put_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    try:
        definition = DpmBulkReviewCampaignDefinition(
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            display_name=request.display_name,
            status=request.status,
            as_of_date=request.as_of_date,
            rationale=request.rationale,
            eligible_portfolio_types=request.eligible_portfolio_types,
            candidates=request.candidates,
            governance=request.governance,
            source_refs=request.source_refs,
            created_by=request.created_by,
            correlation_id=request.correlation_id,
        )
        repository.save_definition(definition=definition)
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    return definition


def list_campaign_definitions_response(
    *,
    campaign_id: str | None,
    campaign_status: str | None,
    as_of_date: str | None,
    limit: int,
    offset: int,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinitionPage:
    items = repository.list_definitions(
        campaign_id=campaign_id,
        status=campaign_status,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return DpmBulkReviewCampaignDefinitionPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
    )


def retire_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionRetirementRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    try:
        retired = retire_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            retired_by=request.retired_by,
            retirement_reason=request.retirement_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if retired is None:
        raise campaign_definition_not_found_http_exception()
    return retired


def supersede_campaign_definition_response(
    *,
    campaign_id: str,
    campaign_version: str,
    request: DpmBulkReviewCampaignDefinitionSupersessionRequest,
    repository: DpmBulkReviewCampaignDefinitionRepository,
) -> DpmBulkReviewCampaignDefinition:
    try:
        superseded = supersede_bulk_review_campaign_definition(
            repository=repository,
            campaign_id=campaign_id,
            campaign_version=campaign_version,
            replacement_version=request.superseded_by_campaign_version,
            superseded_by=request.superseded_by,
            supersession_reason=request.supersession_reason,
            correlation_id=request.correlation_id,
        )
    except DpmBulkReviewCampaignDefinitionConflictError as exc:
        raise campaign_definition_conflict_http_exception(exc) from exc
    except DpmBulkReviewCampaignDefinitionLifecycleError as exc:
        raise campaign_definition_lifecycle_http_exception(exc) from exc
    except ValueError as exc:
        raise campaign_definition_value_http_exception(exc) from exc
    if superseded is None:
        raise campaign_definition_not_found_http_exception()
    return superseded


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
