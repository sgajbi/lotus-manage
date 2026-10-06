import json
import logging
import os
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.api.enterprise_readiness import is_sensitive_field_name, redact_sensitive
from src.api.response_headers import apply_observability_headers

from src.observability.metrics import (
    MANAGE_SUPPORTABILITY_TOTAL as MANAGE_SUPPORTABILITY_TOTAL,
    DPM_CORE_RESOLVER_TOTAL as DPM_CORE_RESOLVER_TOTAL,
    DPM_EXECUTION_TOTAL as DPM_EXECUTION_TOTAL,
    DPM_ASYNC_OPERATION_TOTAL as DPM_ASYNC_OPERATION_TOTAL,
    DPM_POLICY_PACK_RESOLUTION_TOTAL as DPM_POLICY_PACK_RESOLUTION_TOTAL,
    POSTGRES_ACCESS_TOTAL as POSTGRES_ACCESS_TOTAL,
    PM_QUALITY_LIFECYCLE_TOTAL as PM_QUALITY_LIFECYCLE_TOTAL,
    DPM_WORKFLOW_DECISION_TOTAL as DPM_WORKFLOW_DECISION_TOTAL,
    CAMPAIGN_WORKFLOW_TOTAL as CAMPAIGN_WORKFLOW_TOTAL,
    CAMPAIGN_READ_MODEL_SCAN_TOTAL as CAMPAIGN_READ_MODEL_SCAN_TOTAL,
    WAVE_SUPPORTABILITY_TOTAL as WAVE_SUPPORTABILITY_TOTAL,
    OUTCOME_REVIEW_SUPPORTABILITY_TOTAL as OUTCOME_REVIEW_SUPPORTABILITY_TOTAL,
    SOURCE_HTTP_REQUEST_TOTAL as SOURCE_HTTP_REQUEST_TOTAL,
    SOURCE_HTTP_REQUEST_DURATION_SECONDS as SOURCE_HTTP_REQUEST_DURATION_SECONDS,
    SOURCE_HTTP_RETRY_TOTAL as SOURCE_HTTP_RETRY_TOTAL,
    HTTP_REQUESTS_TOTAL as HTTP_REQUESTS_TOTAL,
    ACTION_REGISTER_SUPPORTABILITY_SURFACE as ACTION_REGISTER_SUPPORTABILITY_SURFACE,
    UNKNOWN_ACTION_REGISTER_SURFACE as UNKNOWN_ACTION_REGISTER_SURFACE,
    DPM_CORE_RESOLVER_OPERATION as DPM_CORE_RESOLVER_OPERATION,
    record_action_register_supportability as record_action_register_supportability,
    record_core_resolver_call as record_core_resolver_call,
    record_execution_call as record_execution_call,
    record_async_operation as record_async_operation,
    record_policy_pack_resolution as record_policy_pack_resolution,
    record_postgres_access as record_postgres_access,
    record_pm_quality_lifecycle as record_pm_quality_lifecycle,
    record_pm_quality_http_result as record_pm_quality_http_result,
    record_source_http_request as record_source_http_request,
    record_source_http_retry as record_source_http_retry,
    record_workflow_decision as record_workflow_decision,
    record_campaign_workflow as record_campaign_workflow,
    record_campaign_read_model_scan as record_campaign_read_model_scan,
    record_wave_supportability as record_wave_supportability,
    record_outcome_review_supportability as record_outcome_review_supportability,
)

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

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
_ALLOWED_LOG_EXTRA_FIELD_NAMES = frozenset(
    {
        "acquire_timeout_seconds",
        "application_name",
        "blocked_dimension_count",
        "classification",
        "connect_timeout_seconds",
        "connection_budget",
        "degraded_dimension_count",
        "dimension_count",
        "endpoint",
        "http_method",
        "issue_count",
        "latency_bucket_ms",
        "max_connections",
        "operation",
        "outcome_state",
        "reason",
        "source_ref_count",
        "status_code",
        "status_family",
        "supportability_state",
        "unsupported_dimension_count",
        "wave_state",
    }
)
_ALLOWED_LOG_EXTRA_VALUE_TYPES = (str, int, float, bool)
_LATENCY_BUCKETS_MS = (10, 50, 100, 250, 500, 1000)
_API_ROUTE_PREFIX = "/api/v1"


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
        if not isinstance(key, str):
            continue
        normalized_key = key.casefold()
        if normalized_key in _SENSITIVE_LOG_FIELD_NAMES or is_sensitive_field_name(normalized_key):
            safe_fields[normalized_key] = "[REDACTED]"
            continue
        if key not in _ALLOWED_LOG_EXTRA_FIELD_NAMES:
            continue
        if not isinstance(raw_value, _ALLOWED_LOG_EXTRA_VALUE_TYPES):
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
    audit = getattr(record, "audit", None)
    if record.name == "enterprise_readiness" and record.msg == "enterprise_audit_event":
        safe_audit = _safe_audit_envelope(audit)
        if safe_audit is not None:
            payload["audit"] = safe_audit
    return _without_none_values(payload)


def _safe_audit_envelope(audit: Any) -> dict[str, Any] | None:
    """Serialize only the emitter's known fields, not arbitrary LogRecord attributes."""
    text_fields = (
        "service",
        "action",
        "actor_id",
        "tenant_id",
        "role",
        "correlation_id",
        "timestamp_utc",
        "policy_version",
    )
    if (
        not isinstance(audit, dict)
        or any(not isinstance(audit.get(field), str) for field in text_fields)
        or not isinstance(audit.get("metadata"), dict)
    ):
        return None
    return {
        **{field: audit[field] for field in text_fields},
        "metadata": redact_sensitive(audit["metadata"]),
    }


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
    request.state.correlation_id = correlation_id
    request.state.request_id = request_id
    request.state.trace_id = trace_id

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
