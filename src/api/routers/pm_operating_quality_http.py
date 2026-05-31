from __future__ import annotations

from fastapi import HTTPException, status

from src.core.pm_quality import (
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualitySummaryInvocationConflictError,
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
