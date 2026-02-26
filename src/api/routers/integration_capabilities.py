import os
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

ConsumerSystem = Literal["lotus-gateway", "lotus-performance", "lotus-manage", "UI", "UNKNOWN"]


class FeatureCapability(BaseModel):
    key: str = Field(description="Canonical feature key.")
    enabled: bool = Field(description="Whether this feature is enabled.")
    owner_service: str = Field(description="Owning service for this feature.")
    description: str = Field(description="Human-readable capability summary.")


class WorkflowCapability(BaseModel):
    workflow_key: str = Field(description="Workflow key for feature orchestration.")
    enabled: bool = Field(description="Whether workflow is enabled.")
    required_features: list[str] = Field(default_factory=list)


class IntegrationCapabilitiesResponse(BaseModel):
    contract_version: str = Field(alias="contractVersion")
    source_service: str = Field(alias="sourceService")
    consumer_system: ConsumerSystem = Field(alias="consumerSystem")
    tenant_id: str = Field(alias="tenantId")
    generated_at: datetime = Field(alias="generatedAt")
    as_of_date: date = Field(alias="asOfDate")
    policy_version: str = Field(alias="policyVersion")
    supported_input_modes: list[str] = Field(alias="supportedInputModes")
    features: list[FeatureCapability]
    workflows: list[WorkflowCapability]

    model_config = {"populate_by_name": True}


router = APIRouter(tags=["Integration"])


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@router.get("/integration/capabilities", response_model=IntegrationCapabilitiesResponse)
@router.get("/platform/capabilities", response_model=IntegrationCapabilitiesResponse)
async def get_integration_capabilities(
    consumer_system: ConsumerSystem = Query("lotus-gateway", alias="consumerSystem"),
    tenant_id: str = Query("default", alias="tenantId"),
) -> IntegrationCapabilitiesResponse:
    lifecycle_enabled = _env_bool("DPM_CAP_PROPOSAL_LIFECYCLE_ENABLED", True)
    inline_bundle_enabled = _env_bool("DPM_CAP_INPUT_MODE_INLINE_BUNDLE_ENABLED", True)

    supported_input_modes = ["pas_ref"]
    if inline_bundle_enabled:
        supported_input_modes.append("inline_bundle")

    return IntegrationCapabilitiesResponse(
        contractVersion="v1",
        sourceService=os.getenv("DPM_CAP_SOURCE_SERVICE", "lotus-manage"),
        consumerSystem=consumer_system,
        tenantId=tenant_id,
        generatedAt=datetime.now(UTC),
        asOfDate=date.today(),
        policyVersion=os.getenv("DPM_POLICY_VERSION", "dpm.policy.v1"),
        supportedInputModes=supported_input_modes,
        features=[
            FeatureCapability(
                key="dpm.execution.stateful_pas_ref",
                enabled=True,
                owner_service="lotus-manage",
                description="Stateful lotus-manage execution with lotus-core-referenced data.",
            ),
            FeatureCapability(
                key="dpm.execution.stateless_inline_bundle",
                enabled=inline_bundle_enabled,
                owner_service="lotus-manage",
                description="Stateless lotus-manage execution using inline request bundles.",
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
