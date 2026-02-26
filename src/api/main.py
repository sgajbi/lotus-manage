"""FILE: src/api/main.py"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api.dependencies import get_db_session
from src.api.enterprise_readiness import (
    build_enterprise_audit_middleware,
    validate_enterprise_runtime_config,
)
from src.api.observability import correlation_id_var, setup_observability
from src.api.persistence_profile import validate_persistence_profile_guardrails
from src.api.routers.advisory_simulation import (
    build_proposal_artifact_endpoint,
    simulate_proposal,
)
from src.api.routers.advisory_simulation import (
    router as advisory_simulation_router,
)
from src.api.routers.dpm_policy_packs import router as dpm_policy_pack_router
from src.api.routers.dpm_runs import (
    get_dpm_run_support_service,
    record_dpm_run_for_support,
)
from src.api.routers.dpm_runs import (
    router as dpm_run_support_router,
)
from src.api.routers.dpm_simulation import (
    analyze_scenarios,
    analyze_scenarios_async,
    execute_dpm_async_operation,
    simulate_rebalance,
)
from src.api.routers.dpm_simulation import (
    router as dpm_simulation_router,
)
from src.api.routers.integration_capabilities import (
    router as integration_capabilities_router,
)
from src.api.routers.proposals import router as proposal_lifecycle_router
from src.api.services.advisory_simulation_service import (
    MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE,
    PROPOSAL_IDEMPOTENCY_CACHE,
    run_proposal_simulation,
)
from src.api.services.advisory_simulation_service import (
    simulate_proposal_response as _simulate_proposal_response,
)
from src.api.services.dpm_simulation_service import (
    DEFAULT_DPM_IDEMPOTENCY_CACHE_SIZE,
    DPM_IDEMPOTENCY_CACHE,
    run_simulation,
)
from src.api.services.dpm_simulation_service import (
    async_manual_execution_enabled as _async_manual_execution_enabled,
)
from src.api.services.dpm_simulation_service import (
    env_flag as _env_flag,
)
from src.api.services.dpm_simulation_service import (
    env_int as _env_int,
)
from src.api.services.dpm_simulation_service import (
    execute_batch_analysis as _execute_batch_analysis,
)
from src.api.services.dpm_simulation_service import (
    resolve_async_execution_mode as _resolve_async_execution_mode,
)
from src.api.services.dpm_simulation_service import (
    run_analyze_async_operation as _run_analyze_async_operation,
)


@asynccontextmanager
async def _app_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    validate_persistence_profile_guardrails()
    yield


app = FastAPI(
    title="Lotus Manage API",
    version="0.1.0",
    description=(
        "Deterministic rebalance simulation and discretionary lifecycle service.\n\n"
        "Domain outcomes for valid payloads are returned in response body status: "
        "`READY`, `PENDING_REVIEW`, or `BLOCKED`."
    ),
    openapi_tags=[
        {
            "name": "DPM Simulation",
            "description": "Core deterministic DPM simulation endpoints.",
        },
        {
            "name": "DPM What-If Analysis",
            "description": "Batch scenario analysis endpoints (sync and async).",
        },
        {
            "name": "DPM Run Supportability",
            "description": "Run, operation, idempotency, and artifact retrieval endpoints.",
        },
        {
            "name": "Advisory Simulation",
            "description": "Advisory proposal simulation and artifact endpoints.",
        },
        {
            "name": "Advisory Proposal Lifecycle",
            "description": "Advisory proposal persistence, workflow, and support endpoints.",
        },
    ],
    lifespan=_app_lifespan,
)

logger = logging.getLogger(__name__)
setup_observability(app)
validate_enterprise_runtime_config()
app.middleware("http")(build_enterprise_audit_middleware())

# Canonical versioned API surface only (no legacy unversioned routes).
app.include_router(proposal_lifecycle_router, prefix="/api/v1")
app.include_router(dpm_run_support_router, prefix="/api/v1")
app.include_router(dpm_policy_pack_router, prefix="/api/v1")
app.include_router(dpm_simulation_router, prefix="/api/v1")
app.include_router(advisory_simulation_router, prefix="/api/v1")
app.include_router(integration_capabilities_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health/live")
def health_live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/api/v1/health/ready")
def health_ready() -> dict[str, str]:
    return {"status": "ready"}


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
    "MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE",
    "PROPOSAL_IDEMPOTENCY_CACHE",
    "_async_manual_execution_enabled",
    "_env_flag",
    "_env_int",
    "_execute_batch_analysis",
    "_resolve_async_execution_mode",
    "_run_analyze_async_operation",
    "_simulate_proposal_response",
    "analyze_scenarios",
    "analyze_scenarios_async",
    "app",
    "build_proposal_artifact_endpoint",
    "execute_dpm_async_operation",
    "get_db_session",
    "get_dpm_run_support_service",
    "record_dpm_run_for_support",
    "run_proposal_simulation",
    "run_simulation",
    "simulate_proposal",
    "simulate_rebalance",
    "unhandled_exception_to_problem_details",
]
