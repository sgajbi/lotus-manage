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
DPM_CORE_RESOLVER_TOTAL = Counter(
    "lotus_manage_core_resolver_total",
    "lotus-manage stateful core resolver call outcomes.",
    ["operation", "outcome", "supportability_state", "reason"],
)
DPM_EXECUTION_TOTAL = Counter(
    "lotus_manage_execution_total",
    "lotus-manage DPM execution request outcomes.",
    ["operation", "input_mode", "outcome", "result_status"],
)
DPM_ASYNC_OPERATION_TOTAL = Counter(
    "lotus_manage_async_operation_total",
    "lotus-manage asynchronous operation lifecycle outcomes.",
    ["event", "execution_mode", "outcome"],
)
DPM_POLICY_PACK_RESOLUTION_TOTAL = Counter(
    "lotus_manage_policy_pack_resolution_total",
    "lotus-manage policy-pack resolution outcomes.",
    ["surface", "enabled", "source", "selected"],
)
DPM_WORKFLOW_DECISION_TOTAL = Counter(
    "lotus_manage_workflow_decision_total",
    "lotus-manage workflow decision outcomes.",
    ["surface", "action", "outcome"],
)

ACTION_REGISTER_SUPPORTABILITY_SURFACE = "rebalance/supportability/summary"
UNKNOWN_ACTION_REGISTER_SURFACE = "unknown_surface"
DPM_CORE_RESOLVER_OPERATION = "dpm_execution_context"

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
_ALLOWED_CORE_RESOLVER_OPERATIONS = frozenset({DPM_CORE_RESOLVER_OPERATION})
_ALLOWED_CORE_RESOLVER_OUTCOMES = frozenset({"success", "unavailable", "incomplete", "error"})
_ALLOWED_CORE_SUPPORTABILITY_STATES = frozenset(
    {"ready", "degraded", "incomplete", "unavailable", "unknown"}
)
_ALLOWED_CORE_RESOLVER_REASONS = frozenset(
    {
        "ready",
        "degraded",
        "resolver_unavailable",
        "context_incomplete",
        "invalid_response",
        "unexpected_error",
    }
)
_ALLOWED_EXECUTION_OPERATIONS = frozenset({"simulate", "analyze", "analyze_async"})
_ALLOWED_INPUT_MODES = frozenset({"stateless", "stateful", "unknown"})
_ALLOWED_EXECUTION_OUTCOMES = frozenset(
    {"success", "partial_failure", "blocked", "replayed", "accepted", "conflict", "error"}
)
_ALLOWED_EXECUTION_RESULT_STATUSES = frozenset(
    {"ready", "pending_review", "blocked", "accepted", "partial_success", "failed", "unknown"}
)
_ALLOWED_ASYNC_EVENTS = frozenset({"submit", "execute"})
_ALLOWED_ASYNC_EXECUTION_MODES = frozenset({"inline", "accept_only", "manual", "unknown"})
_ALLOWED_ASYNC_OUTCOMES = frozenset(
    {"accepted", "succeeded", "failed", "conflict", "not_found", "not_executable", "disabled"}
)
_ALLOWED_POLICY_PACK_SURFACES = frozenset({"simulate", "analyze", "analyze_async", "api"})
_ALLOWED_POLICY_PACK_ENABLED = frozenset({"true", "false"})
_ALLOWED_POLICY_PACK_SOURCES = frozenset(
    {"disabled", "request", "tenant_default", "global_default", "none", "unknown"}
)
_ALLOWED_POLICY_PACK_SELECTED = frozenset({"true", "false"})
_ALLOWED_WORKFLOW_SURFACES = frozenset({"run", "trace", "retry"})
_ALLOWED_WORKFLOW_ACTIONS = frozenset({"approve", "reject", "request_changes", "unknown"})
_ALLOWED_WORKFLOW_OUTCOMES = frozenset({"success", "not_found", "disabled", "conflict", "error"})
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


