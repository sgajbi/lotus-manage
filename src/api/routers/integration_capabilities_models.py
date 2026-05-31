from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ConsumerSystem = Literal["lotus-gateway", "lotus-performance", "lotus-manage", "UI", "UNKNOWN"]


CAPABILITIES_RESPONSE_EXAMPLES = {
    "default": {
        "summary": "Default discretionary mandate capability posture",
        "description": (
            "Default posture for lotus-manage before stateful portfolio-id execution and "
            "workflow gates are explicitly enabled."
        ),
        "value": {
            "contract_version": "v1",
            "source_service": "lotus-manage",
            "consumer_system": "lotus-gateway",
            "tenant_id": "default",
            "generated_at": "2026-02-24T12:00:00Z",
            "as_of_date": "2026-02-24",
            "policy_version": "dpm.policy.v1",
            "supported_input_modes": ["stateless"],
            "features": [
                {
                    "key": "dpm.execution.stateful_portfolio_id",
                    "enabled": False,
                    "owner_service": "lotus-manage",
                    "description": (
                        "Stateful lotus-manage rebalance execution using a governed "
                        "portfolio identifier; enable only when a governed lotus-core "
                        "resolver is configured."
                    ),
                },
                {
                    "key": "dpm.execution.stateless",
                    "enabled": True,
                    "owner_service": "lotus-manage",
                    "description": (
                        "Stateless lotus-manage rebalance execution using explicit request bundles."
                    ),
                },
                {
                    "key": "dpm.workflow.review_gate",
                    "enabled": False,
                    "owner_service": "lotus-manage",
                    "description": (
                        "Discretionary mandate run review gates for approve, reject, and "
                        "request-changes decisions."
                    ),
                },
                {
                    "key": "dpm.execution.solver_target_generation",
                    "enabled": True,
                    "owner_service": "lotus-manage",
                    "description": (
                        "Optional solver-backed target generation for discretionary mandate "
                        "rebalance requests when solver dependencies are installed."
                    ),
                },
                {
                    "key": "manage.observability.action_register_supportability",
                    "enabled": True,
                    "owner_service": "lotus-manage",
                    "description": (
                        "Source-backed action register and supportability summary posture "
                        "with bounded states, reasons, and metrics."
                    ),
                },
            ],
            "workflows": [
                {
                    "workflow_key": "dpm_rebalance_lifecycle",
                    "enabled": False,
                    "required_features": ["dpm.workflow.review_gate"],
                }
            ],
        },
    }
}


class FeatureCapability(BaseModel):
    key: str = Field(
        description="Canonical feature key consumed by gateway and UI orchestration.",
        examples=["dpm.execution.stateful_portfolio_id"],
    )
    enabled: bool = Field(
        description="Whether this feature is currently enabled for the resolved policy context.",
        examples=[True],
    )
    owner_service: str = Field(
        description="Owning service that governs the feature flag and workflow semantics.",
        examples=["lotus-manage"],
    )
    description: str = Field(
        description="Human-readable summary of what the feature enables and when to use it.",
        examples=["Stateful lotus-manage execution with lotus-core-referenced data."],
    )


class WorkflowCapability(BaseModel):
    workflow_key: str = Field(
        description="Canonical workflow key used by downstream orchestration surfaces.",
        examples=["dpm_rebalance_lifecycle"],
    )
    enabled: bool = Field(
        description="Whether the workflow is currently enabled for the resolved policy context.",
        examples=[True],
    )
    required_features: list[str] = Field(
        default_factory=list,
        description="Feature keys that must be enabled before this workflow should be surfaced.",
        examples=[["dpm.workflow.review_gate"]],
    )


class IntegrationCapabilitiesResponse(BaseModel):
    contract_version: str = Field(
        description="Version of the published integration-capabilities contract.",
        examples=["v1"],
    )
    source_service: str = Field(
        description="Service that owns and generated this capabilities response.",
        examples=["lotus-manage"],
    )
    consumer_system: ConsumerSystem = Field(
        description="Resolved downstream consumer system for which capability posture was requested.",
        examples=["lotus-gateway"],
    )
    tenant_id: str = Field(
        description="Resolved tenant context used to shape policy-governed capability publication.",
        examples=["default"],
    )
    generated_at: datetime = Field(
        description="UTC timestamp when this capability payload was generated.",
        examples=["2026-02-24T12:00:00Z"],
    )
    as_of_date: date = Field(
        description="Governing business date for the capability posture publication.",
        examples=["2026-02-24"],
    )
    policy_version: str = Field(
        description="Policy version that governed the resolved capability posture.",
        examples=["dpm.policy.v1"],
    )
    supported_input_modes: list[str] = Field(
        description="Supported execution input modes that downstream callers may use for rebalance flows.",
        examples=[["stateless"]],
    )
    features: list[FeatureCapability] = Field(
        description="Feature-level capability flags for downstream orchestration and UI gating.",
        examples=[
            [
                {
                    "key": "dpm.execution.stateful_portfolio_id",
                    "enabled": False,
                    "owner_service": "lotus-manage",
                    "description": "Stateful lotus-manage execution using a governed portfolio identifier; disabled unless a governed lotus-core resolver is configured.",
                }
            ]
        ],
    )
    workflows: list[WorkflowCapability] = Field(
        description="Workflow-level capability flags and their required feature dependencies.",
        examples=[
            [
                {
                    "workflow_key": "dpm_rebalance_lifecycle",
                    "enabled": True,
                    "required_features": ["dpm.workflow.review_gate"],
                }
            ]
        ],
    )
