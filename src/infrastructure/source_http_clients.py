from __future__ import annotations

from dataclasses import dataclass
import os
from threading import RLock
from typing import Literal

import httpx

SourceHttpClientName = Literal["core", "risk", "advise"]


@dataclass(frozen=True)
class SourceHttpClientPolicy:
    request_timeout_seconds: float
    connect_timeout_seconds: float
    pool_timeout_seconds: float
    max_connections: int
    max_keepalive_connections: int
    keepalive_expiry_seconds: float

    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
            pool=self.pool_timeout_seconds,
        )

    def limits(self) -> httpx.Limits:
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry_seconds,
        )


_SHARED_SOURCE_HTTP_CLIENTS: dict[SourceHttpClientName, httpx.Client] = {}
_SHARED_SOURCE_HTTP_CLIENTS_LOCK = RLock()


def build_source_http_client_policy(
    source: SourceHttpClientName,
    *,
    request_timeout_seconds: float,
) -> SourceHttpClientPolicy:
    prefix = _source_env_prefix(source)
    max_connections = _bounded_int_env(
        specific=f"{prefix}_HTTP_MAX_CONNECTIONS",
        common="DPM_SOURCE_HTTP_MAX_CONNECTIONS",
        default=20,
        minimum=1,
        maximum=200,
    )
    max_keepalive = _bounded_int_env(
        specific=f"{prefix}_HTTP_MAX_KEEPALIVE_CONNECTIONS",
        common="DPM_SOURCE_HTTP_MAX_KEEPALIVE_CONNECTIONS",
        default=min(10, max_connections),
        minimum=0,
        maximum=max_connections,
    )
    return SourceHttpClientPolicy(
        request_timeout_seconds=_bounded_float(
            seconds=request_timeout_seconds,
            default=2.0,
            minimum=0.1,
            maximum=60.0,
        ),
        connect_timeout_seconds=_bounded_float_env(
            specific=f"{prefix}_HTTP_CONNECT_TIMEOUT_SECONDS",
            common="DPM_SOURCE_HTTP_CONNECT_TIMEOUT_SECONDS",
            default=1.0,
            minimum=0.1,
            maximum=30.0,
        ),
        pool_timeout_seconds=_bounded_float_env(
            specific=f"{prefix}_HTTP_POOL_TIMEOUT_SECONDS",
            common="DPM_SOURCE_HTTP_POOL_TIMEOUT_SECONDS",
            default=1.0,
            minimum=0.1,
            maximum=30.0,
        ),
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive,
        keepalive_expiry_seconds=_bounded_float_env(
            specific=f"{prefix}_HTTP_KEEPALIVE_EXPIRY_SECONDS",
            common="DPM_SOURCE_HTTP_KEEPALIVE_EXPIRY_SECONDS",
            default=30.0,
            minimum=1.0,
            maximum=300.0,
        ),
    )


def get_shared_source_http_client(
    source: SourceHttpClientName,
    *,
    policy: SourceHttpClientPolicy,
) -> httpx.Client:
    with _SHARED_SOURCE_HTTP_CLIENTS_LOCK:
        client = _SHARED_SOURCE_HTTP_CLIENTS.get(source)
        if client is None or client.is_closed:
            client = httpx.Client(timeout=policy.timeout(), limits=policy.limits())
            _SHARED_SOURCE_HTTP_CLIENTS[source] = client
        return client


def close_shared_source_http_clients() -> None:
    with _SHARED_SOURCE_HTTP_CLIENTS_LOCK:
        for client in tuple(_SHARED_SOURCE_HTTP_CLIENTS.values()):
            if not client.is_closed:
                client.close()
        _SHARED_SOURCE_HTTP_CLIENTS.clear()


def _source_env_prefix(source: SourceHttpClientName) -> str:
    return {
        "core": "DPM_CORE",
        "risk": "DPM_RISK",
        "advise": "DPM_ADVISE",
    }[source]


def _bounded_int_env(
    *,
    specific: str,
    common: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(specific) or os.getenv(common)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def _bounded_float_env(
    *,
    specific: str,
    common: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = os.getenv(specific) or os.getenv(common)
    if raw is None or not raw.strip():
        return default
    try:
        parsed_seconds = float(raw)
    except ValueError:
        return default
    return _bounded_float(
        seconds=parsed_seconds,
        default=default,
        minimum=minimum,
        maximum=maximum,
    )


def _bounded_float(
    *,
    seconds: float,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        parsed = float(seconds)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)
