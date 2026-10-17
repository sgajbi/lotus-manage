"""Deployment admission and independent-reader composition, with no real network."""

import json
from copy import deepcopy

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.api.composition import composite_source_service as composition
from src.api.services.composite_subject_requests import SubjectRequest
from src.infrastructure import source_http_clients as clients
from src.infrastructure.composites import native_assembly_configuration as native
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.infrastructure.composites.core_financial_sources import registry_binding
from tests.integration.dpm.composites.native_source_provider import (
    CREDENTIALS,
    MONTHLY_SEED,
    deployment_material,
)
from tests.unit.dpm.infrastructure.test_core_source_reader import response, source_request


@pytest.fixture
def deployment(monkeypatch, tmp_path):
    material, records, roots, expected = deployment_material(tmp_path / "synthetic-key")
    for name, secret in CREDENTIALS.items():
        monkeypatch.setenv(name, secret)
    for setting in (
        "DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON",
        "DPM_COMPOSITE_ATTESTATION_VERIFICATION_JSON",
    ):
        monkeypatch.delenv(setting, raising=False)
    monkeypatch.setenv("DPM_COMPOSITE_SOURCES_JSON", json.dumps(material))
    monkeypatch.setattr(native, "read_custody_file", lambda *_args, **_kwargs: MONTHLY_SEED)
    clients.close_shared_source_http_clients()
    yield material, records, roots, expected
    clients.close_shared_source_http_clients()


def test_native_document_is_closed_and_preserves_independent_pins(deployment):
    material, _, _, expected = deployment
    configuration = native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))
    assert configuration.verification.trust.source_keys == ()
    assert (
        configuration.verification.expected_observations_digest
        == (material["verification"]["expected_observations_digest"])
    )
    assert configuration.financial.month == expected.month
    assert "synthetic-assembly-only" not in configuration.model_dump_json()
    assert configuration.reader.credential_env != configuration.verification.reader.credential_env


def test_authored_postgres_history_matches_independent_economics(deployment):
    from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
    from tests.integration.dpm.composites.test_core_financial_sources_postgres import (
        seed_recurring_history,
    )

    material, _, _, expected = deployment
    configuration = native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))
    repository = InMemoryDpmCompositeRepository()
    universe, approval = seed_recurring_history(repository, configuration, expected)
    result = evaluate_monthly_eligibility(
        approval.proposal.policy,
        expected,
        evaluated_at="2026-10-17T00:00:00.000000Z",
        universe_content_hash=universe.content_hash,
    )
    assert result.official_activation == "UNAVAILABLE"
    assert result.population_verification == "UNVERIFIED"
    assert [portfolio.portfolio_id for portfolio in result.portfolios] == ["P1", "P2", "P3"]
    for portfolio in result.portfolios:
        flow = portfolio.assessments[0]
        assert (flow.numerator, flow.denominator, flow.ratio, flow.outcome) == (
            "-10.00",
            "100.00",
            "0.1",
            "FAIL",
        )
    assert universe.source_products[1].owner_service == "lotus-manage"


@pytest.mark.parametrize(
    "path,value",
    [
        ("adapter", "CONTROLLED_SYNTHETIC_NATIVE_ASSEMBLY_V1"),
        ("financial.month", "2025-02"),
        ("reader.tenant_id", "foreign"),
        ("reader.authentication_mode", "bearer"),
        ("reader.endpoint", "https://foreign.test"),
        ("reader.credential_env", "FOREIGN_REFERENCE"),
        ("reader.allow_local_http", True),
        ("verification.reader.authentication_mode", "bearer"),
        ("verification.reader.credential_env", "FOREIGN_REFERENCE"),
        ("verification.reader.endpoint", "https://foreign.test"),
        ("assembly_authorization.tenant_id", "foreign"),
        ("assembly_authorization.service_identity", "monthly-verifier"),
        ("assembly_authorization.capabilities", ["source_data.portfolio_historical_registry.read"]),
        ("verification_authorization.origin", "https://foreign.test"),
        ("verification_authorization.credential_env", "FOREIGN_REFERENCE"),
        ("verifier_key_file", "relative-secret"),
        ("secret", "forbidden"),
        ("verification.trust.source_keys", None),
        ("timeout_seconds", 31),
    ],
)
def test_mismatched_or_secret_policy_refuses_before_clients(deployment, monkeypatch, path, value):
    material = deepcopy(deployment[0])
    fields = path.split(".")
    target = material
    for name in fields[:-1]:
        target = target[name]
    target[fields[-1]] = value
    monkeypatch.setenv("DPM_COMPOSITE_SOURCES_JSON", json.dumps(material))
    monkeypatch.setattr(
        composition,
        "get_partitioned_source_http_client",
        lambda *_args, **_kwargs: pytest.fail("invalid policy created client"),
    )
    with pytest.raises(ValueError):
        composition.build_composite_subject_service(InMemoryDpmCompositeRepository())


