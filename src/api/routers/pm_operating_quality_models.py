from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityEvidenceItem,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
    PmQualityFairnessSegmentType,
    PmQualityReviewActionTargetType,
    PmQualityReviewActionType,
    PmQualitySummaryInvocationState,
)


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


class DpmPmQualityReviewActionRequest(BaseModel):
    target_type: PmQualityReviewActionTargetType = Field(
        description="PM operating-quality product family reviewed by this action.",
        examples=["SCORE_RUN"],
    )
    target_id: str = Field(
        min_length=1,
        description="Persisted score-run or fairness-analysis identifier.",
    )
    action_type: PmQualityReviewActionType = Field(
        description="Bounded bank review action.",
        examples=["REQUEST_EVIDENCE_REMEDIATION"],
    )
    review_action_ref: str = Field(
        min_length=1,
        description="Bank workflow, committee, ticket, or evidence reference for this action.",
        examples=["PMQ-REVIEW-2026-05-001"],
    )
    review_reason: str = Field(
        min_length=1,
        description="Human-authored review rationale or decision note.",
    )
    remediation_due_date: str | None = Field(
        default=None,
        description="Optional due date for evidence remediation or follow-up review.",
        examples=["2026-06-15"],
    )
    actor_id: str = Field(
        min_length=1,
        description="Actor or service recording the review action.",
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Bank review-action source refs, such as committee minutes or tickets.",
    )

    @model_validator(mode="after")
    def validate_review_action_request(self) -> "DpmPmQualityReviewActionRequest":
        if self.remediation_due_date is not None:
            try:
                date.fromisoformat(self.remediation_due_date)
            except ValueError as exc:
                raise ValueError("remediation_due_date must be an ISO date") from exc
        return self


class DpmPmQualityReviewActionResponse(BaseModel):
    review_action: DpmPmQualityReviewAction = Field(
        description="Immutable PM operating-quality review action."
    )


class DpmPmQualityReviewActionListResponse(BaseModel):
    review_actions: list[DpmPmQualityReviewAction] = Field(
        description="Bounded page of persisted PM operating quality review actions."
    )
    count: int = Field(description="Number of review actions returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


class DpmPmQualitySummaryInvocationRequest(BaseModel):
    score_run_id: str = Field(
        min_length=1,
        description="Persisted PM operating-quality score run summarized by the support workflow.",
    )
    review_action_id: str = Field(
        min_length=1,
        description="Persisted review action that gates support-summary invocation.",
    )
    invocation_state: PmQualitySummaryInvocationState = Field(
        default="REQUESTED",
        description="Bounded support-summary invocation state.",
        examples=["REQUESTED"],
    )
    summary_ref: str = Field(
        min_length=1,
        description="Bank workflow, support ticket, or downstream summary request reference.",
        examples=["PMQ-SUMMARY-2026-05-001"],
    )
    workflow_pack_name: str = Field(
        default="pm_quality_summary.pack",
        description="AI-owned workflow pack name. Manage records history only.",
    )
    workflow_pack_version: str = Field(
        default="v1",
        min_length=1,
        description="AI-owned workflow pack version or compatible contract version.",
    )
    workflow_run_id: str | None = Field(
        default=None,
        description="Downstream AI workflow run id when available.",
    )
    summary_artifact_ref: str | None = Field(
        default=None,
        description="Downstream summary artifact reference when available.",
    )
    summary_content_hash: str | None = Field(
        default=None,
        description="Hash of the downstream summary artifact. Narrative text is not accepted.",
    )
    requested_by: str = Field(
        min_length=1,
        description="Actor or service recording support-summary history.",
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Workflow or artifact source refs. Do not include generated narrative text.",
    )

    @model_validator(mode="after")
    def validate_summary_invocation_request(self) -> "DpmPmQualitySummaryInvocationRequest":
        self.score_run_id = self.score_run_id.strip()
        self.review_action_id = self.review_action_id.strip()
        self.summary_ref = self.summary_ref.strip()
        self.workflow_pack_name = self.workflow_pack_name.strip()
        self.workflow_pack_version = self.workflow_pack_version.strip()
        self.workflow_run_id = self.workflow_run_id.strip() if self.workflow_run_id else None
        self.summary_artifact_ref = (
            self.summary_artifact_ref.strip() if self.summary_artifact_ref else None
        )
        self.requested_by = self.requested_by.strip()
        if not self.score_run_id or not self.review_action_id:
            raise ValueError("score_run_id and review_action_id must be non-empty")
        if not self.summary_ref or not self.workflow_pack_version or not self.requested_by:
            raise ValueError(
                "summary_ref, workflow_pack_version, and requested_by must be non-empty"
            )
        if self.summary_content_hash is not None and not self.summary_content_hash.startswith(
            "sha256:"
        ):
            raise ValueError("summary_content_hash must start with sha256:")
        if self.workflow_pack_name != "pm_quality_summary.pack":
            raise ValueError("workflow_pack_name must be pm_quality_summary.pack")
        return self


class DpmPmQualitySummaryInvocationResponse(BaseModel):
    summary_invocation: DpmPmQualitySummaryInvocation = Field(
        description="Append-only PM-quality support-summary invocation history."
    )


class DpmPmQualitySummaryInvocationListResponse(BaseModel):
    summary_invocations: list[DpmPmQualitySummaryInvocation] = Field(
        description="Bounded page of persisted PM-quality support-summary invocation history."
    )
    count: int = Field(description="Number of summary invocations returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")


class DpmPmOperatingQualityPolicyListResponse(BaseModel):
    policies: list[DpmPmOperatingQualityPolicy] = Field(
        description="Bounded page of persisted PM operating quality policy versions."
    )
    count: int = Field(description="Number of policies returned.")
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested page offset.")
