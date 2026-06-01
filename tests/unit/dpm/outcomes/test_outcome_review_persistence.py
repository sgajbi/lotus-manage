from datetime import datetime, timedelta, timezone

from src.api.services.outcome_review_persistence import (
    OUTCOME_REVIEW_RETENTION_DAYS,
    persist_outcome_review,
)
from tests.unit.infrastructure.test_outcome_review_repository import _review


class _CapturingOutcomeReviewRepository:
    def __init__(self) -> None:
        self.saved: dict[str, object] | None = None

    def save_outcome_review(
        self,
        *,
        review: object,
        retention_expires_at: datetime | None,
    ) -> None:
        self.saved = {
            "review": review,
            "retention_expires_at": retention_expires_at,
        }


def test_persist_outcome_review_applies_seven_year_retention_from_persisted_at() -> None:
    repository = _CapturingOutcomeReviewRepository()
    review = _review()
    persisted_at = datetime(2026, 6, 1, 9, 15, tzinfo=timezone.utc)

    persist_outcome_review(
        repository=repository,  # type: ignore[arg-type]
        review=review,
        persisted_at=persisted_at,
    )

    assert repository.saved == {
        "review": review,
        "retention_expires_at": persisted_at + timedelta(days=OUTCOME_REVIEW_RETENTION_DAYS),
    }


def test_outcome_review_persistence_exports_retention_policy_surface() -> None:
    from src.api.services import outcome_review_persistence

    assert outcome_review_persistence.__all__ == [
        "OUTCOME_REVIEW_RETENTION_DAYS",
        "persist_outcome_review",
    ]
