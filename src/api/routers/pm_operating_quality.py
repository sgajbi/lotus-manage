from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator

from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.api.services.pm_operating_quality_service import (
    DpmPmOperatingQualityServiceError,
    DpmPmQualityFairnessAnalysisCommand,
    DpmPmQualityFairnessSegmentCommand,
    build_pm_quality_fairness_analysis_from_command,
)
from src.api.dependencies import (
    get_pm_quality_fairness_analysis_repository,
    get_outcome_review_repository,
    get_pm_quality_policy_repository,
    get_pm_quality_score_run_repository,
)
from src.core.outcomes import DpmOutcomeSourceRef
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityFairnessAnalysisRepository,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityBookScopeEvidence,
    DpmPmQualityEvidenceItem,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityPolicyRepository,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityScoreRunRepository,
    DpmPmQualityValidationError,
    PmQualityFairnessSegmentType,
    build_pm_operating_quality_score_run,
)
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError


class DpmPmOperatingQualityPmBookScopeRequest(BaseModel):
    tenant_id: str | None = Field(
        default=None,
        description="Optional tenant selector forwarded to lotus-core PM-book membership.",
    )
    booking_center_code: str | None = Field(
        default=None,
        description="Optional booking-center selector forwarded to lotus-core PM-book membership.",
        examples=["Singapore"],
    )
    portfolio_types: list[str] = Field(
        default_factory=lambda: ["DPM"],
        description="Portfolio types eligible for the source-owned PM-book membership scope.",
        examples=[["DPM", "DISCRETIONARY"]],
    )
    include_inactive: bool = Field(
        default=False,
        description="Whether inactive PM-book members may be included. Defaults to active only.",
    )

    @model_validator(mode="after")
    def validate_scope(self) -> "DpmPmOperatingQualityPmBookScopeRequest":
        portfolio_types = [value.strip().upper() for value in self.portfolio_types if value.strip()]
        if not portfolio_types:
            raise ValueError("pm_book_scope.portfolio_types must contain at least one value")
        self.portfolio_types = portfolio_types
        return self


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
    pm_book_scope: DpmPmOperatingQualityPmBookScopeRequest | None = Field(
        default=None,
        description=(
            "Optional source-owned PM-book membership scope to materialize from lotus-core. "
            "When supplied, the score run fails closed unless PortfolioManagerBookMembership:v1 "
            "is READY and non-empty."
        ),
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


class DpmPmQualityFairnessSegmentRequest(BaseModel):
    segment_id: str = Field(
        description="Source-defined segment identifier.",
        examples=["mandate_balanced"],
    )
    segment_type: PmQualityFairnessSegmentType = Field(
        description="Source-defined segment dimension used for governance comparison.",
        examples=["MANDATE_TYPE"],
    )
    display_name: str = Field(
        description="Operator-facing segment label.",
        examples=["Balanced DPM Mandates"],
    )
    score_run_ids: list[str] = Field(
        min_length=1,
        max_length=100,
        description="Persisted PM operating quality score runs assigned to this source segment.",
        examples=[["pmq_001", "pmq_002"]],
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description=(
            "Source refs proving the segment definition. These should come from mandate, region, "
            "book-profile, client-constraint, or market-regime source products."
        ),
    )

    @model_validator(mode="after")
    def validate_segment(self) -> "DpmPmQualityFairnessSegmentRequest":
        deduped_ids = [
            score_run_id.strip() for score_run_id in self.score_run_ids if score_run_id.strip()
        ]
        if not deduped_ids:
            raise ValueError("segment.score_run_ids must contain at least one value")
        if len(set(deduped_ids)) != len(deduped_ids):
            raise ValueError("segment.score_run_ids must be unique")
        self.score_run_ids = deduped_ids
        return self


class DpmPmQualityFairnessPreviewRequest(BaseModel):
    policy_id: str = Field(description="PM operating quality policy id shared by score runs.")
    policy_version: str = Field(description="PM operating quality policy version.")
    as_of_date: str = Field(description="Fairness-analysis business as-of date.")
    segments: list[DpmPmQualityFairnessSegmentRequest] = Field(
        min_length=2,
        max_length=20,
        description=(
            "Source-defined segments to compare. Manage does not infer protected classes or "
            "discover segments locally."
        ),
    )
    minimum_segment_score_run_count: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Minimum scorable score runs required before a segment is comparable.",
    )
    maximum_average_score_spread: Decimal = Field(
        default=Decimal("15"),
        ge=0,
        le=100,
        description="Bank-governed maximum average-score spread before review is required.",
    )
    actor_id: str = Field(description="Actor or service requesting the analysis.")

    @model_validator(mode="after")
    def validate_segments(self) -> "DpmPmQualityFairnessPreviewRequest":
        segment_ids = [segment.segment_id for segment in self.segments]
        if len(set(segment_ids)) != len(segment_ids):
            raise ValueError("segments.segment_id values must be unique")
        return self