@pytest.mark.parametrize(
    "field,value",
    [
        ("operation", "candidates"),
        ("tenant_id", "foreign"),
        ("evidence_posture", "QUALIFIED_RECEIPT"),
        ("principal_id", "synthetic-core-producer"),
        ("principal_id", "synthetic-monthly-verifier"),
        ("verification_purposes", ["COMPOSITE_MONTHLY_SOURCE_CUT"]),
    ],
)
def test_policy_channel_cannot_replace_native_or_institutional_authorities(tmp_path, field, value):
    material, *_ = deployment_material(tmp_path / "key", policy=True)
    material["policy_verification"]["bindings"][0][field] = value
    with pytest.raises(ValueError):
        native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))


def test_policy_channel_cannot_share_any_enrolled_key(tmp_path):
    material, *_ = deployment_material(tmp_path / "key", policy=True)
    binding = material["policy_verification"]["bindings"][0]
    material["verification"]["trust"]["source_keys"] = binding["keys"]
    with pytest.raises(ValueError, match="POLICY_CHANNEL_NOT_SEPARATE"):
        native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))


def test_policy_channel_cannot_reuse_verifier_key_under_a_distinct_key_id(tmp_path):
    material, *_ = deployment_material(tmp_path / "key", policy=True)
    binding = material["policy_verification"]["bindings"][0]
    verifier_key = material["verification"]["trust"]["verifier_key"]
    binding["keys"] = [{"kid": "separate-policy-key-id", "x": verifier_key["x"]}]
    with pytest.raises(ValueError, match="POLICY_CHANNEL_NOT_SEPARATE"):
        native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))


def test_reader_authorization_refuses_before_invalid_signer_path(deployment):
    material = deepcopy(deployment[0])
    material["reader"]["credential_env"] = "FOREIGN_REFERENCE"
    material["verifier_key_file"] = "relative-path"
    with pytest.raises(ValueError, match="READER_AUTH_CONFIGURATION_MISMATCH"):
        native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))


@pytest.mark.parametrize("missing", ["assembly", "verification", "signer"])
@pytest.mark.parametrize("value", [None, "", "  "])
def test_missing_native_custody_keeps_subject_unreserved(deployment, monkeypatch, missing, value):
    material = deployment[0]
    if missing == "signer":

        def absent(*_args, **_kwargs):
            raise ValueError("COMPOSITE_NATIVE_CUSTODY_UNAVAILABLE")

        monkeypatch.setattr(native, "read_custody_file", absent)
    else:
        name = material[f"{missing}_authorization"]["credential_env"]
        if value is None:
            monkeypatch.delenv(name)
        else:
            monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        composition,
        "get_partitioned_source_http_client",
        lambda *_args, **_kwargs: pytest.fail("unavailable policy created client"),
    )
    repository = InMemoryDpmCompositeRepository()
    service = composition.build_composite_subject_service(repository)
    config = native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))
    key = ("tenant", "composite", "v1", "unreserved")
    with pytest.raises(ValueError, match="COMPOSITE_SUBJECT_UNIVERSE_UNAVAILABLE"):
        service.create(
            key,
            "maker",
            SubjectRequest(
                display_name="Synthetic native",
                strategy_code="strategy",
                reporting_currency="USD",
                inception_date="2025-01-01",
                termination_date=None,
                eligibility_policy_version="policy",
                month="2025-01",
                registry_binding=registry_binding(config.financial),
                correlation_id="test",
            ),
        )
    assert repository.get_eligibility_subject(key=key) is None
    monthly = composition.build_composite_monthly_service(repository)
    assert type(monthly.source).__name__ == "UnavailableMonthlyEligibilitySource"


