from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status

from src.api.routers.pm_operating_quality_book_scope_builder import (
    book_scope_signal,
    resolve_pm_book_scope_evidence,
)
from src.api.routers.pm_operating_quality_models import (
    DpmPmOperatingQualityScorePreviewRequest,
)
from src.api.routers.pm_operating_quality_policy_resolution import resolve_policy
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityPolicyRepository,
    DpmPmQualityValidationError,
    build_pm_operating_quality_score_run,
)


def build_score_run(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    x_correlation_id: str | None,
    outcome_repository: DpmOutcomeReviewRepository,
    policy_repository: DpmPmQualityPolicyRepository,
    core_resolver_factory: Callable[[], Any],
) -> DpmPmOperatingQualityScoreRun:
    policy = resolve_policy(request=request, repository=policy_repository)
    evidence_items = list(request.evidence_items)
    book_scope_evidence = None
    if request.pm_book_scope is not None:
        book_scope_evidence = resolve_pm_book_scope_evidence(
            request=request,
            scope=request.pm_book_scope,
            correlation_id=x_correlation_id or request.actor_id,
            core_resolver_factory=core_resolver_factory,
        )
        evidence_items.append(book_scope_signal(book_scope_evidence))
    outcome_reviews = []
    for outcome_review_id in request.outcome_review_ids:
        review = outcome_repository.get_outcome_review(outcome_review_id=outcome_review_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OUTCOME_REVIEW_NOT_FOUND:{outcome_review_id}",
            )
        outcome_reviews.append(review)
    try:
        score_run = build_pm_operating_quality_score_run(
            pm_id=request.pm_id,
            book_id=request.book_id,
            as_of_date=request.as_of_date,
            policy=policy,
            evidence_items=evidence_items,
            outcome_reviews=outcome_reviews,
            book_scope_evidence=book_scope_evidence,
            generated_by=request.actor_id,
            correlation_id=x_correlation_id or request.actor_id,
        )
    except DpmPmQualityValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return score_run
