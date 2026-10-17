"""Synthetic fresh admission through separate retained HTTP clients, never bank proof."""

import base64
import hashlib
import json
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from src.core.common.artifact_credentials import verified_artifact
from src.core.composite_eligibility.native_source_verification import NativeAssemblyVerification
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_eligibility.source_assembly import assembly_verification_request
from src.core.composite_eligibility.verification import VerificationRequest
from src.infrastructure.composites.controlled_assembly_verifier import (
    ControlledAssemblyRevocationSnapshot,
    ControlledAssemblyVerifier,
    ControlledAssemblyVerifierConfiguration,
    ControlledAssemblyVerifierTrust,
)
from src.infrastructure.composites.core_financial_configuration import CoreReaderConfiguration
from src.infrastructure.composites.core_financial_sources import CoreMonthlyEligibilitySource
from src.infrastructure.composites.core_source_reader import CoreHttpRetainedReader
from src.infrastructure.composites.source_configuration import SourceKey
from tests.unit.dpm.infrastructure.test_core_source_reader import fixture, response, source_request
from tests.unit.dpm.composites.test_native_source_custody import owner_root

NOW = datetime(2026, 10, 16, tzinfo=UTC)
SEED = bytes(range(32))
OTHER_SEED = bytes(range(32, 64))
ROLES = {"PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"}


def sha(document):
    """Independently stated canonical recipe, without calling production hashing."""
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def decode(segment):
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


def public(seed=SEED, kid="synthetic-verifier"):
    raw = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw()
    return {
        "kid": kid,
        "kty": "OKP",
        "crv": "Ed25519",
        "alg": "EdDSA",
        "x": base64.urlsafe_b64encode(raw).rstrip(b"=").decode(),
        "revoked": False,
    }


def expected_observations():
    # Facts are written from the public fixture's raw inputs, not read from A's normalized output.
    return MonthlyEligibilityObservations.model_validate(
        {
            "product_name": "CompositeMonthlyEligibilityObservations",
            "product_version": "v1",
            "evidence_class": "SYNTHETIC_UNQUALIFIED",
            "tenant_id": "tenant",
            "composite_id": "composite",
            "definition_version": "v1",
            "month": "2025-01",
            "source_cut_id": "normalized-cut",
            "source_revision": "1",
            "reporting_currency": "USD",
            "source_generated_at": "2026-10-16T00:00:00.000000Z",
            "expected_portfolio_ids": ["P1", "P2", "P3"],
            "portfolios": [
                {
                    "portfolio_id": pid,
                    "currency": "USD",
                    "prior_month_end_assets": "100.00",
                    "prior_assets_as_of": "2024-12-31",
                    "month_end_assets": "100.00",
                    "settled_unencumbered_cash": "0.00",
                    "cash_as_of": "2025-01-31",
                    "discretionary": True,
                    "funded": False,
                    "invested": None,
                    "readiness_as_of": "2025-01-31",
                    "flow_coverage_from": "2025-01-01",
                    "flow_coverage_to": "2025-01-31",
                    "flows": [
                        {
                            "event_id": "record",
                            "business_date": "2025-01-31",
                            "received_at": "2026-10-16T00:00:00.000000Z",
                            "currency": "USD",
                            "amount": "-10.00",
                            "classification": "EXTERNAL_CASH",
                            "status": "POSTED",
                            "reverses_event_id": None,
                        }
                    ],
                }
                for pid in ("P1", "P2", "P3")
            ],
        }
    )


def expected_captures(rows):
    return [
        {
            key: value
            for key, value in row.items()
            if key not in {"row_kind", "segment_index", "segment_hash", "bytes_base64"}
        }
        for row in rows
        if row["segment_index"] == 0
    ]


