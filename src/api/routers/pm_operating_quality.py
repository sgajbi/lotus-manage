from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator

from src.api.dependencies import (
    get_outcome_review_repository,
    get_pm_quality_policy_repository,
    get_pm_quality_score_run_repository,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityEvidenceItem,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityPolicyRepository,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityScoreRunRepository,
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
    policy: DpmPmOperatingQualityPolicy | None = Field(
        default=None,
        description=(
            "Explicit bank-owned PM operating quality policy for this run. Supply either this "
            "inline policy or a persisted policy id and version."
        ),
    )
    policy_id: str | None = Field(
        default=None,
        description="Persisted PM operating quality policy identifier to use for this run.",
        examples=["pmq_sg_dpm"],
    )
    policy_version: str | None = Field(
        default=None,
        description="Persisted PM operating quality policy version to use for this run.",
        examples=["2026.05"],
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

    @model_validator(mode="after")
    def validate_policy_selection(self) -> "DpmPmOperatingQualityScorePreviewRequest":
        has_inline = self.policy is not None
        has_ref = self.policy_id is not None or self.policy_version is not None
        if has_inline and has_ref:
            raise ValueError("Supply either inline policy or persisted policy reference, not both")
        if not has_inline and not (self.policy_id and self.policy_version):
            raise ValueError("Supply inline policy or both policy_id and policy_version")
        return self


class DpmPmOperatingQualityScorePreviewResponse(BaseModel):
    score_run: DpmPmOperatingQualityScoreRun = Field(
        description="Deterministic explainable score-run output."
    )


class DpmPmOperatingQualityScoreRunListResponse(BaseModel):
    score_runs: list[DpmPmOperatingQualityScoreRun] = Field(
        description="Bounded page of persisted PM operating quality score runs."
    )
    count: int = Field(description="Number of score runs returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


class DpmPmOperatingQualityPolicyListResponse(BaseModel):
    policies: list[DpmPmOperatingQualityPolicy] = Field(
        description="Bounded page of persisted PM operating quality policy versions."
    )
    count: int = Field(description="Number of policies returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


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
    outcome_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    policy_repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
) -> DpmPmOperatingQualityScorePreviewResponse:
    score_run = _build_score_run(
        request=request,
        x_correlation_id=x_correlation_id,
        outcome_repository=outcome_repository,
        policy_repository=policy_repository,
    )
    return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)


@router.post(
    "/score-runs",
    response_model=DpmPmOperatingQualityScorePreviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create persisted PM operating quality score run",
    description=(
        "What: Build and persist an immutable PM operating quality score run from an explicit "
        "bank-owned policy, source-owned evidence signals, and optional persisted outcome reviews.\n"
        "When: Use after a bank has approved PM operating quality scoring and needs auditable "
        "score-run lifecycle evidence.\n"
        "How: Supply the same evidence contract as preview. The persisted run is content-addressed "
        "and can be retrieved or listed for governance review. This endpoint does not administer "
        "policies, materialize PM books, create HR or compensation decisions, perform conduct "
        "enforcement, autonomously rank PMs, or calculate source-owned risk/performance/tax facts."
    ),
)
def create_pm_operating_quality_score_run_endpoint(
    request: DpmPmOperatingQualityScorePreviewRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(description="Optional correlation id.", examples=["corr-pmq-001"]),
    ] = None,
    outcome_repository: DpmOutcomeReviewRepository = Depends(get_outcome_review_repository),
    policy_repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
    score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
) -> DpmPmOperatingQualityScorePreviewResponse:
    score_run = _build_score_run(
        request=request,
        x_correlation_id=x_correlation_id,
        outcome_repository=outcome_repository,
        policy_repository=policy_repository,
    )
    try:
        score_run_repository.save_score_run(score_run=score_run)
    except DpmPmQualityScoreRunConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)


@router.put(
    "/policies/{policy_id}/versions/{policy_version}",
    response_model=DpmPmOperatingQualityPolicy,
    status_code=status.HTTP_200_OK,
    summary="Persist PM operating quality policy version",
    description=(
        "What: Persist an immutable PM operating quality policy version for later score-run "
        "preview and creation.\n"
        "When: Use after a bank has approved a governed PM operating-quality policy and wants "
        "auditable policy reuse.\n"
        "How: The path id/version must match the policy body. Re-saving identical content is "
        "idempotent; changing an existing version is rejected. This route administers policy "
        "configuration only; it does not materialize PM books, rank PMs, decide compensation, "
        "perform conduct enforcement, or calculate source-owned risk/performance/tax facts."
    ),
)
def put_pm_operating_quality_policy_endpoint(
    policy_id: str,
    policy_version: str,
    policy: DpmPmOperatingQualityPolicy,
    repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
) -> DpmPmOperatingQualityPolicy:
    if policy.policy_id != policy_id or policy.policy_version != policy_version:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PM_QUALITY_POLICY_PATH_BODY_MISMATCH",
        )
    try:
        repository.save_policy(policy=policy)
    except DpmPmQualityPolicyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return policy


