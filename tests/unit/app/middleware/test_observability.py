from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.api.observability import setup_observability
from src.api.response_headers import apply_observability_headers


def _app() -> FastAPI:
    app = FastAPI()
    setup_observability(app)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/error")
    def error() -> None:
        raise RuntimeError("boom")

    return app


def test_apply_observability_headers_adds_security_headers() -> None:
    response = JSONResponse(content={"ok": True})
    apply_observability_headers(response)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "0"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"


def test_apply_observability_headers_preserves_existing_header_values() -> None:
    response = JSONResponse(content={"ok": True}, headers={"X-Frame-Options": "ALLOW"})
    apply_observability_headers(response)

    assert response.headers["X-Frame-Options"] == "ALLOW"


def test_observability_middleware_injects_correlation_and_hardening_headers() -> None:
    client = TestClient(_app())
    response = client.get("/ping", headers={"X-Correlation-Id": "corr-test-1"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-test-1"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Request-Id"]
    assert response.headers["X-Trace-Id"]
    assert response.headers["traceparent"].startswith("00-")
