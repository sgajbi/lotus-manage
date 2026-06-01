from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeDimensionInput,
    DpmOutcomeEvent,
    DpmOutcomeAiEvidenceInput,
    DpmOutcomeReviewComparison,
    DpmOutcomeReportInput,
    DpmOutcomeTolerance,
    DpmPostTradeOutcomeReview,
    DpmRealizedOutcomeSnapshot,
    OutcomeComparisonDirection,
    OutcomeDimension,
    build_ai_evidence_input,
    build_report_input,
    compare_outcome_dimensions,
)
from src.api.services.outcome_review_creation import (
    build_created_outcome_event,
    build_review_content_hash,
)
from src.api.services.portfolio_memory_context_service import (
    build_report_portfolio_memory_context,
)
from src.api.services.outcome_review_search import (
    normalize_outcome_review_search_filter as _normalize_outcome_review_search_filter,
    search_outcome_review_page,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.repository import DpmWaveRepository
from src.core.outcomes.repository import DpmOutcomeReviewConflictError, DpmOutcomeReviewRepository

OUTCOME_REVIEW_RETENTION_DAYS = 365 * 7


class DpmOutcomeReviewValidationError(Exception):
    pass


class DpmOutcomeReviewNotFoundError(Exception):
    pass


def preview_outcome_review(
    *,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    dimension_configs: list[DpmOutcomeDimensionConfig],
) -> DpmOutcomeReviewComparison:
    return compare_outcome_dimensions(
        _dimension_inputs(
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
    event = build_created_outcome_event(
        outcome_review_id=outcome_review_id,
        comparison=comparison,
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        actor_id=actor_id,
        created_at=created_at,
    )
    review = DpmPostTradeOutcomeReview(
        outcome_review_id=outcome_review_id,
        state=comparison.state,
        portfolio_id=expected_snapshot.portfolio_id,
        mandate_id=expected_snapshot.mandate_id,
        rebalance_run_id=expected_snapshot.rebalance_run_id,
        alternative_set_id=expected_snapshot.alternative_set_id,
        selected_alternative_id=expected_snapshot.selected_alternative_id,
        proof_pack_id=expected_snapshot.proof_pack_id,
        wave_id=expected_snapshot.wave_id,
        wave_item_id=expected_snapshot.wave_item_id,
        operations_handoff_ref_id=expected_snapshot.operations_handoff_ref_id,
        review_window=realized_snapshot.review_window,
        expected_snapshot=expected_snapshot,
        realized_snapshot=realized_snapshot,
        dimension_results=comparison.dimension_results,
        overall_outcome=comparison.overall_outcome,
        variance_summary=comparison.variance_summary,
        supportability=comparison.supportability,
        source_lineage=[*expected_snapshot.source_lineage, *realized_snapshot.source_lineage],
        source_hashes={**expected_snapshot.source_hashes, **realized_snapshot.source_hashes},
        section_hashes=expected_snapshot.section_hashes,
        events=[event],
        content_hash=content_hash,
        created_at=created_at,
        created_by=actor_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )
    repository.save_outcome_review(
        review=review,
        retention_expires_at=created_at + timedelta(days=OUTCOME_REVIEW_RETENTION_DAYS),
    )
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
    comparison = preview_outcome_review(
        expected_snapshot=review.expected_snapshot,
        realized_snapshot=realized_snapshot,
        dimension_configs=dimension_configs,
    )
    event = DpmOutcomeEvent(
        event_id=f"{outcome_review_id}_source_refreshed_{uuid4().hex[:8]}",
        event_type="OUTCOME_REVIEW_SOURCE_REFRESHED",
        event_time=datetime.now(timezone.utc).isoformat(),
        actor=actor_id,
        outcome_review_id=outcome_review_id,
        state=comparison.state,
        reason_codes=comparison.supportability.reason_codes,
        source_refs=[*review.expected_snapshot.source_lineage, *realized_snapshot.source_lineage],
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
    return build_report_input(
        review,
        portfolio_memory_context=_portfolio_memory_context_for_report(
            review=review,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=repository,
            mandate_repository=mandate_repository,
        ),
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
    return build_ai_evidence_input(
        review,
        portfolio_memory_context=_portfolio_memory_context_for_report(
            review=review,
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=repository,
            mandate_repository=mandate_repository,
        ),
    )


def _portfolio_memory_context_for_report(
    *,
    review: DpmPostTradeOutcomeReview,
    proof_pack_repository: DpmProofPackRepository | None,
    wave_repository: DpmWaveRepository | None,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
) -> DpmPortfolioMemoryReportContext | None:
    if proof_pack_repository is None or wave_repository is None:
        return None
    return build_report_portfolio_memory_context(
        portfolio_id=review.portfolio_id,
        proof_pack_repository=proof_pack_repository,
        wave_repository=wave_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )


@dataclass(frozen=True)
class DpmOutcomeDimensionConfig:
    dimension: OutcomeDimension
    tolerance: DpmOutcomeTolerance
    materiality: Decimal
    direction: OutcomeComparisonDirection


def _dimension_inputs(
    *,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    dimension_configs: list[DpmOutcomeDimensionConfig],
) -> list[DpmOutcomeDimensionInput]:
    inputs: list[DpmOutcomeDimensionInput] = []
    for config in dimension_configs:
        expected = expected_snapshot.expected_values.get(config.dimension)
        realized = realized_snapshot.realized_values.get(config.dimension)
        if expected is None or realized is None:
            raise DpmOutcomeReviewValidationError(
                f"DPM_OUTCOME_DIMENSION_EVIDENCE_MISSING:{config.dimension}"
            )
        inputs.append(
            DpmOutcomeDimensionInput(
                dimension=config.dimension,
                expected=expected,
                realized=realized,
                tolerance=config.tolerance,
                materiality=config.materiality,
                direction=config.direction,
            )
        )
    return inputs
