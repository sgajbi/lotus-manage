from fastapi.testclient import TestClient
from src.app.main import app
from fastapi.responses import JSONResponse


def test_health_endpoints() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_correlation_header_propagation() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={"X-Correlation-Id": "corr-123"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-123"


def test_integration_capabilities_contract() -> None:
    client = TestClient(app)
    response = client.get('/integration/capabilities')
    assert response.status_code == 200
    body = response.json()
    assert body['sourceService'] == 'lotus-manage'
    assert isinstance(body['features'], list)
    assert isinstance(body['workflows'], list)


def test_rebalance_proxy_forwards_get(monkeypatch) -> None:
    captured: dict[str, str] = {}

    async def _stub_proxy(request, path):  # type: ignore[no-untyped-def]
        captured["method"] = request.method
        captured["path"] = path
        captured["query"] = request.url.query
        return JSONResponse({"ok": True}, status_code=200)

    monkeypatch.setattr("src.app.main._proxy_request", _stub_proxy)
    client = TestClient(app)
    response = client.get("/rebalance/proposals?limit=5")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert captured == {"method": "GET", "path": "/rebalance/proposals", "query": "limit=5"}


def test_rebalance_proxy_forwards_post(monkeypatch) -> None:
    captured: dict[str, str] = {}

    async def _stub_proxy(request, path):  # type: ignore[no-untyped-def]
        captured["method"] = request.method
        captured["path"] = path
        return JSONResponse({"ok": True}, status_code=201)

    monkeypatch.setattr("src.app.main._proxy_request", _stub_proxy)
    client = TestClient(app)
    response = client.post("/rebalance/proposals/simulate", json={"portfolio_id": "P1"})
    assert response.status_code == 201
    assert response.json()["ok"] is True
    assert captured == {"method": "POST", "path": "/rebalance/proposals/simulate"}

