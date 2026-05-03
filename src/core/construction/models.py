"""Domain models for RFC-0039 construction alternatives."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.core.construction.vocabulary import (
    ConstructionMethod,
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
)
from src.core.models import Money


class ConstructionObjectiveTerm(BaseModel):
    term: ConstructionTraceTerm = Field(description="Bounded objective term identifier.")
    value: Decimal = Field(description="Objective value as a deterministic decimal.")
    unit: str = Field(description="Measurement unit for the value.")
    direction: str = Field(description="Whether lower, higher, or target-matching is preferred.")
    description: str = Field(description="Business explanation of the objective term.")


class ConstructionConstraintTrace(BaseModel):
    constraint: ConstructionTraceTerm = Field(description="Bounded constraint identifier.")
    status: ConstructionMethodStatus = Field(description="Constraint-level supportability status.")
    source_family: ConstructionSourceFamily = Field(
        description="Source family that owns or supports the constraint."
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Bounded reason codes explaining constraint handling.",
    )
    description: str = Field(description="Business explanation of the constraint.")


class ConstructionComparisonMetrics(BaseModel):
    drift_before: Decimal = Field(description="Absolute active-weight drift before construction.")
    drift_after: Decimal = Field(description="Absolute active-weight drift after construction.")
    drift_reduction: Decimal = Field(description="Drift_before minus drift_after.")
    turnover_weight: Decimal = Field(description="Security-trade turnover as weight of portfolio.")
    trade_count: int = Field(description="Number of security trade intents.")
    estimated_transaction_cost: Money | None = Field(
        default=None,
        description="Estimated local construction cost when available.",
    )


class ConstructionAlternative(BaseModel):
    alternative_id: str = Field(description="Stable identifier within the alternative set.")
    method: ConstructionMethod = Field(description="Construction method used for this alternative.")
    method_status: ConstructionMethodStatus = Field(
        description="Method-level readiness and supportability posture."
    )
    summary: str = Field(description="Short business summary for the portfolio manager.")
    rebalance_run_id: str | None = Field(
        default=None,
        description="Source rebalance run id when this alternative wraps a simulation result.",
    )
    objective_trace: list[ConstructionObjectiveTerm] = Field(
        description="Bounded objective terms used for comparison."
    )
    constraint_trace: list[ConstructionConstraintTrace] = Field(
        description="Bounded constraints and supportability posture."
    )
    comparison_metrics: ConstructionComparisonMetrics = Field(
        description="Normalized metrics comparable across alternatives."
    )
    intent_ids: list[str] = Field(
        default_factory=list,
        description="Trade/FX intent identifiers referenced by this alternative.",
    )
    diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        description="Bounded diagnostic summary, not raw request or source payloads.",
    )


class ConstructionAlternativeSet(BaseModel):
    alternative_set_id: str = Field(description="Stable construction alternative set identifier.")
    portfolio_id: str = Field(description="Portfolio for which alternatives were generated.")
    as_of: str = Field(description="Business as-of date or timestamp used for construction.")
    status: ConstructionMethodStatus = Field(description="Aggregate alternative set status.")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the alternative set was generated.",
    )
    alternatives: list[ConstructionAlternative] = Field(
        description="Comparable construction alternatives."
    )
