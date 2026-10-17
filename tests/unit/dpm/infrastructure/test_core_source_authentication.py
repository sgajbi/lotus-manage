"""Fixed producer-reviewed protocol answers and actual synthetic prepared requests."""

from copy import deepcopy
import hashlib
import hmac
import json

import httpx
import pytest
from pydantic import ValidationError

from src.infrastructure.composites.core_source_authentication import (
    CoreRetainedReadAuth,
    CoreSourceAuthenticationPolicy,
    _context_bytes,
    _signature,
)

NOW = 1792080000
SECRET = "public-synthetic-manage-core-hmac-v1-key"
ORIGIN = "https://core.example"
PATHS = (
    "/integration/portfolio-historical-registries/query",
    "/integration/financial-source-cuts/query",
)
CAPABILITIES = (
    "source_data.portfolio_historical_registry.read",
    "source_data.portfolio_financial_source_cut.read",
)
HEADERS = {
    "X-Enterprise-Auth-Key-Id": "synthetic-core-key-v1",
    "X-Service-Identity": "lotus-manage",
    "X-Actor-Id": "synthetic-manage-reader",
    "X-Tenant-Id": "synthetic-tenant",
    "X-Role": "system",
    "X-Correlation-Id": "synthetic-correlation-001",
    "X-Enterprise-Auth-Timestamp": "1792080000",
    "X-Capabilities": ",".join(CAPABILITIES),
}
ASCII_SIGNATURE = "509f603c9e00d7db7939488c58155c31814373f3426c79c8d3242041c58d1228"
UNICODE_SIGNATURE = "dc26eb3f661088a6c46227c2135fd175fb739686ac5fbb0efd511c76915f7290"
ASCII_LINES = (
    "lotus-enterprise-auth-context-v1",
    "synthetic-core-key-v1",
    "lotus-manage",
    "synthetic-manage-reader",
    "synthetic-tenant",
    "system",
    "synthetic-correlation-001",
    "1792080000",
    "source_data.portfolio_financial_source_cut.read,source_data.portfolio_historical_registry.read",
)


def policy(**changes):
    return CoreSourceAuthenticationPolicy.model_validate_json(
        json.dumps(
            {
                "origin": ORIGIN,
                "tenant_id": "synthetic-tenant",
                "service_identity": "lotus-manage",
                "actor_id": "synthetic-manage-reader",
                "role": "system",
                "key_id": "synthetic-core-key-v1",
                "capabilities": list(CAPABILITIES),
                "credential_env": "CORE_AUTH_SYNTHETIC_KEY",
                **changes,
            }
        )
    )


def auth(configuration=None, **changes):
    return CoreRetainedReadAuth(
        policy() if configuration is None else configuration,
        credential_resolver=changes.pop("credential_resolver", lambda _: SECRET),
        clock=changes.pop("clock", lambda: NOW),
        correlation_id_factory=changes.pop(
            "correlation_id_factory", lambda: HEADERS["X-Correlation-Id"]
        ),
        **changes,
    )


def client(authentication, calls, *, follow_redirects=False, status=200):
    def send(request):
        calls.append(request)
        return httpx.Response(status, headers={"Location": "https://foreign.example/redirect"})

    return httpx.Client(
        auth=authentication,
        transport=httpx.MockTransport(send),
        follow_redirects=follow_redirects,
    )