@router.get(
    "/policies",
    response_model=DpmPmOperatingQualityPolicyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted PM operating quality policies",
    description=(
        "What: Return a bounded page of persisted PM operating quality policy versions.\n"
        "When: Use for governance review, bank policy selection, and score-run preparation.\n"
        "How: Filter by policy id, enabled state, or as-of date. The response returns stored "
        "policy configuration only and does not compute PM scores."
    ),
)
def list_pm_operating_quality_policies_endpoint(
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    enabled: Annotated[bool | None, Query(description="Filter by policy enabled flag.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by policy as-of date.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
) -> DpmPmOperatingQualityPolicyListResponse:
    policies = repository.list_policies(
        policy_id=policy_id,
        enabled=enabled,
        as_of_date=as_of_date,
        limit=limit,
        offset=offset,
    )
    return DpmPmOperatingQualityPolicyListResponse(
        policies=policies,
        count=len(policies),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/policies/{policy_id}/versions/{policy_version}",
    response_model=DpmPmOperatingQualityPolicy,
    status_code=status.HTTP_200_OK,
    summary="Get persisted PM operating quality policy version",
    description=(
        "What: Return one persisted PM operating quality policy version.\n"
        "When: Use for audit, supportability review, and score-run preparation.\n"
        "How: The endpoint returns immutable stored policy configuration and does not compute "
        "PM scores or source-owned facts."
    ),
)
def get_pm_operating_quality_policy_endpoint(
    policy_id: str,
    policy_version: str,
    repository: DpmPmQualityPolicyRepository = Depends(get_pm_quality_policy_repository),
) -> DpmPmOperatingQualityPolicy:
    policy = repository.get_policy(policy_id=policy_id, policy_version=policy_version)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_POLICY_NOT_FOUND:{policy_id}:{policy_version}",
        )
    return policy


@router.get(
    "/score-runs",
    response_model=DpmPmOperatingQualityScoreRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted PM operating quality score runs",
    description=(
        "What: Return a bounded page of persisted PM operating quality score runs.\n"
        "When: Use for PM operating-quality governance review and supportability diagnostics.\n"
        "How: Filter by PM, book, policy, as-of date, or bounded state. The response returns "
        "stored score-run evidence only and does not recompute scores."
    ),
)
def list_pm_operating_quality_score_runs_endpoint(
    pm_id: Annotated[str | None, Query(description="Filter by portfolio manager id.")] = None,
    book_id: Annotated[str | None, Query(description="Filter by PM book id.")] = None,
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by business as-of date.")] = None,
    state: Annotated[str | None, Query(description="Filter by score-run state.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    repository: DpmPmQualityScoreRunRepository = Depends(get_pm_quality_score_run_repository),
) -> DpmPmOperatingQualityScoreRunListResponse:
    score_runs = repository.list_score_runs(
        pm_id=pm_id,
        book_id=book_id,
        policy_id=policy_id,
        as_of_date=as_of_date,
        state=state,
        limit=limit,
        offset=offset,
    )
    return DpmPmOperatingQualityScoreRunListResponse(
        score_runs=score_runs,
        count=len(score_runs),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/score-runs/{score_run_id}",
    response_model=DpmPmOperatingQualityScorePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persisted PM operating quality score run",
    description=(
        "What: Return one persisted PM operating quality score run by stable id.\n"
        "When: Use for audit, supportability review, and downstream evidence retrieval.\n"
        "How: The endpoint returns immutable stored score-run evidence and does not recompute "
        "source facts or policy output."
    ),
)
def get_pm_operating_quality_score_run_endpoint(
    score_run_id: str,
    repository: DpmPmQualityScoreRunRepository = Depends(get_pm_quality_score_run_repository),
) -> DpmPmOperatingQualityScorePreviewResponse:
    score_run = repository.get_score_run(score_run_id=score_run_id)
    if score_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_SCORE_RUN_NOT_FOUND:{score_run_id}",
        )
    return DpmPmOperatingQualityScorePreviewResponse(score_run=score_run)


def _build_score_run(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    x_correlation_id: str | None,
    outcome_repository: DpmOutcomeReviewRepository,
    policy_repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityScoreRun:
    policy = _resolve_policy(request=request, repository=policy_repository)
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
    return score_run


def _resolve_policy(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    repository: DpmPmQualityPolicyRepository,
) -> DpmPmOperatingQualityPolicy:
    if request.policy is not None:
        return request.policy
    if request.policy_id is None or request.policy_version is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PM_QUALITY_POLICY_REFERENCE_REQUIRED",
        )
    policy = repository.get_policy(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
    )
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_POLICY_NOT_FOUND:{request.policy_id}:{request.policy_version}",
        )
    return policy
