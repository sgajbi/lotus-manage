from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from threading import BoundedSemaphore, Lock
from typing import Any, Callable

logger = logging.getLogger("lotus-manage.postgres")

_TRANSIENT_SQLSTATES = frozenset(
    {
        "40001",
        "40P01",
        "53300",
        "53400",
        "55P03",
        "57014",
        "57P01",
        "57P02",
        "57P03",
    }
)
_TRANSIENT_SQLSTATE_PREFIXES = ("08",)
_PERMANENT_SQLSTATE_PREFIXES = ("22", "23", "42")


class PostgresAccessError(RuntimeError):
    pass


class PostgresConfigurationError(PostgresAccessError):
    pass


class PostgresUnavailableError(PostgresAccessError):
    pass


@dataclass(frozen=True)
class PostgresAccessPolicy:
    max_connections: int
    connect_timeout_seconds: int
    statement_timeout_ms: int
    idle_in_transaction_timeout_ms: int
    acquire_timeout_seconds: int

    @property
    def session_options(self) -> str:
        return (
            f"-c statement_timeout={self.statement_timeout_ms} "
            "-c idle_in_transaction_session_timeout="
            f"{self.idle_in_transaction_timeout_ms}"
        )


class ManagedPostgresConnection:
    def __init__(self, connection: Any, semaphore: BoundedSemaphore) -> None:
        self._connection = connection
        self._semaphore = semaphore
        self._released = False

    def __enter__(self) -> Any:
        enter = getattr(self._connection, "__enter__", None)
        if callable(enter):
            return enter()
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> bool:
        try:
            exit_context = getattr(self._connection, "__exit__", None)
            if callable(exit_context):
                return bool(exit_context(_exc_type, _exc, _tb))
            self.close()
            return False
        finally:
            self._release_once()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def close(self) -> None:
        try:
            close = getattr(self._connection, "close", None)
            if callable(close):
                close()
        finally:
            self._release_once()

    def _release_once(self) -> None:
        if not self._released:
            self._semaphore.release()
            self._released = True


_semaphore_lock = Lock()
_semaphore: BoundedSemaphore | None = None
_semaphore_capacity: int | None = None


def postgres_access_policy() -> PostgresAccessPolicy:
    return PostgresAccessPolicy(
        max_connections=_bounded_int_env(
            "DPM_POSTGRES_MAX_CONNECTIONS",
            default=10,
            minimum=1,
            maximum=100,
        ),
        connect_timeout_seconds=_bounded_int_env(
            "DPM_POSTGRES_CONNECT_TIMEOUT_SECONDS",
            default=3,
            minimum=1,
            maximum=30,
        ),
        statement_timeout_ms=_bounded_int_env(
            "DPM_POSTGRES_STATEMENT_TIMEOUT_MS",
            default=5000,
            minimum=100,
            maximum=60000,
        ),
        idle_in_transaction_timeout_ms=_bounded_int_env(
            "DPM_POSTGRES_IDLE_IN_TRANSACTION_TIMEOUT_MS",
            default=10000,
            minimum=1000,
            maximum=120000,
        ),
        acquire_timeout_seconds=_bounded_int_env(
            "DPM_POSTGRES_ACQUIRE_TIMEOUT_SECONDS",
            default=2,
            minimum=1,
            maximum=30,
        ),
    )


def validate_postgres_access_policy() -> None:
    postgres_access_policy()


def connect_postgres(
    dsn: str,
    *,
    connect_fn: Callable[..., Any],
    row_factory: Any,
    application_name: str,
) -> ManagedPostgresConnection:
    policy = postgres_access_policy()
    semaphore = _connection_semaphore(policy)
    acquired = semaphore.acquire(timeout=policy.acquire_timeout_seconds)
    if not acquired:
        _record_postgres_access(
            operation="connect",
            outcome="failure",
            reason="acquire_timeout",
            classification="transient",
        )
        logger.warning(
            "postgres.connection.acquire_timeout",
            extra={
                "extra_fields": {
                    "operation": "postgres.connect",
                    "reason": "acquire_timeout",
                    "classification": "transient",
                    "application_name": application_name,
                    "max_connections": policy.max_connections,
                    "acquire_timeout_seconds": policy.acquire_timeout_seconds,
                }
            },
        )
        raise PostgresUnavailableError("POSTGRES_CONNECTION_ACQUIRE_TIMEOUT")

    try:
        connection = connect_fn(
            dsn,
            row_factory=row_factory,
            connect_timeout=policy.connect_timeout_seconds,
            options=policy.session_options,
            application_name=application_name,
        )
    except Exception as exc:
        classification = classify_postgres_error(exc)
        semaphore.release()
        _record_postgres_access(
            operation="connect",
            outcome="failure",
            reason="connection_unavailable",
            classification=classification,
        )
        logger.warning(
            "postgres.connection.unavailable",
            extra={
                "extra_fields": {
                    "operation": "postgres.connect",
                    "reason": "connection_unavailable",
                    "classification": classification,
                    "application_name": application_name,
                    "connect_timeout_seconds": policy.connect_timeout_seconds,
                }
            },
        )
        raise PostgresUnavailableError("POSTGRES_CONNECTION_UNAVAILABLE") from exc

    _record_postgres_access(
        operation="connect",
        outcome="success",
        reason="connected",
        classification="none",
    )
    return ManagedPostgresConnection(connection, semaphore)


def classify_postgres_error(error: BaseException) -> str:
    sqlstate = _sqlstate(error)
    if not sqlstate:
        return "unknown"
    if sqlstate in _TRANSIENT_SQLSTATES or sqlstate.startswith(_TRANSIENT_SQLSTATE_PREFIXES):
        return "transient"
    if sqlstate.startswith(_PERMANENT_SQLSTATE_PREFIXES):
        return "permanent"
    return "unknown"


def _connection_semaphore(policy: PostgresAccessPolicy) -> BoundedSemaphore:
    global _semaphore, _semaphore_capacity
    with _semaphore_lock:
        if _semaphore is None or _semaphore_capacity != policy.max_connections:
            _semaphore = BoundedSemaphore(policy.max_connections)
            _semaphore_capacity = policy.max_connections
        return _semaphore


def _bounded_int_env(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise PostgresConfigurationError(f"POSTGRES_ACCESS_POLICY_INVALID:{name}") from exc
    if value < minimum or value > maximum:
        raise PostgresConfigurationError(
            f"POSTGRES_ACCESS_POLICY_OUT_OF_RANGE:{name}:{minimum}:{maximum}"
        )
    return value


def _record_postgres_access(
    *,
    operation: str,
    outcome: str,
    reason: str,
    classification: str,
) -> None:
    from src.api.observability import record_postgres_access

    record_postgres_access(
        operation=operation,
        outcome=outcome,
        reason=reason,
        classification=classification,
    )


def _sqlstate(error: BaseException) -> str:
    sqlstate = getattr(error, "sqlstate", "")
    if isinstance(sqlstate, str) and sqlstate:
        return sqlstate
    diagnostics = getattr(error, "diag", None)
    diagnostic_sqlstate = getattr(diagnostics, "sqlstate", "") if diagnostics is not None else ""
    return diagnostic_sqlstate if isinstance(diagnostic_sqlstate, str) else ""


def _reset_postgres_access_state_for_tests() -> None:
    global _semaphore, _semaphore_capacity
    with _semaphore_lock:
        _semaphore = None
        _semaphore_capacity = None
