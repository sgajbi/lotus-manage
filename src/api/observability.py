import json
import logging
import os
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from src.api.response_headers import apply_observability_headers

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
POSTGRES_ACCESS_TOTAL = Counter(
    "lotus_manage_postgres_access_total",
    "lotus-manage bounded Postgres access outcomes.",
    ["operation", "outcome", "reason", "classification"],
)
PM_QUALITY_LIFECYCLE_TOTAL = Counter(
    "lotus_manage_pm_quality_lifecycle_total",
    "lotus-manage PM operating-quality route-family lifecycle outcomes.",
    ["surface", "outcome", "reason"],
)
DPM_WORKFLOW_DECISION_TOTAL = Counter(
    "lotus_manage_workflow_decision_total",
    "lotus-manage workflow decision outcomes.",
    ["surface", "action", "outcome"],
)
CAMPAIGN_WORKFLOW_TOTAL = Counter(
    "lotus_manage_campaign_workflow_total",
    "lotus-manage campaign workflow mutation, readiness, launch, and audit outcomes.",
    ["surface", "outcome", "reason"],
)
WAVE_SUPPORTABILITY_TOTAL = Counter(
    "lotus_manage_wave_supportability_total",
    "lotus-manage rebalance wave supportability endpoint outcomes.",
    ["surface", "supportability_state", "reason"],
)
OUTCOME_REVIEW_SUPPORTABILITY_TOTAL = Counter(
    "lotus_manage_outcome_review_supportability_total",
    "lotus-manage outcome review API and supportability outcomes.",
    ["surface", "supportability_state", "reason"],
)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests",
    "HTTP requests processed by lotus-manage.",
    ["method", "endpoint", "status_family"],
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
_ALLOWED_POSTGRES_ACCESS_OPERATIONS = frozenset({"connect"})
_ALLOWED_POSTGRES_ACCESS_OUTCOMES = frozenset({"success", "failure"})
_ALLOWED_POSTGRES_ACCESS_REASONS = frozenset(
    {"connected", "acquire_timeout", "connection_unavailable"}
)
_ALLOWED_POSTGRES_ACCESS_CLASSIFICATIONS = frozenset(
    {"none", "transient", "permanent", "unknown"}
)
_ALLOWED_PM_QUALITY_SURFACES = frozenset(
    {
        "policy",
        "score_run",
        "fairness_analysis",
        "review_action",
        "summary_invocation",
        "unknown",
    }
)
_ALLOWED_PM_QUALITY_OUTCOMES = frozenset(
    {
        "success",
        "forbidden",
        "not_found",
        "conflict",
        "validation_failed",
        "dependency_failed",
        "unavailable",
        "error",
    }
)
_ALLOWED_PM_QUALITY_REASONS = frozenset(
    {
        "success",
        "forbidden",
        "not_found",
        "immutable_conflict",
        "validation_error",
        "dependency_incomplete",
        "dependency_unavailable",
        "unexpected_error",
    }
)
_ALLOWED_WORKFLOW_SURFACES = frozenset({"run", "trace", "retry"})
_ALLOWED_WORKFLOW_ACTIONS = frozenset({"approve", "reject", "request_changes", "unknown"})
_ALLOWED_WORKFLOW_OUTCOMES = frozenset({"success", "not_found", "disabled", "conflict", "error"})
_ALLOWED_CAMPAIGN_WORKFLOW_SURFACES = frozenset(
    {
        "approval_decision",
        "assignment_action",
        "assignment_task_open",
        "assignment_task_transition",
        "maker_checker_control",
        "preview_readiness",
        "launch_package",
        "launch",
        "launch_history",
        "unknown",
    }
)
_ALLOWED_CAMPAIGN_WORKFLOW_OUTCOMES = frozenset(
    {
        "success",
        "replay",
        "conflict",
        "validation_failed",
        "entitlement_failed",
        "not_found",
        "blocked",
        "error",
    }
)
_ALLOWED_CAMPAIGN_WORKFLOW_REASONS = frozenset(
    {
        "success",
        "replay",
        "definition_conflict",
        "reference_conflict",
        "validation_error",
        "entitlement_required",
        "entitlement_denied",
        "definition_not_found",
        "task_not_found",
        "launch_blocked",
        "wave_validation_error",
        "unexpected_error",
    }
)
_ALLOWED_WAVE_SUPPORTABILITY_SURFACES = frozenset({"rebalance/waves/supportability"})
_ALLOWED_WAVE_SUPPORTABILITY_STATES = frozenset({"ready", "degraded", "blocked", "not_found"})
_ALLOWED_WAVE_SUPPORTABILITY_REASONS = frozenset(
    {
        "wave_supportability_ready",
        "wave_degraded_items",
        "wave_blocked_items",
        "wave_not_found",
        "wave_supportability_error",
    }
)
_ALLOWED_OUTCOME_REVIEW_SURFACES = frozenset(
    {
        "rebalance/outcome-reviews/create",
        "rebalance/outcome-reviews/refresh-sources",
        "rebalance/outcome-reviews/supportability",
    }
)
_ALLOWED_OUTCOME_REVIEW_STATES = frozenset(
    {
        "ready",
        "pending_review",
        "breached",
        "degraded",
        "blocked",
        "not_supported",
        "not_found",
        "error",
    }
)
_ALLOWED_OUTCOME_REVIEW_REASONS = frozenset(
    {
        "outcome_review_ready",
        "outcome_review_pending_review",
        "outcome_review_breached",
        "outcome_review_degraded",
        "outcome_review_blocked",
        "outcome_review_not_supported",
        "outcome_review_source_refreshed",
        "outcome_review_not_found",
        "outcome_review_error",
    }
)
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
_API_ROUTE_PREFIX = "/api/v1"
_PM_QUALITY_ROUTE_PREFIX = "/api/v1/rebalance/pm-operating-quality"


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
    if not isinstance(route_path, str) or not route_path:
        return "unmatched"
    request_path = request.scope.get("path")
    return _route_template_with_request_prefix(
        route_path=route_path,
        request_path=request_path if isinstance(request_path, str) else "",
    )


