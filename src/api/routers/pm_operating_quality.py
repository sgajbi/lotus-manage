from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_outcome_review_repository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityEvidenceItem,
    DpmPmQualityValidationError,
    build_pm_operating_quality_score_run,
)


class DpmPmOperatingQualityScorePreviewRequest(BaseModel):
    pm_id: str = Field(
        description="Portfolio manager identifier supplied by the buying bank.",
        examples=["pm_001"],
    )
    book_id: str | None = Field(
        default=None,
        description="PM book identifier when the score run covers a defined book.",
        examples=["sg_dpm_balanced_book"],
    )
    as_of_date: str = Field(description="Score-run business as-of date.", examples=["2026-05-12"])
    policy: DpmPmOperatingQualityPolicy = Field(
        description="Explicit bank-owned PM operating quality policy for this run."
    )
    evidence_items: list[DpmPmQualityEvidenceItem] = Field(
        default_factory=list,
        description="Source-owned evidence signals not already represented by outcome-review ids.",
    )
    outcome_review_ids: list[str] = Field(
        default_factory=list,
        description="Persisted lotus-manage outcome reviews to include as source-backed evidence.",
        examples=[["dor_001"]],
    )
    actor_id: str = Field(
        description="Actor or service requesting the score run.", examples=["ops"]
    )


class DpmPmOperatingQualityScorePreviewResponse(BaseModel):
    score_run: DpmPmOperatingQualityScoreRun = Field(
        description="Deterministic explainable score-run output."
    )


router = APIRouter(
    prefix="/rebalance/pm-operating-quality",
    tags=["lotus-manage PM Operating Quality"],
)


@router.post(
    "/score-runs/preview",
    response_model=DpmPmOperatingQualityScorePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview PM operating quality score run",
    description=(
        "What: Build a deterministic, explainable PM operating quality score run from an explicit "
        "bank-owned policy, source-owned evidence signals, and optional persisted outcome reviews.\n"
        "When: Use for DPM supervisory control, operations support, or evidence review after the "
        "bank has enabled a governed scoring policy.\n"
        "How: Supply the policy, source-backed evidence, and optional outcome-review ids. Disabled "
        "policies return a DISABLED run with no score; missing required evidence blocks the run. "
        "The endpoint does not create HR, compensation, conduct-enforcement, autonomous ranking, "
        "AI-generated, risk, performance, execution, or tax methodology."
    ),
)
def preview_pm_operating_quality_score_run_endpoint(
    request: DpmPmOperatingQualityScorePreviewRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(description="Optional correlation id.", examples=["corr-pmq-001"]),
    ] = None,
    repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
) -> DpmPmOperatingQualityScorePreviewResponse:
    outcome_reviews = []
    for outcome_review_id in request.outcome_review_ids:
        review = repository.get_outcome_review(outcome_review_id=outcome_review_id)
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
            policy=request.policy,
            evidence_items=request.evidence_items,
            outcome_reviews=outcome_reviews,
            generated_by=request.actor_id,
            correlation_id=x_correlation_id or request.actor_id,
        )
    except DpmPmQualityValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)