class DpmPmQualityFairnessPreviewResponse(BaseModel):
    fairness_analysis: DpmPmQualityFairnessAnalysis = Field(
        description="Bounded source-segment fairness analysis output."
    )


class DpmPmQualityFairnessAnalysisListResponse(BaseModel):
    fairness_analyses: list[DpmPmQualityFairnessAnalysis] = Field(
        description="Bounded page of persisted PM operating quality fairness analyses."
    )
    count: int = Field(description="Number of fairness analyses returned.")
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
        "Optionally supply pm_book_scope to attach source-owned lotus-core PM-book membership "
        "evidence; unavailable, incomplete, degraded, or empty membership fails closed. "
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
        "policies, create HR or compensation decisions, perform conduct "
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


@router.post(
    "/fairness-analyses/preview",
    response_model=DpmPmQualityFairnessPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview PM operating quality cross-segment fairness analysis",
    description=(
        "What: Build a bounded cross-segment fairness analysis from persisted PM operating "
        "quality score runs and source-defined segment assignments.\n"
        "When: Use for bank model-risk, fairness, supervisory-control, or governance review "
        "after score runs have been created under one approved policy.\n"
        "How: Supply two or more source-defined segments with persisted score-run ids and segment "
        "source refs. Manage validates the score runs share policy and as-of date, requires a "
        "minimum scorable count per segment, compares segment average scores against a governed "
        "spread threshold, and returns review-required posture when the spread exceeds policy. "
        "This endpoint does not infer protected classes, rank PMs, administer compensation or HR "
        "decisions, perform conduct enforcement, or calculate source-owned risk/performance facts."
    ),
)
def preview_pm_quality_fairness_analysis_endpoint(
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(description="Optional correlation id.", examples=["corr-pmq-fairness-001"]),
    ] = None,
    repository: DpmPmQualityScoreRunRepository = Depends(get_pm_quality_score_run_repository),
) -> DpmPmQualityFairnessPreviewResponse:
    fairness_analysis = _build_fairness_analysis(
        request=request,
        x_correlation_id=x_correlation_id,
        repository=repository,
    )
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


@router.post(
    "/fairness-analyses",
    response_model=DpmPmQualityFairnessPreviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create persisted PM operating quality fairness analysis",
    description=(
        "What: Build and persist an immutable PM operating quality cross-segment fairness "
        "analysis from persisted score runs and source-defined segment assignments.\n"
        "When: Use after a bank needs auditable fairness governance evidence for PM operating "
        "quality score runs created under one approved policy.\n"
        "How: Supply the same source-segment contract as preview. The persisted analysis is "
        "content-addressed and can be listed or retrieved for governance review. This endpoint "
        "does not infer protected classes, rank PMs, administer compensation or HR decisions, "
        "perform conduct enforcement, or calculate source-owned risk/performance facts."
    ),
)
def create_pm_quality_fairness_analysis_endpoint(
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: Annotated[
        str | None,
        Header(description="Optional correlation id.", examples=["corr-pmq-fairness-create"]),
    ] = None,
    score_run_repository: DpmPmQualityScoreRunRepository = Depends(
        get_pm_quality_score_run_repository
    ),
    fairness_repository: DpmPmQualityFairnessAnalysisRepository = Depends(
        get_pm_quality_fairness_analysis_repository
    ),
) -> DpmPmQualityFairnessPreviewResponse:
    fairness_analysis = _build_fairness_analysis(
        request=request,
        x_correlation_id=x_correlation_id,
        repository=score_run_repository,
    )
    try:
        fairness_repository.save_fairness_analysis(analysis=fairness_analysis)
    except DpmPmQualityFairnessAnalysisConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


