from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.api.observability import correlation_id_var
from src.api.response_headers import apply_observability_headers
from src.api.services.core_resolver_service import (
    CoreResolverError,
    CoreResolverUnavailableError,
)
from src.api.services.pm_operating_quality_service import DpmPmOperatingQualityServiceError
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityReviewActionIntegrityError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationIntegrityError,
)

PmQualityConflictError = (
    DpmPmQualityScoreRunConflictError
    | DpmPmQualityFairnessAnalysisConflictError
    | DpmPmQualityReviewActionConflictError
    | DpmPmQualityReviewActionIntegrityError
    | DpmPmQualitySummaryInvocationConflictError
    | DpmPmQualitySummaryInvocationIntegrityError
    | DpmPmQualityPolicyConflictError
)


def _pm_quality_problem_response(
    *,
    description: str,
    status_code: int,
    title: str,
    reason_code: str,
    detail: str,
) -> dict[str, object]:
    return {
        "description": description,
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/PmQualityProblemDetails"},
                "example": {
                    "type": "about:blank",
                    "title": title,
                    "status": status_code,
                    "detail": detail,
                    "reasonCode": reason_code,
                    "correlationId": "corr-pm-quality-example",
                    "instance": "/api/v1/rebalance/pm-operating-quality/score-runs/example",
                },
            }
        },
    }


PM_QUALITY_PROBLEM_RESPONSES: dict[int, dict[str, object]] = {
    403: _pm_quality_problem_response(
        description="PM-quality request is not authorized for the trusted caller identity.",
        status_code=403,
        title="Forbidden",
        reason_code="PM_QUALITY_TRUSTED_ACTOR_MISMATCH",
        detail="PM-quality request is not authorized for the trusted caller identity.",
    ),
    404: _pm_quality_problem_response(
        description="PM-quality resource was not found.",
        status_code=404,
        title="Not Found",
        reason_code="PM_QUALITY_SCORE_RUN_NOT_FOUND",
        detail="Requested PM-quality resource was not found.",
    ),
    409: _pm_quality_problem_response(
        description="PM-quality immutable persistence conflict.",
        status_code=409,
        title="Conflict",
        reason_code="PM_QUALITY_SCORE_RUN_IMMUTABLE_CONFLICT",
        detail="PM-quality request conflicts with immutable persisted state.",
    ),
    422: _pm_quality_problem_response(
        description="PM-quality semantic validation failed.",
        status_code=422,
        title="Validation Error",
        reason_code="PM_QUALITY_POLICY_AS_OF_DATE_MISMATCH",
        detail="PM-quality request failed semantic validation.",
    ),
    424: _pm_quality_problem_response(
        description="PM-quality source dependency is incomplete or not ready.",
        status_code=424,
        title="Failed Dependency",
        reason_code="DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE",
        detail="PM-book membership is not source-ready for PM operating quality.",
    ),
    503: _pm_quality_problem_response(
        description="PM-quality source dependency is unavailable.",
        status_code=503,
        title="Service Unavailable",
        reason_code="DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
        detail="Required PM-quality source dependency is unavailable.",
    ),
}


@dataclass(frozen=True)
class PmQualityProblemDetailsException(Exception):
    status_code: int
    reason_code: str
    title: str
    detail: str
    problem_type: str = "about:blank"

    def __post_init__(self) -> None:
        Exception.__init__(self, self.reason_code)


async def pm_quality_problem_details_exception_handler(
    request: Request,
    exc: PmQualityProblemDetailsException,
) -> JSONResponse:
    response = JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        content={
            "type": exc.problem_type,
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "reasonCode": exc.reason_code,
            "correlationId": correlation_id_var.get() or "",
            "instance": str(request.url.path),
        },
    )
    apply_observability_headers(response)
    return response


def pm_quality_conflict_http_exception(
    exc: PmQualityConflictError,
) -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_409_CONFLICT,
        reason_code=_reason_code(str(exc)),
        detail="PM-quality request conflicts with immutable persisted state.",
    )


def pm_quality_authorization_http_exception(
    *,
    reason_code: str,
) -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_403_FORBIDDEN,
        reason_code=reason_code,
        detail="PM-quality request is not authorized for the trusted caller identity.",
    )


def pm_quality_not_found_http_exception(
    *,
    code: str,
    identifier: str,
    secondary_identifier: str | None = None,
) -> PmQualityProblemDetailsException:
    detail = f"{code}:{identifier}"
    if secondary_identifier is not None:
        detail = f"{detail}:{secondary_identifier}"
    return _pm_quality_not_found_problem(detail)


def pm_quality_validation_http_exception(
    detail: str | Exception,
) -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        reason_code=_reason_code(str(detail)),
        detail="PM-quality request failed semantic validation.",
    )


def pm_quality_service_http_exception(
    exc: DpmPmOperatingQualityServiceError,
) -> PmQualityProblemDetailsException:
    if exc.code == "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE":
        return _pm_quality_problem_details(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            reason_code=exc.code,
            detail="Required PM-quality source dependency is unavailable.",
        )
    if exc.code == "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY":
        return _pm_quality_problem_details(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            reason_code=exc.code,
            detail="PM-book membership returned no portfolios for PM operating quality.",
        )
    if exc.code.startswith(("DPM_CORE_PM_BOOK_MEMBERSHIP_", "DPM_CORE_PM_BOOK_")):
        return _pm_quality_problem_details(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            reason_code=exc.code,
            detail="PM-book membership is not source-ready for PM operating quality.",
        )
    not_found = _pm_quality_not_found_detail(exc.code)
    if not_found is not None:
        return _pm_quality_not_found_problem(not_found)
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
) -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        reason_code=str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE",
        detail="Required PM-quality source dependency is unavailable.",
    )


def pm_quality_core_resolver_incomplete_http_exception(
    exc: CoreResolverError,
) -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        reason_code=str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE",
        detail="PM-book membership is not source-ready for PM operating quality.",
    )


def pm_quality_pm_book_membership_not_ready_http_exception(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        reason_code=membership.supportability.reason,
        detail="PM-book membership is not source-ready for PM operating quality.",
    )


def pm_quality_pm_book_membership_empty_http_exception() -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        reason_code="DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
        detail="PM-book membership returned no portfolios for PM operating quality.",
    )


def _pm_quality_not_found_problem(code: str) -> PmQualityProblemDetailsException:
    return _pm_quality_problem_details(
        status_code=status.HTTP_404_NOT_FOUND,
        reason_code=_reason_code(code),
        detail="Requested PM-quality resource was not found.",
    )


def _pm_quality_problem_details(
    *,
    status_code: int,
    reason_code: str,
    detail: str,
) -> PmQualityProblemDetailsException:
    return PmQualityProblemDetailsException(
        status_code=status_code,
        reason_code=reason_code,
        title=_problem_title(status_code),
        detail=detail,
    )


def _reason_code(code: str) -> str:
    return code.split(":", 1)[0]


def _problem_title(status_code: int) -> str:
    return {
        status.HTTP_404_NOT_FOUND: "Not Found",
        status.HTTP_409_CONFLICT: "Conflict",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation Error",
        status.HTTP_424_FAILED_DEPENDENCY: "Failed Dependency",
        status.HTTP_503_SERVICE_UNAVAILABLE: "Service Unavailable",
    }.get(status_code, "Error")
