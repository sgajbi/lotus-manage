from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeEvent,
    DpmOutcomeAiEvidenceInput,
    DpmOutcomeReviewComparison,
    DpmOutcomeReportInput,
    DpmPostTradeOutcomeReview,
    DpmRealizedOutcomeSnapshot,
    compare_outcome_dimensions,
)
from src.api.services.outcome_review_creation import (
    build_created_outcome_review,
    build_review_content_hash,
)
from src.api.services.outcome_review_refresh import build_source_refresh_result
from src.api.services.outcome_review_dimensions import (
    DpmOutcomeDimensionConfig as DpmOutcomeDimensionConfig,
    DpmOutcomeReviewValidationError as DpmOutcomeReviewValidationError,
    dimension_inputs_for_review,
)
from src.api.services.outcome_review_persistence import persist_outcome_review
from src.api.services.outcome_review_report_inputs import (
    build_outcome_ai_evidence_input,
    build_outcome_report_input,
    portfolio_memory_context_for_report,
)
from src.api.services.outcome_review_search import (
    normalize_outcome_review_search_filter as _normalize_outcome_review_search_filter,
    search_outcome_review_page,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository
from src.core.outcomes.repository import DpmOutcomeReviewConflictError, DpmOutcomeReviewRepository


class DpmOutcomeReviewNotFoundError(Exception):
    pass


_dimension_inputs = dimension_inputs_for_review
_portfolio_memory_context_for_report = portfolio_memory_context_for_report


def preview_outcome_review(
    *,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    dimension_configs: list[DpmOutcomeDimensionConfig],
) -> DpmOutcomeReviewComparison:
    return compare_outcome_dimensions(
        dimension_inputs_for_review(
            expected_snapshot=expected_snapshot,
            realized_snapshot=realized_snapshot,
            dimension_configs=dimension_configs,
        )
    )


def create_outcome_review(
    *,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    dimension_configs: list[DpmOutcomeDimensionConfig],
    actor_id: str,
    correlation_id: str,
    idempotency_key: str,
    repository: DpmOutcomeReviewRepository,
) -> DpmPostTradeOutcomeReview:
    comparison = preview_outcome_review(
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        dimension_configs=dimension_configs,
    )
    content_hash = build_review_content_hash(
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        comparison=comparison,
    )
    existing = repository.get_outcome_review_by_idempotency(idempotency_key=idempotency_key)
    if existing is not None:
        if existing.content_hash != content_hash:
            raise DpmOutcomeReviewConflictError("DPM_OUTCOME_REVIEW_IDEMPOTENCY_CONFLICT")
        return existing
    created_at = datetime.now(timezone.utc)
    outcome_review_id = f"dor_{uuid4().hex[:16]}"
    review = build_created_outcome_review(
        outcome_review_id=outcome_review_id,
        comparison=comparison,
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        actor_id=actor_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        content_hash=content_hash,
        created_at=created_at,
    )
    persist_outcome_review(repository=repository, review=review, persisted_at=created_at)
    return review


def get_outcome_review(
    *,
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository,
) -> DpmPostTradeOutcomeReview:
    review = repository.get_outcome_review(outcome_review_id=outcome_review_id)
    if review is None:
        raise DpmOutcomeReviewNotFoundError(outcome_review_id)
    return review


def search_outcome_reviews(
    *,
    repository: DpmOutcomeReviewRepository,
    portfolio_id: str | None = None,
    mandate_id: str | None = None,
    wave_id: str | None = None,
    rebalance_run_id: str | None = None,
    state: str | None = None,
    source_system: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    source_scan_limit: int = 500,
) -> tuple[
    list[DpmPostTradeOutcomeReview],
    int,
    dict[str, int],
    dict[str, int],
    str | None,
    str | None,
]:
    """Search persisted outcome reviews without querying source-owner systems."""

    page = search_outcome_review_page(
        repository=repository,
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        wave_id=wave_id,
        rebalance_run_id=rebalance_run_id,
        state=state,
        source_system=source_system,
        source_type=source_type,
        limit=limit,
        offset=offset,
        source_scan_limit=source_scan_limit,
    )
    return (
        page.items,
        page.total,
        page.source_owner_counts,
        page.source_type_counts,
        page.normalized_source_system,
        page.normalized_source_type,
    )


def refresh_outcome_review_sources(
    *,
    outcome_review_id: str,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    dimension_configs: list[DpmOutcomeDimensionConfig],
    actor_id: str,
    repository: DpmOutcomeReviewRepository,
) -> tuple[DpmOutcomeEvent, DpmOutcomeReviewComparison]:
    review = get_outcome_review(outcome_review_id=outcome_review_id, repository=repository)
    event, comparison = build_source_refresh_result(
        review=review,
        realized_snapshot=realized_snapshot,
        dimension_configs=dimension_configs,
        actor_id=actor_id,
        refreshed_at=datetime.now(timezone.utc),
        event_id_suffix=uuid4().hex[:8],
    )
    repository.append_event(event=event)
    return event, comparison


def normalize_outcome_review_search_filter(value: str | None) -> str | None:
    return _normalize_outcome_review_search_filter(value)


def get_report_input(
    *,
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository,
    proof_pack_repository: DpmProofPackRepository | None = None,
    wave_repository: DpmWaveRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
) -> DpmOutcomeReportInput:
    review = get_outcome_review(outcome_review_id=outcome_review_id, repository=repository)
    return build_outcome_report_input(
        review=review,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=repository,
        mandate_repository=mandate_repository,
    )


def get_ai_evidence_input(
    *,
    outcome_review_id: str,
    repository: DpmOutcomeReviewRepository,
    proof_pack_repository: DpmProofPackRepository | None = None,
    wave_repository: DpmWaveRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
) -> DpmOutcomeAiEvidenceInput:
    review = get_outcome_review(outcome_review_id=outcome_review_id, repository=repository)
    return build_outcome_ai_evidence_input(
        review=review,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=repository,
        mandate_repository=mandate_repository,
    )
