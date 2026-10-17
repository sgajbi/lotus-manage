"""Ordinary execution enrollment transport proof without business HTTP or credentials."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
from pathlib import Path
import subprocess

import httpx
import pytest

from src.infrastructure.core_sourcing.client import (
    DpmCoreResolverClient,
    DpmCoreResolverConfig,
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)
from src.infrastructure.core_sourcing.request_context import (
    CoreExecutionError,
    load_core_execution_policy,
)

QCP = "https://core.test"
QUERY = "https://query.test"
ENV = {
    "CORE_EXECUTION_ENABLED": "true",
    "CORE_EXECUTION_KEY_ID": "test-key",
    "CORE_EXECUTION_SECRET": "synthetic-test-secret",
    "CORE_EXECUTION_SERVICE_IDENTITY": "lotus-manage",
    "CORE_EXECUTION_ACTOR_ID": "test-actor",
    "CORE_EXECUTION_ROLE": "test-role",
    "CORE_EXECUTION_ALLOWED_TENANTS": '["tenant-a","tenant-b"]',
    "CORE_EXECUTION_CAPABILITIES": '["source_data.portfolio_state_snapshot.read"]',
}


@pytest.fixture(autouse=True)
def enrolled(monkeypatch):
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)


def _resolver(handler):
    return DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url=QCP, query_base_url=QUERY),
        client=httpx.Client(transport=httpx.MockTransport(handler), trust_env=False),
    )


def _request(resolver, *, tenant="tenant-a", url=QCP + "/integration/test", selector=None):
    return resolver._post_source_product(
        url=url,
        payload={} if selector is None else selector,
        admitted_tenant_id=tenant,
        correlation_id="trace-1",
        unavailable_code="UNAVAILABLE",
        incomplete_code="INCOMPLETE",
    )


def _independent_signature(request, secret):
    names = (
        "x-enterprise-auth-key-id",
        "x-service-identity",
        "x-actor-id",
        "x-tenant-id",
        "x-role",
        "x-correlation-id",
        "x-enterprise-auth-timestamp",
        "x-capabilities",
    )
    value = "\n".join(
        ("lotus-enterprise-auth-context-v1", *(request.headers[name] for name in names))
    )
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


@pytest.mark.parametrize("field", list(ENV)[1:])
@pytest.mark.parametrize("value", [None, "", " "])
def test_enabled_missing_or_blank_settings_refuse(field, value):
    env = {**ENV}
    if value is None:
        del env[field]
    else:
        env[field] = value
    with pytest.raises(CoreExecutionError, match="CONFIGURATION"):
        load_core_execution_policy(QCP, QUERY, environment=env)


@pytest.mark.parametrize("value", ["[]", '["a","a"]', '["*"]', "[1]", "{}", '"a"', '["a,b"]'])
@pytest.mark.parametrize("field", ["CORE_EXECUTION_ALLOWED_TENANTS", "CORE_EXECUTION_CAPABILITIES"])
def test_exact_scope_arrays_refuse_malformed_duplicate_wildcard(field, value):
    with pytest.raises(CoreExecutionError, match="CONFIGURATION"):
        load_core_execution_policy(QCP, QUERY, environment={**ENV, field: value})


def test_default_off_and_strict_enablement():
    assert load_core_execution_policy("", None, environment={}) is None
    assert load_core_execution_policy("", None, environment={"CORE_EXECUTION_ENABLED": "0"}) is None
    for value in ("", "yes", "2"):
        with pytest.raises(CoreExecutionError, match="ENABLEMENT"):
            load_core_execution_policy(QCP, QUERY, environment={"CORE_EXECUTION_ENABLED": value})


def test_default_off_transport_preserves_unsigned_selector(monkeypatch):
    monkeypatch.delenv("CORE_EXECUTION_ENABLED", raising=False)

    def handler(request):
        assert json.loads(request.content) == {"tenant_id": "legacy-tenant"}
        assert request.headers["x-tenant-id"] == "legacy-tenant"
        assert not any(name.startswith("x-enterprise-auth-") for name in request.headers)
        return httpx.Response(200, json={"legacy": True})

    resolver = _resolver(handler)
    assert _request(resolver, tenant="legacy-tenant", selector={"tenant_id": "legacy-tenant"}) == {
        "legacy": True
    }
    resolver._client.close()


def test_composition_reuses_isolated_partition_and_shutdown(monkeypatch):
    from src.api.composition.core_resolver_service import build_core_resolver_client
    from src.infrastructure.source_http_clients import close_shared_source_http_clients

    monkeypatch.setenv("DPM_CORE_BASE_URL", QCP)
    monkeypatch.setenv("DPM_CORE_QUERY_BASE_URL", QUERY)
    close_shared_source_http_clients()
    first = build_core_resolver_client()
    second = build_core_resolver_client()
    assert first._client is second._client
    assert first._client.trust_env is False
    assert first._client.follow_redirects is False
    monkeypatch.setenv("CORE_EXECUTION_ACTOR_ID", "other-actor")
    third = build_core_resolver_client()
    assert third._client is not first._client
    first.close()
    assert not first._client.is_closed
    close_shared_source_http_clients()
    assert first._client.is_closed and third._client.is_closed


@pytest.mark.parametrize("timeout,attempts", [(float("nan"), 2), (0, 2), (61, 2), (2, 0), (2, 4)])
def test_enabled_retry_configuration_is_bounded(timeout, attempts):
    with pytest.raises(CoreExecutionError, match="TIMEOUT"):
        DpmCoreResolverClient(
            config=DpmCoreResolverConfig(
                base_url=QCP, query_base_url=QUERY, timeout_seconds=timeout, max_attempts=attempts
            )
        )


@pytest.mark.parametrize("refusal", ["wrong-secret", "stale"])
def test_native_verifier_refusal_is_not_local_credential_detection(refusal):
    seen = []

    def verifier(request):
        seen.append(request)
        expected = _independent_signature(
            request,
            "remote-different-secret"
            if refusal == "wrong-secret"
            else ENV["CORE_EXECUTION_SECRET"],
        )
        admitted = hmac.compare_digest(request.headers["x-enterprise-auth-signature"], expected)
        admitted = (
            admitted and abs(2000 - int(request.headers["x-enterprise-auth-timestamp"])) <= 300
        )
        return httpx.Response(200 if admitted else 403, json={"ok": admitted})

    resolver = _resolver(verifier)
    resolver._execution_auth._clock = lambda: 1000 if refusal == "stale" else 2000
    with pytest.raises(DpmCoreResolverError, match="INCOMPLETE"):
        _request(resolver)
    assert len(seen) == 1
    resolver._client.close()


@pytest.mark.parametrize(
    "origin",
    [
        "",
        QCP,
        "https://u:p@query.test",
        "file:///tmp/a",
        "https://query.test/path",
        "https://query.test#x",
        "https://query.test?x",
        "https://query.test\\evil",
    ],
)
def test_unsafe_or_ambiguous_query_configuration_refuses(origin):
    with pytest.raises(CoreExecutionError, match="CONFIGURATION"):
        load_core_execution_policy(QCP, origin, environment=ENV)


def test_signed_retry_is_fresh_and_credential_rotation_is_visible(monkeypatch):
    observed = []

    def handler(request):
        observed.append(request)
        secret = ENV["CORE_EXECUTION_SECRET"] if len(observed) == 1 else "rotated-test-secret"
        assert request.headers["x-enterprise-auth-signature"] == _independent_signature(
            request, secret
        )
        assert request.headers["x-service-identity"] == "lotus-manage"
        assert json.loads(request.content) == {"tenant_id": "tenant-a"}
        if len(observed) == 1:
            monkeypatch.setenv("CORE_EXECUTION_SECRET", "rotated-test-secret")
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    resolver = _resolver(handler)
    assert resolver._execution_auth is not None
    times = iter((1000, 1001))
    resolver._execution_auth._clock = lambda: next(times)
    assert _request(resolver, selector={"tenant_id": "tenant-a"}) == {"ok": True}
    assert [r.headers["x-enterprise-auth-timestamp"] for r in observed] == ["1000", "1001"]
    assert "x-tenant-id" not in resolver._client.headers
    resolver._client.close()


def test_concurrent_admitted_tenants_never_mutate_pool():
    def handler(request):
        assert request.headers["x-enterprise-auth-signature"] == _independent_signature(
            request, ENV["CORE_EXECUTION_SECRET"]
        )
        return httpx.Response(200, json={"tenant": request.headers["x-tenant-id"]})

    resolver = _resolver(handler)
    with ThreadPoolExecutor(max_workers=8) as executor:
        tenants = ["tenant-a", "tenant-b"] * 8
        assert (
            list(executor.map(lambda tenant: _request(resolver, tenant=tenant)["tenant"], tenants))
            == tenants
        )
    assert "x-tenant-id" not in resolver._client.headers
    resolver._client.close()


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 403])
def test_auth_and_redirect_refusals_never_retry_or_follow(status):
    seen = []
    resolver = _resolver(
        lambda request: (
            seen.append(request)
            or httpx.Response(status, headers={"location": "https://foreign.test"})
        )
    )
    with pytest.raises(DpmCoreResolverError):
        _request(resolver)
    assert len(seen) == 1
    resolver._client.close()


@pytest.mark.parametrize(
    "tenant,url,selector",
    [
        ("foreign", QCP + "/integration/test", {}),
        (None, QCP + "/integration/test", {}),
        ("tenant-a", "https://foreign.test/integration/test", {}),
        ("tenant-a", "https://u:p@core.test/integration/test", {}),
        ("tenant-a", QCP + "/integration/test#fragment", {}),
        ("tenant-a", QCP + "/integration/%2e%2e/test", {}),
        ("tenant-a", QCP + "/integration/test", {"tenant_id": "tenant-b"}),
    ],
)
def test_admission_refusals_precede_wire(tenant, url, selector):
    seen = []
    resolver = _resolver(lambda request: seen.append(request))
    with pytest.raises(CoreExecutionError):
        _request(resolver, tenant=tenant, url=url, selector=selector)
    assert seen == []
    resolver._client.close()


def test_query_plane_never_receives_signing_credentials(monkeypatch):
    def handler(request):
        assert request.url.host == "query.test"
        assert request.headers["x-tenant-id"] == "tenant-a"
        assert not any(name.startswith("x-enterprise-auth-") for name in request.headers)
        assert "x-service-identity" not in request.headers
        return httpx.Response(200, json={"global_fact": 1})

    resolver = _resolver(handler)
    monkeypatch.delenv("CORE_EXECUTION_SECRET")
    assert _request(resolver, url=QUERY + "/portfolios/p/cashflow-projection") == {"global_fact": 1}
    resolver._client.close()


def test_get_signs_admitted_context_without_changing_global_selector():
    def handler(request):
        assert request.method == "GET"
        assert dict(request.url.params) == {"currency": "USD"}
        assert "cookie" not in request.headers
        assert request.headers["x-tenant-id"] == "tenant-a"
        assert request.headers["x-enterprise-auth-signature"] == _independent_signature(
            request, ENV["CORE_EXECUTION_SECRET"]
        )
        return httpx.Response(200, json={"global": True})

    resolver = _resolver(handler)
    resolver._client.cookies.set("browser-session", "untrusted")
    assert resolver._get_source_product(
        url=QCP + "/integration/reference",
        params={"currency": "USD"},
        admitted_tenant_id="tenant-a",
        correlation_id="trace-1",
        unavailable_code="UNAVAILABLE",
        incomplete_code="INCOMPLETE",
    ) == {"global": True}
    resolver._client.close()


@pytest.mark.parametrize(
    "name",
    [
        "Authorization",
        "X-Actor-Id",
        "X-Service-Identity",
        "X-Role",
        "X-Capabilities",
        "X-Caller-Capabilities",
        "X-Enterprise-Auth-Signature",
    ],
)
def test_pooled_authority_is_refused(name):
    seen = []
    resolver = _resolver(lambda request: seen.append(request))
    resolver._client.headers[name] = "untrusted"
    with pytest.raises(CoreExecutionError, match="AUTHORITY"):
        _request(resolver)
    assert seen == []
    resolver._client.close()


def test_fallback_is_signed_secure_and_owned(monkeypatch):
    from src.infrastructure.core_sourcing import client as client_module

    actual_client = httpx.Client
    owned = []

    def factory(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["verify"] is True
        assert kwargs["follow_redirects"] is False

        def handler(request):
            assert request.headers["x-enterprise-auth-signature"] == _independent_signature(
                request, ENV["CORE_EXECUTION_SECRET"]
            )
            return httpx.Response(200, json={"ok": True})

        client = actual_client(transport=httpx.MockTransport(handler), **kwargs)
        owned.append(client)
        return client

    resolver = DpmCoreResolverClient(
        config=DpmCoreResolverConfig(base_url=QCP, query_base_url=QUERY)
    )
    monkeypatch.setattr(client_module.httpx, "Client", factory)
    assert _request(resolver) == {"ok": True}
    assert owned[0].is_closed


def test_enabled_unsafe_injected_proxy_client_refuses():
    with httpx.Client() as client:
        with pytest.raises(CoreExecutionError, match="UNSAFE_CLIENT"):
            DpmCoreResolverClient(
                config=DpmCoreResolverConfig(base_url=QCP, query_base_url=QUERY), client=client
            )


def test_removed_credential_and_invalid_clock_precede_wire(monkeypatch):
    seen = []
    resolver = _resolver(lambda request: seen.append(request))
    monkeypatch.delenv("CORE_EXECUTION_SECRET")
    with pytest.raises(CoreExecutionError, match="CREDENTIAL"):
        _request(resolver)
    monkeypatch.setenv("CORE_EXECUTION_SECRET", ENV["CORE_EXECUTION_SECRET"])
    resolver._execution_auth._clock = lambda: float("nan")
    with pytest.raises(CoreExecutionError, match="CREDENTIAL"):
        _request(resolver)
    assert seen == []
    resolver._client.close()


def test_expired_operation_budget_refuses_without_wire(monkeypatch):
    from src.infrastructure.core_sourcing import source_product_transport as transport

    seen = []
    resolver = _resolver(lambda request: seen.append(request))
    clock = iter((0.0, 291.0))
    monkeypatch.setattr(transport.time, "perf_counter", lambda: next(clock))
    with pytest.raises(DpmCoreResolverUnavailableError, match="UNAVAILABLE"):
        _request(resolver)
    assert seen == []
    resolver._client.close()


@pytest.mark.parametrize(
    "files,service",
    [
        (["docker-compose.yml"], "lotus-manage"),
        (["docker-compose.yml", "docker-compose.production.yml"], "lotus-manage"),
        (["docker-compose.ci-local.yml"], "ci-local"),
    ],
)
def test_actual_offline_compose_delivery_into_policy(files, service, tmp_path):
    # config never contacts the daemon. Supply a scrubbed environment and no .env file.
    import os

    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "COMSPEC",
            "PATHEXT",
            "PROGRAMFILES",
            "PROGRAMDATA",
        }
    }
    docker_config = tmp_path / "docker-config"
    docker_config.mkdir()
    env.update(DOCKER_CONFIG=str(docker_config), DOCKER_HOST="tcp://127.0.0.1:9")
    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    command = ["docker", "compose", "--env-file", str(empty)]
    for filename in files:
        command.extend(("-f", filename))
    command.extend(("config", "--format", "json"))
    for inputs in ({}, ENV, {**ENV, "CORE_EXECUTION_ROLE": ""}, {"CORE_EXECUTION_ENABLED": ""}):
        result = subprocess.run(
            command,
            cwd=Path.cwd(),
            env={**env, **inputs},
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        delivered = json.loads(result.stdout)["services"][service]["environment"]
        if not inputs:
            assert load_core_execution_policy(QCP, QUERY, environment=delivered) is None
        elif inputs.get("CORE_EXECUTION_ENABLED") == "":
            assert delivered["CORE_EXECUTION_ENABLED"] == ""
            with pytest.raises(CoreExecutionError, match="ENABLEMENT"):
                load_core_execution_policy(QCP, QUERY, environment=delivered)
        elif inputs["CORE_EXECUTION_ROLE"]:
            policy = load_core_execution_policy(QCP, QUERY, environment=delivered)
            assert policy.allowed_tenants == ("tenant-a", "tenant-b")
            assert policy.service_identity == "lotus-manage"
        else:
            with pytest.raises(CoreExecutionError, match="CONFIGURATION"):
                load_core_execution_policy(QCP, QUERY, environment=delivered)