@router.get(
    "/fairness-analyses",
    response_model=DpmPmQualityFairnessAnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted PM operating quality fairness analyses",
    description=(
        "What: Return a bounded page of persisted PM operating quality fairness analyses.\n"
        "When: Use for PM operating-quality governance review, supportability diagnostics, and "
        "model-risk evidence retrieval.\n"
        "How: Filter by policy, as-of date, or bounded state. The response returns stored "
        "fairness-analysis evidence only and does not recompute score runs or segment posture."
    ),
)
def list_pm_quality_fairness_analyses_endpoint(
    policy_id: Annotated[str | None, Query(description="Filter by policy id.")] = None,
    policy_version: Annotated[str | None, Query(description="Filter by policy version.")] = None,
    as_of_date: Annotated[str | None, Query(description="Filter by business as-of date.")] = None,
    state: Annotated[str | None, Query(description="Filter by fairness-analysis state.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum rows to return.")] = 50,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    repository: DpmPmQualityFairnessAnalysisRepository = Depends(
        get_pm_quality_fairness_analysis_repository
    ),
) -> DpmPmQualityFairnessAnalysisListResponse:
    fairness_analyses = repository.list_fairness_analyses(
        policy_id=policy_id,
        policy_version=policy_version,
        as_of_date=as_of_date,
        state=state,
        limit=limit,
        offset=offset,
    )
    return DpmPmQualityFairnessAnalysisListResponse(
        fairness_analyses=fairness_analyses,
        count=len(fairness_analyses),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/fairness-analyses/{fairness_analysis_id}",
    response_model=DpmPmQualityFairnessPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persisted PM operating quality fairness analysis",
    description=(
        "What: Return one persisted PM operating quality fairness analysis by stable id.\n"
        "When: Use for audit, model-risk review, and downstream governance evidence retrieval.\n"
        "How: The endpoint returns immutable stored fairness-analysis evidence and does not "
        "recompute score runs, infer protected classes, or rank PMs."
    ),
)
def get_pm_quality_fairness_analysis_endpoint(
    fairness_analysis_id: str,
    repository: DpmPmQualityFairnessAnalysisRepository = Depends(
        get_pm_quality_fairness_analysis_repository
    ),
) -> DpmPmQualityFairnessPreviewResponse:
    fairness_analysis = repository.get_fairness_analysis(fairness_analysis_id=fairness_analysis_id)
    if fairness_analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PM_QUALITY_FAIRNESS_ANALYSIS_NOT_FOUND:{fairness_analysis_id}",
        )
    return DpmPmQualityFairnessPreviewResponse(fairness_analysis=fairness_analysis)


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
    evidence_items = list(request.evidence_items)
    book_scope_evidence = None
    if request.pm_book_scope is not None:
        book_scope_evidence = _resolve_pm_book_scope_evidence(
            request=request,
            scope=request.pm_book_scope,
            correlation_id=x_correlation_id or request.actor_id,
        )
        evidence_items.append(_book_scope_signal(book_scope_evidence))
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


