from __future__ import annotations

import hashlib
import json
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
    OutcomeEventType,
    build_ai_evidence_input,
    build_report_input,
    compare_outcome_dimensions,
)
from src.api.services.portfolio_memory_context_service import (
    build_report_portfolio_memory_context,
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
    content_hash = _review_content_hash(
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
    event = DpmOutcomeEvent(
        event_id=f"{outcome_review_id}_created",
        event_type=_created_event_type(comparison.state),
        event_time=created_at.isoformat(),
        actor=actor_id,
        outcome_review_id=outcome_review_id,
        state=comparison.state,
        reason_codes=comparison.supportability.reason_codes,
        source_refs=[*expected_snapshot.source_lineage, *realized_snapshot.source_lineage],
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
) -> DpmOutcomeAiEvidenceInput:
    return build_ai_evidence_input(
        get_outcome_review(outcome_review_id=outcome_review_id, repository=repository)
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


def _created_event_type(state: str) -> OutcomeEventType:
    if state == "BLOCKED":
        return "OUTCOME_REVIEW_BLOCKED"
    if state == "DEGRADED":
        return "OUTCOME_REVIEW_DEGRADED"
    if state == "READY":
        return "OUTCOME_REVIEW_READY"
    return "OUTCOME_REVIEW_CREATED"


def _content_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _review_content_hash(
    *,
    expected_snapshot: DpmExpectedOutcomeSnapshot,
    realized_snapshot: DpmRealizedOutcomeSnapshot,
    comparison: DpmOutcomeReviewComparison,
) -> str:
    return _content_hash(
        {
            "expected_snapshot": expected_snapshot.model_dump(mode="json"),
            "realized_snapshot": realized_snapshot.model_dump(mode="json"),
            "dimension_results": [
                result.model_dump(mode="json") for result in comparison.dimension_results
            ],
        }
    )
