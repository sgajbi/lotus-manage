"""Frozen normalized HTTP contract, deployment trust and bounded transport refusals."""

import base64
import json
from pathlib import Path

import httpx
import pytest

from src.api.composition import composite_source_service as composition
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.historical_policy import (
    admitted_historical_policy,
    HistoricalPolicyMapping,
)
from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration
from src.infrastructure.composites.historical_verifier import ConfiguredHistoricalPolicyVerifier
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_historical_policy_helpers import historical_contract_material


@pytest.fixture(scope="module")
def material():
    return historical_contract_material()


def configuration(material, **changes):
    return HistoricalPolicyConfiguration(
        **(
            {
                "endpoint": "https://independent.test/historical",
                "credential_env": "CONTROLLED_HISTORICAL_HTTP_AUTH",
                "trust": material[0].trust.model_dump(mode="json"),
            }
            | changes
        )
    )


def test_documented_configuration_shape_validates():
    path = (
        Path(__file__).resolve().parents[4]
        / "docs/examples/composite-historical-provider-configuration.json"
    )
    assert (
        HistoricalPolicyConfiguration.model_validate_json(path.read_text()).maximum_response_bytes
        == 8_000_000
    )


def test_maximum_original_fits_bounded_envelope_without_truncation(material, monkeypatch):
    import hashlib

    raw = b"x" * 2_000_000
    wire = material[0].mapping.model_dump(mode="json")
    wire["raw_original_base64"] = base64.b64encode(raw).decode()
    wire["original_credential"] = base64.b64encode(material[0].signer.sign(raw)).decode()
    wire["reference"]["raw_digest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    mapping = HistoricalPolicyMapping.model_validate(wire | {"content_hash": ""})
    request = material[1].verification.request.model_copy(update={"reference": mapping.reference})

    def change(proof):
        proof["mapping"] = mapping.model_dump(mode="json")
        proof["request"] = request.model_dump(mode="json")

    body = json.dumps(signed_wire(material, change)).encode()
    assert 2_000_000 < len(body) < 8_000_000
    port = verifier(material, monkeypatch, lambda _: httpx.Response(200, content=body))
    result = admitted_historical_policy(port, request)
    assert base64.b64decode(result.mapping.raw_original_base64) == raw


def signed_wire(material, change=None):
    port, proposal, *_ = material
    wire = proposal.verification.model_dump(mode="json")
    wire.pop("content_hash")
    wire.pop("verifier_credential")
    if change:
        change(wire)
    wire["verifier_credential"] = base64.b64encode(
        port.verifier.sign(hash_canonical_payload(wire).encode())
    ).decode()
    return wire


def verifier(material, monkeypatch, handler, **changes):
    monkeypatch.setenv("CONTROLLED_HISTORICAL_HTTP_AUTH", "controlled-conformance-only")
    return ConfiguredHistoricalPolicyVerifier(
        configuration(material, **changes), httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_production_composition_posts_exact_frozen_request_and_admits_signed_response(
    material,
    monkeypatch,
):
    request = material[1].verification.request
    calls = []

    def provider(incoming):
        calls.append(incoming)
        assert incoming.method == "POST"
        assert str(incoming.url) == "https://independent.test/historical"
        assert incoming.headers["Authorization"] == "Bearer controlled-conformance-only"
        assert incoming.headers["Accept-Encoding"] == "identity"
        assert json.loads(incoming.content) == request.model_dump(mode="json")
        return httpx.Response(200, json=signed_wire(material))

    port = verifier(material, monkeypatch, provider)
    monkeypatch.setenv(
        "DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON", port.configuration.model_dump_json()
    )
    monkeypatch.delenv("DPM_COMPOSITE_SOURCES_JSON", raising=False)
    monkeypatch.setattr(composition, "get_shared_source_http_client", lambda *a, **k: port.client)
    service = composition.build_composite_monthly_service(InMemoryDpmCompositeRepository())
    result = admitted_historical_policy(service.historical_admission, request)
    assert result == material[1].verification
    assert len(calls) == 1
    assert result.mapping.original_credential == material[0].mapping.original_credential


@pytest.mark.parametrize("raw", [None, "", " \n"])
def test_empty_configuration_remains_unavailable(monkeypatch, raw):
    monkeypatch.delenv("DPM_COMPOSITE_SOURCES_JSON", raising=False)
    if raw is None:
        monkeypatch.delenv("DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON", raising=False)
    else:
        monkeypatch.setenv("DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON", raw)
    assert (
        composition.build_composite_monthly_service(
            InMemoryDpmCompositeRepository()
        ).historical_admission.trust
        is None
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:443/verify",
        "http://provider.test",
        "https:///verify",
        "https://user:pass@provider.test",
        "https://provider.test?x=1",
        "https://provider.test#x",
        "https://provider.test?",
        "https://provider.test#",
        "https://provider.test:0",
    ],
)
def test_unpinned_transport_refuses(material, endpoint):
    with pytest.raises(ValueError, match="ENDPOINT_INVALID"):
        configuration(material, endpoint=endpoint)


@pytest.mark.parametrize(
    "change",
    [
        {"attempts": 0},
        {"attempts": 4},
        {"timeout_seconds": 0},
        {"timeout_seconds": 31},
        {"maximum_response_bytes": 100},
        {"maximum_response_bytes": 8_000_001},
        {"credential_env": "caller supplied"},
        {"allow_local_http": True},
        {"extra": True},
    ],
)
def test_invalid_configuration_refuses(material, change):
    with pytest.raises(ValueError):
        configuration(material, **change)


@pytest.mark.parametrize(
    "endpoint", ["https://provider.test:invalid", "https://provider.test:65536"]
)
def test_invalid_endpoint_port_refuses_configuration(material, endpoint):
    with pytest.raises(ValueError):
        configuration(material, endpoint=endpoint)


@pytest.mark.parametrize(
    "field,source",
    [
        ("verifier_principal_id", "signer_principal_id"),
        ("verifier_key_digest", "signer_key_digest"),
    ],
)
def test_nonindependent_trust_refuses(material, field, source):
    trust = material[0].trust.model_dump(mode="json")
    trust[field] = trust[source]
    with pytest.raises(ValueError, match="INDEPENDENCE_REQUIRED"):
        configuration(material, trust=trust)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "foreign-tenant"),
        ("signing_contract", "unsupported-format"),
    ],
)
def test_wrong_scope_does_not_contact_provider(material, monkeypatch, field, value):
    trust = material[0].trust.model_dump(mode="json") | {field: value}
    port = verifier(
        material, monkeypatch, lambda _: pytest.fail("foreign scope contacted"), trust=trust
    )
    with pytest.raises(ValueError, match="TRUST_MISMATCH"):
        admitted_historical_policy(port, material[1].verification.request)