def expected_views(records, roots, pid):
    values = []
    for view in ("CUT", "MEMBERS" if pid is None else "INPUTS", "CAPTURES"):
        rows = records[(pid, view)]
        if view == "CUT":
            kind, order, domain, items = (
                "CUT_HEADERS",
                "single_cut",
                "NeutralSourceCutHeaders:v1",
                [roots[pid]],
            )
        elif view == "MEMBERS":
            kind, order, domain = (
                "REGISTRY_MEMBERS",
                "provider_namespace,source_member_id",
                "PortfolioHistoricalRegistryMembers:v1",
            )
            items = [row["member_content_hash"] for row in rows]
        elif view == "INPUTS":
            kind, order, domain = (
                "SELECTED_FINANCIAL_INPUTS",
                "selected_portfolio",
                "PortfolioFinancialSourceCutInputs:v1",
            )
            items = [row["input_content_hash"] for row in rows]
        else:
            kind, order, domain = (
                "CAPTURE_ARTIFACTS",
                "role,source_page_index,capture_id,segment_index",
                "PortfolioNeutralSourceCaptureArtifacts:v1",
            )
            items = [
                sha(
                    {"contract": "PortfolioNeutralSourceCaptureArtifact:v1", **capture}
                ).removeprefix("sha256:")
                for capture in expected_captures(rows)
            ]
        values.append(
            {
                "view": view,
                "total_count": len(rows),
                "ordered_set_hash": owner_root(domain, items),
                "root_item_count": len(items),
                "root_kind": kind,
                "ordering": order,
            }
        )
    return values


def expected_custody(h):
    # Construct complete expected custody from the public wire fixture, without any A DTO/reader output.
    records, config, roots = h.records, h.config.financial, h.roots

    def locator(pid, address):
        return {
            "product_name": "PortfolioHistoricalRegistry"
            if pid is None
            else "PortfolioFinancialSourceCut",
            "product_version": "v1",
            "source_address": address.model_dump(mode="json", exclude={"content_hash"}),
            "batch_manifest_hash": roots[pid],
        }

    receipt = {
        "receipt_job_id": "terminal",
        "received_at": "2026-10-16T00:00:00Z",
        "completed_at": "2026-10-16T00:00:00Z",
        "generated_at": "2026-10-16T00:00:00Z",
    }
    registry = {
        "locator": locator(None, config.registry),
        "manifest": records[(None, "CUT")][0]["manifest"],
        "receipt": receipt,
        "view_roots": expected_views(records, roots, None),
        "captures": expected_captures(records[(None, "CAPTURES")]),
        "member_bindings": [],
    }
    portfolios = []
    for binding, member in zip(config.members, records[(None, "MEMBERS")], strict=True):
        registry["member_bindings"].append(
            {
                "portfolio_id": binding.portfolio_id,
                "provider_id": "native-provider",
                "provider_namespace": "native",
                "source_member_id": binding.source_member_id,
                "member_revision": 1,
                "member_content_hash": member["member_content_hash"],
            }
        )
        pid = binding.portfolio_id
        row = records[(pid, "INPUTS")][0]
        portfolios.append(
            {
                "portfolio_id": pid,
                "locator": locator(pid, binding.financial_cut),
                "manifest": records[(pid, "CUT")][0]["manifest"],
                "receipt": receipt,
                "view_roots": expected_views(records, roots, pid),
                "input_content_hash": row["input_content_hash"],
                "graph": row["graph"],
                "graph_content_hash": row["graph_content_hash"],
                "captures": expected_captures(records[(pid, "CAPTURES")]),
            }
        )
    material = {
        "product_name": "CompositeMonthlyNativeCustody",
        "product_version": "v1",
        "registry": registry,
        "portfolios": portfolios,
    }
    return {**material, "content_hash": sha(material)}


def expected_role_digests(custody):
    registry = custody["registry"]
    members = {member["portfolio_id"]: member for member in registry["member_bindings"]}
    return {
        role: sha(
            {
                "contract": "CompositeMonthlyRoleSet:v1",
                "kind": role,
                "registry_content_hash": sha(registry),
                "portfolio_roles": [
                    {
                        "portfolio_id": p["portfolio_id"],
                        "financial_locator": p["locator"],
                        "receipt": p["receipt"],
                        "input_content_hash": p["input_content_hash"],
                        "graph_content_hash": p["graph_content_hash"],
                        "member_content_hash": members[p["portfolio_id"]]["member_content_hash"],
                        "selection": next(s for s in p["graph"]["selections"] if s["role"] == role),
                        "captures": [c for c in p["captures"] if c["role"] == role],
                    }
                    for p in custody["portfolios"]
                ],
            }
        )
        for role in ROLES
    }


