from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DpmCoreModelPortfolioTargetRow(BaseModel):
    instrument_id: str = Field(description="Core-governed target instrument identifier.")
    target_weight: Decimal = Field(description="Target instrument weight as a decimal ratio.")
    min_weight: Optional[Decimal] = Field(
        default=None,
        description="Optional lower target band as a decimal ratio.",
    )
    max_weight: Optional[Decimal] = Field(
        default=None,
        description="Optional upper target band as a decimal ratio.",
    )
    target_status: str = Field(description="Target lifecycle status from lotus-core.")
    quality_status: str = Field(description="Data quality status from lotus-core.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for audit and replay.",
    )


class DpmCoreModelPortfolioTargetSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for model target consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    target_count: int = Field(description="Number of target rows returned by lotus-core.")
    total_target_weight: Decimal = Field(description="Sum of returned target weights.")


class DpmCoreModelPortfolioTargetResponse(BaseModel):
    product_name: Literal["DpmModelPortfolioTarget"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    model_portfolio_id: str = Field(description="Core-governed model portfolio identifier.")
    model_portfolio_version: str = Field(description="Core-governed model portfolio version.")
    as_of_date: date = Field(description="As-of date used to resolve the target product.")
    display_name: str = Field(description="Business display name for the model portfolio.")
    base_currency: str = Field(description="Model portfolio base currency.")
    risk_profile: str = Field(description="Mandate risk profile aligned to the model.")
    mandate_type: str = Field(description="Mandate type for which this model is approved.")
    rebalance_frequency: Optional[str] = Field(
        default=None,
        description="Expected rebalance cadence.",
    )
    approval_status: str = Field(description="Approval lifecycle status for the model version.")
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the model version was approved.",
    )
    effective_from: date = Field(description="Resolved model version effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Resolved model version effective end date.",
    )
    targets: list[DpmCoreModelPortfolioTargetRow] = Field(
        description="Resolved target rows from lotus-core."
    )
    supportability: DpmCoreModelPortfolioTargetSupportability = Field(
        description="Completeness and readiness posture for the model target product."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreRebalanceBands(BaseModel):
    default_band: Decimal = Field(description="Default rebalance band as a decimal ratio.")
    cash_reserve_weight: Optional[Decimal] = Field(
        default=None,
        description="Optional mandate cash reserve target as a decimal ratio.",
    )


class DpmCoreMandateBindingSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for mandate binding consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    missing_data_families: list[str] = Field(
        default_factory=list,
        description="Source families missing from the mandate binding product.",
    )


class DpmCoreMandateBindingResponse(BaseModel):
    product_name: Literal["DiscretionaryMandateBinding"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    mandate_id: str = Field(description="Core-governed discretionary mandate identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    mandate_type: str = Field(description="Resolved mandate type.")
    discretionary_authority_status: str = Field(description="Resolved discretionary authority.")
    booking_center_code: str = Field(description="Resolved booking-center code.")
    jurisdiction_code: str = Field(description="Resolved jurisdiction code.")
    model_portfolio_id: str = Field(description="Model portfolio selected by the mandate.")
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Policy pack selected by the mandate.",
    )
    mandate_objective: Optional[str] = Field(
        default=None,
        description="Source-owned discretionary mandate objective from lotus-core.",
    )
    risk_profile: str = Field(description="Mandate risk profile.")
    investment_horizon: str = Field(description="Mandate investment horizon.")
    review_cadence: Optional[str] = Field(
        default=None,
        description="Source-owned mandate review cadence from lotus-core.",
    )
    last_review_date: Optional[date] = Field(
        default=None,
        description="Most recent completed mandate review date from lotus-core.",
    )
    next_review_due_date: Optional[date] = Field(
        default=None,
        description="Next due mandate review date from lotus-core.",
    )
    leverage_allowed: bool = Field(description="Whether mandate leverage is allowed.")
    tax_awareness_allowed: bool = Field(description="Whether tax-aware execution is allowed.")
    settlement_awareness_required: bool = Field(
        description="Whether settlement-aware execution is required."
    )
    rebalance_frequency: str = Field(description="Mandate rebalance cadence.")
    rebalance_bands: DpmCoreRebalanceBands = Field(
        description="Mandate rebalance bands and cash reserve policy."
    )
    effective_from: date = Field(description="Resolved binding effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Resolved binding effective end date.",
    )
    binding_version: int = Field(description="Resolved binding version.")
    supportability: DpmCoreMandateBindingSupportability = Field(
        description="Completeness and readiness posture for the mandate binding product."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )


class DpmCoreBenchmarkAssignmentResponse(BaseModel):
    product_name: Literal["BenchmarkAssignment"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    benchmark_id: str = Field(description="Core-governed benchmark identifier.")
    as_of_date: date = Field(description="As-of date used to resolve the assignment.")
    effective_from: date = Field(description="Assignment effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Assignment effective end date.",
    )
    assignment_source: str = Field(description="Source channel that established the assignment.")
    assignment_status: str = Field(description="Benchmark assignment lifecycle status.")
    policy_pack_id: Optional[str] = Field(default=None)
    source_system: Optional[str] = Field(default=None)
    assignment_recorded_at: datetime = Field(
        description="Timestamp when the assignment was recorded in lotus-core."
    )
    assignment_version: int = Field(description="Version used for effective-date tie-breaks.")
    contract_version: str = Field(default="rfc_062_v1")
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)


class DpmCorePortfolioManagerBookMember(BaseModel):
    portfolio_id: str = Field(description="Core-governed portfolio identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    booking_center_code: str = Field(description="Portfolio booking center.")
    portfolio_type: str = Field(description="Portfolio type used for book filtering.")
    status: str = Field(description="Portfolio lifecycle status in the PM book.")
    open_date: Optional[date] = Field(default=None, description="Portfolio open date.")
    close_date: Optional[date] = Field(default=None, description="Portfolio close date.")
    base_currency: Optional[str] = Field(default=None, description="Portfolio base currency.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for replay and audit.",
    )


class DpmCorePortfolioManagerBookSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for PM-book membership consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    returned_portfolio_count: int = Field(
        description="Number of portfolio memberships returned by lotus-core."
    )
    filters_applied: dict[str, Any] = Field(
        default_factory=dict,
        description="Core-applied filters used to resolve the book membership.",
    )


class DpmCorePortfolioManagerBookMembershipResponse(BaseModel):
    product_name: Literal["PortfolioManagerBookMembership"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve the PM book.")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant selector.")
    portfolio_manager_id: str = Field(description="Portfolio manager identifier.")
    booking_center_code: Optional[str] = Field(
        default=None,
        description="Optional booking-center filter.",
    )
    members: list[DpmCorePortfolioManagerBookMember] = Field(
        description="Resolved PM-book portfolio memberships from lotus-core."
    )
    supportability: DpmCorePortfolioManagerBookSupportability = Field(
        description="Completeness and readiness posture for PM-book membership."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )
    source_batch_fingerprint: Optional[str] = Field(
        default=None,
        description="Core source-batch fingerprint for replay and evidence tie-out.",
    )
    snapshot_id: Optional[str] = Field(
        default=None,
        description="Core snapshot identifier for the resolved PM-book membership.",
    )


class DpmCoreCioModelChangeAffectedMandate(BaseModel):
    portfolio_id: str = Field(description="Core-governed affected portfolio identifier.")
    mandate_id: str = Field(description="Core-governed affected mandate identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    booking_center_code: str = Field(description="Mandate booking center.")
    jurisdiction_code: str = Field(description="Mandate jurisdiction.")
    discretionary_authority_status: str = Field(
        description="Discretionary authority status selected by lotus-core."
    )
    model_portfolio_id: str = Field(description="Approved model portfolio identifier.")
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Policy pack associated with the mandate binding.",
    )
    risk_profile: str = Field(description="Mandate risk profile.")
    effective_from: date = Field(description="Mandate binding effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Mandate binding effective end date.",
    )
    binding_version: int = Field(description="Selected mandate binding version.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for replay and audit.",
    )


class DpmCoreCioModelChangeSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE", "UNAVAILABLE"] = Field(
        description="Core readiness state for CIO model-change cohort consumption."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    returned_mandate_count: int = Field(
        description="Number of affected mandates returned by lotus-core."
    )
    filters_applied: list[str] = Field(
        default_factory=list,
        description="Core-applied filters used to resolve the affected cohort.",
    )


class DpmCoreCioModelChangeAffectedCohortResponse(BaseModel):
    product_name: Literal["CioModelChangeAffectedCohort"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve the cohort.")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant selector.")
    model_portfolio_id: str = Field(description="Approved model portfolio identifier.")
    model_portfolio_version: str = Field(description="Approved model portfolio version.")
    model_change_event_id: str = Field(description="Core source-owned model-change event id.")
    approval_state: str = Field(description="Selected model definition approval state.")
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the selected model version was approved.",
    )
    effective_from: date = Field(description="Selected model version effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Selected model version effective end date.",
    )
    affected_mandates: list[DpmCoreCioModelChangeAffectedMandate] = Field(
        description="Resolved affected mandates from lotus-core."
    )
    supportability: DpmCoreCioModelChangeSupportability = Field(
        description="Completeness and readiness posture for CIO model-change discovery."
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(
        default=None,
        description="Core runtime data quality status.",
    )
    latest_evidence_timestamp: Optional[datetime] = Field(
        default=None,
        description="Latest evidence timestamp returned by lotus-core.",
    )
    source_batch_fingerprint: Optional[str] = Field(
        default=None,
        description="Core source-batch fingerprint for replay and evidence tie-out.",
    )
    snapshot_id: Optional[str] = Field(
        default=None,
        description="Core snapshot identifier for the resolved affected cohort.",
    )


class DpmCorePortfolioUniverseCandidate(BaseModel):
    portfolio_id: str = Field(description="Core-governed candidate portfolio identifier.")
    mandate_id: str = Field(description="Source-owned discretionary mandate identifier.")
    client_id: str = Field(description="Core-governed client identifier.")
    booking_center_code: str = Field(description="Mandate booking center.")
    jurisdiction_code: str = Field(description="Mandate jurisdiction.")
    discretionary_authority_status: str = Field(
        description="Discretionary authority status selected by lotus-core."
    )
    model_portfolio_id: str = Field(description="Approved model portfolio identifier.")
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Policy pack associated with the mandate binding.",
    )
    mandate_objective: Optional[str] = Field(default=None)
    risk_profile: str = Field(description="Mandate risk profile.")
    investment_horizon: str = Field(description="Mandate investment horizon.")
    effective_from: date = Field(description="Mandate binding effective start date.")
    effective_to: Optional[date] = Field(
        default=None,
        description="Mandate binding effective end date.",
    )
    binding_version: int = Field(description="Selected mandate binding version.")
    source_record_id: Optional[str] = Field(
        default=None,
        description="Core source record identifier for replay and audit.",
    )


class DpmCorePortfolioUniversePageMetadata(BaseModel):
    page_size: int = Field(description="Maximum candidates requested from lotus-core.")
    sort_key: str = Field(description="Deterministic sort key applied by lotus-core.")
    returned_component_count: int = Field(description="Number of candidates returned.")
    request_scope_fingerprint: str = Field(
        description="Core fingerprint of request selectors and paging scope."
    )
    next_page_token: Optional[str] = Field(
        default=None,
        description="Opaque continuation token when more candidates are available.",
    )


class DpmCorePortfolioUniverseCandidateSupportability(BaseModel):
    state: Literal["READY", "DEGRADED", "INCOMPLETE"] = Field(
        description="Core readiness state for DPM portfolio-universe discovery."
    )
    reason: str = Field(description="Bounded core readiness reason code.")
    returned_candidate_count: int = Field(
        description="Number of candidates returned in the current page."
    )
    filters_applied: list[str] = Field(
        default_factory=list,
        description="Core-applied filters used to resolve the candidate page.",
    )
    page_truncated: bool = Field(
        description="True when additional source candidates remain behind a continuation token."
    )


class DpmCorePortfolioUniverseCandidateSelectionBasis(BaseModel):
    basis_type: Literal["EFFECTIVE_DISCRETIONARY_MANDATE_BINDING"] = Field(
        description=(
            "Core-owned selection-basis code for candidate membership; downstream consumers must "
            "not reinterpret it as broader campaign membership or execution authority."
        )
    )
    source_table: Literal["portfolio_mandate_bindings"] = Field(
        description="Core source table family used to resolve DPM candidate membership."
    )
    included_when: list[str] = Field(
        default_factory=list,
        description="Core source predicates required before a candidate is included.",
    )
    downstream_boundary: str = Field(
        description="Consumer boundary attached by Core for downstream audit and non-claims."
    )


class DpmCorePortfolioUniverseCandidateResponse(BaseModel):
    product_name: Literal["DpmPortfolioUniverseCandidate"] = Field(
        description="Core source-data product name."
    )
    product_version: Literal["v1"] = Field(description="Core source-data product version.")
    as_of_date: date = Field(description="As-of date used to resolve the candidate universe.")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant selector.")
    candidates: list[DpmCorePortfolioUniverseCandidate] = Field(
        description="Resolved DPM portfolio-universe candidates from lotus-core."
    )
    page: DpmCorePortfolioUniversePageMetadata = Field(
        description="Core pagination metadata for the candidate response."
    )
    supportability: DpmCorePortfolioUniverseCandidateSupportability = Field(
        description="Completeness and readiness posture for candidate discovery."
    )
    selection_basis: DpmCorePortfolioUniverseCandidateSelectionBasis | None = Field(
        default=None,
        description=(
            "Core-owned rule basis explaining why returned mandate bindings qualify as DPM "
            "portfolio-universe candidates."
        ),
    )
    lineage: dict[str, str] = Field(
        default_factory=dict,
        description="Core lineage metadata for audit and diagnostics.",
    )
    data_quality_status: Optional[str] = Field(default=None)
    latest_evidence_timestamp: Optional[datetime] = Field(default=None)
    source_batch_fingerprint: Optional[str] = Field(
        default=None,
        description="Core source-batch fingerprint for replay and evidence tie-out.",
    )
    snapshot_id: Optional[str] = Field(
        default=None,
        description="Core snapshot identifier for the resolved candidate page.",
    )