def reference_accepts(headers, now=NOW):
    """Independent literal field recipe; fixed reviewed answers anchor its HMAC oracle."""
    fields = {key.lower(): value.strip() for key, value in headers.items()}
    canonical = "\n".join(
        [
            "lotus-enterprise-auth-context-v1",
            fields["x-enterprise-auth-key-id"],
            fields["x-service-identity"],
            fields["x-actor-id"],
            fields["x-tenant-id"],
            fields["x-role"],
            fields["x-correlation-id"],
            fields["x-enterprise-auth-timestamp"],
            ",".join(sorted({v.strip() for v in fields["x-capabilities"].split(",") if v.strip()})),
        ]
    ).encode("utf-8")
    expected = hmac.new(SECRET.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    return (
        not fields.get("authorization")
        and fields["x-enterprise-auth-key-id"] == "synthetic-core-key-v1"
        and abs(now - int(fields["x-enterprise-auth-timestamp"])) <= 300
        and hmac.compare_digest(expected, fields["x-enterprise-auth-signature"])
    )


@pytest.mark.parametrize("unicode", [False, True])
def test_independently_fixed_ascii_and_unicode_canonical_bytes_and_signatures(unicode):
    headers, lines = deepcopy(HEADERS), list(ASCII_LINES)
    if unicode:
        headers["X-Actor-Id"] = lines[3] = "synthetic-café"
        headers["X-Correlation-Id"] = lines[6] = "synthetic-correlation-Ω"
    expected = "\n".join(lines).encode("utf-8")
    assert expected.count(b"\n") == 8 and not expected.endswith(b"\n")
    assert _context_bytes(headers) == expected
    assert hashlib.sha256(expected).hexdigest() == (
        "a88278e3babe9132d1dddd9229b524c9ad95490e61f125d4ab56d21be015d8c3"
        if unicode
        else "2d097e78551250b4b706660a8a0e8003b503fe879c87e0afecad2313aed30402"
    )
    signature = UNICODE_SIGNATURE if unicode else ASCII_SIGNATURE
    assert _signature(headers, SECRET) == signature
    assert reference_accepts(headers | {"X-Enterprise-Auth-Signature": signature})


def test_producer_case_whitespace_capability_normalization_and_unbound_headers():
    headers = {key.upper(): "  " + value + "  " for key, value in HEADERS.items()}
    headers["X-CAPABILITIES"] = (
        " ," + CAPABILITIES[1] + ", " + CAPABILITIES[0] + "," + CAPABILITIES[1] + ", "
    )
    headers["Traceparent"] = "unbound-attribution"
    assert _signature(headers, SECRET) == ASCII_SIGNATURE
    assert (
        _signature({" " + key: value for key, value in HEADERS.items()}, SECRET) != ASCII_SIGNATURE
    )


@pytest.mark.parametrize(
    "field,value,expected",
    [
        (
            "X-Enterprise-Auth-Key-Id",
            "synthetic-core-key-v1-mutant",
            "a6a0fb0824ff34ab07b1767f9df36c61acf15e645972a6827ba88ff686f68dfc",
        ),
        (
            "X-Service-Identity",
            "lotus-manage-mutant",
            "30c9d6cfd8f1cad5f89464f60fd2999f534da639a56b855e4efd9f94f12a6d98",
        ),
        (
            "X-Actor-Id",
            "synthetic-manage-reader-mutant",
            "12c727d7ebc654baea48a60a2eee567d7439b8bff22ef329c892b9e1e8d344f0",
        ),
        (
            "X-Tenant-Id",
            "synthetic-tenant-mutant",
            "7390474e320756431a9d18999b359a316645b8389fe3d6f406ba524698b8c91f",
        ),
        (
            "X-Role",
            "system-mutant",
            "fcf6d1c8533c38ad3c9a88be82ee124d09b4bce6528632cce11de34c9d3a92f1",
        ),
        (
            "X-Correlation-Id",
            "synthetic-correlation-001-mutant",
            "155ac5f18c3ffc54ef546e7db8ead2ba0967f937e5b895fd98cd788e44cabfdb",
        ),
        (
            "X-Enterprise-Auth-Timestamp",
            "1792080001",
            "cea7297b1d49cd76b4d15c0ad9509b9868bd13d7d7247b0639fc1329cd6f017a",
        ),
        (
            "X-Capabilities",
            CAPABILITIES[0] + "," + CAPABILITIES[1] + "-mutant",
            "3f98833dbf4c16da724f9d97e196bbdd50d4be9ce7149ecee6649b0d000bdf35",
        ),
    ],
)
def test_every_signed_field_matches_fixed_resigned_mutant_and_original_signature_refuses(
    field, value, expected
):
    changed = HEADERS | {field: value}
    assert _signature(changed, SECRET) == expected
    assert not reference_accepts(changed | {"X-Enterprise-Auth-Signature": ASCII_SIGNATURE})


@pytest.mark.parametrize(
    "offset,expected,accepted",
    [
        (-301, "a2df37e853d8170fc80b3678bcdd3e1cffbaffdfa2414a542b8ba5cc721b8912", False),
        (-300, "17cfd807260e2518debed184405a1f2687759fc573ddff98f0936fcc28dc8c8e", True),
        (300, "d9a88cccda9586e7234f3014fb3d883338b7db5791a45fe2fb490a4b0607e4a8", True),
        (301, "983d8b1a2884406c05f3afadfb092ed6907a01795f01e393f5744f90db493536", False),
    ],
)
def test_fixed_producer_timestamp_skew_boundaries(offset, expected, accepted):
    headers = HEADERS | {"X-Enterprise-Auth-Timestamp": str(NOW + offset)}
    assert _signature(headers, SECRET) == expected
    assert reference_accepts(headers | {"X-Enterprise-Auth-Signature": expected}) is accepted


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("tenant", [None, "synthetic-tenant", " synthetic-tenant "])
def test_actual_prepared_request_has_fixed_compatible_context_without_bearer_or_secret(
    path, tenant
):
    calls = []
    authentication = auth()
    with client(authentication, calls, follow_redirects=False) as connection:
        connection.post(
            ORIGIN + path,
            headers={} if tenant is None else {"X-Tenant-Id": tenant},
            json={"cut": "fixed"},
        )
    request = calls[0]
    assert len(request.headers.get_list("X-Tenant-Id")) == 1
    assert "Authorization" not in request.headers
    assert SECRET not in str(request.headers) + str(request.content) + repr(authentication)
    assert request.headers["X-Enterprise-Auth-Signature"] == ASCII_SIGNATURE
    assert reference_accepts(dict(request.headers))
    assert {name.lower(): request.headers[name] for name in HEADERS} == {
        name.lower(): value for name, value in HEADERS.items()
    } | {"x-capabilities": ",".join(sorted(CAPABILITIES))}


@pytest.mark.parametrize(
    "method,url",
    [
        ("GET", ORIGIN + PATHS[0]),
        ("POST", "http://core.example" + PATHS[0]),
        ("POST", "https://foreign.example" + PATHS[0]),
        ("POST", "https://core.example:444" + PATHS[0]),
        ("POST", "https://user:private@core.example" + PATHS[0]),
        ("POST", ORIGIN + PATHS[0] + "?"),
        ("POST", ORIGIN + PATHS[0] + "?tenant=foreign"),
        ("POST", ORIGIN + PATHS[0] + "#fragment"),
        ("POST", ORIGIN + PATHS[0] + "/"),
        ("POST", ORIGIN + "/integration/%66inancial-source-cuts/query"),
    ],
)
def test_exact_method_origin_path_userinfo_query_fragment_refuse_before_io(method, url):
    calls, resolved = [], []
    with client(
        auth(credential_resolver=lambda name: resolved.append(name) or SECRET), calls
    ) as connection:
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_TARGET_FORBIDDEN$"):
            connection.request(method, url)
    assert calls == resolved == []


@pytest.mark.parametrize(
    "name", [*HEADERS, "X-Enterprise-Auth-Signature", "Authorization", "Proxy-Authorization"]
)
def test_duplicate_authority_headers_refuse_even_when_identical(name):
    calls = []
    with client(auth(), calls) as connection:
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_DUPLICATE_AUTHORITY$"):
            connection.post(ORIGIN + PATHS[0], headers=[(name, "same"), (name.lower(), "same")])
    assert calls == []


@pytest.mark.parametrize(
    "name",
    [name for name in HEADERS if name != "X-Tenant-Id"]
    + ["Authorization", "X-Enterprise-Auth-Signature", "X-Enterprise-Auth-Nonce"],
)
def test_caller_authority_is_not_adopted_even_empty_or_matching(name):
    calls = []
    with client(auth(), calls) as connection:
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_CALLER_AUTHORITY_FORBIDDEN$"):
            connection.post(ORIGIN + PATHS[0], headers={name: HEADERS.get(name, "")})
    assert calls == []


@pytest.mark.parametrize("tenant", ["foreign", "synthetic-tenant,synthetic-tenant", ""])
def test_conflicting_owned_tenant_assertion_is_not_rewritten(tenant):
    calls = []
    with client(auth(), calls) as connection:
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_TENANT_MISMATCH$"):
            connection.post(ORIGIN + PATHS[0], headers={"X-Tenant-Id": tenant})
    assert calls == []


@pytest.mark.parametrize("secret", [None, "", " ", " padded ", b"wrong-type"])
def test_missing_or_unclean_credential_is_bounded_and_never_sent(secret):
    calls = []
    with client(auth(credential_resolver=lambda _: secret), calls) as connection:
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_CREDENTIAL_UNAVAILABLE$"):
            connection.post(ORIGIN + PATHS[0])
    assert calls == []


def test_resolver_failure_never_exposes_secret_in_error_or_auth_representation():
    def failing(_):
        raise RuntimeError(SECRET)

    calls, authentication = [], auth(credential_resolver=failing)
    with client(authentication, calls) as connection:
        with pytest.raises(ValueError) as caught:
            connection.post(ORIGIN + PATHS[0])
    assert SECRET not in str(caught.value) + repr(authentication) + str(authentication.__dict__)
    assert caught.value.__suppress_context__
    assert calls == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("service_identity", "foreign"),
        ("actor_id", "x" * 129),
        ("actor_id", "café"),
        ("role", " bad "),
        ("key_id", "bad\nkey"),
        ("credential_env", ""),
        ("origin", "https://core.example/path"),
        ("capabilities", [CAPABILITIES[0], CAPABILITIES[0]]),
        ("secret", SECRET),
    ],
)
def test_closed_policy_rejects_invalid_or_nontransport_assertions(field, value):
    with pytest.raises(ValidationError):
        policy(**{field: value})


