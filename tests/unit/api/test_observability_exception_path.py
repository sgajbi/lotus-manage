from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.observability import setup_observability


def test_observability_middleware_logs_and_reraises_unhandled_exceptions() -> None:
    app = FastAPI()
    setup_observability(app)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