@pytest.mark.parametrize(
    "raw,error", [(bytes(range(32, 64)), "SIGNER_MISMATCH"), (b"short", "SIGNER_SIZE_INVALID")]
)
def test_signer_is_deployment_owned_and_never_generated(deployment, monkeypatch, raw, error):
    monkeypatch.setattr(native, "read_custody_file", lambda *_args, **_kwargs: raw)
    with pytest.raises(ValueError, match=error):
        composition.build_composite_subject_service(InMemoryDpmCompositeRepository())


def test_unsafe_signer_custody_refuses_instead_of_disabling(deployment, monkeypatch):
    def unsafe(*_args, **_kwargs):
        raise ValueError("COMPOSITE_NATIVE_SECRET_READ_ONLY_REQUIRED")

    monkeypatch.setattr(native, "read_custody_file", unsafe)
    with pytest.raises(ValueError, match="SECRET_READ_ONLY_REQUIRED"):
        composition.build_composite_subject_service(InMemoryDpmCompositeRepository())


def test_factories_own_distinct_fresh_readers_and_reuse_only_managed_clients(
    deployment, monkeypatch
):
    material, records, roots, expected = deployment
    calls, constructed = [], []
    real_client = httpx.Client
    state = {"deny": set()}

    def handler(request):
        role = request.headers["X-Actor-Id"]
        assert "Authorization" not in request.headers
        assert request.headers["X-Service-Identity"] == "lotus-manage"
        calls.append((role, request.headers["X-Correlation-Id"], json.loads(request.content)))
        return (
            httpx.Response(503)
            if role in state["deny"]
            else httpx.Response(200, json=response(request, records, roots))
        )

    def client_factory(**kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        client = real_client(transport=httpx.MockTransport(handler), **kwargs)
        constructed.append(client)
        return client

    monkeypatch.setattr(clients.httpx, "Client", client_factory)
    repository = InMemoryDpmCompositeRepository()
    subject = composition.build_composite_subject_service(repository)
    monthly = composition.build_composite_monthly_service(repository)
    assert len(constructed) == 2
    assert subject.observations.reader is not monthly.source.reader
    assert subject.observations.verifier is not monthly.source.verifier
    assert subject.observations.reader.client is monthly.source.reader.client
    assert subject.observations.reader.client is not subject.observations.verifier.client
    assert type(subject.verifier).__name__ == "UnavailableCompositeEvidenceVerifier"
    assert type(subject.historical_admission).__name__ == "UnavailableHistoricalPolicyAdmission"
    request = source_request(subject.observations.configuration, expected)
    first = subject.observations.resolve(request)
    assert first.observations == expected
    evidence = first.source_assembly_evidence
    assert evidence.assembly.product_version == "v2" and evidence.native_proof is not None
    assert evidence.verification.posture == "SYNTHETIC_NON_CERTIFYING"
    roles = [call[0] for call in calls]
    assert roles.count("synthetic-assembly") == roles.count("synthetic-verification") > 0
    assert len({call[1] for call in calls}) == len(calls)
    count = len(calls)
    assert monthly.source.resolve(request).observations == expected
    assert len(calls) == count * 2
    state["deny"].add("synthetic-verification")
    assert subject.observations.resolve(request).observations is None
    assert not hasattr(subject.observations.verifier, "last_proof")
    clients.close_shared_source_http_clients()
    assert all(client.is_closed for client in constructed)
    assert (
        native.native_monthly_signer(
            native.NativeAssemblyConfiguration.model_validate_json(json.dumps(material))
        )
        .public_key()
        .public_bytes_raw()
        == Ed25519PrivateKey.from_private_bytes(MONTHLY_SEED).public_key().public_bytes_raw()
    )
