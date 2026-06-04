import os

from fastapi import APIRouter, Query, Request

from src.api.services.integration_capabilities_service import build_capabilities_response
from src.api.routers.integration_capabilities_models import (
    CAPABILITIES_RESPONSE_EXAMPLES,
    ConsumerSystem,
    IntegrationCapabilitiesResponse,
)
from src.api.routers.runtime_utils import reject_unexpected_query_params
from src.core.common.capabilities import has_solver_dependencies


router = APIRouter(tags=["Integration"])


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
    return IntegrationCapabilitiesResponse.model_validate(
        build_capabilities_response(
            consumer_system=consumer_system,
            tenant_id=tenant_id,
            solver_available=has_solver_dependencies(),
            env_get=os.getenv,
        )
    )
