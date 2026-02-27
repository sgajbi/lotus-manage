import pytest

import src.api.routers.proposals_config as proposals_config


def test_proposal_store_backend_name_accepts_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "postgres")
    assert proposals_config.proposal_store_backend_name() == "POSTGRES"


def test_proposal_store_backend_name_rejects_unsupported_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "inmemory")
    with pytest.raises(RuntimeError, match="PROPOSAL_STORE_BACKEND_UNSUPPORTED"):
        proposals_config.proposal_store_backend_name()


def test_proposal_postgres_dsn_trims_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "  postgresql://proposal  ")
    assert proposals_config.proposal_postgres_dsn() == "postgresql://proposal"


def test_build_repository_requires_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError, match="PROPOSAL_POSTGRES_DSN_REQUIRED"):
        proposals_config.build_repository()


def test_build_repository_maps_connection_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://proposal")
    monkeypatch.setattr(
        proposals_config,
        "PostgresProposalRepository",
        lambda **_kwargs: (_ for _ in ()).throw(TypeError("connection failure")),
    )

    with pytest.raises(RuntimeError, match="PROPOSAL_POSTGRES_CONNECTION_FAILED"):
        proposals_config.build_repository()


def test_build_repository_preserves_runtime_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://proposal")
    monkeypatch.setattr(
        proposals_config,
        "PostgresProposalRepository",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")),
    )

    with pytest.raises(RuntimeError, match="PROPOSAL_POSTGRES_DSN_REQUIRED"):
        proposals_config.build_repository()


def test_build_repository_returns_repository_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://proposal")

    class _Repo:
        pass

    repo = _Repo()
    monkeypatch.setattr(proposals_config, "PostgresProposalRepository", lambda **_kwargs: repo)
    assert proposals_config.build_repository() is repo
