from __future__ import annotations

from fastapi import HTTPException, status

from src.api.services.outcome_review_service import (
    DpmOutcomeReviewValidationError,
)
from src.core.outcomes.repository import DpmOutcomeReviewConflictError

OUTCOME_REVIEW_NOT_FOUND_DETAIL = "OUTCOME_REVIEW_NOT_FOUND"


def outcome_review_not_found_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=OUTCOME_REVIEW_NOT_FOUND_DETAIL,
    )


def outcome_review_conflict_http_exception(
    exc: DpmOutcomeReviewConflictError,
) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def outcome_review_validation_http_exception(
    exc: DpmOutcomeReviewValidationError,
) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