@pytest.mark.parametrize("value", [None, "", "  "])
def test_missing_auth_is_unavailable_without_network(material, monkeypatch, value):
    port = verifier(material, monkeypatch, lambda _: pytest.fail("missing auth contacted"))
    if value is None:
        monkeypatch.delenv("CONTROLLED_HISTORICAL_HTTP_AUTH")
    else:
        monkeypatch.setenv("CONTROLLED_HISTORICAL_HTTP_AUTH", value)
    with pytest.raises(ValueError, match="ADMISSION_UNAVAILABLE"):
        admitted_historical_policy(port, material[1].verification.request)


@pytest.mark.parametrize(
    "field,value",
    [
        ("signer_principal_id", "other-signer"),
        ("verifier_principal_id", "other-verifier"),
        ("signer_key_digest", "sha256:" + "c" * 64),
        ("configuration_digest", "sha256:" + "c" * 64),
        ("posture", "QUALIFIED_RECEIPT"),
    ],
)
def test_valid_signature_cannot_override_deployment_trust(material, monkeypatch, field, value):
    wire = signed_wire(material, lambda w: w.update({field: value}))
    port = verifier(material, monkeypatch, lambda _: httpx.Response(200, json=wire))
    with pytest.raises(ValueError, match="TRUST_MISMATCH"):
        admitted_historical_policy(port, material[1].verification.request)


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda w: w["request"].update(intent_digest="sha256:" + "c" * 64), "REQUEST_MISMATCH"),
        (lambda w: w["request"].update(actor_id="foreign-actor"), "REQUEST_MISMATCH"),
        (lambda w: w.update(verifier_key_digest="sha256:" + "c" * 64), "SIGNATURE_INVALID"),
        (lambda w: w.update(checked_at="2026-10-10T01:00:01.000000Z"), "WINDOW_INVALID"),
        (lambda w: w.update(expires_at="2026-10-10T01:00:00.000000Z"), "WINDOW_INVALID"),
        (lambda w: w.update(current_revocation_status="REVOKED"), "literal_error"),
        (lambda w: w.update(original_signature_status="UNVERIFIED"), "literal_error"),
        (lambda w: w.update(product_version="v2"), "literal_error"),
        (lambda w: w.update(product_version=None), "literal_error"),
        (lambda w: w.update(extra=True), "extra_forbidden"),
    ],
)
def test_re_signed_invalid_proofs_refuse(material, monkeypatch, change, code):
    wire = signed_wire(material, change)
    port = verifier(material, monkeypatch, lambda _: httpx.Response(200, json=wire))
    expected = "REQUEST_MISMATCH" if code == "REQUEST_MISMATCH" else "RESPONSE_INVALID"
    with pytest.raises(ValueError, match=expected):
        admitted_historical_policy(port, material[1].verification.request)


