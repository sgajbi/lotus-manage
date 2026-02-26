import builtins

import pytest

from src.api.routers import dpm_runs_config


def test_supportability_backend_aliases_and_defaults(monkeypatch):
    monkeypatch.delenv("DPM_SUPPORTABILITY_STORE_BACKEND", raising=False)
    assert dpm_runs_config.supportability_store_backend_name() == "POSTGRES"

    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    assert dpm_runs_config.supportability_store_backend_name() == "POSTGRES"

    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "SQLITE")
    with pytest.raises(RuntimeError, match="DPM_SUPPORTABILITY_STORE_BACKEND_UNSUPPORTED"):
        dpm_runs_config.supportability_store_backend_name()


def test_supportability_postgres_dsn(monkeypatch):
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)
    assert dpm_runs_config.supportability_postgres_dsn() == ""

    monkeypatch.setenv(
        "DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://user:pass@localhost:5432/dpm"
    )
    assert (
        dpm_runs_config.supportability_postgres_dsn() == "postgresql://user:pass@localhost:5432/dpm"
    )


def test_artifact_store_mode_fallback(monkeypatch):
    monkeypatch.delenv("DPM_ARTIFACT_STORE_MODE", raising=False)
    assert dpm_runs_config.artifact_store_mode() == "DERIVED"

    monkeypatch.setenv("DPM_ARTIFACT_STORE_MODE", "PERSISTED")
    assert dpm_runs_config.artifact_store_mode() == "PERSISTED"

    monkeypatch.setenv("DPM_ARTIFACT_STORE_MODE", "invalid")
    assert dpm_runs_config.artifact_store_mode() == "DERIVED"


def test_env_parsers(monkeypatch):
    monkeypatch.setenv("DPM_TEST_FLAG", "true")
    assert dpm_runs_config.env_flag("DPM_TEST_FLAG", False) is True

    monkeypatch.setenv("DPM_TEST_INT", "9")
    assert dpm_runs_config.env_int("DPM_TEST_INT", 5) == 9
    monkeypatch.setenv("DPM_TEST_INT", "-1")
    assert dpm_runs_config.env_int("DPM_TEST_INT", 5) == 5

    monkeypatch.setenv("DPM_TEST_NON_NEGATIVE", "0")
    assert dpm_runs_config.env_non_negative_int("DPM_TEST_NON_NEGATIVE", 5) == 0
    monkeypatch.setenv("DPM_TEST_NON_NEGATIVE", "-1")
    assert dpm_runs_config.env_non_negative_int("DPM_TEST_NON_NEGATIVE", 5) == 5

    monkeypatch.setenv("DPM_TEST_CSV", "A, B ,,C")
    assert dpm_runs_config.env_csv_set("DPM_TEST_CSV", {"X"}) == {"A", "B", "C"}


def test_build_repository_postgres_requires_dsn(monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("DPM_SUPPORTABILITY_POSTGRES_DSN", raising=False)

    try:
        dpm_runs_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing Postgres DSN")


def test_build_repository_postgres_driver_error_passthrough(monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv(
        "DPM_SUPPORTABILITY_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/dpm",
    )

    def _raise_driver_error(**_kwargs):
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING")

    monkeypatch.setattr(
        dpm_runs_config,
        "PostgresDpmRunRepository",
        _raise_driver_error,
    )

    try:
        dpm_runs_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError passthrough for Postgres init runtime error")


def test_build_repository_postgres_connection_failure_mapped(monkeypatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv(
        "DPM_SUPPORTABILITY_POSTGRES_DSN",
        "postgresql://user:pass@localhost:5432/dpm",
    )

    def _raise_connection_error(**_kwargs):
        raise ValueError("connection broken")

    monkeypatch.setattr(
        dpm_runs_config,
        "PostgresDpmRunRepository",
        _raise_connection_error,
    )

    try:
        dpm_runs_config.build_repository()
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED"
    else:
        raise AssertionError("Expected RuntimeError for Postgres connection failure")


def test_postgres_connection_exception_types_handles_missing_driver(monkeypatch):
    original_import = builtins.__import__

    def _import_with_psycopg_missing(name, *args, **kwargs):
        if name == "psycopg":
            raise ImportError("psycopg not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import_with_psycopg_missing)
    exception_types = dpm_runs_config._postgres_connection_exception_types()
    assert ValueError in exception_types
