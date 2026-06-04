from __future__ import annotations

from src.api.services import rebalance_policy_pack_repository as policy_pack_repository


def test_policy_pack_repository_builds_only_from_postgres_dsn(monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://explicit")
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    repository = policy_pack_repository.build_policy_pack_repository()
    assert repository is not None


def test_policy_pack_repository_falls_back_to_supportability_dsn(monkeypatch):
    monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://fallback")
    repository = policy_pack_repository.build_policy_pack_repository()
    assert repository is not None


def test_policy_pack_repository_requires_dsn(monkeypatch):
    monkeypatch.delenv("DPM_POLICY_PACK_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)

    try:
        policy_pack_repository.build_policy_pack_repository()
    except RuntimeError as exc:
        assert str(exc) == "DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing policy pack DSN")


def test_policy_pack_repository_maps_connection_failures(monkeypatch):
    monkeypatch.setenv("DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://policypack")

    def _raise_connection_error(**_kwargs):
        raise ValueError("connection failed")

    monkeypatch.setattr(
        policy_pack_repository,
        "PostgresDpmPolicyPackRepository",
        _raise_connection_error,
    )

    try:
        policy_pack_repository.build_policy_pack_repository()
    except RuntimeError as exc:
        assert str(exc) == "DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED"
    else:
        raise AssertionError("Expected RuntimeError for connection failure mapping")