class CountingSigner:
    def __init__(self, seed=SEED, after_sign=None, corrupt=False):
        self.key = Ed25519PrivateKey.from_private_bytes(seed)
        self.calls = []
        self.after_sign, self.corrupt = after_sign, corrupt

    def public_key(self):
        return self.key.public_key()

    def sign(self, message):
        self.calls.append(message)
        result = self.key.sign(message)
        if self.after_sign:
            self.after_sign()
        return b"x" * 64 if self.corrupt else result


@pytest.fixture
def harness(monkeypatch):
    financial, records, roots = fixture()
    expected = expected_observations()
    state = SimpleNamespace(now=NOW, mutate=None, unavailable=False, alternate_records=None)
    monkeypatch.setenv("C2_SYNTHETIC_READ_TOKEN", "synthetic-only")
    reader_config = CoreReaderConfiguration(
        tenant_id="tenant",
        endpoint="https://core.example",
        credential_env="C2_SYNTHETIC_READ_TOKEN",
        page_size=2,
    )
    calls_a, calls_c = [], []

    def transport(calls, independent):
        def read(request):
            body = json.loads(request.content)
            calls.append(body)
            assert request.headers["authorization"] == "Bearer synthetic-only"
            if independent and state.unavailable:
                return httpx.Response(503)
            selected = (
                state.alternate_records if independent and state.alternate_records else records
            )
            result = response(request, deepcopy(selected), roots)
            if independent and state.mutate:
                state.mutate(result, body)
            return httpx.Response(200, json=result)

        return httpx.MockTransport(read)

    client_a, client_c = (
        httpx.Client(transport=transport(calls_a, False)),
        httpx.Client(transport=transport(calls_c, True)),
    )
    reader_a = CoreHttpRetainedReader(reader_config, client_a, members=financial.members)
    assembly = CoreMonthlyEligibilitySource(
        financial, reader_a, controlled_synthetic=True
    ).assemble(source_request(financial, expected))
    assert assembly.observations == expected
    config = ControlledAssemblyVerifierConfiguration.model_validate_json(
        json.dumps(
            {
                "financial": financial.model_dump(mode="json"),
                "reader": reader_config.model_dump(mode="json"),
                "expected_observations_digest": sha(expected.model_dump(mode="json")),
                "trust": {
                    "tenant_id": "tenant",
                    "issuer": "urn:synthetic:monthly:C2",
                    "receipt_issuer_id": "synthetic-receipt",
                    "principal_id": "synthetic-independent-verifier",
                    "audience": "lotus-manage",
                    "purpose": "COMPOSITE_MONTHLY_SOURCE_CUT",
                    "operation": "verification",
                    "evidence_posture": "SYNTHETIC_NON_CERTIFYING",
                    "verifier_key": public(),
                    "key_valid_from": "2026-10-16T00:00:00Z",
                    "key_valid_to": "2026-10-16T00:10:00Z",
                    "source_principal_ids": ["synthetic-enrolled-core-producer"],
                    "source_keys": [],
                },
                "revocation": {
                    "revision": "synthetic-r1",
                    "checked_at": "2026-10-16T00:00:00Z",
                    "expires_at": "2026-10-16T00:05:00Z",
                    "revoked_credentials": [],
                    "revoked_subjects": [],
                    "revoked_key_digests": [],
                },
            }
        ),
        strict=True,
    )
    signer = CountingSigner()
    verifier = ControlledAssemblyVerifier(config, client_c, signer=signer, clock=lambda: state.now)
    yield SimpleNamespace(
        config=config,
        assembly=assembly,
        request=assembly_verification_request(assembly),
        verifier=verifier,
        signer=signer,
        state=state,
        calls_a=calls_a,
        calls_c=calls_c,
        client_a=client_a,
        client_c=client_c,
        expected=expected,
        records=records,
        roots=roots,
    )
    client_a.close()
    client_c.close()


def configure(harness, **changes):
    document = harness.config.model_dump(mode="json")
    for path, value in changes.items():
        target = document
        *parents, leaf = path.split("__")
        for parent in parents:
            target = target[parent]
        target[leaf] = value
    harness.verifier.configuration = ControlledAssemblyVerifierConfiguration.model_validate_json(
        json.dumps(document), strict=True
    )


