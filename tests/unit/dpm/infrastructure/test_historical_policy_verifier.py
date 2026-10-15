"""Frozen normalized HTTP contract, deployment trust and bounded transport refusals."""

import base64
import hashlib
import json
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from src.api.composition import composite_source_service as composition
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyMapping,
    admitted_historical_policy,
)
from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration
from src.infrastructure.composites.historical_verifier import ConfiguredHistoricalPolicyVerifier
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_historical_policy_helpers import historical_contract_material


def native_controlled_configuration(tmp_path, mapping):
    """Ephemeral independent test authors; only public original bytes enter production adapter."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    from src.infrastructure.composites.native_source_configuration import (
        key_digest,
        native_configuration_digest,
    )

    signer, verifier_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    instant = datetime.now(UTC)

    def stamp(value):
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")

    source_public = signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    verifier_public = verifier_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    key_file = tmp_path / "verifier.key"
    key_file.write_bytes(
        verifier_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    )
    key_file.chmod(stat.S_IREAD)
    originals = tmp_path / "originals"
    originals.mkdir()
    body = {
        "format": "CONTROLLED_SYNTHETIC_POLICY_V1",
        "posture": "SYNTHETIC_NON_CERTIFYING",
        "purpose": "COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION",
        "signature_semantics": "SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE",
        "issuer_id": mapping.reference.issuer_id,
        "artifact_id": mapping.reference.artifact_id,
        "revision": mapping.reference.revision,
        "signer_principal_id": "native-controlled-source",
        "actual_issued_at": stamp(instant - timedelta(seconds=1)),
        "policy": mapping.policy.model_dump(mode="json"),
        "eligibility_policy_version": mapping.eligibility_policy_version,
        "reporting_currency": mapping.reporting_currency,
        "attachments": [item.model_dump(mode="json") for item in mapping.attachments],
        "scenario_proposed_by": mapping.original_proposed_by,
        "scenario_proposed_at": mapping.original_proposed_at,
        "scenario_approved_by": mapping.original_approved_by,
        "scenario_approved_at": mapping.original_approved_at,
    }
    raw = (json.dumps(body, indent=3) + "\r\n").encode()
    reference = mapping.reference.model_copy(
        update={
            "raw_digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "signing_contract": "CONTROLLED_SYNTHETIC_POLICY_V1",
        }
    )
    envelope = {
        "raw_original_base64": base64.b64encode(raw).decode(),
        "original_credential": base64.b64encode(signer.sign(raw)).decode(),
    }
    original_file = originals / (reference.raw_digest[7:] + ".json")
    original_file.write_text(json.dumps(envelope), encoding="utf-8")
    document = {
        "adapter": "CONTROLLED_SYNTHETIC_POLICY_V1",
        "trust": {
            "tenant_id": mapping.policy.scope.tenant_id,
            "signing_contract": "CONTROLLED_SYNTHETIC_POLICY_V1",
            "signer_principal_id": "native-controlled-source",
            "verifier_principal_id": "native-controlled-verifier",
            "signer_key_digest": key_digest(source_public),
            "verifier_key_digest": key_digest(verifier_public),
            "configuration_digest": "sha256:" + "0" * 64,
            "posture": "SYNTHETIC_NON_CERTIFYING",
        },
        "source_public_key_base64": base64.b64encode(source_public).decode(),
        "source_key_valid_from": stamp(instant - timedelta(days=1)),
        "source_key_valid_to": stamp(instant + timedelta(days=1)),
        "verifier_id": "native-controlled-verifier",
        "verifier_key_file": str(key_file),
        "originals_directory": str(originals),
        "revocation": {
            "revision": "explicit-current-r1",
            "checked_at": stamp(instant - timedelta(seconds=2)),
            "expires_at": stamp(instant + timedelta(minutes=4)),
            "revoked_principals": [],
            "revoked_key_digests": [],
            "revoked_original_digests": [],
        },
    }
    document["trust"]["configuration_digest"] = native_configuration_digest(document)
    return document, reference, raw, original_file, signer


@pytest.fixture
def native_history(tmp_path, material):
    document, reference, raw, original_file, signer = native_controlled_configuration(
        tmp_path, material[0].mapping
    )
    from src.core.composite_eligibility.controlled_scenario import (
        ControlledScenarioVerificationRequest,
    )

    request = ControlledScenarioVerificationRequest.model_validate(
        material[1].verification.request.model_dump(mode="json")
        | {
            "product_version": "v2",
            "purpose": "COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION",
            "reference": reference,
            "requested_at": datetime.now(UTC)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z"),
        }
    )
    return document, request, raw, original_file, signer


def test_native_original_production_composition_preserves_actual_and_scenario_time(
    native_history, monkeypatch
):
    document, request, raw, _, _ = native_history
    monkeypatch.delenv("DPM_COMPOSITE_SOURCES_JSON", raising=False)
    monkeypatch.setenv("DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON", json.dumps(document))
    service = composition.build_composite_subject_service(InMemoryDpmCompositeRepository())
    proof = admitted_historical_policy(service.historical_admission, request)
    assert base64.b64decode(proof.mapping.raw_original_base64) == raw
    original = json.loads(raw)
    assert proof.mapping.scenario_approved_at == original["scenario_approved_at"]
    assert proof.admitted_at >= request.requested_at > original["actual_issued_at"]
    assert original["actual_issued_at"] > proof.mapping.scenario_approved_at
    assert proof.posture == "SYNTHETIC_NON_CERTIFYING"
    assert proof.original_signature_status == "VERIFIED_AT_ACTUAL_ISSUANCE"
    assert proof.signature_semantics == "SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE"
    assert proof.mapping.actual_issued_at == original["actual_issued_at"]
    assert proof.mapping.scenario_approved_at < document["source_key_valid_from"]
    assert not {"original_proposed_at", "original_approved_at"} & proof.mapping.model_dump().keys()
    assert type(service.candidates).__name__ == "UnavailableCandidateUniverseSource"


@pytest.mark.parametrize(
    "change",
    [
        "tenant",
        "currency",
        "purpose",
        "signature",
        "signature-alias",
        "raw-hash",
        "principal",
        "future",
        "scenario-after-issuance",
        "scenario-after-month",
        "scenario-maker-checker",
        "actual-before-key",
        "key-window",
        "revoked",
        "revoked-key",
        "revoked-original",
        "expired",
        "config-hash",
    ],
)
def test_native_original_refuses_untrusted_or_stale_material(native_history, change):
    from src.infrastructure.composites.controlled_source_verifier import (
        NativeControlledHistoricalVerifier,
    )
    from src.infrastructure.composites.native_source_configuration import (
        NativeHistoricalConfiguration,
        native_configuration_digest,
    )

    document, request, raw, original_file, signer = native_history
    if change == "tenant":
        request = request.model_copy(
            update={"scope": request.scope.model_copy(update={"tenant_id": "foreign"})}
        )
    elif change == "currency":
        request = request.model_copy(update={"reporting_currency": "EUR"})
    elif change in {
        "purpose",
        "principal",
        "future",
        "scenario-after-issuance",
        "scenario-after-month",
        "scenario-maker-checker",
        "actual-before-key",
    }:
        body = json.loads(raw)
        field, value = {
            "purpose": ("purpose", "COMPOSITE_ECONOMIC_AUTHORITY_PROFILE"),
            "principal": ("signer_principal_id", "foreign"),
            "future": ("actual_issued_at", "2099-01-01T00:00:00.000000Z"),
            "scenario-after-issuance": ("scenario_approved_at", "2099-01-01T00:00:00.000000Z"),
            "scenario-after-month": ("scenario_approved_at", "2026-09-15T00:00:00.000000Z"),
            "scenario-maker-checker": ("scenario_approved_by", body["scenario_proposed_by"]),
            "actual-before-key": ("actual_issued_at", "2026-10-01T00:00:00.000000Z"),
        }[change]
        body[field] = value
        changed = json.dumps(body).encode()
        request = request.model_copy(
            update={
                "reference": request.reference.model_copy(
                    update={"raw_digest": "sha256:" + hashlib.sha256(changed).hexdigest()}
                )
            }
        )
        original_file = original_file.parent / (request.reference.raw_digest[7:] + ".json")
        original_file.write_text(
            json.dumps(
                {
                    "raw_original_base64": base64.b64encode(changed).decode(),
                    "original_credential": base64.b64encode(signer.sign(changed)).decode(),
                }
            ),
            encoding="utf-8",
        )
    elif change == "signature":
        envelope = json.loads(original_file.read_text())
        envelope["original_credential"] = base64.b64encode(bytes(64)).decode()
        original_file.write_text(json.dumps(envelope), encoding="utf-8")
    elif change == "signature-alias":
        envelope = json.loads(original_file.read_text())
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        original_signature = envelope["original_credential"]
        alias = (
            original_signature[:85] + alphabet[alphabet.index(original_signature[85]) + 1] + "=="
        )
        assert base64.b64decode(alias) == base64.b64decode(original_signature)
        envelope["original_credential"] = alias
        original_file.write_text(json.dumps(envelope), encoding="utf-8")
    elif change == "raw-hash":
        envelope = json.loads(original_file.read_text())
        envelope["raw_original_base64"] = base64.b64encode(raw + b" ").decode()
        original_file.write_text(json.dumps(envelope), encoding="utf-8")
    elif change == "key-window":
        document["source_key_valid_to"] = "2000-01-01T00:00:00.000000Z"
    elif change.startswith("revoked"):
        field, value = {
            "revoked": ("revoked_principals", document["trust"]["signer_principal_id"]),
            "revoked-key": ("revoked_key_digests", document["trust"]["verifier_key_digest"]),
            "revoked-original": ("revoked_original_digests", request.reference.raw_digest),
        }[change]
        document["revocation"][field] = [value]
    elif change == "expired":
        document["revocation"]["expires_at"] = document["revocation"]["checked_at"]
    if change != "config-hash":
        document["trust"]["configuration_digest"] = native_configuration_digest(document)
    else:
        document["verifier_id"] = "tampered"
    with pytest.raises(ValueError):
        admitted_historical_policy(
            NativeControlledHistoricalVerifier(
                NativeHistoricalConfiguration.model_validate(document)
            ),
            request,
        )


@pytest.mark.parametrize("change", ["missing", "directory", "writable", "oversized", "wrong-key"])
def test_native_verifier_secret_custody_refuses_invalid_files(native_history, change):
    from src.infrastructure.composites.controlled_source_verifier import (
        NativeControlledHistoricalVerifier,
    )
    from src.infrastructure.composites.native_source_configuration import (
        NativeHistoricalConfiguration,
        native_configuration_digest,
    )

    document, request, _, _, _ = native_history
    path = Path(document["verifier_key_file"])
    if change == "missing":
        document["verifier_key_file"] = str(path.parent / "missing")
    elif change == "directory":
        document["verifier_key_file"] = str(path.parent)
    else:
        path.chmod(stat.S_IREAD | stat.S_IWRITE)
        if change != "writable":
            path.write_bytes(bytes(33 if change == "oversized" else 32))
            path.chmod(stat.S_IREAD)
    document["trust"]["configuration_digest"] = native_configuration_digest(document)
    with pytest.raises(ValueError, match="COMPOSITE_NATIVE"):
        admitted_historical_policy(
            NativeControlledHistoricalVerifier(
                NativeHistoricalConfiguration.model_validate(document)
            ),
            request,
        )


def test_native_secret_rejects_link_metadata_without_platform_symlink_privilege(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from src.infrastructure.composites.native_source_configuration import read_custody_file

    monkeypatch.setattr(
        Path, "lstat", lambda self: SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
    )
    with pytest.raises(ValueError, match="LINK_FORBIDDEN"):
        read_custody_file(tmp_path / "key", 32, secret=True)


@pytest.mark.parametrize(
    "change",
    [
        "qualified",
        "contract",
        "principal",
        "same-key",
        "wrong-public",
        "oversized-public",
        "relative-path",
    ],
)
def test_native_configuration_refuses_noncontrolled_or_unbound_trust(native_history, change):
    from src.infrastructure.composites.native_source_configuration import (
        NativeHistoricalConfiguration,
        native_configuration_digest,
    )

    document, *_ = native_history
    if change == "qualified":
        document["trust"]["posture"] = "QUALIFIED_RECEIPT"
    elif change == "contract":
        document["trust"]["signing_contract"] = "FOREIGN_CONTRACT"
    elif change == "principal":
        document["trust"]["verifier_principal_id"] = document["trust"]["signer_principal_id"]
    elif change == "same-key":
        document["trust"]["verifier_key_digest"] = document["trust"]["signer_key_digest"]
    elif change == "wrong-public":
        document["source_public_key_base64"] = base64.b64encode(bytes(32)).decode()
    elif change == "oversized-public":
        document["source_public_key_base64"] = "A" * 44
    elif change == "relative-path":
        document["verifier_key_file"] = "relative.key"
    document["trust"]["configuration_digest"] = native_configuration_digest(document)
    with pytest.raises(ValueError):
        NativeHistoricalConfiguration.model_validate(document)


def test_native_configuration_and_original_json_refuse_duplicate_members():
    from src.infrastructure.composites.native_source_configuration import strict_controlled_json

    with pytest.raises(ValueError, match="JSON_DUPLICATE_MEMBER"):
        strict_controlled_json('{"purpose":"original","purpose":"replacement"}')
    assert strict_controlled_json('{"purpose":"original"}') == {"purpose": "original"}


def test_native_admission_rechecks_revocation_after_original_and_key_io(
    native_history, monkeypatch
):
    from src.infrastructure.composites import controlled_source_verifier as native
    from src.infrastructure.composites.native_source_configuration import (
        NativeHistoricalConfiguration,
    )

    document, request, *_ = native_history
    instants = iter(
        [
            datetime.fromisoformat(request.requested_at) + timedelta(milliseconds=1),
            datetime.fromisoformat(document["revocation"]["expires_at"]),
        ]
    )

    class AdvancingClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return next(instants)

    monkeypatch.setattr(native, "datetime", AdvancingClock)
    with pytest.raises(ValueError, match="REVOCATION_WINDOW_INVALID"):
        native.NativeControlledHistoricalVerifier(
            NativeHistoricalConfiguration.model_validate(document)
        ).verify(request)


@pytest.mark.parametrize(
    "change", ["opened-nonregular", "opened-identity", "after-identity", "access-error"]
)
def test_native_custody_refuses_replacement_races_and_access_errors(
    native_history, monkeypatch, change
):
    import errno
    import os

    from src.infrastructure.composites import native_source_configuration as custody

    document, *_ = native_history
    path = Path(document["verifier_key_file"])
    if change == "access-error":
        original_open = os.open

        def fail_write_open(location, flags):
            if flags & os.O_WRONLY:
                raise OSError(errno.EIO, "simulated storage failure")
            return original_open(location, flags)

        monkeypatch.setattr(custody.os, "open", fail_write_open)
    elif change == "after-identity":
        original_path = custody._regular_path
        calls = []

        def replaced_path(location):
            observed = original_path(location)
            calls.append(location)
            if len(calls) == 1:
                return observed
            values = list(observed)
            values[1] += 1
            return os.stat_result(values)

        monkeypatch.setattr(custody, "_regular_path", replaced_path)
    else:
        original_stat = os.fstat

        def replaced_descriptor(descriptor):
            values = list(original_stat(descriptor))
            if change == "opened-nonregular":
                values[0] = stat.S_IFIFO
            else:
                values[1] += 1
            return os.stat_result(values)

        monkeypatch.setattr(custody.os, "fstat", replaced_descriptor)
    with pytest.raises(ValueError, match="COMPOSITE_NATIVE"):
        custody.read_custody_file(path, 32, secret=True)


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
