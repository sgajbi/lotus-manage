from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from src.api.main import app


def test_health_endpoints_available():
    client = TestClient(app)
    health = client.get("/health")
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert health.status_code == 200
    assert live.status_code == 200
    assert ready.status_code == 200
    assert health.json() == {"status": "ok"}
    assert live.json() == {"status": "live"}
    assert ready.json() == {"status": "ready"}


def test_correlation_headers_are_exposed():
    client = TestClient(app)
    response = client.get(
        "/integration/capabilities?consumer_system=lotus-gateway&tenant_id=default",
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


def test_traceparent_header_propagates_trace_id():
    client = TestClient(app)
    upstream_trace_id = "1234567890abcdef1234567890abcdef"
    response = client.get(
        "/integration/capabilities?consumer_system=lotus-gateway&tenant_id=default",
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
