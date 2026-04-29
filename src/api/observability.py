import json
import logging
import os
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

MANAGE_SUPPORTABILITY_TOTAL = Counter(
    "lotus_manage_action_register_supportability_total",
    "lotus-manage action register supportability outcomes.",
    ["surface", "supportability_state", "reason", "freshness_bucket"],
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": os.getenv("SERVICE_NAME", "lotus-manage"),
            "environment": os.getenv("ENVIRONMENT", "local"),
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get() or None,
            "request_id": request_id_var.get() or None,
            "trace_id": trace_id_var.get() or None,
        }
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            payload.update(record.extra_fields)
        return json.dumps({k: v for k, v in payload.items() if v is not None})


def setup_observability(app: FastAPI) -> None:
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    Instrumentator().instrument(app).expose(app)

    @app.middleware("http")
    async def _request_observability_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        logger = logging.getLogger("http.access")
        started = time.perf_counter()

        correlation_id = request.headers.get("X-Correlation-Id") or f"corr_{uuid4().hex[:12]}"
        request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex[:12]}"
        traceparent = request.headers.get("traceparent", "")
        trace_id = uuid4().hex
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4 and len(parts[1]) == 32:
                trace_id = parts[1]

        correlation_token = correlation_id_var.set(correlation_id)
        request_token = request_id_var.set(request_id)
        trace_token = trace_id_var.set(trace_id)
        try:
            response: Response = await call_next(request)
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request.completed",
                extra={
                    "extra_fields": {
                        "http_method": request.method,
                        "endpoint": request.url.path,
                        "latency_ms": latency_ms,
                    }
                },
            )
            correlation_id_var.reset(correlation_token)
            request_id_var.reset(request_token)
            trace_id_var.reset(trace_token)

        response_correlation_id = response.headers.get("X-Correlation-Id", correlation_id)
        response.headers["X-Correlation-Id"] = response_correlation_id
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Trace-Id"] = trace_id
        response.headers["traceparent"] = f"00-{trace_id}-0000000000000001-01"
        return response


def record_action_register_supportability(
    *,
    surface: str,
    supportability_state: str,
    reason: str,
    freshness_bucket: str,
) -> None:
    MANAGE_SUPPORTABILITY_TOTAL.labels(
        surface=surface,
        supportability_state=supportability_state,
        reason=reason,
        freshness_bucket=freshness_bucket,
    ).inc()
