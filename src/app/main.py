import os

import httpx
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import Response as FastAPIResponse
from prometheus_fastapi_instrumentator import Instrumentator
from src.app.middleware.correlation import CorrelationIdMiddleware

SERVICE_NAME = "lotus-manage"
SERVICE_VERSION = "0.1.0"
ROUNDING_POLICY_VERSION = "v1"
UPSTREAM_BASE_URL = os.getenv("MANAGE_UPSTREAM_BASE_URL", "http://localhost:8000").rstrip("/")

app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)
app.add_middleware(CorrelationIdMiddleware, service_name=SERVICE_NAME)
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready(response: Response) -> dict[str, str]:
    if bool(getattr(app.state, "is_draining", False)):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "draining"}
    return {"status": "ready"}


@app.get("/metadata")
async def metadata() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "roundingPolicyVersion": ROUNDING_POLICY_VERSION,
    }


@app.get("/integration/capabilities")
async def integration_capabilities() -> dict:
    return {
        "sourceService": SERVICE_NAME,
        "policyVersion": "manage.v1",
        "supportedInputModes": ["api"],
        "features": [
            {"key": "manage.lifecycle.proxy", "enabled": True},
            {"key": "manage.workflow.execution", "enabled": True},
        ],
        "workflows": [
            {"workflow_key": "manage_lifecycle", "enabled": True},
        ],
    }


def _upstream_url(path: str, query: str) -> str:
    if query:
        return f"{UPSTREAM_BASE_URL}{path}?{query}"
    return f"{UPSTREAM_BASE_URL}{path}"


def _forward_headers(request: Request) -> dict[str, str]:
    forwarded: dict[str, str] = {}
    for key in ("x-correlation-id", "idempotency-key", "content-type", "accept"):
        value = request.headers.get(key)
        if value:
            forwarded[key] = value
    return forwarded


async def _proxy_request(request: Request, path: str) -> FastAPIResponse:
    body = await request.body()
    timeout_seconds = float(os.getenv("MANAGE_UPSTREAM_TIMEOUT_SECONDS", "10"))
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        upstream = await client.request(
            method=request.method,
            url=_upstream_url(path, request.url.query),
            content=body if body else None,
            headers=_forward_headers(request),
        )
    response = FastAPIResponse(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )
    corr_id = request.headers.get("x-correlation-id")
    if corr_id:
        response.headers["X-Correlation-Id"] = corr_id
    return response


@app.api_route(
    "/rebalance/{proxy_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def rebalance_proxy(proxy_path: str, request: Request) -> FastAPIResponse:
    return await _proxy_request(request, f"/rebalance/{proxy_path}")