@pytest.mark.parametrize("construction", ["copy", "copied_extra", "construct", "absent"])
def test_invalid_copied_constructed_or_absent_policy_refuses_before_io(construction):
    configuration = policy()
    if construction == "copy":
        configuration = configuration.model_copy(update={"service_identity": "foreign"})
    elif construction == "copied_extra":
        configuration = configuration.model_copy(update={"secret": SECRET})
    elif construction == "construct":
        configuration = CoreSourceAuthenticationPolicy.model_construct(
            **(configuration.model_dump() | {"credential_env": ""})
        )
    else:
        configuration = None
    calls = []
    with client(CoreRetainedReadAuth(configuration), calls) as connection:
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_POLICY_(INVALID|UNAVAILABLE)$"):
            connection.post(ORIGIN + PATHS[0])
    assert calls == []


@pytest.mark.parametrize(
    "dependency,value",
    [
        ("clock", float("nan")),
        ("clock", float("inf")),
        ("clock", -1),
        ("clock", True),
        ("correlation_id_factory", ""),
        ("correlation_id_factory", "x" * 129),
        ("correlation_id_factory", "with\nnewline"),
    ],
)
def test_invalid_server_clock_or_correlation_refuses_before_io(dependency, value):
    calls = []
    with client(auth(**{dependency: lambda: value}), calls) as connection:
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_CONTEXT_INVALID$"):
            connection.post(ORIGIN + PATHS[0])
    assert calls == []


