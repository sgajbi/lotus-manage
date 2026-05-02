from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers.rebalance_policy_packs import (
    _postgres_connection_exception_types,
    reset_dpm_policy_pack_repository_for_tests,
)


def setup_function() -> None:
    reset_dpm_policy_pack_repository_for_tests()


def test_policy_pack_admin_apis_disabled_by_default():
    with TestClient(app) as client:
        response = client.put(
            "/api/v1/rebalance/policies/catalog/dpm_standard_v1",
            json={"version": "1"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "DPM_POLICY_PACK_ADMIN_APIS_DISABLED"


def test_policy_pack_admin_apis_env_repository_roundtrip(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "true")
        monkeypatch.delenv("DPM_POLICY_PACK_CATALOG_BACKEND", raising=False)
        reset_dpm_policy_pack_repository_for_tests()

        upsert = client.put(
            "/api/v1/rebalance/policies/catalog/dpm_standard_v1",
            json={
                "version": "2",
                "turnover_policy": {"max_turnover_pct": "0.15"},
                "tax_policy": {
                    "enable_tax_awareness": True,
                    "max_realized_capital_gains": "1000",
                },
                "settlement_policy": {
                    "enable_settlement_awareness": True,
                    "settlement_horizon_days": 3,
                },
                "constraint_policy": {
                    "single_position_max_weight": "0.25",
                    "group_constraints": {"sector:TECH": {"max_weight": "0.20"}},
                },
                "workflow_policy": {
                    "enable_workflow_gates": True,
                    "workflow_requires_mandate_approval": True,
                    "mandate_approval_already_obtained": False,
                },
                "idempotency_policy": {"replay_enabled": True},
            },
        )
        assert upsert.status_code == 200
        upsert_item = upsert.json()["item"]
        assert upsert_item["policy_pack_id"] == "dpm_standard_v1"
        assert upsert_item["version"] == "2"
        assert upsert_item["turnover_policy"]["max_turnover_pct"] == "0.15"
        assert upsert_item["tax_policy"]["enable_tax_awareness"] is True
        assert upsert_item["tax_policy"]["max_realized_capital_gains"] == "1000"
        assert upsert_item["settlement_policy"]["settlement_horizon_days"] == 3
        assert upsert_item["constraint_policy"]["single_position_max_weight"] == "0.25"
        assert upsert_item["constraint_policy"]["group_constraints"]["sector:TECH"] == {
            "max_weight": "0.20"
        }
        assert upsert_item["workflow_policy"]["workflow_requires_mandate_approval"] is True
        assert upsert_item["workflow_policy"]["mandate_approval_already_obtained"] is False
        assert upsert_item["idempotency_policy"]["replay_enabled"] is True

        get_one = client.get("/api/v1/rebalance/policies/catalog/dpm_standard_v1")
        assert get_one.status_code == 200
        get_one_body = get_one.json()
        assert get_one_body["policy_pack_id"] == "dpm_standard_v1"
        assert get_one_body["turnover_policy"]["max_turnover_pct"] == "0.15"
        assert get_one_body["tax_policy"] == upsert_item["tax_policy"]
        assert get_one_body["settlement_policy"] == upsert_item["settlement_policy"]
        assert get_one_body["constraint_policy"] == upsert_item["constraint_policy"]
        assert get_one_body["workflow_policy"] == upsert_item["workflow_policy"]
        assert get_one_body["idempotency_policy"] == upsert_item["idempotency_policy"]

        catalog = client.get("/api/v1/rebalance/policies/catalog")
        assert catalog.status_code == 200
        assert catalog.json()["total"] >= 1
        assert "dpm_standard_v1" in {item["policy_pack_id"] for item in catalog.json()["items"]}

        delete = client.delete("/api/v1/rebalance/policies/catalog/dpm_standard_v1")
        assert delete.status_code == 204

        get_missing = client.get("/api/v1/rebalance/policies/catalog/dpm_standard_v1")
        assert get_missing.status_code == 404
        assert get_missing.json()["detail"] == "DPM_POLICY_PACK_NOT_FOUND"


def test_policy_pack_catalog_item_admin_routes_reject_unexpected_query_params(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "true")
        monkeypatch.delenv("DPM_POLICY_PACK_CATALOG_BACKEND", raising=False)
        reset_dpm_policy_pack_repository_for_tests()

        requests = [
            (
                "get",
                "/api/v1/rebalance/policies/catalog/dpm_standard_v1?include_disabled=true",
                None,
                "include_disabled",
            ),
            (
                "put",
                "/api/v1/rebalance/policies/catalog/dpm_standard_v1?dry_run=true",
                {"version": "1"},
                "dry_run",
            ),
            (
                "delete",
                "/api/v1/rebalance/policies/catalog/dpm_standard_v1?force=true",
                None,
                "force",
            ),
        ]

        for method, url, body, unsupported_param in requests:
            response = (
                getattr(client, method)(url, json=body) if body else getattr(client, method)(url)
            )
            assert response.status_code == 422
            assert response.json()["detail"] == (
                f"UNSUPPORTED_QUERY_PARAMETER: {unsupported_param} not supported for this endpoint"
            )


def test_policy_pack_admin_delete_missing_returns_404(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_ADMIN_APIS_ENABLED", "true")
        monkeypatch.delenv("DPM_POLICY_PACK_CATALOG_BACKEND", raising=False)
        reset_dpm_policy_pack_repository_for_tests()

        response = client.delete("/api/v1/rebalance/policies/catalog/does_not_exist")
        assert response.status_code == 404
        assert response.json()["detail"] == "DPM_POLICY_PACK_NOT_FOUND"


def test_postgres_connection_exception_types_handles_missing_psycopg(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "psycopg":
            raise ImportError("psycopg unavailable in test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    exception_types = _postgres_connection_exception_types()
    assert ConnectionError in exception_types
