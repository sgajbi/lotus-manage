"""Configurable PM operating quality models for RFC42-WTBD-008."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.core.outcomes import DpmOutcomeSourceRef

PmQualityIndicator = Literal[
    "OUTCOME_DISCIPLINE",
    "SOURCE_QUALITY",
    "EXCEPTION_DISCIPLINE",
    "EVIDENCE_COMPLETENESS",
]

PmQualityState = Literal[
    "DISABLED",
    "READY",
    "PENDING_REVIEW",
    "DEGRADED",
    "BREACHED",
    "BLOCKED",
]

PmQualityAccessPurpose = Literal[
    "PORTFOLIO_MANAGEMENT_REVIEW",
    "SUPERVISORY_CONTROL_REVIEW",
    "OPERATIONS_SUPPORT",
    "CLIENT_DEMO_EVIDENCE",
]

PmQualityFairnessSegmentType = Literal[
    "MANDATE_TYPE",
    "REGION",
    "BOOK_PROFILE",
    "CLIENT_CONSTRAINT_PROFILE",
    "MARKET_REGIME",
    "CUSTOM_SOURCE_SEGMENT",
]

PmQualityReviewActionTargetType = Literal[
    "SCORE_RUN",
    "FAIRNESS_ANALYSIS",
]

PmQualityReviewActionType = Literal[
    "ACKNOWLEDGE",
    "REQUEST_EVIDENCE_REMEDIATION",
    "ACCEPT_GOVERNANCE_EXCEPTION",
    "ESCALATE_MODEL_RISK_REVIEW",
    "CLOSE_REVIEW",
]

PmQualityReviewActionState = Literal[
    "RECORDED",
    "REVIEW_REQUIRED",
    "ESCALATED",
    "CLOSED",
]

PmQualitySummaryInvocationState = Literal[
    "REQUESTED",
    "COMPLETED",
    "FAILED",
]


class DpmPmQualityWeight(BaseModel):
    """One configured scoring dimension for PM operating quality."""

    indicator: PmQualityIndicator = Field(
        description="Bounded indicator included in the bank-configured score policy.",
        examples=["OUTCOME_DISCIPLINE"],
    )
    weight: Decimal = Field(
        gt=0,
        le=100,
        description="Relative indicator weight. Weights are normalized by the score engine.",
        examples=["50"],
    )
    minimum_evidence_count: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Minimum source-backed signals required for this indicator.",
        examples=[1],
    )


class DpmPmQualityGovernanceApproval(BaseModel):
    """Bank approval and fairness-review evidence for an enabled PM quality policy."""

    approval_ref: str = Field(
        description="Bank approval reference for this PM operating quality policy.",
        examples=["PMQ-APPROVAL-2026-05"],
    )
    approved_by: str = Field(description="Approver or committee identifier.")
    approved_at: str = Field(description="UTC timestamp or bank approval timestamp.")
    fairness_review_ref: str = Field(
        description="Reference for the bank fairness/access governance review.",
        examples=["FAIRNESS-PMQ-2026-05"],
    )
    fairness_reviewed_by: str = Field(description="Fairness reviewer or committee identifier.")
    fairness_reviewed_at: str = Field(description="Fairness review timestamp.")
    expires_on: str | None = Field(
        default=None,
        description="Optional ISO date after which this policy may no longer score runs.",
        examples=["2026-06-30"],
    )
    entitled_actor_ids: list[str] = Field(
        default_factory=list,
        description="Optional actor allow-list. When supplied, generated_by must be listed.",
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Approval, entitlement, or fairness-review source refs.",
    )


class DpmPmQualityPeerGroupPolicy(BaseModel):
    """Bank-defined PM peer-group scope for governed score-run comparison."""

    peer_group_id: str = Field(description="Bank-owned peer-group identifier.")
    display_name: str = Field(description="Operator-facing peer-group label.")
    segment_type: PmQualityFairnessSegmentType = Field(
        description="Source-defined dimension used for the peer group."
    )
    minimum_peer_count: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Minimum source-defined peers required before peer context is comparable.",
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source refs proving the peer-group definition.",
    )

    @model_validator(mode="after")
    def validate_peer_group(self) -> "DpmPmQualityPeerGroupPolicy":
        if not self.peer_group_id.strip():
            raise ValueError("PM_QUALITY_PEER_GROUP_ID_REQUIRED")
        if not self.display_name.strip():
            raise ValueError("PM_QUALITY_PEER_GROUP_DISPLAY_NAME_REQUIRED")
        if not self.source_refs:
            raise ValueError("PM_QUALITY_PEER_GROUP_SOURCE_REFS_REQUIRED")
        return self


class DpmPmQualityLookbackWindowPolicy(BaseModel):
    """Bank-defined evidence lookback window for PM operating quality."""

    window_id: str = Field(description="Bank-owned lookback-window identifier.")
    start_date: str = Field(description="Inclusive ISO business date for evidence.")
    end_date: str = Field(description="Inclusive ISO business date for evidence.")
    timezone: str = Field(default="UTC", description="Business timezone for the window.")
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source refs proving approval or source ownership for the window.",
    )

    @model_validator(mode="after")
    def validate_lookback_window(self) -> "DpmPmQualityLookbackWindowPolicy":
        if not self.window_id.strip():
            raise ValueError("PM_QUALITY_LOOKBACK_WINDOW_ID_REQUIRED")
        try:
            start = datetime.fromisoformat(self.start_date).date()
            end = datetime.fromisoformat(self.end_date).date()
        except ValueError as exc:
            raise ValueError("PM_QUALITY_LOOKBACK_WINDOW_DATE_INVALID") from exc
        if start > end:
            raise ValueError("PM_QUALITY_LOOKBACK_WINDOW_RANGE_INVALID")
        if not self.source_refs:
            raise ValueError("PM_QUALITY_LOOKBACK_WINDOW_SOURCE_REFS_REQUIRED")
        return self


class DpmPmOperatingQualityPolicy(BaseModel):
    """Bank-owned PM operating quality policy supplied to a score run."""

    policy_id: str = Field(description="Bank-owned policy identifier.", examples=["pmq_sg_dpm"])
    policy_version: str = Field(description="Policy version.", examples=["2026.05"])
    enabled: bool = Field(
        default=False,
        description="Explicit enablement switch. Disabled policies produce no PM score.",
        examples=[True],
    )
    as_of_date: str = Field(description="Policy business as-of date.", examples=["2026-05-12"])
    access_purpose: PmQualityAccessPurpose = Field(
        description="Permitted purpose for this score run.",
        examples=["SUPERVISORY_CONTROL_REVIEW"],
    )
    weights: list[DpmPmQualityWeight] = Field(
        default_factory=list,
        description="Configured scoring weights. Required when policy is enabled.",
    )
    ready_threshold: Decimal = Field(
        default=Decimal("80"),
        ge=0,
        le=100,
        description="Minimum score for READY posture.",
        examples=["80"],
    )
    watch_threshold: Decimal = Field(
        default=Decimal("60"),
        ge=0,
        le=100,
        description="Minimum score before BREACHED posture.",
        examples=["60"],
    )
    allowed_uses: list[str] = Field(
        default_factory=lambda: [
            "portfolio_management_review",
            "supervisory_control_review",
            "operations_support",
        ],
        description=(
            "Operator-visible allowed uses. Compensation, HR, conduct enforcement, and autonomous "
            "decisioning are rejected by the score engine."
        ),
    )
    governance_approval: DpmPmQualityGovernanceApproval | None = Field(
        default=None,
        description=(
            "Required bank approval and fairness-review evidence when the policy is enabled. "
            "Disabled policies may omit it."
        ),
    )
    peer_group_policy: DpmPmQualityPeerGroupPolicy | None = Field(
        default=None,
        description=(
            "Optional bank-defined peer-group policy. Manage records the context and source refs "
            "but does not rank PMs or discover peers locally."
        ),
    )
    lookback_window_policy: DpmPmQualityLookbackWindowPolicy | None = Field(
        default=None,
        description=(
            "Optional bank-defined evidence lookback window. When supplied, score-run evidence "
            "outside the window fails closed."
        ),
    )

    @model_validator(mode="after")
    def validate_policy(self) -> "DpmPmOperatingQualityPolicy":
        if self.ready_threshold < self.watch_threshold:
            raise ValueError("ready_threshold must be greater than or equal to watch_threshold")
        if self.enabled and not self.weights:
            raise ValueError("enabled PM quality policies require at least one configured weight")
        if self.enabled and self.governance_approval is None:
            raise ValueError("PM_QUALITY_GOVERNANCE_APPROVAL_REQUIRED")
        indicators = [weight.indicator for weight in self.weights]
        if len(set(indicators)) != len(indicators):
            raise ValueError("PM quality policy indicators must be unique")
        forbidden = {"compensation", "hr", "conduct_enforcement", "autonomous_decisioning"}
        normalized_uses = {use.strip().lower() for use in self.allowed_uses}
        if normalized_uses & forbidden:
            raise ValueError("PM quality policy contains a prohibited use")
        return self


class DpmPmQualityEvidenceItem(BaseModel):
    """Source-owned signal supplied to a PM operating quality score run."""

    indicator: PmQualityIndicator = Field(description="Indicator represented by this signal.")
    evidence_state: PmQualityState = Field(
        description="Bounded source evidence posture.",
        examples=["READY"],
    )
    score: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Source-supplied bounded score. Null requires a state-derived score.",
        examples=["92"],
    )
    source_system: str = Field(description="System that owns this signal.", examples=["lotus-risk"])
    source_type: str = Field(
        description="Source data product, artifact, or event type.",
        examples=["RollingRiskMetricsReport"],
    )
    source_id: str = Field(description="Source identifier.", examples=["risk_pm_001"])
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining this signal.",
        examples=[["SOURCE_READY"]],
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source refs supporting this signal.",
    )


class DpmPmQualityIndicatorResult(BaseModel):
    """Decomposed PM operating quality indicator result."""

    indicator: PmQualityIndicator = Field(description="Scored indicator.")
    score: Decimal | None = Field(description="Indicator score, null when unavailable.")
    weight: Decimal = Field(description="Policy weight applied to this indicator.")
    state: PmQualityState = Field(description="Indicator state.")
    evidence_count: int = Field(description="Number of source-backed signals used.")
    reason_codes: list[str] = Field(description="Bounded indicator reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(description="Source refs used by the indicator.")


class DpmPmQualityBookScopeEvidence(BaseModel):
    """Source-owned PM-book scope evidence attached to a score run."""

    source_system: Literal["lotus-core"] = Field(
        default="lotus-core",
        description="System that owns PM-book membership source truth.",
    )
    source_type: Literal["PortfolioManagerBookMembership"] = Field(
        default="PortfolioManagerBookMembership",
        description="Source data product used to materialize the PM book.",
    )
    source_id: str = Field(description="Core PM-book membership snapshot or batch identifier.")
    product_version: str = Field(description="Core source data product version.")
    supportability_state: str = Field(description="Core supportability state for the book scope.")
    returned_portfolio_count: int = Field(
        ge=1,
        description="Number of portfolios returned by the source-owned PM-book membership product.",
    )
    member_portfolio_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Bounded portfolio identifiers returned by Core for portfolio-memory lineage "
            "projection. Empty means member identity was not retained in this score-run record."
        ),
    )
    filters_applied: dict[str, object] = Field(
        default_factory=dict,
        description="Source-applied filters returned by lotus-core for replay and audit.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining the book-scope evidence.",
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        default_factory=list,
        description="Source references supporting the PM-book scope.",
    )


class DpmPmQualityGovernanceEvidence(BaseModel):
    """Governance evidence applied to a score run."""

    approval_ref: str = Field(description="Bank approval reference used by this score run.")
    approved_by: str = Field(description="Approver or committee identifier.")
    approved_at: str = Field(description="Approval timestamp.")
    fairness_review_ref: str = Field(description="Fairness/access governance review reference.")
    fairness_reviewed_by: str = Field(description="Fairness reviewer or committee identifier.")
    fairness_reviewed_at: str = Field(description="Fairness review timestamp.")
    expires_on: str | None = Field(description="Optional policy expiry date.")
    actor_entitlement_state: Literal["AUTHORIZED", "NOT_SUPPLIED"] = Field(
        description="Actor entitlement posture applied to this run."
    )
    reason_codes: list[str] = Field(description="Bounded governance reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(
        description="Approval, entitlement, or fairness-review source refs."
    )


class DpmPmQualityScopeEvidence(BaseModel):
    """Materialized PM-quality scope evidence attached to a score run."""

    peer_group_id: str | None = Field(
        default=None,
        description="Bank-defined peer group recorded for the run, if supplied.",
    )
    peer_group_display_name: str | None = Field(default=None)
    peer_group_segment_type: PmQualityFairnessSegmentType | None = Field(default=None)
    minimum_peer_count: int | None = Field(default=None, ge=1)
    lookback_window_id: str | None = Field(default=None)
    lookback_start_date: str | None = Field(default=None)
    lookback_end_date: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    reason_codes: list[str] = Field(description="Bounded scope materialization reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(
        description="Peer-group and lookback-window source refs used by the run."
    )


class DpmPmOperatingQualityScoreRun(BaseModel):
    """Deterministic, explainable PM operating quality score run."""

    product_name: Literal["PmOperatingQualityScoreRun"] = Field(
        default="PmOperatingQualityScoreRun",
        description="Domain data product name emitted by lotus-manage.",
    )
    product_version: Literal["v1"] = Field(default="v1", description="Product version.")
    score_run_id: str = Field(description="Stable content-addressed score-run identifier.")
    pm_id: str = Field(description="Portfolio manager identifier.", examples=["pm_001"])
    book_id: str | None = Field(default=None, description="PM book identifier when available.")
    as_of_date: str = Field(description="Score-run business as-of date.", examples=["2026-05-12"])
    policy_id: str = Field(description="Policy identifier.")
    policy_version: str = Field(description="Policy version.")
    state: PmQualityState = Field(description="Score-run state.")
    score: Decimal | None = Field(description="Overall score, null when scoring is disabled.")
    indicator_results: list[DpmPmQualityIndicatorResult] = Field(
        description="Decomposed indicator results."
    )
    book_scope_evidence: DpmPmQualityBookScopeEvidence | None = Field(
        default=None,
        description=(
            "Optional source-owned PM-book membership evidence used to materialize the score-run "
            "scope. Null means the caller supplied scope without Core PM-book materialization."
        ),
    )
    governance_evidence: DpmPmQualityGovernanceEvidence | None = Field(
        default=None,
        description="Governance approval and fairness-review evidence applied to the score run.",
    )
    scope_evidence: DpmPmQualityScopeEvidence | None = Field(
        default=None,
        description=(
            "Optional materialized peer-group and lookback-window scope evidence. Manage records "
            "this context without ranking PMs or owning source methodology."
        ),
    )
    reason_codes: list[str] = Field(description="Bounded score-run reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(description="Source refs used by the run.")
    forbidden_uses: list[str] = Field(
        default_factory=lambda: [
            "compensation_decision",
            "hr_decision",
            "conduct_enforcement",
            "autonomous_pm_ranking",
        ],
        description="Uses explicitly outside this product contract.",
    )
    content_hash: str = Field(description="Canonical score-run content hash.")
    generated_at: datetime = Field(description="UTC generation timestamp.")
    generated_by: str = Field(description="Actor or service that generated the score run.")
    correlation_id: str = Field(description="Correlation identifier.")


class DpmPmQualityFairnessSegmentResult(BaseModel):
    """Cross-segment fairness posture for one source-defined PM-quality cohort."""

    segment_id: str = Field(description="Source-defined segment identifier.")
    segment_type: PmQualityFairnessSegmentType = Field(
        description="Source-defined segment dimension used for governance comparison."
    )
    display_name: str = Field(description="Operator-facing segment label.")
    state: PmQualityState = Field(description="Segment fairness analysis state.")
    score_run_count: int = Field(
        ge=0,
        description="Number of persisted PM operating quality score runs included.",
    )
    average_score: Decimal | None = Field(
        default=None,
        description="Average score for scorable runs in this segment, null when blocked.",
    )
    minimum_score: Decimal | None = Field(
        default=None,
        description="Minimum scorable run score in this segment, null when blocked.",
    )
    maximum_score: Decimal | None = Field(
        default=None,
        description="Maximum scorable run score in this segment, null when blocked.",
    )
    reason_codes: list[str] = Field(description="Bounded segment-level reason codes.")
    score_run_refs: list[DpmOutcomeSourceRef] = Field(
        description="Score-run source refs included in this segment."
    )
    source_refs: list[DpmOutcomeSourceRef] = Field(
        description="Source refs proving the segment definition."
    )


class DpmPmQualityFairnessAnalysis(BaseModel):
    """Bounded fairness analysis over source-defined PM operating quality segments."""

    product_name: Literal["PmOperatingQualityFairnessAnalysis"] = Field(
        default="PmOperatingQualityFairnessAnalysis",
        description="Domain data product name emitted by lotus-manage.",
    )
    product_version: Literal["v1"] = Field(default="v1", description="Product version.")
    fairness_analysis_id: str = Field(
        description="Stable content-addressed fairness-analysis identifier."
    )
    policy_id: str = Field(description="Policy identifier shared by included score runs.")
    policy_version: str = Field(description="Policy version shared by included score runs.")
    as_of_date: str = Field(description="Analysis business as-of date.")
    state: PmQualityState = Field(description="Overall fairness-analysis state.")
    segment_results: list[DpmPmQualityFairnessSegmentResult] = Field(
        description="Source-defined segment comparison results."
    )
    minimum_segment_score_run_count: int = Field(
        ge=1,
        description="Minimum scorable runs required before comparing a segment.",
    )
    maximum_average_score_spread: Decimal = Field(
        ge=0,
        le=100,
        description="Bank-governed maximum average-score spread before review is required.",
    )
    observed_average_score_spread: Decimal | None = Field(
        default=None,
        description="Observed spread between ready segment average scores, null when blocked.",
    )
    reason_codes: list[str] = Field(description="Bounded analysis-level reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(
        description="Deduplicated score-run and segment source refs used by the analysis."
    )
    forbidden_uses: list[str] = Field(
        default_factory=lambda: [
            "protected_class_inference",
            "compensation_decision",
            "hr_decision",
            "conduct_enforcement",
            "autonomous_pm_ranking",
        ],
        description="Uses explicitly outside this product contract.",
    )
    content_hash: str = Field(description="Canonical fairness-analysis content hash.")
    generated_at: datetime = Field(description="UTC generation timestamp.")
    generated_by: str = Field(description="Actor or service that generated the analysis.")
    correlation_id: str = Field(description="Correlation identifier.")


class DpmPmQualityReviewAction(BaseModel):
    """Immutable PM operating-quality review action over existing governed evidence."""

    product_name: Literal["PmOperatingQualityReviewAction"] = Field(
        default="PmOperatingQualityReviewAction",
        description="Domain data product name emitted by lotus-manage.",
    )
    product_version: Literal["v1"] = Field(default="v1", description="Product version.")
    review_action_id: str = Field(description="Stable content-addressed review-action identifier.")
    review_action_ref: str = Field(
        min_length=1,
        description="Bank workflow, committee, ticket, or evidence reference for this action.",
        examples=["PMQ-REVIEW-2026-05-001"],
    )
    target_type: PmQualityReviewActionTargetType = Field(
        description="PM operating-quality product family reviewed by this action."
    )
    target_id: str = Field(description="Persisted score-run or fairness-analysis identifier.")
    target_content_hash: str = Field(description="Content hash of the reviewed evidence record.")
    policy_id: str = Field(description="Policy identifier on the reviewed evidence.")
    policy_version: str = Field(description="Policy version on the reviewed evidence.")
    as_of_date: str = Field(description="Business as-of date on the reviewed evidence.")
    target_state: PmQualityState = Field(description="State of the reviewed evidence.")
    action_type: PmQualityReviewActionType = Field(description="Bounded review action.")
    action_state: PmQualityReviewActionState = Field(
        description="Bounded review-action state derived from action_type."
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
    reason_codes: list[str] = Field(description="Bounded review-action reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(
        description="Target evidence ref plus any bank review-action source refs."
    )
    forbidden_uses: list[str] = Field(
        default_factory=lambda: [
            "compensation_decision",
            "hr_decision",
            "conduct_enforcement",
            "client_contact",
            "trade_approval",
            "order_routing",
            "oms_execution",
            "autonomous_pm_ranking",
        ],
        description="Uses explicitly outside this product contract.",
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: [
            "IMMUTABLE_REVIEW_ACTION_LEDGER",
            "NO_SCORE_RECALCULATION",
            "NO_FAIRNESS_RECOMPUTATION",
            "NO_PM_RANKING",
            "NO_HR_COMPENSATION_OR_CONDUCT_DECISION",
            "NO_CLIENT_CONTACT",
            "NO_TRADE_APPROVAL",
            "NO_ORDER_OR_OMS_EXECUTION",
        ],
        description="Unsupported downstream claims the review action must not imply.",
    )
    content_hash: str = Field(description="Canonical review-action content hash.")
    generated_at: datetime = Field(description="UTC generation timestamp.")
    correlation_id: str = Field(description="Correlation identifier.")


class DpmPmQualitySummaryInvocation(BaseModel):
    """Append-only audit record for PM-quality support-summary invocation."""

    product_name: Literal["PmOperatingQualitySummaryInvocation"] = Field(
        default="PmOperatingQualitySummaryInvocation",
        description="Domain data product name emitted by lotus-manage.",
    )
    product_version: Literal["v1"] = Field(default="v1", description="Product version.")
    summary_invocation_id: str = Field(
        description="Stable content-addressed summary-invocation identifier."
    )
    score_run_id: str = Field(description="Persisted score-run identifier summarized.")
    score_run_content_hash: str = Field(description="Content hash of the summarized score run.")
    review_action_id: str = Field(
        description="Review action that gates the support-summary invocation."
    )
    review_action_content_hash: str = Field(
        description="Content hash of the review action gating the invocation."
    )
    policy_id: str = Field(description="Policy identifier on the summarized score run.")
    policy_version: str = Field(description="Policy version on the summarized score run.")
    as_of_date: str = Field(description="Business as-of date on the summarized score run.")
    invocation_state: PmQualitySummaryInvocationState = Field(
        description="Bounded support-summary invocation state."
    )
    summary_ref: str = Field(
        min_length=1,
        description="Bank workflow, support ticket, or downstream summary request reference.",
        examples=["PMQ-SUMMARY-2026-05-001"],
    )
    workflow_pack_name: Literal["pm_quality_summary.pack"] = Field(
        default="pm_quality_summary.pack",
        description="AI-owned workflow pack name. Manage records history only.",
    )
    workflow_pack_version: str = Field(
        default="v1",
        description="AI-owned workflow pack version or compatible contract version.",
    )
    workflow_run_id: str | None = Field(
        default=None,
        description="Downstream AI workflow run id when available.",
    )
    summary_artifact_ref: str | None = Field(
        default=None,
        description="Downstream artifact reference when available. No narrative text is stored.",
    )
    summary_content_hash: str | None = Field(
        default=None,
        description="Hash of the downstream summary artifact when available.",
    )
    requested_by: str = Field(min_length=1, description="Actor or service requesting history.")
    reason_codes: list[str] = Field(description="Bounded invocation reason codes.")
    source_refs: list[DpmOutcomeSourceRef] = Field(
        description="Score-run, review-action, workflow, and artifact source refs."
    )
    forbidden_uses: list[str] = Field(
        default_factory=lambda: [
            "summary_text_storage",
            "score_recalculation",
            "fairness_recomputation",
            "compensation_decision",
            "hr_decision",
            "conduct_enforcement",
            "client_contact",
            "trade_approval",
            "order_routing",
            "oms_execution",
            "autonomous_pm_ranking",
        ],
        description="Uses explicitly outside this product contract.",
    )
    operating_boundaries: list[str] = Field(
        default_factory=lambda: [
            "APPEND_ONLY_SUMMARY_INVOCATION_HISTORY",
            "NO_SUMMARY_TEXT_STORAGE",
            "NO_SCORE_RECALCULATION",
            "NO_FAIRNESS_RECOMPUTATION",
            "NO_PM_RANKING",
            "NO_HR_COMPENSATION_OR_CONDUCT_DECISION",
            "NO_CLIENT_CONTACT",
            "NO_TRADE_APPROVAL",
            "NO_ORDER_OR_OMS_EXECUTION",
        ],
        description="Unsupported downstream claims the summary history must not imply.",
    )
    content_hash: str = Field(description="Canonical summary-invocation content hash.")
    generated_at: datetime = Field(description="UTC generation timestamp.")
    correlation_id: str = Field(description="Correlation identifier.")