def _build_fairness_analysis(
    *,
    request: DpmPmQualityFairnessPreviewRequest,
    x_correlation_id: str | None,
    repository: DpmPmQualityScoreRunRepository,
) -> DpmPmQualityFairnessAnalysis:
    command = DpmPmQualityFairnessAnalysisCommand(
        policy_id=request.policy_id,
        policy_version=request.policy_version,
        as_of_date=request.as_of_date,
        segments=[
            DpmPmQualityFairnessSegmentCommand(
                segment_id=segment.segment_id,
                segment_type=segment.segment_type,
                display_name=segment.display_name,
                score_run_ids=segment.score_run_ids,
                source_refs=segment.source_refs,
            )
            for segment in request.segments
        ],
        minimum_segment_score_run_count=request.minimum_segment_score_run_count,
        maximum_average_score_spread=request.maximum_average_score_spread,
        actor_id=request.actor_id,
        correlation_id=x_correlation_id or request.actor_id,
    )
    try:
        return build_pm_quality_fairness_analysis_from_command(
            command=command,
            score_run_repository=repository,
        )
    except DpmPmOperatingQualityServiceError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if exc.code.startswith("PM_QUALITY_SCORE_RUN_NOT_FOUND:")
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(
            status_code=status_code,
            detail=exc.code,
        ) from exc


def _resolve_pm_book_scope_evidence(
    *,
    request: DpmPmOperatingQualityScorePreviewRequest,
    scope: DpmPmOperatingQualityPmBookScopeRequest,
    correlation_id: str,
) -> DpmPmQualityBookScopeEvidence:
    try:
        as_of_date = date.fromisoformat(request.as_of_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="INVALID_AS_OF_DATE",
        ) from exc
    try:
        membership = build_core_resolver_client().resolve_portfolio_manager_book_membership(
            portfolio_manager_id=request.pm_id,
            as_of_date=as_of_date,
            tenant_id=scope.tenant_id,
            booking_center_code=scope.booking_center_code,
            portfolio_types=scope.portfolio_types,
            include_inactive=scope.include_inactive,
            correlation_id=correlation_id,
        )
    except DpmCoreResolverUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_UNAVAILABLE"},
        ) from exc
    except DpmCoreResolverError as exc:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={"code": str(exc) or "DPM_CORE_PM_BOOK_MEMBERSHIP_INCOMPLETE"},
        ) from exc

    if membership.supportability.state != "READY":
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": membership.supportability.reason,
                "message": "PM-book membership is not source-ready for PM operating quality.",
            },
        )
    if not membership.members:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail={
                "code": "DPM_CORE_PM_BOOK_MEMBERSHIP_EMPTY",
                "message": "PM-book membership returned no portfolios for PM operating quality.",
            },
        )

    source_id = (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm_book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )
    book_ref = DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="PortfolioManagerBookMembership",
        source_id=source_id,
        source_version=membership.product_version,
        content_hash=membership.source_batch_fingerprint,
    )
    member_refs = [
        DpmOutcomeSourceRef(
            source_system="lotus-core",
            source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
            source_id=member.source_record_id or member.portfolio_id,
            source_version=membership.as_of_date.isoformat(),
        )
        for member in membership.members[:100]
    ]
    return DpmPmQualityBookScopeEvidence(
        source_id=source_id,
        product_version=membership.product_version,
        supportability_state=membership.supportability.state,
        returned_portfolio_count=len(membership.members),
        member_portfolio_ids=[member.portfolio_id for member in membership.members[:100]],
        filters_applied=membership.supportability.filters_applied,
        reason_codes=[
            "PM_BOOK_SCOPE_MATERIALIZED",
            membership.supportability.reason,
        ],
        source_refs=[book_ref, *member_refs],
    )


def _book_scope_signal(
    book_scope_evidence: DpmPmQualityBookScopeEvidence,
) -> DpmPmQualityEvidenceItem:
    return DpmPmQualityEvidenceItem(
        indicator="SOURCE_QUALITY",
        evidence_state="READY",
        score=None,
        source_system=book_scope_evidence.source_system,
        source_type=book_scope_evidence.source_type,
        source_id=book_scope_evidence.source_id,
        reason_codes=book_scope_evidence.reason_codes,
        source_refs=book_scope_evidence.source_refs,
    )


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
