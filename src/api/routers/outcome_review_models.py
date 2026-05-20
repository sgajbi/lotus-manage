from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from src.api.services.outcome_review_service import DpmOutcomeDimensionConfig
from src.core.outcomes import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeClientCommunicationBoundaryEvidence,
    DpmOutcomeEvent,
    DpmOutcomeExternalExecutionBoundaryEvidence,
    DpmOutcomeReviewComparison,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    DpmPostTradeOutcomeReview,
    DpmRealizedOutcomeSnapshot,
    OutcomeComparisonDirection,
    OutcomeDimension,
)


class DpmOutcomeDimensionConfigRequest(BaseModel):
    dimension: OutcomeDimension = Field(
        description="Outcome dimension to compare.",
        examples=["DRIFT_REDUCTION"],
    )
    tolerance: DpmOutcomeTolerance = Field(description="Soft and hard tolerance for the dimension.")
    materiality: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Materiality threshold used in comparison output.",
        examples=["0.0050"],
    )
    direction: OutcomeComparisonDirection = Field(
        description="Comparison direction for the dimension.",
        examples=["LOWER_IS_BETTER"],
    )

    def to_domain(self) -> DpmOutcomeDimensionConfig:
        return DpmOutcomeDimensionConfig(
            dimension=self.dimension,
            tolerance=self.tolerance,
            materiality=self.materiality,
            direction=self.direction,
        )


class DpmOutcomeReviewPreviewRequest(BaseModel):
    expected_snapshot: DpmExpectedOutcomeSnapshot = Field(
        description="Expected snapshot assembled from pre-trade manage evidence.",
    )
    realized_snapshot: DpmRealizedOutcomeSnapshot = Field(
        description="Realized snapshot assembled from source-owner evidence.",
    )
    dimension_configs: list[DpmOutcomeDimensionConfigRequest] = Field(
        min_length=1,
        description="Dimensions to compare and their tolerance policy.",
    )


class DpmOutcomeReviewPreviewResponse(BaseModel):
    comparison: DpmOutcomeReviewComparison = Field(description="Deterministic comparison result.")


class DpmOutcomeReviewCreateRequest(DpmOutcomeReviewPreviewRequest):
    actor_id: str = Field(description="Actor creating the outcome review.", examples=["pm_001"])


class DpmOutcomeReviewCreateResponse(BaseModel):
    outcome_review: DpmPostTradeOutcomeReview = Field(description="Persisted immutable review.")


class DpmOutcomeReviewLookupResponse(BaseModel):
    outcome_review: DpmPostTradeOutcomeReview = Field(description="Persisted immutable review.")


class DpmOutcomeReviewListResponse(BaseModel):
    items: list[DpmPostTradeOutcomeReview] = Field(description="Bounded review search results.")
    total: int = Field(description="Returned item count.", examples=[1])


class DpmOutcomeReviewSupportabilityResponse(BaseModel):
    outcome_review_id: str = Field(description="Outcome review identifier.", examples=["dor_001"])
    supportability: DpmOutcomeSupportability = Field(description="Operator-safe supportability.")
    state: str = Field(description="Outcome review state.", examples=["DEGRADED"])
    reason_codes: list[str] = Field(description="Bounded supportability reason codes.")
    source_ref_count: int = Field(
        description="Count of source refs linked to the review.",
        examples=[3],
    )
    source_owners: list[str] = Field(
        description="Bounded source-owner systems represented in lineage.",
        examples=[["lotus-manage", "lotus-risk", "lotus-performance"]],
    )
    dimension_state_counts: dict[str, int] = Field(
        description="Count of compared dimensions by outcome state.",
        examples=[{"READY": 2, "DEGRADED": 1, "BLOCKED": 1}],
    )
    blocked_dimension_count: int = Field(
        description="Number of blocked dimensions.",
        examples=[1],
    )
    degraded_dimension_count: int = Field(
        description="Number of degraded dimensions.",
        examples=[1],
    )
    unsupported_dimension_count: int = Field(
        description="Number of not-supported dimensions.",
        examples=[0],
    )
    freshness_state_counts: dict[str, int] = Field(
        description="Count of source freshness states across compared dimensions.",
        examples=[{"CURRENT": 2, "STALE": 1}],
    )
    remediation_routes: list[str] = Field(
        description="Operator-safe remediation routes by source-owner family.",
        examples=[["lotus-risk:refresh-post-trade-risk-source"]],
    )
    external_execution_boundary: DpmOutcomeExternalExecutionBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-OMS boundary evidence for outcome-review supportability "
            "consumers."
        )
    )
    client_communication_boundary: DpmOutcomeClientCommunicationBoundaryEvidence = Field(
        description=(
            "Structured fail-closed no-client-communication boundary evidence for outcome-review "
            "supportability consumers."
        )
    )


class DpmOutcomeReviewRefreshSourcesRequest(BaseModel):
    actor_id: str = Field(description="Actor requesting source refresh.", examples=["pm_001"])
    realized_snapshot: DpmRealizedOutcomeSnapshot = Field(
        description=(
            "New realized source-owner snapshot to compare against the immutable expected snapshot."
        ),
    )
    dimension_configs: list[DpmOutcomeDimensionConfigRequest] = Field(
        min_length=1,
        description="Dimensions to re-evaluate and their tolerance policy.",
    )


class DpmOutcomeReviewRefreshSourcesResponse(BaseModel):
    event: DpmOutcomeEvent = Field(description="Appended source-refresh event.")
    comparison: DpmOutcomeReviewComparison = Field(
        description=(
            "Fresh expected-versus-realized comparison produced from the supplied source snapshot."
        ),
    )
