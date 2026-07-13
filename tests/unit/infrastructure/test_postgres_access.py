from __future__ import annotations

import logging
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.infrastructure.postgres_access import (
    PostgresConfigurationError,
    PostgresUnavailableError,
    _reset_postgres_access_state_for_tests,
    classify_postgres_error,
    connect_postgres,
    postgres_access_policy,
)

ROOT = Path(__file__).resolve().parents[3]
POLICY_ENV_NAMES = (
    "DPM_POSTGRES_MAX_CONNECTIONS",
    "DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS",
    "DPM_POSTGRES_STATEMENT_TIMEOUT_MS",
    "DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS",
    "DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def reset_postgres_access_policy(monkeypatch: pytest.MonkeyPatch):
    for name in POLICY_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    _reset_postgres_access_state_for_tests()
    yield
    _reset_postgres_access_state_for_tests()


def test_postgres_access_policy_defaults_are_bounded() -> None:
    policy = postgres_access_policy()

    assert policy.max_connections == 10
    assert policy.connect_timeout_seconds == 3
    assert policy.statement_timeout_ms == 5000
    assert policy.idle_in_transaction_timeout_ms == 10000
    assert policy.acquire_timeout_seconds == 2
    assert "statement_timeout=5000" in policy.session_options
    assert "idle_in_transaction_session_timeout=10000" in policy.session_options


def test_postgres_access_policy_rejects_invalid_and_out_of_range_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DPM_POSTGRES_MAX_CONNECTIONS", "many")
    with pytest.raises(
        PostgresConfigurationError,
        match="POSTGRES_ACCESS_POLICY_INVALID:DPM_POSTGRES_MAX_CONNECTIONS",
    ):
        postgres_access_policy()

    monkeypatch.setenv("DPM_POSTGRES_MAX_CONNECTIONS", "0")
    with pytest.raises(
        PostgresConfigurationError,
        match="POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:DPM_POSTGRES_MAX_CONNECTIONS:1:100",
    ):
        postgres_access_policy()


def test_connect_postgres_applies_bounded_policy_and_releases_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DPM_POSTGRES_MAX_CONNECTIONS", "1")
    monkeypatch.setenv("DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("DPM_POSTGRES_STATEMENT_TIMEOUT_MS", "9000")
    monkeypatch.setenv("DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS", "11000")
    calls: list[dict[str, Any]] = []
    closed: list[str] = []

    class FakeConnection:
        def close(self) -> None:
            closed.append("close")

    def fake_connect(dsn: str, **kwargs: Any) -> FakeConnection:
        calls.append({"dsn": dsn, **kwargs})
        return FakeConnection()

    connection = connect_postgres(
        "postgresql://user:password@localhost/manage",
        connect_fn=fake_connect,
        row_factory="dict_row",
        application_name="lotus-manage:test",
    )
    connection.close()
    second_connection = connect_postgres(
        "postgresql://user:password@localhost/manage",
        connect_fn=fake_connect,
        row_factory="dict_row",
        application_name="lotus-manage:test",
    )
    second_connection.close()

    assert calls[0] == {
        "dsn": "postgresql://user:password@localhost/manage",
        "row_factory": "dict_row",
        "connect_timeout": 7,
        "options": "-c statement_timeout=9000 -c idle_in_transaction_session_timeout=11000",
        "application_name": "lotus-manage:test",
    }
    assert closed == ["close", "close"]


def test_connect_postgres_acquire_timeout_is_stable_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("DPM_POSTGRES_MAX_CONNECTIONS", "1")
    monkeypatch.setenv("DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS", "1")

    class FakeConnection:
        def close(self) -> None:
            return None

    first_connection = connect_postgres(
        "postgresql://user:secret@localhost/manage",
        connect_fn=lambda *_args, **_kwargs: FakeConnection(),
        row_factory="dict_row",
        application_name="lotus-manage:test",
    )
    try:
        with caplog.at_level(logging.WARNING, logger="lotus-manage.postgres"):
            with pytest.raises(
                PostgresUnavailableError,
                match="POSTGRES_CONNECTION_ACQUIRE_TIMEOUT",
            ):
                connect_postgres(
                    "postgresql://user:secret@localhost/manage",
                    connect_fn=lambda *_args, **_kwargs: FakeConnection(),
                    row_factory="dict_row",
                    application_name="lotus-manage:test",
                )
    finally:
        first_connection.close()

    assert "acquire_timeout" in caplog.text
    assert "postgresql://user:secret" not in caplog.text


def test_connect_postgres_releases_slot_after_driver_failure() -> None:
    class TransientDriverError(Exception):
        sqlstate = "57P03"

    class FakeConnection:
        def close(self) -> None:
            return None

    calls = 0

    def flaky_connect(*_args: Any, **_kwargs: Any) -> FakeConnection:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TransientDriverError("database starting")
        return FakeConnection()

    with pytest.raises(PostgresUnavailableError, match="POSTGRES_CONNECTION_UNAVAILABLE"):
        connect_postgres(
            "postgresql://manage",
            connect_fn=flaky_connect,
            row_factory="dict_row",
            application_name="lotus-manage:test",
        )

    recovered = connect_postgres(
        "postgresql://manage",
        connect_fn=flaky_connect,
        row_factory="dict_row",
        application_name="lotus-manage:test",
    )
    recovered.close()
    assert calls == 2


def test_classify_postgres_error_uses_sqlstate_and_diagnostics() -> None:
    assert classify_postgres_error(SimpleNamespace(sqlstate="40001")) == "transient"
    assert classify_postgres_error(SimpleNamespace(sqlstate="23505")) == "permanent"
    assert (
        classify_postgres_error(SimpleNamespace(diag=SimpleNamespace(sqlstate="08006")))
        == "transient"
    )
    assert classify_postgres_error(Exception("network closed")) == "unknown"


def test_runtime_postgres_connections_use_shared_access_policy() -> None:
    direct_call_pattern = re.compile(r"(?<!connect_fn=)psycopg\.connect\(")
    runtime_paths = [
        *sorted((ROOT / "src" / "infrastructure").rglob("*.py")),
        ROOT / "src" / "api" / "production_cutover_contract.py",
    ]
    offenders = [
        str(path.relative_to(ROOT))
        for path in runtime_paths
        if path.name != "postgres_access.py" and direct_call_pattern.search(path.read_text())
    ]

    assert offenders == []
