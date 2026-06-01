from __future__ import annotations

from fastapi import HTTPException, status

from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualitySummaryInvocationConflictError,
)
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError

PmQualityConflictError = (
    DpmPmQualityScoreRunConflictError
    | DpmPmQualityFairnessAnalysisConflictError
    | DpmPmQualityReviewActionConflictError
    | DpmPmQualitySummaryInvocationConflictError
    | DpmPmQualityPolicyConflictError
)


def pm_quality_conflict_http_exception(exc: PmQualityConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def pm_quality_not_found_http_exception(
    *,
    code: str,
    identifier: str,
    secondary_identifier: str | None = None,
) -> HTTPException:
    detail = f"{code}:{identifier}"
    if secondary_identifier is not None:
        detail = f"{detail}:{secondary_identifier}"
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def pm_quality_validation_http_exception(detail: str | Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(detail))


def pm_quality_core_resolver_unavailable_http_exception(
    exc: DpmCoreResolverUnavailableError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE"},
    )


def pm_quality_core_resolver_incomplete_http_exception(exc: DpmCoreResolverError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE"},
    )


def pm_quality_pm_book_membership_not_ready_http_exception(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={
            "code": membership.supportability.reason,
            "message": "PM-book membership is not source-ready for PM operating quality.",
        },
    )


def pm_quality_pm_book_membership_empty_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={
            "code": "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
            "message": "PM-book membership returned no portfolios for PM operating quality.",
        },
    )