def test_fresh_three_member_five_role_pair_and_independent_jws(harness):
    h = harness
    pair = h.verifier.verify_with_proof(h.request)
    assert isinstance(pair, NativeAssemblyVerification)
    assert h.client_a is not h.client_c and h.calls_c == h.calls_a
    assert len(h.calls_c) > 15 and any(call["page"]["page_token"] for call in h.calls_c)
    assert {p.portfolio_id for p in h.assembly.native_custody.portfolios} == {"P1", "P2", "P3"}
    assert {i.kind for i in h.assembly.inputs} == ROLES
    expected_native = expected_custody(h)
    assert h.assembly.native_custody.model_dump(mode="json") == expected_native
    assert {item.kind: item.evidence.digest for item in h.assembly.inputs} == expected_role_digests(
        expected_native
    )
    assert h.request.subject_content_hash == sha(h.expected.model_dump(mode="json"))
    custody = h.assembly.native_custody.model_dump(mode="json")
    assert custody.pop("content_hash") == sha(custody) == pair.receipt.artifact_digest
    result = pair.proof.result
    assert result.receipt == pair.receipt
    assert pair.receipt.request == h.request
    assert (
        pair.receipt.posture,
        pair.receipt.verifier_id,
        pair.receipt.issuer_id,
        pair.receipt.artifact_revision,
    ) == ("SYNTHETIC_NON_CERTIFYING", "synthetic-independent-verifier", "synthetic-receipt", "1")
    assert result.admission.configuration_digest == sha(h.config.model_dump(mode="json"))
    assert result.admission.revocation_digest == sha(h.config.revocation.model_dump(mode="json"))
    assert result.admission.verifier_key_digest == sha(public())
    head, claims, _ = pair.proof.verifier_credential.split(".")
    assert decode(head) == {"alg": "EdDSA", "kid": "synthetic-verifier", "typ": "JWT"}
    digests = {
        "request_digest": sha(h.request.model_dump(mode="json")),
        "payload_digest": sha(result.model_dump(mode="json")),
    }
    assert decode(claims) == {
        "iss": "urn:synthetic:monthly:C2",
        "aud": "lotus-manage",
        "sub": "synthetic-independent-verifier",
        "tenant": "tenant",
        "principal_kind": "service",
        "jti": sha(digests),
        "nbf": int(NOW.timestamp()),
        "exp": int(NOW.timestamp()) + 300,
        "operation": "verification",
        "evidence_posture": "SYNTHETIC_NON_CERTIFYING",
        **digests,
    }
    # This anchor is authored from configuration, independently of embedded admission.
    binding = SimpleNamespace(
        keys=(h.config.trust.verifier_key,),
        issuer="urn:synthetic:monthly:C2",
        principal_id="synthetic-independent-verifier",
        tenant_id="tenant",
        revoked_credentials=(),
        revoked_subjects=(),
        operation="verification",
        evidence_posture="SYNTHETIC_NON_CERTIFYING",
    )
    verified_artifact(
        pair.proof.verifier_credential,
        binding=binding,
        request=h.request.model_dump(mode="json"),
        payload=result.model_dump(mode="json"),
        now=NOW.timestamp(),
    )


@pytest.mark.parametrize("missing", ["configuration", "signer", "credential"])
def test_unconfigured_or_missing_credential_performs_zero_reads(harness, monkeypatch, missing):
    h = harness
    if missing == "credential":
        monkeypatch.delenv("C2_SYNTHETIC_READ_TOKEN")
    else:
        setattr(h.verifier, missing, None)
    assert h.verifier.verify_with_proof(h.request) is None
    assert h.calls_c == [] and h.signer.calls == []


@pytest.mark.parametrize(
    "field,value,before_reads",
    [
        ("purpose", "ELIGIBILITY_POLICY", True),
        ("tenant_id", "other", True),
        ("composite_id", "other", True),
        ("definition_version", "other", True),
        ("source_product", "OtherProduct", True),
        ("source_product", None, True),
        ("effective_from", "2025-01-02", True),
        ("effective_to", "2025-02-01", True),
        ("subject_content_hash", "sha256:" + "a" * 64, False),
        ("claims_digest", "sha256:" + "a" * 64, False),
        ("binding", None, False),
    ],
)
def test_every_request_field_must_match_independent_rebuild(harness, field, value, before_reads):
    h = harness
    request = VerificationRequest.model_validate(
        {**h.request.model_dump(mode="json"), field: value}
    )
    with pytest.raises(ValueError, match="COMPOSITE_NATIVE_ASSEMBLY_REQUEST_"):
        h.verifier.verify_with_proof(request)
    assert not h.signer.calls
    assert bool(h.calls_c) is not before_reads


