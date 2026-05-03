"""FILE: src/api/main.py"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal

from fastapi import FastAPI, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.api.dependencies import get_db_session
from src.api.enterprise_readiness import (
    build_enterprise_audit_middleware,
    validate_enterprise_runtime_config,
)
from src.api.observability import correlation_id_var, setup_observability
from src.api.openapi_enrichment import enrich_openapi_schema
from src.api.persistence_profile import validate_persistence_profile_guardrails
from src.api.persistence_profile import app_persistence_profile_name
from src.api.production_cutover_contract import validate_cutover_migrations_applied
from src.api.routers.construction import router as construction_router
from src.api.routers.rebalance_policy_packs import router as rebalance_policy_pack_router
from src.api.routers.rebalance_runs import (
    get_dpm_run_support_service,
    record_dpm_run_for_support,
)
from src.api.routers.rebalance_runs import (
    router as rebalance_run_support_router,
)
from src.api.routers.rebalance_simulation import (
    analyze_scenarios,
    analyze_scenarios_async,
    execute_dpm_async_operation,
    simulate_rebalance,
)
from src.api.routers.rebalance_simulation import (
    router as rebalance_simulation_router,
)
from src.api.routers.integration_capabilities import (
    router as integration_capabilities_router,
)
from src.api.routers.mandates import router as mandates_router
from src.api.routers.monitoring import router as monitoring_router
from src.api.routers.proof_packs import router as proof_pack_router
from src.api.routers.waves import router as waves_router
from src.api.services.rebalance_simulation_service import (
    DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE,
    DPM_IDEMPOTENCY_CACHE,
    run_simulation,
)
from src.api.services.rebalance_simulation_service import (
    async_manual_execution_enabled as _async_manual_execution_enabled,
)
from src.api.services.rebalance_simulation_service import (
    env_flag as _env_flag,
)
from src.api.services.rebalance_simulation_service import (
    env_int as _env_int,
)
from src.api.services.rebalance_simulation_service import (
    execute_batch_analysis as _execute_batch_analysis,
)
from src.api.services.rebalance_simulation_service import (
    resolve_async_execution_mode as _resolve_async_execution_mode,
)
from src.api.services.rebalance_simulation_service import (
    run_analyze_async_operation as _run_analyze_async_operation,
)


class HealthStatusResponse(BaseModel):
    status: Literal["ok", "live", "ready"] = Field(
        description=(
            "Health state returned by the selected probe: ok for general service health, "
            "live for process liveness, or ready when runtime guardrails and production "
            "persistence migration checks have passed."
        ),
        examples=["ready"],
    )


_HEALTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"description": "Health probe succeeded."},
}

_READY_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"description": "Readiness probe succeeded."},
    500: {
        "description": (
            "Readiness guardrails failed, including production persistence profile or migration "
            "cutover checks."
        )
    },
}


@asynccontextmanager
async def _app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    validate_persistence_profile_guardrails()
    yield


app = FastAPI(
    title="Private Banking Rebalance API",
    version="0.1.0",
    description=(
        "Deterministic rebalance simulation and discretionary lifecycle service.\n\n"
        "Domain outcomes for valid payloads are returned in response body status: "
        "`READY`, `PENDING_REVIEW`, or `BLOCKED`."
    ),
    openapi_tags=[
        {
            "name": "lotus-manage Simulation",
            "description": "Core deterministic lotus-manage simulation endpoints.",
        },
        {
            "name": "lotus-manage What-If Analysis",
            "description": "Batch scenario analysis endpoints (sync and async).",
        },
        {
            "name": "lotus-manage Run Supportability",
            "description": "Run, operation, idempotency, and artifact retrieval endpoints.",
        },
        {
            "name": "lotus-manage Mandates",
            "description": (
                "Discretionary mandate digital twin, version history, diff, and core refresh "
                "endpoints for RFC-0038."
            ),
        },
        {
            "name": "lotus-manage Monitoring",
            "description": "Mandate health monitoring runs and exception queue endpoints.",
        },
        {
            "name": "lotus-manage Construction Alternatives",
            "description": (
                "RFC-0039 portfolio construction alternative generation, retrieval, and "
                "selection endpoints."
            ),
        },
        {
            "name": "lotus-manage Proof Packs",
            "description": "RFC-0040 pre-trade proof-pack generation and evidence endpoints.",
        },
        {
            "name": "lotus-manage Rebalance Waves",
            "description": (
                "RFC-0041 rebalance-wave preview and durable creation endpoints for explicit "
                "affected-portfolio lists."
            ),
        },
    ],
    lifespan=_app_lifespan,
)


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    app.openapi_schema = enrich_openapi_schema(schema, service_name="lotus-manage")
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]

logger = logging.getLogger(__name__)
setup_observability(app)
validate_enterprise_runtime_config()
app.middleware("http")(build_enterprise_audit_middleware())

# Canonical versioned API surface.
app.include_router(rebalance_run_support_router, prefix="/api/v1")
app.include_router(rebalance_policy_pack_router, prefix="/api/v1")
app.include_router(rebalance_simulation_router, prefix="/api/v1")
app.include_router(integration_capabilities_router, prefix="/api/v1")
app.include_router(mandates_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(construction_router, prefix="/api/v1")
app.include_router(proof_pack_router, prefix="/api/v1")
app.include_router(waves_router, prefix="/api/v1")


@app.get(
    "/health",
    response_model=HealthStatusResponse,
    summary="General lotus-manage Health",
    description=(
        "Returns a minimal service health response for lightweight operator and ingress checks. "
        "Use `/health/live` for process liveness and `/health/ready` for readiness that validates "
        "runtime guardrails."
    ),
    responses=_HEALTH_RESPONSES,
    tags=["Health"],
)
def health() -> HealthStatusResponse:
    return HealthStatusResponse(status="ok")


@app.get(
    "/health/live",
    response_model=HealthStatusResponse,
    summary="lotus-manage Liveness Probe",
    description=(
        "Returns process liveness without touching persistence dependencies. Use this endpoint "
        "for container liveness probes so transient database issues do not trigger unnecessary "
        "process restarts."
    ),
    responses=_HEALTH_RESPONSES,
    tags=["Health"],
)
def health_live() -> HealthStatusResponse:
    return HealthStatusResponse(status="live")


@app.get(
    "/health/ready",
    response_model=HealthStatusResponse,
    summary="lotus-manage Readiness Probe",
    description=(
        "Returns readiness only after runtime persistence guardrails pass. In production profile "
        "this also validates that required cutover migrations have been applied, so supportability "
        "APIs do not appear ready while their backing store is missing or unmigrated."
    ),
    responses=_READY_RESPONSES,
    tags=["Health"],
)
def health_ready() -> HealthStatusResponse:
    validate_persistence_profile_guardrails()
    if app_persistence_profile_name() == "PRODUCTION":
        validate_cutover_migrations_applied()
    return HealthStatusResponse(status="ready")


@app.exception_handler(Exception)
async def unhandled_exception_to_problem_details(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while serving request", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
            "instance": str(request.url.path),
            "correlation_id": correlation_id_var.get() or "",
        },
    )


__all__ = [
    "DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE",
    "DPM_IDEMPOTENCY_CACHE",
    "HealthStatusResponse",
    "_async_manual_execution_enabled",
    "_env_flag",
    "_env_int",
    "_execute_batch_analysis",
    "_resolve_async_execution_mode",
    "_run_analyze_async_operation",
    "analyze_scenarios",
    "analyze_scenarios_async",
    "app",
    "execute_dpm_async_operation",
    "get_db_session",
    "get_dpm_run_support_service",
    "record_dpm_run_for_support",
    "run_simulation",
    "simulate_rebalance",
    "unhandled_exception_to_problem_details",
]
