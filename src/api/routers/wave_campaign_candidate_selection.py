from __future__ import annotations

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from src.api.routers.wave_portfolio_type_validation import normalize_required_portfolio_type
from src.api.services import wave_service


class BulkReviewCampaignCandidate(Protocol):
    @property
    def portfolio_type(self) -> str | None: ...

    @property
    def source_refs(self) -> Sequence[object]: ...


T = TypeVar("T", bound=BulkReviewCampaignCandidate)


@dataclass(frozen=True)
class BulkReviewCampaignCandidateSelection(Generic[T]):
    included_candidates: list[T]
    excluded_count: int


def select_bulk_review_campaign_candidates(
    *,
    candidates: Iterable[T],
    eligible_portfolio_types: Collection[str],
) -> BulkReviewCampaignCandidateSelection[T]:
    included_candidates: list[T] = []
    excluded_count = 0
    for candidate in candidates:
        portfolio_type = normalize_required_portfolio_type(
            candidate.portfolio_type,
            required_code="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED",
            required_message=(
                "BULK_REVIEW_CAMPAIGN candidate portfolios require source-owned portfolio_type."
            ),
        )
        if portfolio_type not in eligible_portfolio_types:
            excluded_count += 1
            continue
        if not candidate.source_refs:
            raise wave_service.DpmWaveValidationError(
                "BULK_REVIEW_CAMPAIGN_SOURCE_REFS_REQUIRED",
                "BULK_REVIEW_CAMPAIGN candidate portfolios require source_refs.",
            )
        included_candidates.append(candidate)

    return BulkReviewCampaignCandidateSelection(
        included_candidates=included_candidates,
        excluded_count=excluded_count,
    )