def test_fresh_key_clock_correlation_for_repeated_and_independent_reader_instances():
    resolved, calls = [], []
    ticks, correlations = iter([NOW, NOW + 1, NOW + 2]), iter(["A1", "A2", "C1"])
    secrets = iter([SECRET, SECRET + "-rotated", SECRET])

    def resolve(name):
        resolved.append(name)
        return next(secrets)

    first = auth(
        credential_resolver=resolve,
        clock=lambda: next(ticks),
        correlation_id_factory=lambda: next(correlations),
    )
    second = auth(
        credential_resolver=resolve,
        clock=lambda: next(ticks),
        correlation_id_factory=lambda: next(correlations),
    )
    with client(first, calls) as assembler, client(second, calls) as verifier:
        assembler.post(ORIGIN + PATHS[0])
        assembler.post(ORIGIN + PATHS[1])
        verifier.post(ORIGIN + PATHS[0])
    assert resolved == ["CORE_AUTH_SYNTHETIC_KEY"] * 3
    assert [r.headers["X-Enterprise-Auth-Timestamp"] for r in calls] == [
        str(NOW + n) for n in range(3)
    ]
    assert [r.headers["X-Correlation-Id"] for r in calls] == ["A1", "A2", "C1"]
    assert len({r.headers["X-Enterprise-Auth-Signature"] for r in calls}) == 3
    assert SECRET not in str(first.__dict__) + str(second.__dict__)


