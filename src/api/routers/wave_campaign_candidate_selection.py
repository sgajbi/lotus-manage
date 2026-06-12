from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Collection, Iterable, Mapping, Sequence
from typing import Generic, Protocol, TypeVar
from typing import cast

from src.api.routers.wave_portfolio_type_validation import normalize_required_portfolio_type
from src.api.services import wave_service


class BulkReviewCampaignCandidate(Protocol):
    @property
    def portfolio_type(self) -> str | None: ...

    @property
    def source_refs(self) -> Sequence[object]: ...


def _candidate_attribute(candidate: object, name: str) -> object | None:
    if isinstance(candidate, Mapping):
        if name in candidate:
            value = candidate[name]
            return cast(object | None, value)
        return None
    return cast(object | None, getattr(candidate, name, None))


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
        portfolio_type = _candidate_portfolio_type(candidate)
        if portfolio_type not in eligible_portfolio_types:
            excluded_count += 1
            continue
        _candidate_source_refs(candidate)
        included_candidates.append(candidate)

    return BulkReviewCampaignCandidateSelection(
        included_candidates=included_candidates,
        excluded_count=excluded_count,
    )


def _candidate_portfolio_type(candidate: object) -> str:
    portfolio_type_value = _candidate_attribute(candidate, "portfolio_type")
    if portfolio_type_value is not None and not isinstance(portfolio_type_value, str):
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_INVALID",
            "BULK_REVIEW_CAMPAIGN candidate portfolio_type must be a string.",
        )
    return normalize_required_portfolio_type(
        portfolio_type_value,
        required_code="BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED",
        required_message=(
            "BULK_REVIEW_CAMPAIGN candidate portfolios require source-owned portfolio_type."
        ),
    )


def _candidate_source_refs(candidate: object) -> Sequence[object]:
    source_refs = _candidate_attribute(candidate, "source_refs")
    if source_refs is not None and not isinstance(source_refs, Sequence):
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_SOURCE_REFS_INVALID",
            "BULK_REVIEW_CAMPAIGN candidate source_refs must be a sequence.",
        )
    if not source_refs:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_SOURCE_REFS_REQUIRED",
            "BULK_REVIEW_CAMPAIGN candidate portfolios require source_refs.",
        )
    return source_refs
