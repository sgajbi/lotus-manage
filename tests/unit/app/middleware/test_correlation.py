from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app.middleware.correlation import CorrelationIdMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware, service_name="lotus-manage")

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_correlation_middleware_reuses_incoming_correlation_id() -> None:
    client = TestClient(_app())
    response = client.get("/ping", headers={"X-Correlation-Id": "corr-test-1"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-test-1"
    assert response.headers["X-Service-Name"] == "lotus-manage"
    assert float(response.headers["X-Request-Duration-Ms"]) >= 0


def test_correlation_middleware_generates_correlation_id_when_missing() -> None:
    client = TestClient(_app())
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"]
    assert response.headers["X-Service-Name"] == "lotus-manage"
