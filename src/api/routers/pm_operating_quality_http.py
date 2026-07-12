from __future__ import annotations

from fastapi import HTTPException, status

from src.api.services.pm_operating_quality_service import DpmPmOperatingQualityServiceError
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualitySummaryInvocationConflictError,
)
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.api.services.core_resolver_service import (
    CoreResolverError,
    CoreResolverUnavailableError,
)

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


def pm_quality_service_http_exception(exc: DpmPmOperatingQualityServiceError) -> HTTPException:
    if exc.code == "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE":
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code},
        )
    if exc.code == "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY":
        return HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": exc.code,
                "message": "PM-book membership returned no portfolios for PM operating quality.",
            },
        )
    if exc.code.startswith(("DPM_CORE_PM_BOOK_MEMBERSHIP_", "DPM_CORE_PM_BOOK_")):
        return HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": exc.code,
                "message": "PM-book membership is not source-ready for PM operating quality.",
            },
        )
    not_found = _pm_quality_not_found_detail(exc.code)
    if not_found is not None:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found)
    return pm_quality_validation_http_exception(exc.code)


def _pm_quality_not_found_detail(code: str) -> str | None:
    not_found_prefixes = (
        "OUTCOME_REVIEW_NOT_FOUND:",
        "PM_QUALITY_POLICY_NOT_FOUND:",
        "PM_QUALITY_SCORE_RUN_NOT_FOUND:",
        "PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:",
        "PM_QUALITY_REVIEW_ACTION_NOT_FOUND:",
        "PM_QUALITY_SUMMARY_INVOCATION_NOT_FOUND:",
    )
    for prefix in not_found_prefixes:
        if code.startswith(prefix):
            return code
    return None


def pm_quality_core_resolver_unavailable_http_exception(
    exc: CoreResolverUnavailableError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE"},
    )


def pm_quality_core_resolver_incomplete_http_exception(exc: CoreResolverError) -> HTTPException:
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