def test_no_follow_client_receives_one_redirect_and_adapter_refuses_it():
    calls = []
    with client(auth(), calls, follow_redirects=False, status=307) as connection:
        assert connection.follow_redirects is False
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_REDIRECT_REFUSED$"):
            connection.post(ORIGIN + PATHS[0])
    assert len(calls) == 1


def test_arbitrary_follow_client_internal_redirects_are_outside_auth_flow_guarantee():
    calls = []

    def send(request):
        calls.append(request)
        return (
            httpx.Response(307, headers={"Location": "https://foreign.example/redirect"})
            if len(calls) == 1
            else httpx.Response(200)
        )

    with httpx.Client(
        auth=auth(), transport=httpx.MockTransport(send), follow_redirects=True
    ) as connection:
        connection.post(ORIGIN + PATHS[0])
    assert len(calls) == 2
    assert calls[1].url.host == "foreign.example"
    assert calls[1].headers["X-Enterprise-Auth-Signature"] == ASCII_SIGNATURE


def test_context_signature_does_not_claim_body_or_route_binding_or_replay_prevention():
    calls = []
    with client(auth(), calls, follow_redirects=False) as connection:
        connection.post(ORIGIN + PATHS[0], json={"cut": "first"})
        connection.post(ORIGIN + PATHS[1], json={"cut": "different"})
    assert calls[0].content != calls[1].content
    assert (
        calls[0].headers["X-Enterprise-Auth-Signature"]
        == calls[1].headers["X-Enterprise-Auth-Signature"]
    )
    assert all(reference_accepts(dict(request.headers)) for request in calls)


def pooled_signed_connection(
    monkeypatch, calls, *, headers=None, cookies=None, authentication=None
):
    """Use the actual policy pool with an owned synthetic transport and isolated registry."""
    from src.infrastructure import source_http_clients

    original_client = httpx.Client
    monkeypatch.setattr(source_http_clients, "_SHARED_SOURCE_HTTP_CLIENTS", {})

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={},
            headers={"Set-Cookie": "pooled-response=public-synthetic-response; Path=/"},
        )

    def create_client(**options):
        return original_client(
            **options, headers=headers, cookies=cookies, transport=httpx.MockTransport(respond)
        )

    monkeypatch.setattr(source_http_clients.httpx, "Client", create_client)
    transport_policy = source_http_clients.SourceHttpClientPolicy(2, 1, 1, 4, 2, 10)
    authentication = authentication or auth()

    def acquire():
        return source_http_clients.get_partitioned_source_http_client(
            "core",
            partition="public-synthetic-same-tenant-policy",
            policy=transport_policy,
            auth=authentication,
        )

    return acquire(), acquire, authentication


