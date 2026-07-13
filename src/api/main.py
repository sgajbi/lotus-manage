"""FILE: src/api/main.py"""

import logging
import os
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
from src.api.response_headers import apply_observability_headers
from src.api.routers.construction import router as construction_router
from src.api.routers.rebalance_policy_packs import router as rebalance_policy_pack_router
from src.api.routers.rebalance_runs import (
    router as rebalance_run_support_router,
)
from src.api.services.rebalance_run_support_service import (
    get_dpm_run_support_service,
    record_dpm_run_for_support,
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
from src.api.routers.portfolio_memory import router as portfolio_memory_router
from src.api.routers.pm_operating_quality import router as pm_operating_quality_router
from src.api.routers.pm_operating_quality_http import (
    PmQualityProblemDetailsException,
    pm_quality_problem_details_exception_handler,
)
from src.api.routers.proof_packs import router as proof_pack_router
from src.api.routers.outcome_reviews import (
    router as outcome_reviews_router,
    run_lookup_router as outcome_review_run_lookup_router,
    wave_lookup_router as outcome_review_wave_lookup_router,
)
from src.api.routers.waves import router as waves_router
from src.api.services.rebalance_simulation_service import (
    execute_batch_analysis as _execute_batch_analysis,
)
from src.core.rebalance.engine import run_simulation
from src.infrastructure.source_http_clients import close_shared_source_http_clients


class HealthStatusResponse(BaseModel):
    status: Literal["ok", "live", "ready"] = Field(
        description=(
            "Health state returned by the selected probe: ok for general service health, "
            "live for process liveness, or ready when runtime guardrails and production "
            "persistence migration checks have passed."
        ),
        examples=["ready"],
    )


class VersionMetadataResponse(BaseModel):
    service_name: str = Field(description="Lotus service name.", examples=["lotus-manage"])
    version: str = Field(description="Application version exposed by FastAPI metadata.")
    git_commit_sha: str = Field(description="Git commit SHA used to build the image.")
    git_branch: str = Field(description="Git branch or ref used to build the image.")
    build_timestamp: str = Field(description="UTC image build timestamp.")
    repo_url: str = Field(description="Source repository URL used for the image build.")
    image_digest: str = Field(description="OCI image digest or local image id when not pushed.")
    ci_pipeline_id: str = Field(description="CI pipeline or run identifier for the image build.")


_HEALTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"description": "Health probe succeeded."},
    503: {
        "description": (
            "Health probe cannot run because a required dependency is unavailable or the "
            "service is not accepting traffic."
        )
    },
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
    try:
        yield
    finally:
        close_shared_source_http_clients()


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
        {
            "name": "lotus-manage Outcome Reviews",
            "description": (
                "RFC-0042 post-trade expected-versus-realized outcome-review endpoints."
            ),
        },
        {
            "name": "lotus-manage PM Operating Quality",
            "description": (
                "RFC42-WTBD-008 configurable PM operating quality score-run lifecycle endpoints."
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
app.include_router(outcome_reviews_router, prefix="/api/v1")
app.include_router(outcome_review_run_lookup_router, prefix="/api/v1")
app.include_router(outcome_review_wave_lookup_router, prefix="/api/v1")
app.include_router(portfolio_memory_router, prefix="/api/v1")
app.include_router(pm_operating_quality_router, prefix="/api/v1")


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
    "/version",
    response_model=VersionMetadataResponse,
    summary="lotus-manage Version Metadata",
    description=(
        "Returns the same release metadata expected on OCI image labels and release manifests: "
        "Git commit, branch, build timestamp, repository URL, image digest, CI run id, and app "
        "version."
    ),
    tags=["Health"],
)
def version_metadata() -> VersionMetadataResponse:
    return VersionMetadataResponse(
        service_name="lotus-manage",
        version=app.version,
        git_commit_sha=os.getenv("LOTUS_IMAGE_GIT_SHA", "unknown"),
        git_branch=os.getenv("LOTUS_IMAGE_GIT_BRANCH", "unknown"),
        build_timestamp=os.getenv("LOTUS_IMAGE_BUILD_TIMESTAMP", "unknown"),
        repo_url=os.getenv("LOTUS_IMAGE_REPO_URL", "unknown"),
        image_digest=os.getenv("LOTUS_IMAGE_DIGEST", "unknown"),
        ci_pipeline_id=os.getenv("LOTUS_IMAGE_CI_PIPELINE_ID", "local"),
    )


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


app.add_exception_handler(
    PmQualityProblemDetailsException,
    pm_quality_problem_details_exception_handler,
)


@app.exception_handler(Exception)
async def unhandled_exception_to_problem_details(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while serving request", exc_info=exc)
    response = JSONResponse(
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
    apply_observability_headers(response)
    return response


__all__ = [
    "HealthStatusResponse",
    "_execute_batch_analysis",
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
