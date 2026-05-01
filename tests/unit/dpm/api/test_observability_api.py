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
