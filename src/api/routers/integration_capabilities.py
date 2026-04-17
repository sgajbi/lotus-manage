import os
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

ConsumerSystem = Literal["lotus-gateway", "lotus-performance", "lotus-manage", "UI", "UNKNOWN"]


class FeatureCapability(BaseModel):
    key: str = Field(
        description="Canonical feature key consumed by gateway and UI orchestration.",
        examples=["dpm.execution.stateful_pas_ref"],
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
        examples=[["dpm.proposals.lifecycle"]],
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
        examples=[["pas_ref", "inline_bundle"]],
    )
    features: list[FeatureCapability] = Field(
        description="Feature-level capability flags for downstream orchestration and UI gating.",
        examples=[
            [
                {
                    "key": "dpm.execution.stateful_pas_ref",
                    "enabled": True,
                    "owner_service": "lotus-manage",
                    "description": "Stateful lotus-manage execution with lotus-core-referenced data.",
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
                    "required_features": ["dpm.proposals.lifecycle"],
                }
            ]
        ],
    )


router = APIRouter(tags=["Integration"])


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@router.get(
    "/integration/capabilities",
    response_model=IntegrationCapabilitiesResponse,
    summary="Get rebalance integration capabilities",
    description=(
        "Use this route when gateway, UI, or peer services need backend-governed rebalance feature "
        "and workflow capability posture for a resolved consumer and tenant context. This is a "
        "control-plane discovery contract, not a source-data or simulation-state read. Callers must use the "
        "canonical snake_case query parameters `consumer_system` and `tenant_id`."
    ),
)
@router.get(
    "/platform/capabilities",
    response_model=IntegrationCapabilitiesResponse,
    summary="Get rebalance platform capabilities",
    description=(
        "Alias of `/integration/capabilities` for platform-facing capability discovery. Use it when "
        "the caller needs the same backend-governed rebalance feature/workflow posture through the "
        "platform namespace. Callers must use the canonical snake_case query parameters "
        "`consumer_system` and `tenant_id`."
    ),
)
async def get_integration_capabilities(
    consumer_system: ConsumerSystem = Query(
        "lotus-gateway",
        description=(
            "Consumer system requesting capability posture. Use this to resolve the correct backend-"
            "governed rebalance feature and workflow view for the caller. Send it as the canonical snake_case "
            "query parameter `consumer_system`."
        ),
        examples=["lotus-gateway"],
    ),
    tenant_id: str = Query(
        "default",
        description=(
            "Tenant context for policy-governed capability publication. Omit to use the default "
            "tenant posture. Send it as the canonical snake_case query parameter `tenant_id`."
        ),
        examples=["default"],
    ),
) -> IntegrationCapabilitiesResponse:
    lifecycle_enabled = _env_bool("DPM_CAP_PROPOSAL_LIFECYCLE_ENABLED", True)
    inline_bundle_enabled = _env_bool("DPM_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED", True)

    supported_input_modes = ["pas_ref"]
    if inline_bundle_enabled:
        supported_input_modes.append("inline_bundle")

    return IntegrationCapabilitiesResponse(
        contract_version="v1",
        source_service=os.getenv("DPM_CAP_SOURCE_SERVICE", "lotus-manage"),
        consumer_system=consumer_system,
        tenant_id=tenant_id,
        generated_at=datetime.now(UTC),
        as_of_date=date.today(),
        policy_version=os.getenv("DPM_POLICY_VERSION", "dpm.policy.v1"),
        supported_input_modes=supported_input_modes,
        features=[
            FeatureCapability(
                key="dpm.execution.stateful_pas_ref",
                enabled=True,
                owner_service="lotus-manage",
                description="Stateful lotus-manage rebalance execution with lotus-core-referenced data.",
            ),
            FeatureCapability(
                key="dpm.execution.stateless_inline_bundle",
                enabled=inline_bundle_enabled,
                owner_service="lotus-manage",
                description="Stateless lotus-manage rebalance execution using inline request bundles.",
            ),
            FeatureCapability(
                key="dpm.proposals.lifecycle",
                enabled=lifecycle_enabled,
                owner_service="lotus-manage",
                description="lotus-manage lifecycle proposal and supportability workflows.",
            ),
        ],
        workflows=[
            WorkflowCapability(
                workflow_key="dpm_rebalance_lifecycle",
                enabled=lifecycle_enabled,
                required_features=["dpm.proposals.lifecycle"],
            ),
        ],
    )
