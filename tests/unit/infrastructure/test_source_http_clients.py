from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest

from src.infrastructure.source_http_clients import (
    build_source_http_client_policy,
    close_shared_source_http_clients,
    get_shared_source_http_client,
    get_partitioned_source_http_client,
)


def test_source_http_policy_uses_bounded_common_and_authority_specific_env(monkeypatch) -> None:
    monkeypatch.setenv("DPM_SOURCE_HTTP_MAX_CONNECTIONS", "9")
    monkeypatch.setenv("DPM_SOURCE_HTTP_MAX_KEEPALIVE_CONNECTIONS", "4")
    monkeypatch.setenv("DPM_SOURCE_HTTP_CONNECT_TIMEOUT_SECONDS", "0.2")
    monkeypatch.setenv("DPM_SOURCE_HTTP_POOL_TIMEOUT_SECONDS", "0.3")
    monkeypatch.setenv("DPM_SOURCE_HTTP_KEEPALIVE_EXPIRY_SECONDS", "12")
    monkeypatch.setenv("DPM_RISK_HTTP_MAX_CONNECTIONS", "3")
    monkeypatch.setenv("DPM_RISK_HTTP_MAX_KEEPALIVE_CONNECTIONS", "20")

    common_policy = build_source_http_client_policy("core", request_timeout_seconds=2.5)
    risk_policy = build_source_http_client_policy("risk", request_timeout_seconds=99)
    timeout = common_policy.timeout()
    limits = common_policy.limits()

    assert common_policy.max_connections == 9
    assert common_policy.max_keepalive_connections == 4
    assert common_policy.connect_timeout_seconds == 0.2
    assert common_policy.pool_timeout_seconds == 0.3
    assert common_policy.keepalive_expiry_seconds == 12
    assert timeout.connect == 0.2
    assert timeout.pool == 0.3
    assert limits.max_connections == 9
    assert limits.max_keepalive_connections == 4
    assert risk_policy.max_connections == 3
    assert risk_policy.max_keepalive_connections == 3
    assert risk_policy.request_timeout_seconds == 60.0


def test_source_http_policy_uses_defaults_for_invalid_numeric_env(monkeypatch) -> None:
    monkeypatch.setenv("DPM_SOURCE_HTTP_MAX_CONNECTIONS", "not-an-int")
    monkeypatch.setenv("DPM_SOURCE_HTTP_MAX_KEEPALIVE_CONNECTIONS", "not-an-int")
    monkeypatch.setenv("DPM_SOURCE_HTTP_CONNECT_TIMEOUT_SECONDS", "not-a-float")
    monkeypatch.setenv("DPM_SOURCE_HTTP_POOL_TIMEOUT_SECONDS", "not-a-float")
    monkeypatch.setenv("DPM_SOURCE_HTTP_KEEPALIVE_EXPIRY_SECONDS", "not-a-float")

    policy = build_source_http_client_policy(
        "core",
        request_timeout_seconds="not-a-float",  # type: ignore[arg-type]
    )

    assert policy.max_connections == 20
    assert policy.max_keepalive_connections == 10
    assert policy.request_timeout_seconds == 2.0
    assert policy.connect_timeout_seconds == 1.0
    assert policy.pool_timeout_seconds == 1.0
    assert policy.keepalive_expiry_seconds == 30.0


def test_shared_source_http_client_is_reused_closed_and_recreated() -> None:
    close_shared_source_http_clients()
    policy = build_source_http_client_policy("advise", request_timeout_seconds=1.0)

    first = get_shared_source_http_client("advise", policy=policy)
    second = get_shared_source_http_client("advise", policy=policy)

    assert first is second
    assert not first.is_closed

    close_shared_source_http_clients()
    assert first.is_closed

    replacement = get_shared_source_http_client("advise", policy=policy)
    try:
        assert replacement is not first
        assert not replacement.is_closed
    finally:
        close_shared_source_http_clients()


def test_shared_source_http_client_creation_is_stable_under_concurrent_resolution() -> None:
    close_shared_source_http_clients()
    policy = build_source_http_client_policy("core", request_timeout_seconds=1.0)

    def _resolve_client_id(_: int) -> int:
        return id(get_shared_source_http_client("core", policy=policy))

    try:
        with ThreadPoolExecutor(max_workers=16) as pool:
            client_ids = set(pool.map(_resolve_client_id, range(64)))

        assert len(client_ids) == 1
    finally:
        close_shared_source_http_clients()


def test_partitioned_native_clients_keep_roles_policy_and_legacy_pool_separate(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://must-not-be-used.invalid:1234")
    close_shared_source_http_clients()
    policy = build_source_http_client_policy("composite", request_timeout_seconds=1)
    auth = httpx.BasicAuth("synthetic", "unit-only")
    try:
        legacy = get_shared_source_http_client("composite", policy=policy)
        assembly = get_partitioned_source_http_client(
            "composite", partition="assembly-public-policy", policy=policy, auth=auth
        )
        verification = get_partitioned_source_http_client(
            "composite", partition="verification-public-policy", policy=policy, auth=auth
        )
        changed = get_partitioned_source_http_client(
            "composite",
            partition="assembly-public-policy",
            policy=replace(policy, request_timeout_seconds=3),
            auth=auth,
        )
        assert len({id(client) for client in (legacy, assembly, verification, changed)}) == 4
        assert assembly.follow_redirects is False and assembly.trust_env is False
        assert verification.follow_redirects is False and verification.trust_env is False
        assert "Authorization" not in assembly.headers
        assert assembly.timeout.read == 1 and changed.timeout.read == 3
        with ThreadPoolExecutor(max_workers=8) as pool:
            resolved = set(
                pool.map(
                    lambda _: id(
                        get_partitioned_source_http_client(
                            "composite",
                            partition="assembly-public-policy",
                            policy=policy,
                            auth=auth,
                        )
                    ),
                    range(24),
                )
            )
        assert resolved == {id(assembly)}
        assembly.close()
        replacement = get_partitioned_source_http_client(
            "composite", partition="assembly-public-policy", policy=policy, auth=auth
        )
        assert replacement is not assembly
    finally:
        close_shared_source_http_clients()
    assert all(
        client.is_closed for client in (legacy, assembly, verification, changed, replacement)
    )


def test_native_pool_requires_an_explicit_partition() -> None:
    with pytest.raises(ValueError, match="PARTITION_REQUIRED"):
        get_partitioned_source_http_client(
            "composite",
            partition="",
            policy=build_source_http_client_policy("composite", request_timeout_seconds=1),
            auth=httpx.BasicAuth("synthetic", "unit-only"),
        )
