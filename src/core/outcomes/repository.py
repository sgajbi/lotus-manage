"""Persistence contracts for RFC-0042 outcome reviews."""

from datetime import datetime
from typing import Protocol

from src.core.outcomes.models import (
    DpmOutcomeEvent,
    DpmOutcomeRetentionMetadata,
    DpmPostTradeOutcomeReview,
)


class DpmOutcomeReviewNotFoundError(Exception):
    """Raised when an outcome review does not exist."""


class DpmOutcomeReviewConflictError(Exception):
    """Raised when immutable outcome-review identity or idempotency conflicts."""


class DpmOutcomeReviewRepository(Protocol):
    def save_outcome_review(
        self,
        *,
        review: DpmPostTradeOutcomeReview,
        retention_expires_at: datetime | None,
    ) -> None:
        """Persist an immutable outcome review."""

    def get_outcome_review(
        self,
        *,
        outcome_review_id: str,
    ) -> DpmPostTradeOutcomeReview | None:
        """Return a review by id, or None when absent."""

    def get_outcome_review_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> DpmPostTradeOutcomeReview | None:
        """Return a review by idempotency key."""

    def list_outcome_reviews(
        self,
        *,
        portfolio_id: str | None = None,
        mandate_id: str | None = None,
        wave_id: str | None = None,
        rebalance_run_id: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPostTradeOutcomeReview]:
        """Return a bounded page of reviews."""

    def get_retention_metadata(
        self,
        *,
        outcome_review_id: str,
    ) -> DpmOutcomeRetentionMetadata | None:
        """Return retention metadata for a review."""

    def append_event(self, *, event: DpmOutcomeEvent) -> None:
        """Append an outcome event without mutating the immutable review body."""

    def list_events(self, *, outcome_review_id: str) -> list[DpmOutcomeEvent]:
        """Return append-only events for a review."""
