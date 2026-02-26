import os
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

ConsumerSystem = Literal["BFF", "PA", "DPM", "UI", "UNKNOWN"]


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


@router.get("/platform/capabilities", response_model=IntegrationCapabilitiesResponse)
async def get_integration_capabilities(
    consumer_system: ConsumerSystem = Query("BFF", alias="consumerSystem"),
    tenant_id: str = Query("default", alias="tenantId"),
) -> IntegrationCapabilitiesResponse:
    lifecycle_enabled = _env_bool("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", True)
    async_enabled = _env_bool("PROPOSAL_ASYNC_OPERATIONS_ENABLED", True)

    return IntegrationCapabilitiesResponse(
        contractVersion="v1",
        sourceService="lotus-manage",
        consumerSystem=consumer_system,
        tenantId=tenant_id,
        generatedAt=datetime.now(UTC),
        asOfDate=date.today(),
        policyVersion="advisory.v1",
        supportedInputModes=["advisor_input"],
        features=[
            FeatureCapability(
                key="advisory.proposals.lifecycle",
                enabled=lifecycle_enabled,
                owner_service="ADVISORY",
                description="Advisory proposal lifecycle APIs.",
            ),
            FeatureCapability(
                key="advisory.proposals.async_operations",
                enabled=async_enabled,
                owner_service="ADVISORY",
                description="Async advisory proposal operations.",
            ),
        ],
        workflows=[
            WorkflowCapability(
                workflow_key="advisory_proposal_lifecycle",
                enabled=lifecycle_enabled,
                required_features=["advisory.proposals.lifecycle"],
            ),
        ],
    )

