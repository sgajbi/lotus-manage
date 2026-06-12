from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Iterable

from src.core.outcomes.models import (
    DpmOutcomeEvent,
    DpmOutcomeRetentionMetadata,
    DpmPostTradeOutcomeReview,
)
from src.core.outcomes.repository import (
    DpmOutcomeReviewConflictError,
    DpmOutcomeReviewRepository,
)


@dataclass(frozen=True)
class _OutcomeReviewFilters:
    portfolio_id: str | None
    mandate_id: str | None
    wave_id: str | None
    rebalance_run_id: str | None
    state: str | None


class InMemoryDpmOutcomeReviewRepository(DpmOutcomeReviewRepository):
    def __init__(self) -> None:
        self._lock = Lock()
        self._reviews: dict[str, DpmPostTradeOutcomeReview] = {}
        self._idempotency_index: dict[str, str] = {}
        self._retention: dict[str, DpmOutcomeRetentionMetadata] = {}
        self._events: dict[str, list[DpmOutcomeEvent]] = {}

    def save_outcome_review(
        self,
        *,
        review: DpmPostTradeOutcomeReview,
        retention_expires_at: datetime | None,
    ) -> None:
        with self._lock:
            _raise_on_outcome_review_identity_conflict(self._reviews, review)
            _register_outcome_review_idempotency(self._idempotency_index, review)
            self._reviews[review.outcome_review_id] = deepcopy(review)
            self._retention[review.outcome_review_id] = _retention_metadata_for_review(
                review=review,
                retention_expires_at=retention_expires_at,
            )
            _append_missing_outcome_events(
                self._events.setdefault(review.outcome_review_id, []),
                review.events,
            )

    def get_outcome_review(
        self,
        *,
        outcome_review_id: str,
    ) -> DpmPostTradeOutcomeReview | None:
        with self._lock:
            review = self._reviews.get(outcome_review_id)
            return deepcopy(review) if review is not None else None

    def get_outcome_review_by_idempotency(
        self,
        *,
        idempotency_key: str,
    ) -> DpmPostTradeOutcomeReview | None:
        with self._lock:
            outcome_review_id = self._idempotency_index.get(idempotency_key)
            if outcome_review_id is None:
                return None
            review = self._reviews.get(outcome_review_id)
            return deepcopy(review) if review is not None else None

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
        with self._lock:
            reviews = _list_outcome_reviews(
                self._reviews.values(),
                _OutcomeReviewFilters(
                    portfolio_id=portfolio_id,
                    mandate_id=mandate_id,
                    wave_id=wave_id,
                    rebalance_run_id=rebalance_run_id,
                    state=state,
                ),
                limit=limit,
                offset=offset,
            )
            return deepcopy(reviews)

    def get_retention_metadata(
        self,
        *,
        outcome_review_id: str,
    ) -> DpmOutcomeRetentionMetadata | None:
        with self._lock:
            row = self._retention.get(outcome_review_id)
            return deepcopy(row) if row is not None else None

    def append_event(self, *, event: DpmOutcomeEvent) -> None:
        with self._lock:
            events = self._events.setdefault(event.outcome_review_id, [])
            if not any(existing.event_id == event.event_id for existing in events):
                events.append(deepcopy(event))

    def list_events(self, *, outcome_review_id: str) -> list[DpmOutcomeEvent]:
        with self._lock:
            events = self._events.get(outcome_review_id, [])
            return deepcopy(sorted(events, key=lambda event: (event.event_time, event.event_id)))


def _raise_on_outcome_review_identity_conflict(
    reviews: dict[str, DpmPostTradeOutcomeReview],
    review: DpmPostTradeOutcomeReview,
) -> None:
    existing = reviews.get(review.outcome_review_id)
    if existing is not None and existing.content_hash != review.content_hash:
        raise DpmOutcomeReviewConflictError("DPM_OUTCOME_REVIEW_IMMUTABLE_CONFLICT")


def _register_outcome_review_idempotency(
    idempotency_index: dict[str, str],
    review: DpmPostTradeOutcomeReview,
) -> None:
    if review.idempotency_key is None:
        return
    existing_id = idempotency_index.get(review.idempotency_key)
    if existing_id is not None and existing_id != review.outcome_review_id:
        raise DpmOutcomeReviewConflictError("DPM_OUTCOME_REVIEW_IDEMPOTENCY_CONFLICT")
    idempotency_index[review.idempotency_key] = review.outcome_review_id


def _retention_metadata_for_review(
    *,
    review: DpmPostTradeOutcomeReview,
    retention_expires_at: datetime | None,
) -> DpmOutcomeRetentionMetadata:
    return DpmOutcomeRetentionMetadata(
        outcome_review_id=review.outcome_review_id,
        retention_policy=review.retention_policy,
        retention_expires_at=retention_expires_at.isoformat() if retention_expires_at else None,
        legal_hold_state=review.legal_hold_state,
    )


def _append_missing_outcome_events(
    existing_events: list[DpmOutcomeEvent],
    candidate_events: Iterable[DpmOutcomeEvent],
) -> None:
    existing_event_ids = {event.event_id for event in existing_events}
    for event in candidate_events:
        if event.event_id in existing_event_ids:
            continue
        existing_events.append(deepcopy(event))
        existing_event_ids.add(event.event_id)


def _outcome_review_matches_filters(
    review: DpmPostTradeOutcomeReview,
    filters: _OutcomeReviewFilters,
) -> bool:
    return (
        _optional_value_matches(review.portfolio_id, filters.portfolio_id)
        and _optional_value_matches(review.mandate_id, filters.mandate_id)
        and _optional_value_matches(review.wave_id, filters.wave_id)
        and _optional_value_matches(review.rebalance_run_id, filters.rebalance_run_id)
        and _optional_value_matches(review.state, filters.state)
    )


def _optional_value_matches(actual: str | None, expected: str | None) -> bool:
    return expected is None or actual == expected


def _sort_outcome_reviews(
    reviews: list[DpmPostTradeOutcomeReview],
) -> list[DpmPostTradeOutcomeReview]:
    return sorted(
        reviews,
        key=lambda review: (review.created_at, review.outcome_review_id),
        reverse=True,
    )


def _list_outcome_reviews(
    reviews: Iterable[DpmPostTradeOutcomeReview],
    filters: _OutcomeReviewFilters,
    *,
    limit: int,
    offset: int,
) -> list[DpmPostTradeOutcomeReview]:
    matched_reviews = [
        review for review in reviews if _outcome_review_matches_filters(review, filters)
    ]
    sorted_reviews = _sort_outcome_reviews(matched_reviews)
    return sorted_reviews[offset : offset + limit]