def _route_template_with_request_prefix(*, route_path: str, request_path: str) -> str:
    if route_path.startswith(_API_ROUTE_PREFIX):
        return route_path
    if request_path.startswith(f"{_API_ROUTE_PREFIX}/"):
        return f"{_API_ROUTE_PREFIX}{route_path}"
    return route_path


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
        return json.dumps(_json_log_payload(record))


def _json_log_payload(record: logging.LogRecord) -> dict[str, Any]:
    payload = _base_json_log_payload(record)
    extra_fields = getattr(record, "extra_fields", None)
    if isinstance(extra_fields, dict):
        payload.update(_safe_log_extra_fields(extra_fields))
    return _without_none_values(payload)


def _base_json_log_payload(record: logging.LogRecord) -> dict[str, Any]:
    return {
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


def _without_none_values(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def setup_observability(app: FastAPI) -> None:
    _configure_root_json_logging()
    _initialize_http_metrics_baseline()
    app.get(
        "/metrics",
        tags=["Monitoring"],
        summary="Metrics",
        operation_id="metrics_metrics_get",
        responses={503: {"description": "Metrics exposition unavailable."}},
        response_description="Prometheus text exposition for lotus-manage metrics.",
    )(_metrics_endpoint)
    app.middleware("http")(_request_observability_middleware)


def _configure_root_json_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)


def _initialize_http_metrics_baseline() -> None:
    HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/metrics", status_family="2xx")


def _metrics_endpoint() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _trace_id_from_traceparent(traceparent: str) -> str:
    if traceparent:
        parts = traceparent.split("-")
        if len(parts) >= 4 and len(parts[1]) == 32:
            return parts[1]
    return uuid4().hex


async def _request_observability_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    logger = logging.getLogger("http.access")
    started = time.perf_counter()

    correlation_id = request.headers.get("X-Correlation-Id") or f"corr_{uuid4().hex[:12]}"
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex[:12]}"
    trace_id = _trace_id_from_traceparent(request.headers.get("traceparent", ""))

    correlation_token = correlation_id_var.set(correlation_id)
    request_token = request_id_var.set(request_id)
    trace_token = trace_id_var.set(trace_id)
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        endpoint = _route_template(request)
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_family="5xx",
        ).inc()
        logger.info(
            "request.completed",
            extra={
                "extra_fields": {
                    "http_method": request.method,
                    "endpoint": endpoint,
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
    endpoint = _route_template(request)
    status_family = _status_family(response.status_code)
    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        endpoint=endpoint,
        status_family=status_family,
    ).inc()
    if response.status_code < 400:
        record_pm_quality_http_result(path=endpoint, status_code=response.status_code)
    logger.info(
        "request.completed",
        extra={
            "extra_fields": {
                "http_method": request.method,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "status_family": status_family,
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
    apply_observability_headers(response)
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


def record_postgres_access(
    *,
    operation: str,
    outcome: str,
    reason: str,
    classification: str,
) -> None:
    POSTGRES_ACCESS_TOTAL.labels(
        operation=_safe_metric_label(
            operation,
            allowed_values=_ALLOWED_POSTGRES_ACCESS_OPERATIONS,
            fallback="connect",
        ),
        outcome=_safe_metric_label(
            outcome,
            allowed_values=_ALLOWED_POSTGRES_ACCESS_OUTCOMES,
            fallback="failure",
        ),
        reason=_safe_metric_label(
            reason,
            allowed_values=_ALLOWED_POSTGRES_ACCESS_REASONS,
            fallback="connection_unavailable",
        ),
        classification=_safe_metric_label(
            classification,
            allowed_values=_ALLOWED_POSTGRES_ACCESS_CLASSIFICATIONS,
            fallback="unknown",
        ),
    ).inc()


def record_pm_quality_lifecycle(
    *,
    surface: str,
    outcome: str,
    reason: str,
) -> None:
    PM_QUALITY_LIFECYCLE_TOTAL.labels(
        surface=_safe_metric_label(
            surface,
            allowed_values=_ALLOWED_PM_QUALITY_SURFACES,
            fallback="unknown",
        ),
        outcome=_safe_metric_label(
            outcome,
            allowed_values=_ALLOWED_PM_QUALITY_OUTCOMES,
            fallback="error",
        ),
        reason=_safe_metric_label(
            reason,
            allowed_values=_ALLOWED_PM_QUALITY_REASONS,
            fallback="unexpected_error",
        ),
    ).inc()


def record_pm_quality_http_result(*, path: str, status_code: int) -> None:
    surface = _pm_quality_surface_from_path(path)
    if surface is None:
        return
    outcome, reason = _pm_quality_outcome_reason(status_code=status_code)
    record_pm_quality_lifecycle(surface=surface, outcome=outcome, reason=reason)


def _pm_quality_surface_from_path(path: str) -> str | None:
    if not path.startswith(_PM_QUALITY_ROUTE_PREFIX):
        return None
    if "/policies" in path:
        return "policy"
    if "/score-runs" in path:
        return "score_run"
    if "/fairness-analyses" in path:
        return "fairness_analysis"
    if "/review-actions" in path:
        return "review_action"
    if "/summary-invocations" in path:
        return "summary_invocation"
    return "unknown"


def _pm_quality_outcome_reason(*, status_code: int) -> tuple[str, str]:
    if 200 <= status_code < 400:
        return "success", "success"
    if status_code == 403:
        return "forbidden", "forbidden"
    if status_code == 404:
        return "not_found", "not_found"
    if status_code == 409:
        return "conflict", "immutable_conflict"
    if status_code == 422:
        return "validation_failed", "validation_error"
    if status_code == 424:
        return "dependency_failed", "dependency_incomplete"
    if status_code == 503:
        return "unavailable", "dependency_unavailable"
    return "error", "unexpected_error"


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


def record_campaign_workflow(
    *,
    surface: str,
    outcome: str,
    reason: str,
) -> None:
    CAMPAIGN_WORKFLOW_TOTAL.labels(
        surface=_safe_metric_label(
            surface,
            allowed_values=_ALLOWED_CAMPAIGN_WORKFLOW_SURFACES,
            fallback="unknown",
        ),
        outcome=_safe_metric_label(
            outcome,
            allowed_values=_ALLOWED_CAMPAIGN_WORKFLOW_OUTCOMES,
            fallback="error",
        ),
        reason=_safe_metric_label(
            reason,
            allowed_values=_ALLOWED_CAMPAIGN_WORKFLOW_REASONS,
            fallback="unexpected_error",
        ),
    ).inc()


def record_wave_supportability(
    *,
    surface: str,
    supportability_state: str,
    reason: str,
) -> None:
    WAVE_SUPPORTABILITY_TOTAL.labels(
        surface=_safe_metric_label(
            surface,
            allowed_values=_ALLOWED_WAVE_SUPPORTABILITY_SURFACES,
            fallback="rebalance/waves/supportability",
        ),
        supportability_state=_safe_metric_label(
            supportability_state,
            allowed_values=_ALLOWED_WAVE_SUPPORTABILITY_STATES,
            fallback="blocked",
        ),
        reason=_safe_metric_label(
            reason,
            allowed_values=_ALLOWED_WAVE_SUPPORTABILITY_REASONS,
            fallback="wave_supportability_error",
        ),
    ).inc()


def record_outcome_review_supportability(
    *,
    surface: str,
    supportability_state: str,
    reason: str,
) -> None:
    OUTCOME_REVIEW_SUPPORTABILITY_TOTAL.labels(
        surface=_safe_metric_label(
            surface,
            allowed_values=_ALLOWED_OUTCOME_REVIEW_SURFACES,
            fallback="rebalance/outcome-reviews/supportability",
        ),
        supportability_state=_safe_metric_label(
            supportability_state,
            allowed_values=_ALLOWED_OUTCOME_REVIEW_STATES,
            fallback="error",
        ),
        reason=_safe_metric_label(
            reason,
            allowed_values=_ALLOWED_OUTCOME_REVIEW_REASONS,
            fallback="outcome_review_error",
        ),
    ).inc()
