from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers.rebalance_runs import reset_dpm_run_support_service_for_tests


def _simulate(client: TestClient, *, correlation_id: str, idempotency_key: str) -> dict:
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_lineage",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {},
    }
    response = client.post(
        "/api/v1/rebalance/simulate",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
            "X-Correlation-Id": correlation_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_lineage_api_supports_filters_and_pagination(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("DPM_LINEAGE_APIS_ENABLED", "true")
        reset_dpm_run_support_service_for_tests()
        body = _simulate(client, correlation_id="corr-lineage-1", idempotency_key="idem-lineage-1")
        run_id = body["rebalance_run_id"]

        all_edges = client.get(f"/api/v1/rebalance/lineage/{run_id}")
        assert all_edges.status_code == 200
        all_items = all_edges.json()["edges"]
        assert len(all_items) >= 2

        typed = client.get(
            f"/api/v1/rebalance/lineage/{run_id}",
            params={"limit": 1},
        )
        assert typed.status_code == 200
        typed_body = typed.json()
        assert len(typed_body["edges"]) == 1
        assert typed_body["next_cursor"] is not None

        second_page = client.get(
            f"/api/v1/rebalance/lineage/{run_id}",
            params={
                "limit": 1,
                "cursor": typed_body["next_cursor"],
            },
        )
        assert second_page.status_code == 200
        assert len(second_page.json()["edges"]) == 1
