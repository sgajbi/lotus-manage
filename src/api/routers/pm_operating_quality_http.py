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
