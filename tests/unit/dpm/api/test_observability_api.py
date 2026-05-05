import json
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

import src.api.main as main_module
import src.api.observability as observability_module
from src.api.main import app


def test_health_endpoints_available():
    client = TestClient(app)
    expected = {
        "/health": {"status": "ok"},
        "/health/live": {"status": "live"},
        "/health/ready": {"status": "ready"},
    }

    for path, body in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == body

    assert {client.get(path).headers["content-type"] for path in expected} == {"application/json"}


def test_health_ready_validates_cutover_migrations_in_production(monkeypatch):
    called = {"migrations": 0}
    monkeypatch.setattr(main_module, "app_persistence_profile_name", lambda: "PRODUCTION")
    monkeypatch.setattr(main_module, "validate_persistence_profile_guardrails", lambda: None)
    monkeypatch.setattr(
        main_module,
        "validate_cutover_migrations_applied",
        lambda: called.__setitem__("migrations", called["migrations"] + 1),
    )

    assert main_module.health_ready().model_dump() == {"status": "ready"}
    assert called["migrations"] == 1


def test_health_ready_skips_cutover_migrations_outside_production(monkeypatch):
    called = {"guardrails": 0, "migrations": 0}
    monkeypatch.setattr(main_module, "app_persistence_profile_name", lambda: "LOCAL")
    monkeypatch.setattr(
        main_module,
        "validate_persistence_profile_guardrails",
        lambda: called.__setitem__("guardrails", called["guardrails"] + 1),
    )
    monkeypatch.setattr(
        main_module,
        "validate_cutover_migrations_applied",
        lambda: called.__setitem__("migrations", called["migrations"] + 1),
    )

    assert main_module.health_ready().model_dump() == {"status": "ready"}
    assert called == {"guardrails": 1, "migrations": 0}


def test_health_live_does_not_touch_readiness_dependencies(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "validate_persistence_profile_guardrails",
        lambda: (_ for _ in ()).throw(AssertionError("readiness guardrail was called")),
    )
    monkeypatch.setattr(
        main_module,
        "validate_cutover_migrations_applied",
        lambda: (_ for _ in ()).throw(AssertionError("migration guardrail was called")),
    )

    assert main_module.health_live().model_dump() == {"status": "live"}


