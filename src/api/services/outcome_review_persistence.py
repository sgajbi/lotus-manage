from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.outcomes import DpmPostTradeOutcomeReview
from src.core.outcomes.repository import DpmOutcomeReviewRepository

OUTCOME_REVIEW_RETENTION_DAYS = 365 * 7


def persist_outcome_review(
    *,
    repository: DpmOutcomeReviewRepository,
    review: DpmPostTradeOutcomeReview,
    persisted_at: datetime | None = None,
) -> None:
    retention_base = persisted_at or datetime.now(timezone.utc)
    repository.save_outcome_review(
        review=review,
        retention_expires_at=retention_base + timedelta(days=OUTCOME_REVIEW_RETENTION_DAYS),
    )


__all__ = ["OUTCOME_REVIEW_RETENTION_DAYS", "persist_outcome_review"]