def test_invalid_signature_refuses(material, monkeypatch):
    wire = signed_wire(material)
    wire["verifier_credential"] = base64.b64encode(bytes(64)).decode()
    port = verifier(material, monkeypatch, lambda _: httpx.Response(200, json=wire))
    with pytest.raises(ValueError, match="RESPONSE_INVALID"):
        admitted_historical_policy(port, material[1].verification.request)


@pytest.mark.parametrize("body", [b"{", b"[]", b"null", b'{"x":1,"x":2}', b'{"x":{"y":1,"y":2}}'])
def test_strict_json_refuses_before_model_validation(material, monkeypatch, body):
    port = verifier(material, monkeypatch, lambda _: httpx.Response(200, content=body))
    with pytest.raises(ValueError, match="RESPONSE_INVALID"):
        admitted_historical_policy(port, material[1].verification.request)


@pytest.mark.parametrize(
    "status,error",
    [
        (302, "PROVIDER_REJECTED"),
        (401, "PROVIDER_REJECTED"),
        (422, "PROVIDER_REJECTED"),
        (500, "ADMISSION_UNAVAILABLE"),
        (503, "ADMISSION_UNAVAILABLE"),
    ],
)
def test_terminal_http_failures(material, monkeypatch, status, error):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"Location": "https://foreign.test"})

    port = verifier(material, monkeypatch, handler)
    with pytest.raises(ValueError, match=error):
        admitted_historical_policy(port, material[1].verification.request)
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["compression", "oversize", "timeout"])
def test_bounded_transport_refusals(material, monkeypatch, failure):
    def handler(_):
        if failure == "timeout":
            raise httpx.ReadTimeout("controlled timeout")
        if failure == "compression":
            return httpx.Response(200, headers={"Content-Encoding": "br"}, content=b"{}")
        return httpx.Response(200, content=b" " * 1025)

    port = verifier(material, monkeypatch, handler, maximum_response_bytes=1024)
    error = "ADMISSION_UNAVAILABLE" if failure == "timeout" else "RESPONSE_INVALID"
    with pytest.raises(ValueError, match=error):
        admitted_historical_policy(port, material[1].verification.request)


def test_retry_preserves_exact_request_then_valid_signed_admission(material, monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.content)
        if len(calls) == 1:
            raise httpx.ConnectTimeout("controlled transient")
        if len(calls) == 2:
            return httpx.Response(503)
        return httpx.Response(200, json=signed_wire(material))

    port = verifier(material, monkeypatch, handler, attempts=3)
    assert (
        admitted_historical_policy(port, material[1].verification.request)
        == material[1].verification
    )
    assert len(calls) == 3 and len(set(calls)) == 1
