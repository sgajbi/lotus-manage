import os

from fastapi import APIRouter, Query, Request

from src.api.routers.integration_capabilities_builders import (
    build_capabilities_response,
    build_feature_capabilities,
    build_workflow_capabilities,
    env_bool,
    stateful_execution_publishable,
    supported_input_modes,
)
from src.api.routers.integration_capabilities_models import (
    CAPABILITIES_RESPONSE_EXAMPLES,
    ConsumerSystem,
    FeatureCapability,
    IntegrationCapabilitiesResponse,
    WorkflowCapability,
)
from src.api.routers.runtime_utils import reject_unexpected_query_params
from src.core.common.capabilities import has_solver_dependencies


router = APIRouter(tags=["Integration"])


def _env_bool(name: str, default: bool) -> bool:
    return env_bool(name, default, env_get=os.getenv)


def _supported_input_modes(
    *,
    stateful_enabled: bool,
    stateless_enabled: bool,
) -> list[str]:
    return supported_input_modes(
        stateful_enabled=stateful_enabled,
        stateless_enabled=stateless_enabled,
    )


def _stateful_execution_publishable() -> bool:
    return stateful_execution_publishable(env_get=os.getenv)


def _build_feature_capabilities(
    *,
    workflow_enabled: bool,
    stateful_enabled: bool,
    stateless_enabled: bool,
    solver_available: bool,
) -> list[FeatureCapability]:
    return build_feature_capabilities(
        workflow_enabled=workflow_enabled,
        stateful_enabled=stateful_enabled,
        stateless_enabled=stateless_enabled,
        solver_available=solver_available,
    )


def _build_workflow_capabilities(*, workflow_enabled: bool) -> list[WorkflowCapability]:
    return build_workflow_capabilities(workflow_enabled=workflow_enabled)


def _build_capabilities_response(
    *,
    consumer_system: ConsumerSystem,
    tenant_id: str,
) -> IntegrationCapabilitiesResponse:
    return build_capabilities_response(
        consumer_system=consumer_system,
        tenant_id=tenant_id,
        solver_available=has_solver_dependencies(),
        env_get=os.getenv,
    )


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
    responses={
        200: {
            "description": "Backend-governed discretionary mandate capability posture.",
            "content": {
                "application/json": {
                    "examples": CAPABILITIES_RESPONSE_EXAMPLES,
                }
            },
        },
        422: {
            "description": "Unsupported query parameters or invalid consumer values were supplied."
        },
    },
)
async def get_integration_capabilities(
    request: Request,
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
    reject_unexpected_query_params(
        request,
        allowed_params={"consumer_system", "tenant_id"},
    )
    return _build_capabilities_response(
        consumer_system=consumer_system,
        tenant_id=tenant_id,
    )