def test_correlation_headers_are_exposed():
    client = TestClient(app)
    response = client.get(
        "/api/v1/integration/capabilities?consumer_system=lotus-gateway&tenant_id=default",
        headers={"X-Correlation-Id": "corr_dpm_1"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-Id") == "corr_dpm_1"
    assert response.headers.get("X-Request-Id")
    assert response.headers.get("X-Trace-Id")


def test_metrics_endpoint_available():
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "http_request_duration" in response.text


def test_action_register_supportability_metric_labels_are_bounded(monkeypatch):
    captured: dict[str, str] = {}

    class _Counter:
        def labels(self, **labels):
            captured.update(labels)
            return self

        def inc(self):
            return None

    monkeypatch.setattr(observability_module, "MANAGE_SUPPORTABILITY_TOTAL", _Counter())

    observability_module.record_action_register_supportability(
        surface="rebalance/supportability/summary/PB_SG_GLOBAL_BAL_001",
        supportability_state="ready",
        reason="client_name:private-bank-client",
        freshness_bucket="portfolio:PB_SG_GLOBAL_BAL_001",
    )

    assert captured == {
        "surface": "unknown_surface",
        "supportability_state": "ready",
        "reason": "supportability_summary_error",
        "freshness_bucket": "unknown",
    }
    assert "PB_SG_GLOBAL_BAL_001" not in captured.values()
    assert "client_name:private-bank-client" not in captured.values()


def test_core_resolver_metric_labels_are_bounded(monkeypatch):
    captured: dict[str, str] = {}

    class _Counter:
        def labels(self, **labels):
            captured.update(labels)
            return self

        def inc(self):
            return None

    monkeypatch.setattr(observability_module, "DPM_CORE_RESOLVER_TOTAL", _Counter())

    observability_module.record_core_resolver_call(
        operation="dpm_execution_context/PB_SG_GLOBAL_BAL_001",
        outcome="timeout_for_portfolio",
        supportability_state="client:private-bank-client",
        reason="request_hash:sha256:secret",
    )

    assert captured == {
        "operation": "dpm_execution_context",
        "outcome": "error",
        "supportability_state": "unknown",
        "reason": "unexpected_error",
    }
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(captured)
    assert "sha256:secret" not in json.dumps(captured)


def test_execution_metric_labels_are_bounded(monkeypatch):
    captured: dict[str, str] = {}

    class _Counter:
        def labels(self, **labels):
            captured.update(labels)
            return self

        def inc(self):
            return None

    monkeypatch.setattr(observability_module, "DPM_EXECUTION_TOTAL", _Counter())

    observability_module.record_execution_call(
        operation="simulate/PB_SG_GLOBAL_BAL_001",
        input_mode="portfolio:PB_SG_GLOBAL_BAL_001",
        outcome="failed_for_request_hash",
        result_status="client:private-bank-client",
    )

    assert captured == {
        "operation": "simulate",
        "input_mode": "unknown",
        "outcome": "error",
        "result_status": "unknown",
    }
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(captured)


def test_async_policy_and_workflow_metric_labels_are_bounded(monkeypatch):
    captured: dict[str, dict[str, str]] = {}

    class _Counter:
        def __init__(self, name: str) -> None:
            self.name = name

        def labels(self, **labels):
            captured[self.name] = labels
            return self

        def inc(self):
            return None

    monkeypatch.setattr(observability_module, "DPM_ASYNC_OPERATION_TOTAL", _Counter("async"))
    monkeypatch.setattr(
        observability_module,
        "DPM_POLICY_PACK_RESOLUTION_TOTAL",
        _Counter("policy"),
    )
    monkeypatch.setattr(
        observability_module,
        "DPM_WORKFLOW_DECISION_TOTAL",
        _Counter("workflow"),
    )
    monkeypatch.setattr(
        observability_module,
        "WAVE_SUPPORTABILITY_TOTAL",
        _Counter("wave"),
    )
    monkeypatch.setattr(
        observability_module,
        "OUTCOME_REVIEW_SUPPORTABILITY_TOTAL",
        _Counter("outcome"),
    )

    observability_module.record_async_operation(
        event="submit/PB_SG_GLOBAL_BAL_001",
        execution_mode="request_hash:sha256:secret",
        outcome="timeout_for_actor",
    )
    observability_module.record_policy_pack_resolution(
        surface="simulate/client",
        enabled="yes_for_private_bank_client",
        source="policy_pack_id:dpm_standard",
        selected="policy_pack_id:dpm_standard",
    )
    observability_module.record_workflow_decision(
        surface="run_id:rr_secret",
        action="actor:reviewer_001",
        outcome="portfolio_conflict",
    )
    observability_module.record_wave_supportability(
        surface="rebalance/waves/supportability/PB_SG_GLOBAL_BAL_001",
        supportability_state="portfolio_blocked",
        reason="client:private-bank-client",
    )
    observability_module.record_outcome_review_supportability(
        surface="rebalance/outcome-reviews/supportability/PB_SG_GLOBAL_BAL_001",
        supportability_state="client:private-bank-client",
        reason="request_hash:sha256:secret",
    )

    assert captured["async"] == {
        "event": "submit",
        "execution_mode": "unknown",
        "outcome": "failed",
    }
    assert captured["policy"] == {
        "surface": "api",
        "enabled": "false",
        "source": "unknown",
        "selected": "false",
    }
    assert captured["workflow"] == {
        "surface": "run",
        "action": "unknown",
        "outcome": "error",
    }
    assert captured["wave"] == {
        "surface": "rebalance/waves/supportability",
        "supportability_state": "blocked",
        "reason": "wave_supportability_error",
    }
    assert captured["outcome"] == {
        "surface": "rebalance/outcome-reviews/supportability",
        "supportability_state": "error",
        "reason": "outcome_review_error",
    }
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(captured)
    assert "sha256:secret" not in json.dumps(captured)
    assert "reviewer_001" not in json.dumps(captured)


def test_json_formatter_redacts_sensitive_extra_fields():
    formatter = observability_module.JsonFormatter()
    record = logging.LogRecord(
        name="lotus-manage.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="sensitive.event",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "request_hash": "sha256:secret-request",
        "status_family": "2xx",
    }

    payload = json.loads(formatter.format(record))

    assert payload["portfolio_id"] == "[REDACTED]"
    assert payload["request_hash"] == "[REDACTED]"
    assert payload["status_family"] == "2xx"
    assert "PB_SG_GLOBAL_BAL_001" not in json.dumps(payload)
    assert "sha256:secret-request" not in json.dumps(payload)


def test_http_access_log_uses_route_template_not_sensitive_path_values():
    captured: list[logging.LogRecord] = []

    class _CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    logger = logging.getLogger("http.access")
    handler = _CaptureHandler()
    logger.addHandler(handler)
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/rebalance/runs/by-request-hash/sha256:sensitive-request-hash"
        )
    finally:
        logger.removeHandler(handler)

    assert response.status_code in {404, 503}
    access_records = [
        record
        for record in captured
        if getattr(record, "msg", None) == "request.completed"
        and isinstance(getattr(record, "extra_fields", None), dict)
    ]
    assert access_records
    extra_fields = access_records[-1].extra_fields
    assert extra_fields["endpoint"] == "/api/v1/rebalance/runs/by-request-hash/{request_hash}"
    assert extra_fields["status_family"] in {"4xx", "5xx"}
    assert extra_fields["latency_bucket_ms"].startswith(("le_", "gt_"))
    assert "sha256:sensitive-request-hash" not in json.dumps(extra_fields)


def test_traceparent_header_propagates_trace_id():
    client = TestClient(app)
    upstream_trace_id = "1234567890abcdef1234567890abcdef"
    response = client.get(
        "/api/v1/integration/capabilities?consumer_system=lotus-gateway&tenant_id=default",
        headers={"traceparent": f"00-{upstream_trace_id}-0000000000000001-01"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Trace-Id") == upstream_trace_id
    assert response.headers.get("traceparent", "").startswith(f"00-{upstream_trace_id}-")


def test_load_concurrency_health_live_requests():
    client = TestClient(app)

    def _call_live() -> int:
        return client.get("/health/live").status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: _call_live(), range(32)))

    assert all(status == 200 for status in statuses)