@pytest.mark.parametrize(
    "field,value",
    [
        ("product_name", "OtherCompatibility"),
        ("revision", "2"),
        ("digest", "sha256:" + "b" * 64),
        ("product_version", "v2"),
    ],
)
def test_each_compatibility_binding_field_is_checked(harness, field, value):
    document = harness.request.model_dump(mode="json")
    document["binding"][field] = value
    if field == "product_version":
        with pytest.raises(ValidationError):
            VerificationRequest.model_validate(document)
    else:
        with pytest.raises(ValueError, match="REQUEST_MISMATCH"):
            harness.verifier.verify_with_proof(VerificationRequest.model_validate(document))
    assert not harness.signer.calls


@pytest.mark.parametrize("failure", ["root", "raw", "context", "member", "unavailable"])
def test_good_assembler_cannot_rescue_different_second_reader(harness, failure):
    h = harness

    def mutate(result, body):
        if failure == "root":
            result["pagination"]["ordered_set_hash"] = "f" * 64
        elif failure == "raw" and body["view"] == "CAPTURES":
            result["rows"][0]["segment_hash"] = "f" * 64
        elif failure == "context" and body["view"] == "CAPTURES":
            result["rows"][0]["source_context"]["snapshot_epoch"] = "invented"
        elif failure == "member" and body["view"] == "MEMBERS":
            result["rows"][0]["member"]["core_portfolio_id"] = "foreign"

    h.state.mutate = mutate
    h.state.unavailable = failure == "unavailable"
    if failure == "unavailable":
        assert h.verifier.verify_with_proof(h.request) is None
    else:
        with pytest.raises(ValueError, match="CORE_"):
            h.verifier.verify_with_proof(h.request)
    assert h.assembly.observations == h.expected and not h.signer.calls


@pytest.mark.parametrize(
    "path",
    [
        "trust.source_keys",
        "trust.source_principal_ids",
        "revocation.revoked_credentials",
        "revocation.revoked_subjects",
        "revocation.revoked_key_digests",
    ],
)
@pytest.mark.parametrize("missing", [True, False])
def test_explicit_required_inventories_refuse_omission_and_null(harness, path, missing):
    document = harness.config.model_dump(mode="json")
    parent, field = path.split(".")
    if missing:
        del document[parent][field]
    else:
        document[parent][field] = None
    with pytest.raises(ValidationError):
        ControlledAssemblyVerifierConfiguration.model_validate_json(
            json.dumps(document), strict=True
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"reader__tenant_id": "foreign"},
        {"trust__source_principal_ids": []},
        {"trust__source_principal_ids": ["duplicate", "duplicate"]},
        {"trust__source_principal_ids": ["synthetic-independent-verifier"]},
        {"trust__source_keys": [public(kid="different-kid")]},
        {"trust__source_keys": [public(OTHER_SEED), public(OTHER_SEED)]},
        {"trust__issuer": "no-scheme"},
        {"trust__audience": "foreign"},
        {"trust__evidence_posture": "QUALIFIED_RECEIPT"},
        {"trust__key_valid_to": "2026-10-15T00:00:00Z"},
        {"revocation__expires_at": "2026-10-16T00:05:01Z"},
        {"revocation__checked_at": "2026-10-16T00:00:00"},
    ],
)
@pytest.mark.parametrize("construction", ["copied", "constructed"])
def test_invalid_copied_or_constructed_nested_configuration_fails_before_io(
    harness, changes, construction
):
    # Bypass constructors deliberately; each invocation must validate the serialized graph.
    document = harness.config.model_dump(mode="python")
    document["trust"]["verifier_key"] = harness.config.trust.verifier_key
    document["trust"]["source_keys"] = harness.config.trust.source_keys
    for path, value in changes.items():
        parent, field = path.split("__")
        if field == "source_keys":
            value = tuple(SourceKey.model_validate(key) for key in value)
        elif field == "source_principal_ids":
            value = tuple(value)
        document[parent][field] = value
    if construction == "constructed":
        trust = ControlledAssemblyVerifierTrust.model_construct(**document["trust"])
        revocation = ControlledAssemblyRevocationSnapshot.model_construct(**document["revocation"])
    else:
        trust = harness.config.trust.model_copy(update=document["trust"])
        revocation = harness.config.revocation.model_copy(update=document["revocation"])
    invalid = harness.config.model_copy(
        update={
            "trust": trust,
            "revocation": revocation,
            "reader": harness.config.reader.model_copy(update=document["reader"]),
        }
    )
    harness.verifier.configuration = invalid
    with pytest.raises(ValueError, match="COMPOSITE_NATIVE_ASSEMBLY_"):
        harness.verifier.verify_with_proof(harness.request)
    assert not harness.calls_c and not harness.signer.calls


