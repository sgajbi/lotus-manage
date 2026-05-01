import json
import logging
import os
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
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

ACTION_REGISTER_SUPPORTABILITY_SURFACE = "rebalance/supportability/summary"
UNKNOWN_ACTION_REGISTER_SURFACE = "unknown_surface"

_ALLOWED_ACTION_REGISTER_SURFACES = frozenset({ACTION_REGISTER_SUPPORTABILITY_SURFACE})
_ALLOWED_SUPPORTABILITY_STATES = frozenset(
    {
        "ready",
        "stale",
        "degraded",
        "empty",
        "error",
        "permission_blocked",
        "unsupported",
    }
)
_ALLOWED_SUPPORTABILITY_REASONS = frozenset(
    {
        "supportability_summary_ready",
        "supportability_summary_empty",
        "supportability_summary_stale",
        "supportability_summary_degraded",
        "supportability_summary_error",
        "permission_blocked",
        "unsupported_surface",
    }
)
_ALLOWED_FRESHNESS_BUCKETS = frozenset({"current", "same_day", "stale", "unknown"})
_SENSITIVE_LOG_FIELD_NAMES = frozenset(
    {
        "account_id",
        "actor_id",
        "client_id",
        "correlation_id",
        "idempotency_key",
        "instrument_id",
        "portfolio_id",
        "request_hash",
        "run_id",
    }
)
_LATENCY_BUCKETS_MS = (10, 50, 100, 250, 500, 1000)


def _safe_metric_label(value: str, *, allowed_values: frozenset[str], fallback: str) -> str:
    candidate = value.strip()
    if candidate in allowed_values:
        return candidate
    return fallback


def _latency_bucket_ms(latency_ms: float) -> str:
    for upper_bound in _LATENCY_BUCKETS_MS:
        if latency_ms <= upper_bound:
            return f"le_{upper_bound}"
    return "gt_1000"


def _status_family(status_code: int) -> str:
    if 100 <= status_code <= 599:
        return f"{status_code // 100}xx"
    return "unknown"


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path if isinstance(route_path, str) and route_path else "unmatched"


def _safe_log_extra_fields(extra_fields: dict[str, Any]) -> dict[str, Any]:
    safe_fields: dict[str, Any] = {}
    for key, raw_value in extra_fields.items():
        if key in _SENSITIVE_LOG_FIELD_NAMES:
            safe_fields[key] = "[REDACTED]"
            continue
        safe_fields[key] = raw_value
    return safe_fields


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
            payload.update(_safe_log_extra_fields(record.extra_fields))
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
            response = await call_next(request)
        except Exception:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request.completed",
                extra={
                    "extra_fields": {
                        "http_method": request.method,
                        "endpoint": _route_template(request),
                        "status_code": 500,
                        "status_family": "5xx",
                        "latency_bucket_ms": _latency_bucket_ms(latency_ms),
                    }
                },
            )
            correlation_id_var.reset(correlation_token)
            request_id_var.reset(request_token)
            trace_id_var.reset(trace_token)
            raise

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "request.completed",
            extra={
                "extra_fields": {
                    "http_method": request.method,
                    "endpoint": _route_template(request),
                    "status_code": response.status_code,
                    "status_family": _status_family(response.status_code),
                    "latency_bucket_ms": _latency_bucket_ms(latency_ms),
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
        surface=_safe_metric_label(
            surface,
            allowed_values=_ALLOWED_ACTION_REGISTER_SURFACES,
            fallback=UNKNOWN_ACTION_REGISTER_SURFACE,
        ),
        supportability_state=_safe_metric_label(
            supportability_state,
            allowed_values=_ALLOWED_SUPPORTABILITY_STATES,
            fallback="error",
        ),
        reason=_safe_metric_label(
            reason,
            allowed_values=_ALLOWED_SUPPORTABILITY_REASONS,
            fallback="supportability_summary_error",
        ),
        freshness_bucket=_safe_metric_label(
            freshness_bucket,
            allowed_values=_ALLOWED_FRESHNESS_BUCKETS,
            fallback="unknown",
        ),
    ).inc()
