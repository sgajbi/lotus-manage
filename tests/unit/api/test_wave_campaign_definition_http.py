from __future__ import annotations

from datetime import date

import pytest
from fastapi import status
from fastapi import HTTPException

from src.api.routers.wave_campaign_definition_http import (
    campaign_definition_conflict_http_exception,
    campaign_definition_launch_blocked_http_exception,
    campaign_definition_lifecycle_http_exception,
    campaign_definition_not_found_http_exception,
    campaign_definition_value_http_exception,
    invalid_campaign_discovery_date_http_exception,
    parse_optional_campaign_discovery_date,
)
from src.core.waves.campaign_definition_launch_execution import (
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
)
from src.core.waves.campaign_definition_readiness import (
    DpmBulkReviewCampaignDefinitionPreviewReadiness,
)
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionConflictError


def test_campaign_definition_not_found_http_exception_maps_payload() -> None:
    http_exc = campaign_definition_not_found_http_exception()

    assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    assert http_exc.detail == {
        "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
        "message": "Bulk-review campaign definition was not found.",
    }


def test_campaign_definition_conflict_http_exception_uses_domain_code() -> None:
    http_exc = campaign_definition_conflict_http_exception(
        DpmBulkReviewCampaignDefinitionConflictError("BULK_REVIEW_CAMPAIGN_DUPLICATE")
    )

    assert http_exc.status_code == status.HTTP_409_CONFLICT
    assert http_exc.detail == {
        "code": "BULK_REVIEW_CAMPAIGN_DUPLICATE",
        "message": "BULK_REVIEW_CAMPAIGN_DUPLICATE",
    }


def test_campaign_definition_conflict_http_exception_accepts_operator_message() -> None:
    http_exc = campaign_definition_conflict_http_exception(
        DpmBulkReviewCampaignDefinitionConflictError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_CONFLICT"
        ),
        message="Bulk-review campaign definition launch audit could not be recorded.",
    )

    assert http_exc.status_code == status.HTTP_409_CONFLICT
    assert http_exc.detail == {
        "code": "BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_CONFLICT",
        "message": "Bulk-review campaign definition launch audit could not be recorded.",
    }


def test_campaign_definition_value_http_exception_maps_validation_failure() -> None:
    http_exc = campaign_definition_value_http_exception(ValueError("CAMPAIGN_VERSION_REQUIRED"))

    assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert http_exc.detail == {
        "code": "CAMPAIGN_VERSION_REQUIRED",
        "message": "CAMPAIGN_VERSION_REQUIRED",
    }


def test_campaign_definition_lifecycle_http_exception_maps_replacement_not_found() -> None:
    http_exc = campaign_definition_lifecycle_http_exception(
        DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND",
            "Replacement bulk-review campaign definition was not found.",
        )
    )

    assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    assert http_exc.detail == {
        "code": "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND",
        "message": "Replacement bulk-review campaign definition was not found.",
    }


def test_campaign_definition_lifecycle_http_exception_maps_invalid_replacement_version() -> None:
    http_exc = campaign_definition_lifecycle_http_exception(
        DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_VERSION_INVALID",
            "superseded_by_campaign_version must identify a different version.",
        )
    )

    assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_campaign_definition_lifecycle_http_exception_maps_default_conflict() -> None:
    http_exc = campaign_definition_lifecycle_http_exception(
        DpmBulkReviewCampaignDefinitionLifecycleError(
            "BULK_REVIEW_CAMPAIGN_DEFINITION_LIFECYCLE_CONFLICT",
            "Only active campaign definitions can be superseded.",
        )
    )

    assert http_exc.status_code == status.HTTP_409_CONFLICT


def test_campaign_definition_launch_blocked_http_exception_preserves_readiness() -> None:
    readiness = DpmBulkReviewCampaignDefinitionPreviewReadiness(
        campaign_id="campaign-holdings-apple-tesla-20260510",
        campaign_version="2026.05",
        campaign_status="ACTIVE",
        definition_as_of_date="2026-05-10",
        requested_as_of_date="2026-05-11",
        preview_create_allowed=False,
        supportability_state="BLOCKED",
        reason_codes=["BULK_REVIEW_CAMPAIGN_EXPIRED"],
        candidate_count=1,
        eligible_candidate_count=1,
        excluded_candidate_count=0,
        eligible_portfolio_types=["DISCRETIONARY"],
        governance_status="APPROVED",
        expiry_state="EXPIRED",
        actor_entitlement_state="NOT_SUPPLIED",
        lifecycle_event_count=1,
        source_ref_count=2,
        content_hash="sha256:readiness",
    )
    http_exc = campaign_definition_launch_blocked_http_exception(
        DpmBulkReviewCampaignDefinitionLaunchBlocked(
            reason_codes=["BULK_REVIEW_CAMPAIGN_EXPIRED"],
            readiness=readiness,
        )
    )

    assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert http_exc.detail["code"] == "BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_BLOCKED"
    assert http_exc.detail["reason_codes"] == ["BULK_REVIEW_CAMPAIGN_EXPIRED"]
    assert http_exc.detail["readiness"]["preview_create_allowed"] is False


def test_invalid_campaign_discovery_date_http_exception_maps_field_name() -> None:
    http_exc = invalid_campaign_discovery_date_http_exception("active_on")

    assert http_exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert http_exc.detail == {
        "code": "BULK_REVIEW_CAMPAIGN_DISCOVERY_DATE_INVALID",
        "message": "active_on must be an ISO date.",
    }


def test_parse_optional_campaign_discovery_date_accepts_empty_and_iso_date() -> None:
    assert parse_optional_campaign_discovery_date(value=None, field_name="active_on") is None
    assert parse_optional_campaign_discovery_date(
        value="2026-05-10",
        field_name="active_on",
    ) == date(2026, 5, 10)


def test_parse_optional_campaign_discovery_date_maps_invalid_date_to_http_error() -> None:
    with pytest.raises(HTTPException) as exc_info:
        parse_optional_campaign_discovery_date(value="2026/05/10", field_name="active_on")

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.detail == {
        "code": "BULK_REVIEW_CAMPAIGN_DISCOVERY_DATE_INVALID",
        "message": "active_on must be an ISO date.",
    }