def test_expected_observations_digest_is_deployment_owned(harness):
    configure(harness, expected_observations_digest="sha256:" + "a" * 64)
    with pytest.raises(ValueError, match="COMPOSITE_ELIGIBILITY_SOURCE_CONTENT_MISMATCH"):
        harness.verifier.verify_with_proof(harness.request)
    assert harness.calls_c and not harness.signer.calls


@pytest.mark.parametrize("change", ["raw", "capture"])
def test_valid_different_custody_with_equal_observations_cannot_reuse_original_request(
    harness, change
):
    h = harness
    records = deepcopy(h.records)
    row = next(row for row in records[("P2", "CAPTURES")] if row["role"] == "CASH")
    if change == "raw":
        # A valid later receipt completion changes bytes, not the cash fact/selection roots.
        wrapper = json.loads(base64.b64decode(row["bytes_base64"]))
        wrapper["payload"]["receipt"]["completed_at"] = "2026-10-16T00:00:01+00:00"
        raw = json.dumps(wrapper, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        row.update(
            bytes_base64=base64.b64encode(raw).decode(),
            byte_count=len(raw),
            raw_hash=hashlib.sha256(raw).hexdigest(),
            segment_hash=hashlib.sha256(raw).hexdigest(),
        )
    else:
        row["source_context"]["captured_at"] = "2026-10-16T00:00:01Z"
    h.state.alternate_records = records
    reader = CoreHttpRetainedReader(h.config.reader, h.client_c, members=h.config.financial.members)
    alternate = CoreMonthlyEligibilitySource(
        h.config.financial, reader, controlled_synthetic=True
    ).assemble(source_request(h.config.financial, h.expected))
    assert alternate.observations == h.expected
    assert alternate.native_custody.content_hash != h.assembly.native_custody.content_hash
    assert assembly_verification_request(alternate).claims_digest != h.request.claims_digest
    with pytest.raises(ValueError, match="COMPOSITE_NATIVE_ASSEMBLY_REQUEST_MISMATCH"):
        h.verifier.verify_with_proof(h.request)
    assert not h.signer.calls


def test_empty_source_key_inventory_still_checks_actual_source_principal(harness):
    configure(harness, revocation__revoked_subjects=["synthetic-enrolled-core-producer"])
    with pytest.raises(ValueError, match="ASSEMBLY_REVOKED"):
        harness.verifier.verify_with_proof(harness.request)
    assert not harness.calls_c and not harness.signer.calls


def test_interleaved_requests_do_not_exchange_proofs(harness):
    h = harness
    foreign = h.request.model_copy(update={"claims_digest": "sha256:" + "f" * 64})
    with ThreadPoolExecutor(max_workers=2) as pool:
        valid = pool.submit(h.verifier.verify_with_proof, h.request)
        invalid = pool.submit(h.verifier.verify_with_proof, foreign)
        pair = valid.result()
        with pytest.raises(ValueError, match="REQUEST_MISMATCH"):
            invalid.result()
    assert pair.receipt.request == h.request and len(h.signer.calls) == 1
    assert len(h.calls_c) == len(h.calls_a) * 2


def test_foreign_self_signed_retained_proof_does_not_enroll_fresh_trust(harness):
    from src.core.composite_eligibility.native_source_verification import (
        MonthlySourceAdmissionProof,
    )
    from tests.unit.dpm.composites.test_native_source_verification import proof_material

    _, material, _ = proof_material(OTHER_SEED)
    foreign = MonthlySourceAdmissionProof.model_validate(material)
    with pytest.raises(TypeError):
        harness.verifier.verify_with_proof(harness.request, proof=foreign)
    harness.verifier.signer = CountingSigner(OTHER_SEED)
    with pytest.raises(ValueError, match="SIGNER_MISMATCH"):
        harness.verifier.verify_with_proof(harness.request)
    assert not harness.calls_c


def test_freshly_derived_credential_id_is_checked_before_signing(harness):
    from src.infrastructure.composites.controlled_assembly_verifier import _credential

    h = harness
    result = h.verifier.verify_with_proof(h.request).proof.result
    identifier = sha(
        {
            "request_digest": sha(h.request.model_dump(mode="json")),
            "payload_digest": sha(result.model_dump(mode="json")),
        }
    )
    configure(h, revocation__revoked_credentials=[identifier])
    h.signer.calls.clear()
    with pytest.raises(ValueError, match="CREDENTIAL_REVOKED"):
        _credential(result, h.verifier.configuration, h.signer, NOW)
    assert not h.signer.calls


@pytest.mark.parametrize(
    "target", ["verifier-principal", "source-principal", "verifier-key", "source-key", "flag"]
)
def test_current_revocation_covers_principals_and_raw_keys(harness, target):
    changes = {"trust__source_keys": [public(OTHER_SEED, "synthetic-source-key")]}
    if target.endswith("principal"):
        changes["revocation__revoked_subjects"] = [
            "synthetic-independent-verifier"
            if target.startswith("verifier")
            else "synthetic-enrolled-core-producer"
        ]
    elif target.endswith("key"):
        seed = SEED if target.startswith("verifier") else OTHER_SEED
        raw = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw()
        changes["revocation__revoked_key_digests"] = ["sha256:" + hashlib.sha256(raw).hexdigest()]
    else:
        changes["trust__verifier_key"] = {**public(), "revoked": True}
    configure(harness, **changes)
    with pytest.raises(ValueError, match="ASSEMBLY_REVOKED"):
        harness.verifier.verify_with_proof(harness.request)
    assert not harness.calls_c and not harness.signer.calls


def test_distinct_source_public_inventory_is_optional_but_honored(harness):
    configure(harness, trust__source_keys=[public(OTHER_SEED, "synthetic-source-key")])
    assert harness.verifier.verify_with_proof(harness.request) is not None


@pytest.mark.parametrize(
    "time",
    [
        NOW - timedelta(microseconds=1),
        NOW + timedelta(minutes=5),
        NOW + timedelta(minutes=10),
        NOW.replace(tzinfo=None),
    ],
)
def test_current_server_clock_refuses_future_stale_expired_or_naive(harness, time):
    harness.state.now = time
    with pytest.raises(ValueError, match="COMPOSITE_NATIVE_ASSEMBLY_"):
        harness.verifier.verify_with_proof(harness.request)
    assert not harness.calls_c and not harness.signer.calls


def test_key_valid_to_equal_now_and_future_snapshot_refuse(harness):
    configure(harness, trust__key_valid_to="2026-10-16T00:00:01Z")
    harness.state.now = NOW + timedelta(seconds=1)
    with pytest.raises(ValueError, match="KEY_WINDOW"):
        harness.verifier.verify_with_proof(harness.request)
    configure(harness, revocation__checked_at="2026-10-16T00:00:02Z")
    with pytest.raises(ValueError, match="REVOCATION_WINDOW"):
        harness.verifier.verify_with_proof(harness.request)
    assert not harness.calls_c


@pytest.mark.parametrize("during", ["read", "sign", "subsecond"])
def test_expiry_during_work_withholds_pair(harness, during):
    h = harness
    if during == "read":
        h.state.mutate = lambda result, body: setattr(h.state, "now", NOW + timedelta(minutes=5))
    elif during == "sign":
        h.signer.after_sign = lambda: setattr(h.state, "now", NOW + timedelta(minutes=5))
    else:
        configure(h, revocation__expires_at="2026-10-16T00:00:00.900000Z")
        h.state.now = NOW + timedelta(microseconds=500000)
    with pytest.raises(ValueError, match="COMPOSITE_NATIVE_ASSEMBLY_"):
        h.verifier.verify_with_proof(h.request)
    assert len(h.signer.calls) == (1 if during == "sign" else 0)


def test_signer_must_match_and_bad_signature_is_never_returned(harness):
    h = harness
    h.verifier.signer = CountingSigner(OTHER_SEED)
    with pytest.raises(ValueError, match="SIGNER_MISMATCH"):
        h.verifier.verify_with_proof(h.request)
    assert not h.calls_c
    h.verifier.signer = CountingSigner(corrupt=True)
    with pytest.raises(ValueError, match="present_but_unverified"):
        h.verifier.verify_with_proof(h.request)


def test_repeated_calls_fresh_io_retained_immutability_and_no_cross_request_exchange(harness):
    h = harness
    first = h.verifier.verify_with_proof(h.request)
    count = len(h.calls_c)
    second = h.verifier.verify_with_proof(h.request)
    assert len(h.calls_c) == count * 2 and first is not second
    first.receipt.request.binding.digest = "sha256:" + "a" * 64
    first.proof.result.receipt.request.tenant_id = "changed"
    assert first.receipt == second.receipt and first.proof == second.proof
    configure(h, trust__receipt_issuer_id="another-synthetic-issuer")
    third = h.verifier.verify_with_proof(h.request)
    with pytest.raises(ValueError, match="PAIRED_RECEIPT_MISMATCH"):
        NativeAssemblyVerification(first.receipt, third.proof)
    h.state.unavailable = True
    assert h.verifier.verify_with_proof(h.request) is None
    assert not hasattr(h.verifier, "last_proof")


def test_closed_api_and_configuration_forbid_caller_proof_clock_key_and_admitted_at(harness):
    h = harness
    pair = h.verifier.verify_with_proof(h.request)
    for name, value in [
        ("proof", pair.proof),
        ("key", public(OTHER_SEED)),
        ("admitted_at", NOW),
        ("clock", lambda: NOW),
        ("configuration", h.config),
    ]:
        with pytest.raises(TypeError):
            h.verifier.verify_with_proof(h.request, **{name: value})
        with pytest.raises(ValidationError):
            ControlledAssemblyVerifierConfiguration.model_validate_json(
                json.dumps({**h.config.model_dump(mode="json"), name: "caller-value"}), strict=True
            )
    h.verifier.signer = None
    assert h.verifier.verify_with_proof(h.request) is None


def test_digest_credential_identifiers_preserve_exact_prefix_and_revocation_membership(harness):
    h = harness
    pair = h.verifier.verify_with_proof(h.request)
    identifier = decode(pair.proof.verifier_credential.split(".")[1])["jti"]
    assert len(identifier) == 71
    snapshot = h.config.revocation.model_copy(update={"revoked_credentials": (identifier,)})
    assert ControlledAssemblyRevocationSnapshot.model_validate_json(
        snapshot.model_dump_json()
    ).revoked_credentials == (identifier,)
    binding = SimpleNamespace(
        keys=(h.config.trust.verifier_key,),
        issuer=h.config.trust.issuer,
        principal_id=h.config.trust.principal_id,
        tenant_id="tenant",
        revoked_credentials=(identifier,),
        revoked_subjects=(),
        operation="verification",
        evidence_posture="SYNTHETIC_NON_CERTIFYING",
    )
    with pytest.raises(ValueError, match="revoked_principal"):
        verified_artifact(
            pair.proof.verifier_credential,
            binding=binding,
            request=h.request.model_dump(mode="json"),
            payload=pair.proof.result.model_dump(mode="json"),
            now=NOW.timestamp(),
        )
    binding.revoked_credentials = (identifier.removeprefix("sha256:"),)
    verified_artifact(
        pair.proof.verifier_credential,
        binding=binding,
        request=h.request.model_dump(mode="json"),
        payload=pair.proof.result.model_dump(mode="json"),
        now=NOW.timestamp(),
    )
    for invalid in ("x" * 129, "sha256:/illegal"):
        with pytest.raises(ValidationError):
            ControlledAssemblyRevocationSnapshot.model_validate_json(
                json.dumps(
                    {
                        **h.config.revocation.model_dump(mode="json"),
                        "revoked_credentials": [invalid],
                    }
                )
            )
