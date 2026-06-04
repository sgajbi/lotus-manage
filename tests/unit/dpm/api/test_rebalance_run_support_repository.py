from __future__ import annotations

from src.api.services import rebalance_run_support_repository as run_support_repository


def test_run_support_repository_builds_with_postgres_dsn(monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://supportability")
    captured: dict[str, str] = {}

    def _in_memory_postgres(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(run_support_repository, "PostgresDpmRunRepository", _in_memory_postgres)

    repository = run_support_repository.build_repository(dsn="postgresql://supportability")
    assert repository is not None
    assert captured == {"dsn": "postgresql://supportability"}


def test_run_support_repository_requires_dsn():
    try:
        run_support_repository.build_repository(dsn="")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing supportability DSN")


def test_run_support_repository_maps_connection_failures(monkeypatch):
    def _raise_connection_error(*, dsn: str):
        raise ValueError("connection broken")

    monkeypatch.setattr(
        run_support_repository,
        "PostgresDpmRunRepository",
        _raise_connection_error,
    )

    try:
        run_support_repository.build_repository(dsn="postgresql://supportability")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED"
    else:
        raise AssertionError("Expected RuntimeError for Postgres connection failure")