@pytest.mark.parametrize(
    "cookie_source",
    ["configured", "default_header", "response", "request_header", "duplicate_header"],
)
def test_signed_partition_pool_scrubs_merged_cookie_without_mutating_shared_state(
    monkeypatch, cookie_source
):
    from src.infrastructure.authority_http import _post_json_attempt

    calls = []
    headers = (
        {"Cookie": "manual=public-synthetic-default"} if cookie_source == "default_header" else None
    )
    if cookie_source == "duplicate_header":
        headers = [
            ("Cookie", "first=public-synthetic-one"),
            ("cookie", "second=public-synthetic-two"),
        ]
    cookies = (
        {"pooled-configured": "public-synthetic-configured"}
        if cookie_source == "configured"
        else None
    )
    connection, acquire, authentication = pooled_signed_connection(
        monkeypatch, calls, headers=headers, cookies=cookies
    )
    with connection:
        original_headers = list(connection.headers.multi_items())
        original_auth_state = dict(authentication.__dict__)
        for path in PATHS:
            assert acquire() is connection
            request_headers = {"Accept-Encoding": "identity"}
            if cookie_source == "request_header":
                request_headers["Cookie"] = "manual=public-synthetic-request"
            response = _post_json_attempt(
                client=connection,
                url=ORIGIN + path,
                payload={},
                headers=request_headers,
                unavailable_error="SYNTHETIC_UNAVAILABLE",
                invalid_response_error="SYNTHETIC_INVALID",
                maximum_response_bytes=1024,
            )
            assert response.status_code == 200
            assert list(connection.headers.multi_items()) == original_headers
            assert connection.auth is authentication
            assert authentication.__dict__ == original_auth_state
            assert connection.cookies.get("pooled-response") == "public-synthetic-response"
            if cookies:
                assert connection.cookies.get("pooled-configured") == cookies["pooled-configured"]
        assert connection.follow_redirects is False
        assert connection.trust_env is False
    assert len(calls) == 2
    assert all("cookie" not in request.headers for request in calls)
    assert all(reference_accepts(dict(request.headers)) for request in calls)
    assert all(request.headers["x-tenant-id"] == "synthetic-tenant" for request in calls)
    assert all("authorization" not in request.headers for request in calls)
    assert SECRET not in str([dict(request.headers) for request in calls])


@pytest.mark.parametrize("header_source", ["default", "request", "duplicate"])
@pytest.mark.parametrize("value", ["public-synthetic-unsigned-grant", ""])
def test_signed_partition_pool_rejects_unsigned_caller_capabilities_before_wire(
    monkeypatch, header_source, value
):
    from src.infrastructure.authority_http import _post_json_attempt

    calls, resolved = [], []
    authentication = auth(credential_resolver=lambda name: resolved.append(name) or SECRET)
    headers = {"X-Caller-Capabilities": value} if header_source == "default" else None
    connection, acquire, _ = pooled_signed_connection(
        monkeypatch, calls, headers=headers, authentication=authentication
    )
    with connection:
        original_headers = list(connection.headers.multi_items())
        request_headers = {"Accept-Encoding": "identity"}
        if header_source != "default":
            request_headers["x-caller-capabilities"] = value
        if header_source == "duplicate":
            request_headers = [("X-Caller-Capabilities", value), ("x-caller-capabilities", value)]
        assert acquire() is connection
        with pytest.raises(
            ValueError, match="^CORE_SOURCE_AUTH_(CALLER_AUTHORITY_FORBIDDEN|DUPLICATE_AUTHORITY)$"
        ):
            _post_json_attempt(
                client=connection,
                url=ORIGIN + PATHS[0],
                payload={},
                headers=request_headers,
                unavailable_error="SYNTHETIC_UNAVAILABLE",
                invalid_response_error="SYNTHETIC_INVALID",
                maximum_response_bytes=1024,
            )
        assert list(connection.headers.multi_items()) == original_headers
        assert connection.auth is authentication
        assert len(connection.cookies) == 0
    assert calls == resolved == []


@pytest.mark.parametrize(
    "name", ["Authorization", "Proxy-Authorization", "X-Enterprise-Auth-Unadmitted", "X-Role"]
)
def test_signed_partition_pool_retains_existing_other_authority_refusals(monkeypatch, name):
    from src.infrastructure.authority_http import _post_json_attempt

    calls = []
    connection, _, authentication = pooled_signed_connection(
        monkeypatch, calls, headers={name: "public-synthetic-unadmitted"}
    )
    with connection:
        original_headers = list(connection.headers.multi_items())
        with pytest.raises(ValueError, match="^CORE_SOURCE_AUTH_CALLER_AUTHORITY_FORBIDDEN$"):
            _post_json_attempt(
                client=connection,
                url=ORIGIN + PATHS[0],
                payload={},
                headers={},
                unavailable_error="SYNTHETIC_UNAVAILABLE",
                invalid_response_error="SYNTHETIC_INVALID",
                maximum_response_bytes=1024,
            )
        assert list(connection.headers.multi_items()) == original_headers
        assert connection.auth is authentication
    assert calls == []
