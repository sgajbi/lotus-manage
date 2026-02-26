import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers.dpm_policy_packs import (
    policy_pack_catalog_backend_name,
    policy_pack_postgres_dsn,
    reset_dpm_policy_pack_repository_for_tests,
)


def setup_function() -> None:
    reset_dpm_policy_pack_repository_for_tests()


def test_policy_pack_catalog_postgres_requires_dsn(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
        monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)
        monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
        reset_dpm_policy_pack_repository_for_tests()

        response = client.get("/api/v1/rebalance/policies/catalog")
        assert response.status_code == 503
        assert response.json()["detail"] == "DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED"


def test_policy_pack_catalog_env_json_backend_deprecated(monkeypatch):
    monkeypatch.delenv("DPM_POLICY_PACK_CATALOG_BACKEND", raising=False)
    assert policy_pack_catalog_backend_name() == "POSTGRES"

    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "ENV_JSON")
    with pytest.raises(RuntimeError, match="DPM_POLICY_PACK_CATALOG_BACKEND_UNSUPPORTED"):
        policy_pack_catalog_backend_name()


def test_policy_pack_postgres_dsn_prefers_explicit_value(monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://explicit")
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://fallback")
    assert policy_pack_postgres_dsn() == "postgresql://explicit"


def test_policy_pack_postgres_dsn_falls_back_to_supportability_dsn(monkeypatch):
    monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://fallback")
    assert policy_pack_postgres_dsn() == "postgresql://fallback"


def test_policy_pack_catalog_postgres_connection_errors_return_503(monkeypatch):
    class _ExplodingRepository:
        def __init__(self, *, dsn):  # noqa: ARG002
            raise ValueError("boom")

    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
        monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
        monkeypatch.setattr(
            "src.api.routers.dpm_policy_packs.PostgresDpmPolicyPackRepository",
            _ExplodingRepository,
        )
        reset_dpm_policy_pack_repository_for_tests()

        response = client.get("/api/v1/rebalance/policies/catalog")
        assert response.status_code == 503
        assert response.json()["detail"] == "DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED"


def test_policy_pack_catalog_postgres_runtime_errors_return_503(monkeypatch):
    class _RuntimeErrorRepository:
        def __init__(self, *, dsn):  # noqa: ARG002
            raise RuntimeError("DPM_POLICY_PACK_POSTGRES_DRIVER_MISSING")

    with TestClient(app) as client:
        monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
        monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://u:p@localhost:5432/db")
        monkeypatch.setattr(
            "src.api.routers.dpm_policy_packs.PostgresDpmPolicyPackRepository",
            _RuntimeErrorRepository,
        )
        reset_dpm_policy_pack_repository_for_tests()

        response = client.get("/api/v1/rebalance/policies/catalog")
        assert response.status_code == 503
        assert response.json()["detail"] == "DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED"