def record_core_resolver_call(
    *,
    operation: str,
    outcome: str,
    supportability_state: str,
    reason: str,
) -> None:
    DPM_CORE_RESOLVER_TOTAL.labels(
        operation=_safe_metric_label(
            operation,
            allowed_values=_ALLOWED_CORE_RESOLVER_OPERATIONS,
            fallback=DPM_CORE_RESOLVER_OPERATION,
        ),
        outcome=_safe_metric_label(
            outcome,
            allowed_values=_ALLOWED_CORE_RESOLVER_OUTCOMES,
            fallback="error",
        ),
        supportability_state=_safe_metric_label(
            supportability_state,
            allowed_values=_ALLOWED_CORE_SUPPORTABILITY_STATES,
            fallback="unknown",
        ),
        reason=_safe_metric_label(
            reason,
            allowed_values=_ALLOWED_CORE_RESOLVER_REASONS,
            fallback="unexpected_error",
        ),
    ).inc()


def record_execution_call(
    *,
    operation: str,
    input_mode: str,
    outcome: str,
    result_status: str,
) -> None:
    DPM_EXECUTION_TOTAL.labels(
        operation=_safe_metric_label(
            operation,
            allowed_values=_ALLOWED_EXECUTION_OPERATIONS,
            fallback="simulate",
        ),
        input_mode=_safe_metric_label(
            input_mode,
            allowed_values=_ALLOWED_INPUT_MODES,
            fallback="unknown",
        ),
        outcome=_safe_metric_label(
            outcome,
            allowed_values=_ALLOWED_EXECUTION_OUTCOMES,
            fallback="error",
        ),
        result_status=_safe_metric_label(
            result_status,
            allowed_values=_ALLOWED_EXECUTION_RESULT_STATUSES,
            fallback="unknown",
        ),
    ).inc()


def record_async_operation(
    *,
    event: str,
    execution_mode: str,
    outcome: str,
) -> None:
    DPM_ASYNC_OPERATION_TOTAL.labels(
        event=_safe_metric_label(
            event,
            allowed_values=_ALLOWED_ASYNC_EVENTS,
            fallback="submit",
        ),
        execution_mode=_safe_metric_label(
            execution_mode,
            allowed_values=_ALLOWED_ASYNC_EXECUTION_MODES,
            fallback="unknown",
        ),
        outcome=_safe_metric_label(
            outcome,
            allowed_values=_ALLOWED_ASYNC_OUTCOMES,
            fallback="failed",
        ),
    ).inc()


def record_policy_pack_resolution(
    *,
    surface: str,
    enabled: str,
    source: str,
    selected: str,
) -> None:
    DPM_POLICY_PACK_RESOLUTION_TOTAL.labels(
        surface=_safe_metric_label(
            surface,
            allowed_values=_ALLOWED_POLICY_PACK_SURFACES,
            fallback="api",
        ),
        enabled=_safe_metric_label(
            enabled,
            allowed_values=_ALLOWED_POLICY_PACK_ENABLED,
            fallback="false",
        ),
        source=_safe_metric_label(
            source,
            allowed_values=_ALLOWED_POLICY_PACK_SOURCES,
            fallback="unknown",
        ),
        selected=_safe_metric_label(
            selected,
            allowed_values=_ALLOWED_POLICY_PACK_SELECTED,
            fallback="false",
        ),
    ).inc()


def record_workflow_decision(
    *,
    surface: str,
    action: str,
    outcome: str,
) -> None:
    DPM_WORKFLOW_DECISION_TOTAL.labels(
        surface=_safe_metric_label(
            surface,
            allowed_values=_ALLOWED_WORKFLOW_SURFACES,
            fallback="run",
        ),
        action=_safe_metric_label(
            action,
            allowed_values=_ALLOWED_WORKFLOW_ACTIONS,
            fallback="unknown",
        ),
        outcome=_safe_metric_label(
            outcome,
            allowed_values=_ALLOWED_WORKFLOW_OUTCOMES,
            fallback="error",
        ),
    ).inc()
